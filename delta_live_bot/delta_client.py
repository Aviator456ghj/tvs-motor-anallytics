"""
Minimal REST client for Delta Exchange India (api.india.delta.exchange).

Signing scheme per Delta's docs: HMAC-SHA256 over
    method + timestamp + request_path + query_string + body
using the API secret, hex-digested, sent as the `signature` header
alongside `api-key` and `timestamp`.

The exact historical-candles path varies across cached copies of Delta's
docs (some show /v2/history/candles, others /v2/candles). `selftest()`
hits the live API directly and tells you which one actually works on
your account before the bot relies on it for anything - don't trust the
hardcoded CANDLE_PATHS list, trust what selftest() reports back.
"""
import hashlib
import hmac
import json
import time

import requests

from config import DELTA_BASE_URL, DELTA_API_KEY, DELTA_API_SECRET

CANDLE_PATHS = ["/v2/history/candles", "/v2/candles"]


class DeltaClient:
    def __init__(self, base_url=DELTA_BASE_URL, api_key=DELTA_API_KEY, api_secret=DELTA_API_SECRET):
        self.base_url = base_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "tvs-motor-anallytics-bot/1.0"})

    def _sign(self, method, path, query_string="", body=""):
        timestamp = str(int(time.time()))
        prehash = method + timestamp + path + query_string + body
        signature = hmac.new(self.api_secret.encode(), prehash.encode(), hashlib.sha256).hexdigest()
        return timestamp, signature

    def _request(self, method, path, params=None, body=None, auth=False):
        query_string = ""
        if params:
            query_string = "?" + "&".join(f"{k}={v}" for k, v in params.items())
        body_str = json.dumps(body) if body else ""
        url = self.base_url + path + query_string

        headers = {}
        if auth:
            timestamp, signature = self._sign(method, path, query_string, body_str)
            headers.update({
                "api-key": self.api_key,
                "signature": signature,
                "timestamp": timestamp,
                "Content-Type": "application/json",
            })

        resp = self.session.request(method, url, headers=headers, data=body_str if body_str else None, timeout=15)
        return resp

    # ---- public, unauthenticated ----

    def get_products(self):
        return self._request("GET", "/v2/products")

    def get_candles(self, symbol, resolution, start, end):
        """start/end are unix seconds. Tries each known candle path and
        returns the first one that responds with HTTP 200."""
        last_resp = None
        for path in CANDLE_PATHS:
            resp = self._request("GET", path, params={
                "symbol": symbol, "resolution": resolution, "start": start, "end": end,
            })
            last_resp = resp
            if resp.status_code == 200:
                return resp, path
        return last_resp, None

    # ---- authenticated ----

    def get_product(self, symbol):
        """Returns the product dict for `symbol` from /v2/products, or None.
        Needed at runtime (not hardcoded) for contract_value, since that
        convention varies by product and must be confirmed against the live
        API before it's used to size a real order."""
        resp = self.get_products()
        if resp.status_code != 200:
            return None
        for product in resp.json().get("result", []):
            if product.get("symbol") == symbol:
                return product
        return None

    def get_wallet_balances(self):
        return self._request("GET", "/v2/wallet/balances", auth=True)

    def get_positions(self, product_id):
        return self._request("GET", "/v2/positions", params={"product_id": product_id}, auth=True)

    def place_order(self, product_id, side, size, order_type="market_order",
                     limit_price=None, bracket_stop_loss_price=None, bracket_take_profit_price=None):
        body = {
            "product_id": product_id,
            "side": side,
            "size": size,
            "order_type": order_type,
        }
        if limit_price is not None:
            body["limit_price"] = str(limit_price)
        if bracket_stop_loss_price is not None:
            body["bracket_stop_loss_price"] = str(bracket_stop_loss_price)
            body["bracket_stop_loss_limit_price"] = str(bracket_stop_loss_price)
        if bracket_take_profit_price is not None:
            body["bracket_take_profit_price"] = str(bracket_take_profit_price)
            body["bracket_take_profit_limit_price"] = str(bracket_take_profit_price)
        return self._request("POST", "/v2/orders", body=body, auth=True)


def selftest(client):
    """Hits the real API to confirm which assumed endpoints actually work
    on this account, before the bot trusts any of them for live trading."""
    report = {}

    r = client.get_products()
    report["products"] = (r.status_code, r.text[:300])

    now = int(time.time())
    r, working_path = client.get_candles("BTCUSD", "1d", now - 30 * 86400, now)
    report["candles"] = (working_path, r.status_code if r is not None else None, r.text[:300] if r is not None else None)

    if client.api_key and client.api_secret:
        r = client.get_wallet_balances()
        report["wallet_balances"] = (r.status_code, r.text[:300])
    else:
        report["wallet_balances"] = "skipped - no credentials set"

    return report


if __name__ == "__main__":
    c = DeltaClient()
    for k, v in selftest(c).items():
        print(f"{k}: {v}")

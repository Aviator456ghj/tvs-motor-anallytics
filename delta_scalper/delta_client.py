"""Minimal REST client for Delta Exchange India (v2 API).

Public endpoints need no auth. Private endpoints are signed with
HMAC-SHA256 over: method + timestamp + path + query_string + body.
Docs: https://docs.delta.exchange
"""
import hashlib
import hmac
import json
import logging
import time

import requests

log = logging.getLogger("delta.client")


class DeltaClient:
    def __init__(self, base_url: str, api_key: str = "", api_secret: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "delta-scalper/1.0"

    # ---------- signing ----------

    def _signed_headers(self, method: str, path: str, query: str, body: str) -> dict:
        ts = str(int(time.time()))
        msg = method + ts + path + query + body
        sig = hmac.new(
            self.api_secret.encode(), msg.encode(), hashlib.sha256
        ).hexdigest()
        return {
            "api-key": self.api_key,
            "timestamp": ts,
            "signature": sig,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, params: dict | None = None,
                 body: dict | None = None, auth: bool = False, retries: int = 3):
        query = ""
        if params:
            query = "?" + "&".join(f"{k}={v}" for k, v in params.items())
        payload = json.dumps(body, separators=(",", ":")) if body else ""
        url = self.base_url + path + query
        headers = (
            self._signed_headers(method, path, query, payload) if auth else {}
        )
        last_err = None
        for attempt in range(retries):
            try:
                r = self.session.request(
                    method, url, data=payload or None, headers=headers, timeout=30
                )
                if r.status_code == 429:
                    wait = 2 ** attempt
                    log.warning("rate limited, sleeping %ss", wait)
                    time.sleep(wait)
                    continue
                data = r.json()
                if not data.get("success", True):
                    raise RuntimeError(f"API error {r.status_code}: {data}")
                r.raise_for_status()
                return data.get("result", data)
            except (requests.RequestException, ValueError) as e:
                last_err = e
                time.sleep(2 ** attempt)
        raise RuntimeError(f"request failed after {retries} retries: {last_err}")

    # ---------- public ----------

    def get_product(self, symbol: str) -> dict:
        return self._request("GET", f"/v2/products/{symbol}")

    def get_ticker(self, symbol: str) -> dict:
        return self._request("GET", f"/v2/tickers/{symbol}")

    def get_candles(self, symbol: str, resolution: str, start: int, end: int) -> list:
        return self._request(
            "GET",
            "/v2/history/candles",
            params={
                "resolution": resolution,
                "symbol": symbol,
                "start": start,
                "end": end,
            },
        )

    # ---------- private ----------

    def get_balances(self) -> list:
        return self._request("GET", "/v2/wallet/balances", auth=True)

    def get_positions(self, product_id: int) -> dict:
        return self._request(
            "GET", "/v2/positions", params={"product_id": product_id}, auth=True
        )

    def place_order(self, product_id: int, side: str, size: int,
                    order_type: str = "limit_order", limit_price: str | None = None,
                    time_in_force: str = "gtc",
                    bracket_stop_loss_price: str | None = None,
                    bracket_take_profit_price: str | None = None) -> dict:
        body = {
            "product_id": product_id,
            "side": side,
            "size": size,
            "order_type": order_type,
        }
        if limit_price is not None:
            body["limit_price"] = limit_price
            body["time_in_force"] = time_in_force
        if bracket_stop_loss_price:
            body["bracket_stop_loss_price"] = bracket_stop_loss_price
            body["bracket_stop_loss_limit_price"] = bracket_stop_loss_price
            body["bracket_stop_trigger_method"] = "mark_price"
        if bracket_take_profit_price:
            body["bracket_take_profit_price"] = bracket_take_profit_price
            body["bracket_take_profit_limit_price"] = bracket_take_profit_price
        return self._request("POST", "/v2/orders", body=body, auth=True)

    def cancel_order(self, product_id: int, order_id: int) -> dict:
        return self._request(
            "DELETE", "/v2/orders",
            body={"id": order_id, "product_id": product_id}, auth=True,
        )

    def get_live_orders(self, product_id: int) -> list:
        return self._request(
            "GET", "/v2/orders",
            params={"product_id": product_id, "state": "open"}, auth=True,
        )

    def close_position(self, product_id: int, size: int, side: str) -> dict:
        """Market-close `size` contracts (side is the closing side)."""
        return self.place_order(
            product_id, side, size, order_type="market_order"
        )

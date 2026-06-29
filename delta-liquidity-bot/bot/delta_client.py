"""
Delta Exchange REST client.

Implements the v2 HMAC-SHA256 auth scheme:
    signature = hex( HMAC_SHA256( api_secret, method + timestamp + path + query + body ) )
with headers: api-key, signature, timestamp, User-Agent.

Docs: https://docs.delta.exchange  (India base: https://api.india.delta.exchange)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Optional

import requests

USER_AGENT = "delta-liquidity-bot/1.0"


class DeltaError(RuntimeError):
    """Raised when the exchange returns an error payload or a bad HTTP status."""


class DeltaClient:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://api.india.delta.exchange",
        timeout: int = 15,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    # ------------------------------------------------------------------ auth
    def _sign(self, method: str, path: str, query: str, body: str) -> dict[str, str]:
        timestamp = str(int(time.time()))
        message = method + timestamp + path + query + body
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return {
            "api-key": self.api_key,
            "signature": signature,
            "timestamp": timestamp,
        }

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        body: Optional[dict[str, Any]] = None,
        auth: bool = False,
    ) -> dict[str, Any]:
        params = params or {}
        # Build the query string EXACTLY as it will be sent, and sign that string.
        query = ""
        if params:
            query = "?" + "&".join(f"{k}={v}" for k, v in params.items())
        payload = json.dumps(body, separators=(",", ":")) if body is not None else ""

        headers: dict[str, str] = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if auth:
            headers.update(self._sign(method, path, query, payload))

        url = self.base_url + path + query
        resp = self.session.request(
            method,
            url,
            data=payload if body is not None else None,
            headers=headers,
            timeout=self.timeout,
        )
        try:
            data = resp.json()
        except ValueError:
            raise DeltaError(f"Non-JSON response {resp.status_code}: {resp.text[:300]}")

        if resp.status_code >= 400 or (isinstance(data, dict) and data.get("success") is False):
            raise DeltaError(f"{method} {path} -> {resp.status_code}: {json.dumps(data)[:400]}")
        return data

    # ---------------------------------------------------------------- public
    def get_candles(self, symbol: str, resolution: str, start: int, end: int) -> list[dict]:
        """
        Historical OHLC. start/end are UNIX seconds. Returns a list of candles
        sorted ascending by time, each: {time, open, high, low, close, volume}.
        """
        data = self._request(
            "GET",
            "/v2/history/candles",
            params={"symbol": symbol, "resolution": resolution, "start": start, "end": end},
        )
        candles = data.get("result", []) or []
        for c in candles:
            for k in ("open", "high", "low", "close", "volume"):
                if k in c and c[k] is not None:
                    c[k] = float(c[k])
        candles.sort(key=lambda c: c["time"])
        return candles

    def get_product(self, symbol: str) -> dict:
        """Product metadata (contract_value, tick_size, product_id, lot/min size)."""
        data = self._request("GET", f"/v2/products/{symbol}")
        return data.get("result", data)

    # ----------------------------------------------------------- private
    def get_wallet(self) -> list[dict]:
        return self._request("GET", "/v2/wallet/balances", auth=True).get("result", [])

    def get_positions(self, product_id: Optional[int] = None) -> list[dict]:
        params = {"product_id": product_id} if product_id else None
        data = self._request("GET", "/v2/positions/margined", params=params, auth=True)
        result = data.get("result", [])
        return result if isinstance(result, list) else [result]

    def place_bracket_market_order(
        self,
        product_id: int,
        size: int,
        side: str,  # "buy" | "sell"
        stop_loss_price: float,
        take_profit_price: float,
        stop_trigger_method: str = "mark_price",
    ) -> dict:
        """
        Market entry with an attached bracket (stop-loss + take-profit).
        Prices are passed as strings, which Delta expects.
        """
        body = {
            "product_id": product_id,
            "size": size,
            "side": side,
            "order_type": "market_order",
            "bracket_stop_loss_price": str(stop_loss_price),
            "bracket_take_profit_price": str(take_profit_price),
            "bracket_stop_trigger_method": stop_trigger_method,
        }
        return self._request("POST", "/v2/orders", body=body, auth=True).get("result", {})

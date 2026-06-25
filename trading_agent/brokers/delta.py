"""Delta Exchange India adapter.

Market data via Delta's public websocket; trading via the signed REST API.
Uses only stdlib + websocket-client + requests so it has no heavy SDK lock-in.

API docs: https://docs.delta.exchange/
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from typing import Callable

import requests
import websocket  # websocket-client

from ..utils.logging import get_logger
from .base import Broker, Order, OrderBook, Position, Side, Tick

log = get_logger("delta")

WS_URL = "wss://socket.india.delta.exchange"


class DeltaBroker(Broker):
    name = "delta"

    def __init__(self, api_key: str, api_secret: str,
                 base_url: str = "https://api.india.delta.exchange"):
        self._key = api_key
        self._secret = api_secret
        self._base = base_url.rstrip("/")
        self._ws: websocket.WebSocketApp | None = None
        self._ws_thread: threading.Thread | None = None
        self._product_ids: dict[str, int] = {}

    # ---- auth helpers ----
    def _signature(self, method: str, path: str, body: str, ts: str) -> str:
        message = method + ts + path + body
        return hmac.new(self._secret.encode(), message.encode(), hashlib.sha256).hexdigest()

    def _headers(self, method: str, path: str, body: str = "") -> dict:
        ts = str(int(time.time()))
        return {
            "api-key": self._key,
            "timestamp": ts,
            "signature": self._signature(method, path, body, ts),
            "Content-Type": "application/json",
            "User-Agent": "rule-scalper/0.1",
        }

    def connect(self) -> None:
        # Map symbols -> product ids (needed for order placement).
        try:
            r = requests.get(f"{self._base}/v2/products", timeout=10)
            r.raise_for_status()
            for p in r.json().get("result", []):
                self._product_ids[p["symbol"]] = p["id"]
            log.info("Delta connected, %d products loaded.", len(self._product_ids))
        except requests.RequestException as e:
            log.error("Delta product load failed: %s", e)

    # ---- market data ----
    def subscribe(self, symbols, on_tick, on_book) -> None:
        def on_open(ws):
            sub = {
                "type": "subscribe",
                "payload": {"channels": [
                    {"name": "v2/ticker", "symbols": symbols},
                    {"name": "l2_orderbook", "symbols": symbols},
                ]},
            }
            ws.send(json.dumps(sub))
            log.info("Delta subscribed: %s", symbols)

        def on_message(ws, raw):
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                return
            mtype = msg.get("type")
            if mtype == "v2/ticker":
                price = float(msg.get("mark_price") or msg.get("close") or 0)
                if price:
                    on_tick(Tick(
                        symbol=msg.get("symbol", ""), price=price, timestamp=time.time(),
                        bid=float(msg.get("best_bid") or 0),
                        ask=float(msg.get("best_ask") or 0),
                        volume=float(msg.get("volume") or 0),
                    ))
            elif mtype == "l2_orderbook":
                on_book(OrderBook(
                    symbol=msg.get("symbol", ""),
                    bids=[(float(b["limit_price"]), float(b["size"])) for b in msg.get("buy", [])],
                    asks=[(float(a["limit_price"]), float(a["size"])) for a in msg.get("sell", [])],
                    timestamp=time.time(),
                ))

        def on_error(ws, err):
            log.warning("Delta ws error: %s", err)

        def on_close(ws, code, reason):
            log.warning("Delta ws closed (%s). Reconnecting in 3s...", code)
            time.sleep(3)
            self.subscribe(symbols, on_tick, on_book)

        self._ws = websocket.WebSocketApp(
            WS_URL, on_open=on_open, on_message=on_message,
            on_error=on_error, on_close=on_close,
        )
        self._ws_thread = threading.Thread(target=self._ws.run_forever, daemon=True)
        self._ws_thread.start()

    # ---- trading ----
    def place_order(self, order: Order) -> Order:
        product_id = self._product_ids.get(order.symbol)
        if product_id is None:
            log.error("Unknown Delta symbol %s", order.symbol)
            order.status = "REJECTED"
            return order

        payload = {
            "product_id": product_id,
            "size": int(order.quantity),
            "side": "buy" if order.side is Side.BUY else "sell",
            "order_type": "market_order" if order.order_type == "MARKET" else "limit_order",
        }
        if order.order_type != "MARKET":
            payload["limit_price"] = str(order.price)

        body = json.dumps(payload, separators=(",", ":"))
        path = "/v2/orders"
        try:
            r = requests.post(self._base + path, data=body,
                              headers=self._headers("POST", path, body), timeout=10)
            r.raise_for_status()
            res = r.json().get("result", {})
            order.broker_order_id = str(res.get("id", ""))
            order.status = res.get("state", "open").upper()
            order.filled_price = float(res.get("average_fill_price") or order.price or 0)
            log.info("Delta order ok: %s", order.broker_order_id)
        except requests.RequestException as e:
            log.error("Delta order failed: %s", e)
            order.status = "REJECTED"
        return order

    def close_position(self, position: Position) -> Order:
        return self.place_order(Order(
            symbol=position.symbol, side=position.side.opposite,
            quantity=position.quantity, order_type="MARKET",
        ))

    def get_positions(self) -> list[Position]:
        path = "/v2/positions/margined"
        try:
            r = requests.get(self._base + path, headers=self._headers("GET", path), timeout=10)
            r.raise_for_status()
            out = []
            for p in r.json().get("result", []):
                size = float(p.get("size") or 0)
                if size == 0:
                    continue
                out.append(Position(
                    symbol=p.get("product_symbol", ""),
                    side=Side.BUY if size > 0 else Side.SELL,
                    quantity=abs(size),
                    entry_price=float(p.get("entry_price") or 0),
                    broker=self.name,
                ))
            return out
        except requests.RequestException as e:
            log.error("Delta positions failed: %s", e)
            return []

    def disconnect(self) -> None:
        if self._ws:
            self._ws.close()

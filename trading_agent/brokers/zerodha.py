"""Zerodha Kite adapter using the official kiteconnect SDK.

Market data via KiteTicker (websocket); trading via KiteConnect REST.
Kite requires a daily access token from the login flow - see README.

Docs: https://kite.trade/docs/connect/v3/
"""

from __future__ import annotations

import threading
import time
from typing import Callable

from ..utils.logging import get_logger
from .base import Broker, Order, OrderBook, Position, Side, Tick

log = get_logger("zerodha")


class ZerodhaBroker(Broker):
    name = "zerodha"

    def __init__(self, api_key: str, api_secret: str, access_token: str,
                 exchange: str = "NFO"):
        self._api_key = api_key
        self._api_secret = api_secret
        self._access_token = access_token
        self._exchange = exchange
        self._kite = None
        self._ticker = None
        self._token_to_symbol: dict[int, str] = {}
        self._symbol_to_token: dict[str, int] = {}

    def connect(self) -> None:
        from kiteconnect import KiteConnect  # lazy import so paper mode needs no SDK

        self._kite = KiteConnect(api_key=self._api_key)
        if self._access_token:
            self._kite.set_access_token(self._access_token)
            log.info("Kite connected.")
        else:
            log.warning("No KITE_ACCESS_TOKEN set. Complete the login flow first "
                        "(see README). Login URL: %s", self._kite.login_url())

    def _resolve_tokens(self, symbols: list[str]) -> None:
        """Map tradingsymbols to instrument tokens via the instruments dump."""
        try:
            for inst in self._kite.instruments(self._exchange):
                if inst["tradingsymbol"] in symbols:
                    tok = inst["instrument_token"]
                    self._symbol_to_token[inst["tradingsymbol"]] = tok
                    self._token_to_symbol[tok] = inst["tradingsymbol"]
        except Exception as e:  # noqa: BLE001 - SDK raises broad errors
            log.error("Kite instrument resolve failed: %s", e)

    def subscribe(self, symbols, on_tick, on_book) -> None:
        from kiteconnect import KiteTicker

        self._resolve_tokens(symbols)
        tokens = list(self._token_to_symbol.keys())
        if not tokens:
            log.error("No Kite tokens resolved for %s", symbols)
            return

        ticker = KiteTicker(self._api_key, self._access_token)

        def on_ticks(ws, ticks):
            for t in ticks:
                sym = self._token_to_symbol.get(t["instrument_token"], "")
                price = float(t.get("last_price") or 0)
                depth = t.get("depth") or {}
                buy = depth.get("buy") or []
                sell = depth.get("sell") or []
                if price:
                    on_tick(Tick(
                        symbol=sym, price=price, timestamp=time.time(),
                        bid=float(buy[0]["price"]) if buy else 0.0,
                        ask=float(sell[0]["price"]) if sell else 0.0,
                        volume=float(t.get("volume_traded") or 0),
                    ))
                if buy or sell:
                    on_book(OrderBook(
                        symbol=sym,
                        bids=[(float(b["price"]), float(b["quantity"])) for b in buy],
                        asks=[(float(a["price"]), float(a["quantity"])) for a in sell],
                        timestamp=time.time(),
                    ))

        def on_connect(ws, response):
            ws.subscribe(tokens)
            ws.set_mode(ws.MODE_FULL, tokens)  # FULL = includes market depth
            log.info("Kite ticker subscribed: %s", symbols)

        def on_close(ws, code, reason):
            log.warning("Kite ticker closed (%s): %s", code, reason)

        ticker.on_ticks = on_ticks
        ticker.on_connect = on_connect
        ticker.on_close = on_close
        self._ticker = ticker
        threading.Thread(target=ticker.connect, kwargs={"threaded": True}, daemon=True).start()

    def place_order(self, order: Order) -> Order:
        try:
            oid = self._kite.place_order(
                variety=self._kite.VARIETY_REGULAR,
                exchange=self._exchange,
                tradingsymbol=order.symbol,
                transaction_type=(self._kite.TRANSACTION_TYPE_BUY if order.side is Side.BUY
                                  else self._kite.TRANSACTION_TYPE_SELL),
                quantity=int(order.quantity),
                product=self._kite.PRODUCT_MIS,            # intraday for scalping
                order_type=(self._kite.ORDER_TYPE_MARKET if order.order_type == "MARKET"
                            else self._kite.ORDER_TYPE_LIMIT),
                price=order.price if order.order_type != "MARKET" else None,
            )
            order.broker_order_id = str(oid)
            order.status = "OPEN"
            log.info("Kite order ok: %s", oid)
        except Exception as e:  # noqa: BLE001
            log.error("Kite order failed: %s", e)
            order.status = "REJECTED"
        return order

    def close_position(self, position: Position) -> Order:
        return self.place_order(Order(
            symbol=position.symbol, side=position.side.opposite,
            quantity=position.quantity, order_type="MARKET",
        ))

    def get_positions(self) -> list[Position]:
        try:
            net = self._kite.positions().get("net", [])
            out = []
            for p in net:
                qty = int(p.get("quantity") or 0)
                if qty == 0:
                    continue
                out.append(Position(
                    symbol=p.get("tradingsymbol", ""),
                    side=Side.BUY if qty > 0 else Side.SELL,
                    quantity=abs(qty),
                    entry_price=float(p.get("average_price") or 0),
                    broker=self.name,
                ))
            return out
        except Exception as e:  # noqa: BLE001
            log.error("Kite positions failed: %s", e)
            return []

    def disconnect(self) -> None:
        if self._ticker:
            try:
                self._ticker.close()
            except Exception:  # noqa: BLE001
                pass

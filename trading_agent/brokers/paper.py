"""Paper-trading wrapper.

Wraps a *real* broker adapter so market data still streams live, but orders
are simulated (filled at the latest price) instead of being sent to the
exchange. This is the default mode - validate the strategy before risking money.
"""

from __future__ import annotations

import itertools
import time
from typing import Callable

from ..utils.logging import get_logger
from .base import Broker, Order, OrderBook, Position, Side, Tick

log = get_logger("paper")


class PaperBroker(Broker):
    def __init__(self, real_broker: Broker):
        self._real = real_broker
        self.name = f"{real_broker.name}-paper"
        self._last_price: dict[str, float] = {}
        self._positions: dict[str, Position] = {}
        self._ids = itertools.count(1)

    def connect(self) -> None:
        # Only connect for market data; no trading credentials are exercised.
        self._real.connect()
        log.info("Paper mode active for %s - orders are SIMULATED.", self._real.name)

    def subscribe(self, symbols, on_tick, on_book) -> None:
        def tick_proxy(t: Tick):
            self._last_price[t.symbol] = t.price
            on_tick(t)

        self._real.subscribe(symbols, tick_proxy, on_book)

    def place_order(self, order: Order) -> Order:
        fill = order.price or self._last_price.get(order.symbol, 0.0)
        order.broker_order_id = f"PAPER-{next(self._ids)}"
        order.status = "FILLED"
        order.filled_price = fill

        pos = self._positions.get(order.symbol)
        if pos is None:
            self._positions[order.symbol] = Position(
                symbol=order.symbol, side=order.side, quantity=order.quantity,
                entry_price=fill, broker=self.name,
            )
        else:  # closing / reducing
            if order.side == pos.side.opposite:
                self._positions.pop(order.symbol, None)
        log.info("[PAPER] %s %s x%.4f @ %.2f", order.side.value, order.symbol,
                 order.quantity, fill)
        return order

    def close_position(self, position: Position) -> Order:
        return self.place_order(Order(
            symbol=position.symbol, side=position.side.opposite,
            quantity=position.quantity, order_type="MARKET",
        ))

    def get_positions(self) -> list[Position]:
        return list(self._positions.values())

    def disconnect(self) -> None:
        self._real.disconnect()

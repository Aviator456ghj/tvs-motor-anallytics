"""A fully-offline broker that generates synthetic market data.

Lets you run the entire engine end-to-end with no internet, no credentials,
and no exchange - purely to verify the wiring and watch the strategy trade.
"""

from __future__ import annotations

import math
import random
import threading
import time

from .base import Broker, Order, OrderBook, Position, Side, Tick
from .paper import PaperBroker


class _SyntheticFeed(Broker):
    name = "sim"

    def __init__(self, symbols: list[str], seed: int = 7):
        self._symbols = symbols
        self._rng = random.Random(seed)
        self._px = {s: 100.0 for s in symbols}
        self._running = False

    def connect(self) -> None:
        pass

    def subscribe(self, symbols, on_tick, on_book) -> None:
        self._running = True

        def run():
            t = 0
            while self._running:
                for s in self._symbols:
                    # random walk with occasional trend bursts
                    drift = math.sin(t / 30.0) * 0.02
                    self._px[s] *= 1 + (self._rng.gauss(0, 0.0006) + drift / 100)
                    px = self._px[s]
                    on_tick(Tick(s, px, time.time(), bid=px * 0.9999,
                                 ask=px * 1.0001, volume=self._rng.random()))
                    skew = self._rng.uniform(0.5, 2.0)
                    on_book(OrderBook(
                        s,
                        bids=[(px * 0.9999, 10 * skew), (px * 0.9998, 8 * skew)],
                        asks=[(px * 1.0001, 10 / skew), (px * 1.0002, 8 / skew)],
                        timestamp=time.time(),
                    ))
                t += 1
                time.sleep(0.01)

        threading.Thread(target=run, daemon=True).start()

    def place_order(self, order: Order) -> Order:  # not used (wrapped by PaperBroker)
        order.status = "FILLED"
        order.filled_price = self._px.get(order.symbol, 0.0)
        return order

    def close_position(self, position: Position) -> Order:
        return self.place_order(Order(position.symbol, position.side.opposite,
                                      position.quantity))

    def get_positions(self):
        return []

    def disconnect(self) -> None:
        self._running = False


def make_simulator(symbols: list[str]) -> Broker:
    """PaperBroker wrapping a synthetic feed - simulated data AND simulated fills."""
    return PaperBroker(_SyntheticFeed(symbols))

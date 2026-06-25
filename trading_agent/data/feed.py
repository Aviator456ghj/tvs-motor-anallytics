"""Per-symbol market state: rolling tick buffer + on-the-fly bar aggregation.

This is what the strategy reads from. It is updated by broker callbacks on the
data thread and read by the decision loop, so access is guarded by a lock.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field

from ..brokers.base import OrderBook, Tick


@dataclass
class Bar:
    start: float
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class MarketState:
    """Holds rolling data for ONE symbol."""

    def __init__(self, symbol: str, timeframe_seconds: int = 5, maxbars: int = 500,
                 maxticks: int = 2000):
        self.symbol = symbol
        self.tf = timeframe_seconds
        self._lock = threading.Lock()
        self.ticks: deque[Tick] = deque(maxlen=maxticks)
        self.bars: deque[Bar] = deque(maxlen=maxbars)
        self.book: OrderBook | None = None
        self._cur_bar: Bar | None = None

    # ---- writers (data thread) ----
    def on_tick(self, t: Tick) -> None:
        with self._lock:
            self.ticks.append(t)
            self._fold_into_bar(t)

    def on_book(self, b: OrderBook) -> None:
        with self._lock:
            self.book = b

    def _fold_into_bar(self, t: Tick) -> None:
        slot = int(t.timestamp // self.tf) * self.tf
        if self._cur_bar is None or self._cur_bar.start != slot:
            if self._cur_bar is not None:
                self.bars.append(self._cur_bar)
            self._cur_bar = Bar(slot, t.price, t.price, t.price, t.price, t.volume)
        else:
            b = self._cur_bar
            b.high = max(b.high, t.price)
            b.low = min(b.low, t.price)
            b.close = t.price
            b.volume += t.volume

    # ---- readers (decision thread) ----
    def snapshot(self):
        """Return a consistent copy of closes, the live bar, last tick and book."""
        with self._lock:
            closes = [b.close for b in self.bars]
            if self._cur_bar is not None:
                closes.append(self._cur_bar.close)
            highs = [b.high for b in self.bars]
            lows = [b.low for b in self.bars]
            last = self.ticks[-1] if self.ticks else None
            recent = list(self.ticks)[-50:]
            return closes, highs, lows, last, self.book, recent

    @property
    def last_price(self) -> float:
        with self._lock:
            return self.ticks[-1].price if self.ticks else 0.0

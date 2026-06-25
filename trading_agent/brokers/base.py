"""Broker abstraction: a common interface every broker adapter implements.

The engine and strategy only ever talk to this interface, so adding a third
broker later means writing one more adapter - nothing else changes.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

    @property
    def opposite(self) -> "Side":
        return Side.SELL if self is Side.BUY else Side.BUY


@dataclass
class Tick:
    """A single market data update."""

    symbol: str
    price: float
    timestamp: float
    bid: float = 0.0
    ask: float = 0.0
    volume: float = 0.0


@dataclass
class OrderBook:
    """Top-of-book / depth snapshot used for imbalance signals."""

    symbol: str
    bids: list[tuple[float, float]] = field(default_factory=list)  # (price, size)
    asks: list[tuple[float, float]] = field(default_factory=list)
    timestamp: float = 0.0

    def imbalance(self, levels: int = 5) -> float:
        """Bid volume / ask volume over the top `levels`. >1 = buy pressure."""
        bid_vol = sum(sz for _, sz in self.bids[:levels])
        ask_vol = sum(sz for _, sz in self.asks[:levels])
        if ask_vol <= 0:
            return float("inf") if bid_vol > 0 else 1.0
        return bid_vol / ask_vol


@dataclass
class Order:
    symbol: str
    side: Side
    quantity: float
    price: float = 0.0          # 0 => market order
    order_type: str = "MARKET"
    broker_order_id: str = ""
    status: str = "NEW"
    filled_price: float = 0.0


@dataclass
class Position:
    symbol: str
    side: Side
    quantity: float
    entry_price: float
    broker: str = ""


class Broker(abc.ABC):
    """Common contract for every broker adapter."""

    name: str = "base"

    @abc.abstractmethod
    def connect(self) -> None:
        """Authenticate and prepare REST/session state."""

    @abc.abstractmethod
    def subscribe(self, symbols: list[str], on_tick: Callable[[Tick], None],
                  on_book: Callable[[OrderBook], None]) -> None:
        """Start streaming ticks and order-book updates via callbacks."""

    @abc.abstractmethod
    def place_order(self, order: Order) -> Order:
        """Submit an order; returns it populated with id/status/fill."""

    @abc.abstractmethod
    def close_position(self, position: Position) -> Order:
        """Flatten an open position with an opposite market order."""

    @abc.abstractmethod
    def get_positions(self) -> list[Position]:
        ...

    def disconnect(self) -> None:  # optional override
        pass

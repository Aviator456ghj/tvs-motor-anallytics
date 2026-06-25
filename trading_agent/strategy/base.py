"""Strategy interface and the Signal it emits."""

from __future__ import annotations

import abc
from dataclasses import dataclass

from ..brokers.base import Side
from ..data.feed import MarketState


@dataclass
class Signal:
    """What the strategy wants the engine to do for a symbol, right now."""

    action: str          # "ENTER", "EXIT", or "HOLD"
    side: Side | None = None
    reason: str = ""
    strength: float = 0.0


class Strategy(abc.ABC):
    name = "base"

    @abc.abstractmethod
    def evaluate(self, state: MarketState, in_position: bool,
                 position_side: Side | None) -> Signal:
        """Return a Signal from the current market state. Pure rules, no AI."""

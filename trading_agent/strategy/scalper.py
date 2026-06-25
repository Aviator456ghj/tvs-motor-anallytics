"""MicroScalper - a deterministic, rule-based scalping strategy.

Entry logic (a confluence of fast micro-signals, evaluated every loop):
  1. Order-book imbalance: one side of the book outweighs the other beyond a
     threshold -> short-term pressure in that direction.
  2. Momentum burst: price has moved > threshold% over the last N ticks.
  3. EMA trend filter: fast EMA above/below slow EMA confirms direction.
  4. Volatility gate: skip dead, choppy markets (ATR% too low).

All four must agree on a direction to enter. This is intentionally strict -
scalping bleeds money on false signals, so we'd rather miss than overtrade.

Exit is handled by the RiskManager (TP / SL / trailing / time-stop), not here,
so the strategy only signals EXIT on a momentum/imbalance reversal.

There is NO machine learning or LLM anywhere in this file - just arithmetic.
"""

from __future__ import annotations

from ..brokers.base import Side
from ..data.feed import MarketState
from .base import Signal, Strategy
from .indicators import atr_pct, ema, momentum_pct


class MicroScalper(Strategy):
    name = "micro_scalper"

    def __init__(self, cfg: dict):
        self.ob_thr = float(cfg.get("ob_imbalance_threshold", 1.8))
        self.ema_fast = int(cfg.get("ema_fast", 9))
        self.ema_slow = int(cfg.get("ema_slow", 21))
        self.mom_lookback = int(cfg.get("momentum_lookback", 10))
        self.mom_thr = float(cfg.get("momentum_threshold_pct", 0.04))
        self.min_atr = float(cfg.get("min_atr_pct", 0.02))

    def evaluate(self, state: MarketState, in_position: bool,
                 position_side: Side | None) -> Signal:
        closes, highs, lows, last, book, recent = state.snapshot()
        if last is None or len(closes) < self.ema_slow:
            return Signal("HOLD", reason="warming up")

        tick_prices = [t.price for t in recent]
        mom = momentum_pct(tick_prices, self.mom_lookback)
        ef = ema(closes, self.ema_fast)
        es = ema(closes, self.ema_slow)
        vol = atr_pct(highs, lows, closes)
        imb = book.imbalance() if book else 1.0

        # ---- exit on reversal while in a position ----
        if in_position and position_side is not None:
            if position_side is Side.BUY and (mom < -self.mom_thr or imb < 1 / self.ob_thr):
                return Signal("EXIT", reason=f"long reversal (mom={mom:.3f}, imb={imb:.2f})")
            if position_side is Side.SELL and (mom > self.mom_thr or imb > self.ob_thr):
                return Signal("EXIT", reason=f"short reversal (mom={mom:.3f}, imb={imb:.2f})")
            return Signal("HOLD", reason="holding")

        # ---- volatility gate ----
        if vol < self.min_atr:
            return Signal("HOLD", reason=f"low vol {vol:.3f}%")

        # ---- long confluence ----
        long_ok = (imb >= self.ob_thr) and (mom > self.mom_thr) and (ef > es)
        if long_ok:
            strength = min(imb / self.ob_thr, mom / self.mom_thr)
            return Signal("ENTER", side=Side.BUY, strength=strength,
                          reason=f"LONG imb={imb:.2f} mom={mom:.3f}% ef>es vol={vol:.3f}%")

        # ---- short confluence ----
        short_ok = (imb <= 1 / self.ob_thr) and (mom < -self.mom_thr) and (ef < es)
        if short_ok:
            strength = min((1 / imb) / self.ob_thr if imb else 0, abs(mom) / self.mom_thr)
            return Signal("ENTER", side=Side.SELL, strength=strength,
                          reason=f"SHORT imb={imb:.2f} mom={mom:.3f}% ef<es vol={vol:.3f}%")

        return Signal("HOLD", reason="no confluence")

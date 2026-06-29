"""
Market-structure engine: swing points (HH/HL/LH/LL), liquidity sweeps, and
fakeout filtering.

This encodes the rules we validated by hand:
  * Trade liquidity only at MAJOR swing extremes (range edges) -> 6/6 worked.
  * Skip anything in the MIDDLE of the range -> that is where fakeouts live.
  * Require a CLOSE back inside the level (reclaim), never a bare wick.
  * Require above-average volume on the sweep candle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class Swing:
    index: int
    price: float
    kind: Literal["high", "low"]


@dataclass
class Signal:
    side: Literal["buy", "sell"]
    kind: str            # "long_sweep" | "short_sweep" | "flip_long" | "flip_short"
    entry: float         # reference price (last close)
    stop: float
    swept_level: float
    reason: str


def find_swings(candles: list[dict], left: int = 2, right: int = 2) -> list[Swing]:
    """Fractal pivots: a swing high/low is the strict extreme of its +/- window."""
    swings: list[Swing] = []
    for i in range(left, len(candles) - right):
        window = candles[i - left : i + right + 1]
        hi = candles[i]["high"]
        lo = candles[i]["low"]
        if hi == max(c["high"] for c in window) and sum(c["high"] == hi for c in window) == 1:
            swings.append(Swing(i, hi, "high"))
        if lo == min(c["low"] for c in window) and sum(c["low"] == lo for c in window) == 1:
            swings.append(Swing(i, lo, "low"))
    return swings


def classify_trend(swings: list[Swing]) -> str:
    """Compare the last two highs and last two lows -> HH/HL/LH/LL summary."""
    highs = [s for s in swings if s.kind == "high"]
    lows = [s for s in swings if s.kind == "low"]
    if len(highs) < 2 or len(lows) < 2:
        return "indeterminate"
    hh = highs[-1].price > highs[-2].price
    hl = lows[-1].price > lows[-2].price
    if hh and hl:
        return "uptrend (HH+HL)"
    if not hh and not hl:
        return "downtrend (LH+LL)"
    if hl and not hh:
        return "basing (HL, still LH)"
    return "topping (LH, still HH)"


@dataclass
class RangeBox:
    high: float
    low: float

    @property
    def size(self) -> float:
        return self.high - self.low

    @property
    def mid(self) -> float:
        return (self.high + self.low) / 2


def compute_range(candles: list[dict], lookback: int) -> RangeBox:
    window = candles[-lookback:]
    return RangeBox(
        high=max(c["high"] for c in window),
        low=min(c["low"] for c in window),
    )


def avg_volume(candles: list[dict], lookback: int) -> float:
    window = candles[-lookback:]
    vols = [c.get("volume", 0.0) for c in window]
    return sum(vols) / len(vols) if vols else 0.0


def detect_signal(
    candles: list[dict],
    *,
    swing_left: int = 2,
    swing_right: int = 2,
    range_lookback: int = 40,
    vol_lookback: int = 20,
    vol_factor: float = 1.3,
    edge_band: float = 0.25,       # how close to a range edge counts as "at the edge"
    reclaim_buffer: float = 0.0005,  # close must reclaim by >= 0.05% of price
    flip_buffer: float = 0.0010,     # flip close must clear the level by >= 0.10%
    enable_long_sweep: bool = True,
    enable_short_sweep: bool = True,
    enable_flip: bool = True,
) -> Optional[Signal]:
    """
    Evaluate the LAST CLOSED candle (caller must pass only closed candles).

    Returns a Signal or None. All fakeout guards are applied here:
      - sweep level must be a real swing AND near the range edge
      - candle must close back inside (reclaim) the swept level
      - sweep candle volume must beat the average by `vol_factor`
      - mid-range price action returns no signal
    """
    if len(candles) < max(range_lookback, vol_lookback) + 5:
        return None

    last = candles[-1]
    prior = candles[:-1]
    swings = find_swings(prior, swing_left, swing_right)
    if not swings:
        return None

    box = compute_range(prior, range_lookback)
    avg_v = avg_volume(prior, vol_lookback)
    vol_ok = avg_v > 0 and last.get("volume", 0.0) >= avg_v * vol_factor

    edge = box.size * edge_band
    recent_high = max((s for s in swings if s.kind == "high"), key=lambda s: s.index, default=None)
    recent_low = min((s for s in swings if s.kind == "low"), key=lambda s: s.index, default=None)

    # ---- Long sweep: pierce a swing low near the range bottom, then reclaim it
    if enable_long_sweep and recent_low is not None:
        level = recent_low.price
        near_edge = level <= box.low + edge
        pierced = last["low"] < level
        reclaimed = last["close"] > level * (1 + reclaim_buffer)
        if near_edge and pierced and reclaimed and vol_ok:
            return Signal(
                side="buy",
                kind="long_sweep",
                entry=last["close"],
                stop=last["low"],          # below the sweep wick
                swept_level=level,
                reason=f"swept swing low {level:.1f}, reclaimed close {last['close']:.1f}, vol>{vol_factor}x avg",
            )

    # ---- Short sweep: pierce a swing high near the range top, then reject it
    if enable_short_sweep and recent_high is not None:
        level = recent_high.price
        near_edge = level >= box.high - edge
        pierced = last["high"] > level
        rejected = last["close"] < level * (1 - reclaim_buffer)
        if near_edge and pierced and rejected and vol_ok:
            return Signal(
                side="sell",
                kind="short_sweep",
                entry=last["close"],
                stop=last["high"],         # above the sweep wick
                swept_level=level,
                reason=f"swept swing high {level:.1f}, rejected close {last['close']:.1f}, vol>{vol_factor}x avg",
            )

    # ---- Structure-flip breakout: CLOSE decisively beyond the range extreme
    if enable_flip:
        if last["close"] > box.high * (1 + flip_buffer) and vol_ok:
            return Signal(
                side="buy",
                kind="flip_long",
                entry=last["close"],
                stop=box.high,             # broken resistance becomes the invalidation
                swept_level=box.high,
                reason=f"4H/structure close {last['close']:.1f} > range high {box.high:.1f} (+vol)",
            )
        if last["close"] < box.low * (1 - flip_buffer) and vol_ok:
            return Signal(
                side="sell",
                kind="flip_short",
                entry=last["close"],
                stop=box.low,
                swept_level=box.low,
                reason=f"4H/structure close {last['close']:.1f} < range low {box.low:.1f} (+vol)",
            )

    return None

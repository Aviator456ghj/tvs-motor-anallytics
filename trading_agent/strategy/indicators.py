"""Pure-function technical indicators. No external state, easy to unit test."""

from __future__ import annotations

from typing import Sequence


def ema(values: Sequence[float], period: int) -> float:
    """Exponential moving average of the last `period`+ values."""
    if not values:
        return 0.0
    if len(values) < period:
        return sum(values) / len(values)
    k = 2 / (period + 1)
    e = values[0]
    for v in values[1:]:
        e = v * k + e * (1 - k)
    return e


def atr_pct(highs: Sequence[float], lows: Sequence[float],
            closes: Sequence[float], period: int = 14) -> float:
    """Average True Range as a % of price - a volatility filter."""
    n = min(len(highs), len(lows), len(closes))
    if n < 2:
        return 0.0
    trs = []
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    window = trs[-period:]
    if not window:
        return 0.0
    atr = sum(window) / len(window)
    last_close = closes[-1] or 1.0
    return (atr / last_close) * 100.0


def momentum_pct(prices: Sequence[float], lookback: int) -> float:
    """% change over the last `lookback` ticks. Sign = direction."""
    if len(prices) <= lookback or prices[-lookback - 1] == 0:
        return 0.0
    old = prices[-lookback - 1]
    return ((prices[-1] - old) / old) * 100.0


def vwap(prices: Sequence[float], volumes: Sequence[float]) -> float:
    tot_v = sum(volumes)
    if tot_v <= 0:
        return prices[-1] if prices else 0.0
    return sum(p * v for p, v in zip(prices, volumes)) / tot_v

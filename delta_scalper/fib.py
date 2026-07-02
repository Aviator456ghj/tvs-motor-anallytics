"""Fibonacci retracement/extension strategy ("the 2.618 idea", tested).

The popular claim: price moves A->B, retraces to a fib level, then extends
to 1.272 / 1.618 / 2.618 of the move — a full road-map of "where it goes,
where it comes back to, where it goes next".

What 180 days of 5m Delta Exchange data actually shows
(backtests/run_fib_backtest.py regenerates all of this):

  * Median pullback depth is ~0.60 of the impulse — the 0.618 level is a
    decent central estimate, with mild clustering near fib levels
    (~19% of pullbacks end within 0.04 of one vs ~14% by chance).
  * 56% of pullbacks NEVER continue — they break the leg origin first.
    An EMA200 trend filter is what makes the setup tradeable.
  * Extensions are probabilities, not predictions: after continuation,
    price reaches 1.272x the leg ~50% of the time, 1.618x ~40%,
    2.618x only ~25%. In the strategy grid the 1.618 target beat 2.618.

Trading rules (walk-forward selected):
  leg   : confirmed fractal swing A->B, k bars each side (default 24 on 5m)
  filter: only legs aligned with the EMA200 trend
  entry : LIMIT at B - 0.618*(B-A)  (the retracement everyone watches)
  stop  : just beyond A (retracement > 1.0 = thesis dead)
  target: fill + 1.618*(B-A)  (risk 0.382*AB to make 1.618*AB, ~4.2 R:R)
"""
import numpy as np
import pandas as pd

from .config import Config
from .indicators import ema
from .strategy import Signal


def fractal_legs(df: pd.DataFrame, k: int) -> list[dict]:
    """Impulse legs between alternating confirmed fractal swings.

    A swing at bar j is confirmed at bar j+k (no lookahead). Returns dicts
    with a/b prices, bar indexes, confirmation bar, and direction.
    """
    h, l = df["high"].values, df["low"].values
    n = len(df)
    swings = []
    for j in range(k, n - k):
        if h[j] == h[j - k: j + k + 1].max():
            swings.append((j + k, j, h[j], "H"))
        if l[j] == l[j - k: j + k + 1].min():
            swings.append((j + k, j, l[j], "L"))
    swings.sort()
    seq = []
    for conf, at, price, kind in swings:
        if seq and seq[-1][3] == kind:
            if (kind == "H" and price > seq[-1][2]) or \
               (kind == "L" and price < seq[-1][2]):
                seq[-1] = (conf, at, price, kind)
        else:
            seq.append((conf, at, price, kind))
    out = []
    for prev, cur in zip(seq[:-1], seq[1:]):
        out.append({"a_bar": prev[1], "a": prev[2],
                    "b_bar": cur[1], "b": cur[2],
                    "conf_bar": cur[0],
                    "dir": 1 if cur[3] == "H" else -1})
    return out


class FibRetracementStrategy:
    """Same interface as the other strategies: signal(closed_candles)."""

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def signal(self, candles: pd.DataFrame) -> Signal | None:
        c = self.cfg
        if len(candles) < max(2 * c.fib_swing_k + 5, 210):
            return None
        df = candles.reset_index(drop=True)
        last = len(df) - 1
        trend = ema(df["close"], 200).values
        close = float(df["close"].iloc[-1])

        h, l = df["high"].values, df["low"].values
        for leg in fractal_legs(df, c.fib_swing_k):
            # act `fib_min_pull_bars` after confirmation: fast crashes into
            # the zone are impulsive, not corrective (23% vs ~37% win rate)
            if leg["conf_bar"] != last - c.fib_min_pull_bars:
                continue
            A, B, d = leg["a"], leg["b"], leg["dir"]
            rng = abs(B - A)
            if rng <= 0:
                continue
            if d * (close - trend[last]) < 0:
                continue  # 56% of legs fail; only trade with the trend
            limit = B - d * c.fib_entry_r * rng
            stop = B - d * c.fib_stop_r * rng
            # void if the waiting window already touched the zone or ran
            # beyond B — the setup we validated no longer exists
            window = range(leg["conf_bar"] + 1, last + 1)
            touched = any(l[j] <= limit for j in window) if d == 1 else \
                any(h[j] >= limit for j in window)
            beyond = any(h[j] > B for j in window) if d == 1 else \
                any(l[j] < B for j in window)
            if touched or beyond:
                continue
            stop_d = abs(limit - stop)
            if stop_d / limit < c.min_move_cost_ratio * c.round_trip_cost:
                continue
            if d * (close - limit) <= 0:
                continue  # already at/through the entry zone
            return Signal(
                side="buy" if d == 1 else "sell",
                entry_ref=float(limit),
                stop_loss=float(stop),
                take_profit=float(limit + d * c.fib_ext_r * rng),
                atr_value=stop_d,
                entry_type="limit",
                expires_bars=c.fib_wait_bars,
                context={
                    "setup": "fib_retracement",
                    "level": float(B),
                    "wick_ratio": None,
                    "sweep_depth_atr": None,
                    "vol_ratio": None,
                    "trend_align": 1,
                    "stop_pct": round(float(stop_d / limit * 100), 3),
                },
            )
        return None

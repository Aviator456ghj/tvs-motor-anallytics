"""Market-structure scalping strategy: confirmed HTF sweep + order-block entry.

Mechanical definition of the classic "smart money" scalp, with the
confirmation stack that backtested best:

  1. Liquidity level  — a confirmed swing low/high on a higher timeframe
     (default 1h, k-bar fractal). Stops rest beyond these levels.
  2. Sweep            — a trading-timeframe bar wicks THROUGH the level but
     closes back inside (the trap / stop-hunt).
  3. Fakeout quality  — the wick beyond the level must be >= `ms_wick_frac`
     of the sweep bar's range (a real rejection, not a graze).
  4. CHoCH confirm    — within `confirm_bars`, price closes beyond the
     sweep bar's local extreme (change of character), without first
     violating the sweep extreme.
  5. Entry            — LIMIT order at the ORDER BLOCK: the sweep bar's
     body edge (top for longs, bottom for shorts). Filled only on a
     retest -> better price, maker fee, tighter stop. Canceled if not
     filled within `ms_wait_bars`.
  6. Exits            — stop at the sweep extreme (exact invalidation
     point); take-profit at `ms_r_multiple` x the stop distance.

Backtest verdict (see reports/market_structure_report.md): the raw
sweep+CHoCH market entry loses after fees; the wick-confirmed order-block
entry is the only variant that reached positive expectancy (ETHUSD both
in- and out-of-sample on 180 days; BTCUSD roughly breakeven). Sample sizes
are small — paper-trade before believing it.
"""
import numpy as np
import pandas as pd

from .config import Config
from .strategy import Signal


def find_swings(df: pd.DataFrame, k: int):
    """Most recent CONFIRMED swing high/low visible at each bar.

    A swing at bar j is only usable from bar j+k onward (no lookahead).
    Returns (swing_high_prices, swing_low_prices) aligned to df's index.
    """
    h, l = df["high"].values, df["low"].values
    n = len(df)
    sh = np.full(n, np.nan)
    sl = np.full(n, np.nan)
    last_h, last_l = np.nan, np.nan
    for i in range(n):
        j = i - k
        if j >= k:
            if h[j] == h[j - k: j + k + 1].max():
                last_h = h[j]
            if l[j] == l[j - k: j + k + 1].min():
                last_l = l[j]
        sh[i], sl[i] = last_h, last_l
    return sh, sl


def resample_ohlc(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    d = df.copy()
    d["dt"] = pd.to_datetime(d["time"], unit="s", utc=True)
    g = d.set_index("dt").resample(f"{minutes}min")
    out = pd.DataFrame({
        "open": g["open"].first(), "high": g["high"].max(),
        "low": g["low"].min(), "close": g["close"].last(),
        "volume": g["volume"].sum(),
    }).dropna().reset_index()
    out["time"] = (
        (out["dt"] - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds().astype("int64")
    )
    return out


def htf_swing_levels(df: pd.DataFrame, htf_minutes: int, k: int):
    """Map confirmed HTF swing levels onto each trading-timeframe bar,
    using only fully closed HTF candles."""
    htf = resample_ohlc(df, htf_minutes)
    sh_p, sl_p = find_swings(htf, k)
    htf_close = htf["time"].values + htf_minutes * 60
    idx = np.searchsorted(htf_close, df["time"].values, side="right") - 1
    safe = np.clip(idx, 0, None)
    sh = np.where(idx >= 0, sh_p[safe], np.nan)
    sl = np.where(idx >= 0, sl_p[safe], np.nan)
    return sh, sl


class MarketStructureStrategy:
    """Same interface as TrendPullbackStrategy: signal(closed_candles)."""

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def signal(self, candles: pd.DataFrame) -> Signal | None:
        c = self.cfg
        min_bars = max(4 * c.ms_htf_minutes // c.timeframe_minutes * c.ms_swing_k,
                       c.ms_confirm_bars + c.ms_micro_bars + 2)
        if len(candles) < min_bars:
            return None
        df = candles.reset_index(drop=True)
        sh, sl = htf_swing_levels(df, c.ms_htf_minutes, c.ms_swing_k)
        o = df["open"].values
        h, l, cl = df["high"].values, df["low"].values, df["close"].values
        n = len(df)
        last = n - 1  # the just-closed bar must be the CHoCH confirmation

        for i in range(last - 1, max(last - 1 - c.ms_confirm_bars, c.ms_micro_bars), -1):
            side = 0
            level = np.nan
            if not np.isnan(sl[i - 1]) and l[i] < sl[i - 1] and cl[i] > sl[i - 1]:
                side, extreme, level = 1, l[i], sl[i - 1]
                trigger = h[i - c.ms_micro_bars: i + 1].max()
            elif not np.isnan(sh[i - 1]) and h[i] > sh[i - 1] and cl[i] < sh[i - 1]:
                side, extreme, level = -1, h[i], sh[i - 1]
                trigger = l[i - c.ms_micro_bars: i + 1].min()
            if side == 0:
                continue
            # fakeout quality: wick beyond the level vs the bar's range
            rng = h[i] - l[i]
            wick = (level - l[i]) if side == 1 else (h[i] - level)
            if c.ms_wick_frac > 0 and (rng <= 0 or wick / rng < c.ms_wick_frac):
                continue
            # invalidation or earlier confirmation between sweep and now
            violated = False
            for w in range(i + 1, last):
                if (side == 1 and (l[w] < extreme or cl[w] > trigger)) or \
                   (side == -1 and (h[w] > extreme or cl[w] < trigger)):
                    violated = True
                    break
            if violated:
                continue
            confirmed = (side == 1 and cl[last] > trigger and l[last] >= extreme) or \
                        (side == -1 and cl[last] < trigger and h[last] <= extreme)
            if not confirmed:
                continue
            # order block: the sweep bar's body edge, awaiting a retest
            ob = float(max(o[i], cl[i]) if side == 1 else min(o[i], cl[i]))
            if side * (float(cl[last]) - ob) <= 0:
                return None  # market already at/through the block
            stop_d = abs(ob - extreme)
            if stop_d <= 0 or stop_d / ob < c.min_move_cost_ratio * c.round_trip_cost:
                return None
            return Signal(
                side="buy" if side == 1 else "sell",
                entry_ref=ob,
                stop_loss=float(extreme),
                take_profit=ob + side * c.ms_r_multiple * stop_d,
                atr_value=stop_d,
                entry_type="limit",
                expires_bars=c.ms_wait_bars,
            )
        return None

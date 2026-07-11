"""Liquidity Sweep Fakeout — live-bot port of the validated logic (see
reports/liquidity_fakeout_report.md and backtests/run_liquidity_fakeout_backtest.py).

A confirmed k-bar swing high/low is where resting liquidity (stop-losses,
breakout entries) clusters. A SWEEP is a wick that pierces >= liq_wick_atr
ATRs beyond that level. A FAKEOUT is the sweeping candle itself failing to
hold beyond the level — it closes back inside — traded ONLY when that
candle's volume is >= liq_vol_mult x its 20-bar average (this filter is
what separates a real stop-hunt from a random wick: PF 0.85 without it,
1.06-1.90 with it, walk-forward, on every asset tested).

Entry: market, on the sweep candle's own close (same-bar confirmation —
there is no waiting window). Stop: beyond the sweep's extreme + an ATR
buffer. Exit: a FIXED R-multiple target, not a ride — a fakeout is a quick
snap-back, not a trend, and ride exits lost money in every configuration
tested for this pattern.

VALIDATED ON 1H ONLY, cross-asset (BTC/ETH/SOL/XRP), walk-forward 70/30:
  BTCUSD  PF 1.06 in-sample -> 1.42 out-of-sample
  ETHUSD  PF 1.26 -> 1.49
  SOLUSD  PF 1.90 -> 1.57
  XRPUSD  PF 1.16 -> 1.43
This strategy FAILS on 15m (PF 0.63-0.99) and is marginal on 30m
(PF 0.81-1.14) — config.py's __post_init__ pins it to 1h and DELTA_STRATEGY
should not be paired with a DELTA_TIMEFRAME_MIN override for this one.

Live-vs-backtest verification: replayed against 1500 held-out bars of
BTCUSD 1h, comparing this module's per-bar signal() output to the full-
history backtest engine's raw fakeout+volume events — 98.8% bar-for-bar
agreement. The residual is explained by the backtest engine's sequential
"one trade at a time" gating (a raw fakeout event on a bar the backtest
was already in a trade never becomes an executed entry), which the
verification harness's raw event set does not model; it is not a
demonstrated logic bug in this module.
"""
import numpy as np
import pandas as pd

from .config import Config
from .indicators import atr
from .strategy import Signal


def confirmed_swings(df: pd.DataFrame, k: int):
    """Chronological alternating swings [(conf_bar, at_bar, price, kind)]."""
    h, l = df["high"].values, df["low"].values
    n = len(df)
    raw = []
    for j in range(k, n - k):
        if h[j] == h[j - k: j + k + 1].max():
            raw.append((j + k, j, h[j], "H"))
        if l[j] == l[j - k: j + k + 1].min():
            raw.append((j + k, j, l[j], "L"))
    raw.sort()
    seq = []
    for conf, at, price, kind in raw:
        if seq and seq[-1][3] == kind:
            if (kind == "H" and price > seq[-1][2]) or \
               (kind == "L" and price < seq[-1][2]):
                seq[-1] = (conf, at, price, kind)
        else:
            seq.append((conf, at, price, kind))
    return seq


class LiquidityFakeoutStrategy:
    """Same interface as the other strategies: signal(closed_candles)."""

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def signal(self, candles: pd.DataFrame) -> Signal | None:
        c = self.cfg
        k = c.liq_swing_k
        if len(candles) < 6 * k + 30:
            return None
        df = candles.reset_index(drop=True)
        o, h, l, cl, v = (df["open"].values, df["high"].values, df["low"].values,
                          df["close"].values, df["volume"].values)
        n = len(df)
        last = n - 1
        a = atr(df, c.atr_period).values
        vol_sma = pd.Series(v).rolling(20).mean().values
        swings = confirmed_swings(df, k)

        # replay every bar to know which swing levels are still "live"
        # (never swept) as of the newest closed bar
        live_highs, live_lows = [], []  # each: [price, already_swept]
        si = 0
        for t in range(n):
            while si < len(swings) and swings[si][0] <= t:
                conf, at, price, kind = swings[si]
                (live_highs if kind == "H" else live_lows).append([price, False])
                si += 1
            if t == last:
                break
            if a[t] <= 0 or np.isnan(a[t]):
                continue
            for lvl in live_highs:
                if not lvl[1] and h[t] >= lvl[0] + c.liq_wick_atr * a[t]:
                    lvl[1] = True
            for lvl in live_lows:
                if not lvl[1] and l[t] <= lvl[0] - c.liq_wick_atr * a[t]:
                    lvl[1] = True

        # the live decision: did a sweep + volume-confirmed fakeout just
        # happen on the bar that closed most recently?
        t = last
        if a[t] <= 0 or np.isnan(a[t]) or vol_sma[t] <= 0 or np.isnan(vol_sma[t]):
            return None
        if v[t] < c.liq_vol_mult * vol_sma[t]:
            return None
        for lvl in live_highs:
            if lvl[1]:
                continue
            level = lvl[0]
            if h[t] >= level + c.liq_wick_atr * a[t]:
                thresh = level - c.liq_reject_frac * (h[t] - level)
                if cl[t] <= thresh:
                    return self._make_signal(-1, cl[t], h[t], a[t])
        for lvl in live_lows:
            if lvl[1]:
                continue
            level = lvl[0]
            if l[t] <= level - c.liq_wick_atr * a[t]:
                thresh = level + c.liq_reject_frac * (level - l[t])
                if cl[t] >= thresh:
                    return self._make_signal(1, cl[t], l[t], a[t])
        return None

    def _make_signal(self, d: int, entry: float, extreme: float, atr_now: float) -> Signal | None:
        c = self.cfg
        stop = extreme - d * c.liq_buf_atr * atr_now
        stop_d = abs(entry - stop)
        if stop_d <= 0 or stop_d / entry < c.min_move_cost_ratio * c.round_trip_cost:
            return None
        tp = entry + d * stop_d * c.liq_r_mult
        return Signal(
            side="buy" if d == 1 else "sell",
            entry_ref=float(entry),
            stop_loss=float(stop),
            take_profit=float(tp),
            atr_value=stop_d,
            entry_type="market",
            expires_bars=0,
            context={
                "setup": "liquidity_fakeout",
                "level": None,
                "wick_ratio": None,
                "sweep_depth_atr": None,
                "vol_ratio": None,
                "trend_align": 0,
                "stop_pct": round(stop_d / entry * 100, 3),
            },
        )

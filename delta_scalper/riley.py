"""Riley Coleman's "5-step checklist" — mechanical translation.

Source: video transcript, "How I'd Trade $4 Into $2,000 In Only 5 Days".

De-jargoned rules:
  1. Location   : trend context from k-bar fractal swing structure
                  (video uses discretionary S/R zones; we use structure,
                  since zones aren't mechanically testable).
  2. Unhealthy move: a Fair Value Gap (3-candle imbalance) in the
                  impulsive leg that produced the extreme — the video's
                  signal that a move is "overextended" and due to snap.
  3. CHoCH      : price CLOSES beyond the prior swing low (uptrend) or
                  swing high (downtrend) — the initial break of structure.
  4. Failed retest: price attempts to continue the OLD trend but fails
                  to make a new extreme (lower high / higher low) and
                  reverses.
  5. Entry      : stop order below/above the failed retest's low/high,
                  trading WITH the new (reversed) direction. Stop beyond
                  that failed extreme; exit via a swing-ratcheted
                  trailing stop (only tightens, never loosens) or a
                  fixed R-multiple target.

Backtest verdict (reports/riley_report.md): validated on 15m BTCUSD and
ETHUSD, walk-forward, positive in all four cells with the FVG >= 0.5 ATR
filter and a swing-trailing exit — the only externally-sourced strategy
in this repo (alongside QWM and ARC, both rejected) that survived
testing. Robust across swing widths k=3 and k=5; k=8 is a near-miss.
"""
import numpy as np
import pandas as pd

from .config import Config
from .indicators import atr
from .strategy import Signal


def _swing_state(df: pd.DataFrame, k: int):
    """Last-two confirmed swing highs/lows as of each bar (no lookahead),
    plus the raw alternating swing sequence for trailing-stop lookups."""
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

    hp = np.full(n, np.nan); ha = np.full(n, -1)
    hp2 = np.full(n, np.nan); ha2 = np.full(n, -1)
    lp = np.full(n, np.nan); la = np.full(n, -1)
    lp2 = np.full(n, np.nan); la2 = np.full(n, -1)
    cur_h = cur_h2 = cur_l = cur_l2 = None
    si = 0
    for t in range(n):
        while si < len(seq) and seq[si][0] <= t:
            conf, at, price, kind = seq[si]
            if kind == "H":
                cur_h2, cur_h = cur_h, (at, price)
            else:
                cur_l2, cur_l = cur_l, (at, price)
            si += 1
        if cur_h:
            ha[t], hp[t] = cur_h
        if cur_h2:
            ha2[t], hp2[t] = cur_h2
        if cur_l:
            la[t], lp[t] = cur_l
        if cur_l2:
            la2[t], lp2[t] = cur_l2
    return hp, ha, hp2, ha2, lp, la, lp2, la2, seq


def trailing_swing_levels(seq, n):
    """For each bar: most recent confirmed swing low/high (no lookahead) —
    used to ratchet a trailing stop in the trade's favor."""
    lo = np.full(n, np.nan); hi = np.full(n, np.nan)
    cur_lo = cur_hi = np.nan
    si = 0
    for t in range(n):
        while si < len(seq) and seq[si][0] <= t:
            _, _, price, kind = seq[si]
            if kind == "L":
                cur_lo = price
            else:
                cur_hi = price
            si += 1
        lo[t], hi[t] = cur_lo, cur_hi
    return lo, hi


def last_confirmed_swings(df: pd.DataFrame, k: int):
    """(last confirmed swing low, last confirmed swing high) as of the
    final bar — used to ratchet the bot's trailing stop."""
    h, l = df["high"].values, df["low"].values
    n = len(df)
    lo = hi = None
    for j in range(n - k - 1, k - 1, -1):
        if lo is None and l[j] == l[j - k: j + k + 1].min():
            lo = float(l[j])
        if hi is None and h[j] == h[j - k: j + k + 1].max():
            hi = float(h[j])
        if lo is not None and hi is not None:
            break
    return lo, hi


def _has_fvg(h, l, atr_v, start, end, kind, fvg_mult):
    if fvg_mult <= 0:
        return True
    end = min(end, len(h) - 2)
    for i in range(max(start, 1), end):
        gap = (l[i + 1] - h[i - 1]) if kind == "bull" else (l[i - 1] - h[i + 1])
        if gap > 0 and atr_v[i] > 0 and gap >= fvg_mult * atr_v[i]:
            return True
    return False


class RileyReversalStrategy:
    """Same interface as the other strategies: signal(closed_candles)."""

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def signal(self, candles: pd.DataFrame) -> Signal | None:
        c = self.cfg
        k = c.riley_swing_k
        if len(candles) < 6 * k + 250:
            return None
        df = candles.reset_index(drop=True)
        o, h, l, cl = df["open"].values, df["high"].values, df["low"].values, \
            df["close"].values
        n = len(df)
        last = n - 1
        atr_v = atr(df, c.atr_period).values
        hp, ha, hp2, ha2, lp, la, lp2, la2, seq = _swing_state(df, k)

        lookback = min(last, 400)
        for t in range(last - lookback, last + 1):
            if np.isnan(hp[t]) or np.isnan(hp2[t]) or np.isnan(lp[t]) or \
                    np.isnan(lp2[t]):
                continue
            d = 0
            if ha[t] > la[t] and hp2[t] < hp[t] and lp2[t] < lp[t]:
                d, ref_price, break_level = -1, hp[t], lp[t]
                leg_start, leg_end, fvg_kind = la[t], ha[t], "bull"
            elif la[t] > ha[t] and lp2[t] > lp[t] and hp2[t] > hp[t]:
                d, ref_price, break_level = 1, lp[t], hp[t]
                leg_start, leg_end, fvg_kind = ha[t], la[t], "bear"
            if d == 0:
                continue
            if not _has_fvg(h, l, atr_v, leg_start, leg_end, fvg_kind,
                            c.riley_fvg_mult):
                continue
            bos_bar = None
            for j in range(t, min(t + 200, n - 1)):
                if (cl[j] < break_level if d == -1 else cl[j] > break_level):
                    bos_bar = j
                    break
            if bos_bar is None or bos_bar > last:
                continue
            w0 = bos_bar + 1
            w1 = min(bos_bar + 1 + c.riley_retest_window, n - 1)
            if w1 <= w0 or w0 > last:
                continue
            if d == -1:
                rb = w0 + int(np.argmax(h[w0:w1]))
                bounce_extreme = h[rb]
                failed = bounce_extreme < ref_price
            else:
                rb = w0 + int(np.argmin(l[w0:w1]))
                bounce_extreme = l[rb]
                failed = bounce_extreme > ref_price
            if not failed or rb > last:
                continue
            entry_level = l[rb] if d == -1 else h[rb]
            fill = None
            for j in range(rb + 1, min(rb + 1 + c.riley_fill_window, n)):
                if (l[j] <= entry_level if d == -1 else h[j] >= entry_level):
                    fill = j
                    break
                if (h[j] > ref_price if d == -1 else l[j] < ref_price):
                    break  # old trend resumed before entry -> void
            if fill != last:
                continue  # only fire the instant the trigger bar closes
            entry = float(cl[last])
            stop = float(bounce_extreme)
            stop_d = abs(entry - stop)
            if stop_d <= 0 or stop_d / entry < c.min_move_cost_ratio * c.round_trip_cost:
                return None
            tp = entry + d * c.riley_r_mult * stop_d \
                if c.riley_exit_mode == "target" else 0.0
            return Signal(
                side="buy" if d == 1 else "sell",
                entry_ref=entry,
                stop_loss=stop,
                take_profit=tp,
                atr_value=stop_d,
                entry_type="market",
                expires_bars=0,
                context={
                    "setup": "riley_failed_retest",
                    "level": float(ref_price),
                    "wick_ratio": None,
                    "sweep_depth_atr": None,
                    "vol_ratio": None,
                    "trend_align": 1,
                    "stop_pct": round(stop_d / entry * 100, 3),
                },
            )
        return None

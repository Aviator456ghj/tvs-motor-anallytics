"""CHoCH-anchored fib strategy — the "trend change swing" setup (1h).

The idea (from the user's chart): when the market changes character —
a downtrend's lower-high gets broken by a close (CHoCH) — anchor a fib
to THAT reversal swing:

    A = the swing low that started the reversal (the bottom)
    B = the first confirmed swing high after the CHoCH break

    entry : limit in the discount zone at the 0.5 retracement of A->B
    stop  : just below A (full retracement = reversal failed)
    target: the 2.618 extension measured from A  (A + 2.618*(B-A))
    mirror logic for CHoCH-down shorts.

Validated on 540 days of 1h data, walk-forward (360/180): positive on
BTCUSD in both phases across the whole k=5 config family (best cell
PF 1.46 in / 1.77 out); ETHUSD did NOT validate — BTC only by default.
Unlike ordinary swings (where 1.618 wins), trend-change swings run far
enough that 2.618 is the best-performing target.
"""
import numpy as np
import pandas as pd

from .config import Config
from .strategy import Signal


def confirmed_swings(df: pd.DataFrame, k: int):
    """Chronological alternating swings [(conf_bar, at_bar, price, kind)].
    A swing at bar j is confirmed at bar j+k (no lookahead)."""
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


def find_choch_setups(df: pd.DataFrame, k: int) -> list[dict]:
    """All completed CHoCH setups in the window.

    Returns dicts: dir (+1 long / -1 short), A/A_bar (reversal origin),
    B/B_bar (post-break swing), break_bar, ready_bar (when tradeable).
    """
    c = df["close"].values
    n = len(df)
    swings = confirmed_swings(df, k)
    setups = []
    si = 0
    last_H: list = []
    last_L: list = []
    pending_up = pending_dn = None  # (break_bar, A_price, A_bar)
    for t in range(n):
        while si < len(swings) and swings[si][0] <= t:
            conf, at, price, kind = swings[si]
            if kind == "H":
                last_H.append((at, price))
                if pending_up and at > pending_up[0]:
                    setups.append(dict(dir=1, A=pending_up[1],
                                       A_bar=pending_up[2], B=price, B_bar=at,
                                       break_bar=pending_up[0], ready_bar=conf))
                    pending_up = None
            else:
                last_L.append((at, price))
                if pending_dn and at > pending_dn[0]:
                    setups.append(dict(dir=-1, A=pending_dn[1],
                                       A_bar=pending_dn[2], B=price, B_bar=at,
                                       break_bar=pending_dn[0], ready_bar=conf))
                    pending_dn = None
            si += 1
        if len(last_H) >= 2 and pending_up is None:
            lh_at, lh_p = last_H[-1]
            if lh_p < last_H[-2][1] and c[t] > lh_p and t > lh_at:
                A_bar, A = min(((at, p) for at, p in last_L
                                if at > last_H[-2][0]),
                               key=lambda x: x[1], default=(None, None))
                if A is not None:
                    pending_up = (t, A, A_bar)
        if len(last_L) >= 2 and pending_dn is None:
            ll_at, ll_p = last_L[-1]
            if ll_p > last_L[-2][1] and c[t] < ll_p and t > ll_at:
                A_bar, A = max(((at, p) for at, p in last_H
                                if at > last_L[-2][0]),
                               key=lambda x: x[1], default=(None, None))
                if A is not None:
                    pending_dn = (t, A, A_bar)
    return setups


class ChochFibStrategy:
    """Same interface as the other strategies: signal(closed_candles)."""

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def signal(self, candles: pd.DataFrame) -> Signal | None:
        if self.cfg.choch_entry_mode == "candle":
            return self._signal_candle_confirm(candles)
        return self._signal_limit(candles)

    # ---- mode "limit": blind limit resting at the 0.5 retracement ----

    def _signal_limit(self, candles: pd.DataFrame) -> Signal | None:
        c = self.cfg
        if len(candles) < 6 * c.choch_swing_k + 20:
            return None
        df = candles.reset_index(drop=True)
        last = len(df) - 1
        close = float(df["close"].iloc[-1])
        for s in find_choch_setups(df, c.choch_swing_k):
            if s["ready_bar"] != last:
                continue  # only act the moment a setup completes
            d = s["dir"]
            A, B = s["A"], s["B"]
            rng = abs(B - A)
            if rng <= 0:
                continue
            entry = B - d * c.choch_entry_r * rng
            stop = A - d * c.choch_stop_buffer * rng  # buffer beyond A
            tp = A + d * c.choch_ext_r * rng
            stop_d = abs(entry - stop)
            if stop_d <= 0 or stop_d / entry < c.min_move_cost_ratio * c.round_trip_cost:
                continue
            if d * (close - entry) <= 0 or d * (tp - entry) <= 0:
                continue
            return self._make_signal(d, entry, stop, tp, stop_d, B,
                                     entry_type="limit",
                                     expires=c.choch_wait_bars)
        return None

    # ---- mode "candle": golden-zone candle-color confirmation ----
    # a candle touches/enters the 0.5-0.618 zone and closes AGAINST the trade
    # direction (red for longs), the NEXT candle closes WITH it (green for
    # longs) -> market entry on that close. Setup voids on a close beyond B,
    # a close past the 0.786 level, or window expiry.

    def _signal_candle_confirm(self, candles: pd.DataFrame) -> Signal | None:
        c = self.cfg
        if len(candles) < 6 * c.choch_swing_k + 20:
            return None
        df = candles.reset_index(drop=True)
        o = df["open"].values
        h, l, cl = df["high"].values, df["low"].values, df["close"].values
        last = len(df) - 1
        for s in find_choch_setups(df, c.choch_swing_k):
            if not (s["ready_bar"] < last <= s["ready_bar"] + c.choch_wait_bars):
                continue
            d = s["dir"]
            A, B = s["A"], s["B"]
            rng = abs(B - A)
            if rng <= 0:
                continue
            z_near = B - d * c.choch_entry_r * rng
            void_lvl = B - d * c.choch_disrespect_r * rng
            trigger_bar = None
            voided = False
            for j in range(s["ready_bar"] + 1, last + 1):
                if (cl[j] > B if d == 1 else cl[j] < B) or \
                   (cl[j] < void_lvl if d == 1 else cl[j] > void_lvl):
                    voided = True
                    break
                if trigger_bar is None and j < last:
                    touched = (l[j] <= z_near if d == 1 else h[j] >= z_near)
                    counter = (cl[j] < o[j]) if d == 1 else (cl[j] > o[j])
                    if touched and counter:
                        conf = (cl[j + 1] > o[j + 1]) if d == 1 else \
                               (cl[j + 1] < o[j + 1])
                        if conf:
                            if c.choch_require_engulf:
                                # true engulf: close beyond the counter
                                # candle's OPEN. The FIRST zone reaction is
                                # the informative one — a weak (non-engulf)
                                # confirmation voids the whole setup rather
                                # than waiting for a later pair (validated:
                                # re-scanning underperforms the base).
                                engulfed = (cl[j + 1] > o[j]) if d == 1 else \
                                           (cl[j + 1] < o[j])
                                if not engulfed:
                                    voided = True
                                    break
                            trigger_bar = j + 1
                            break
            if voided or trigger_bar != last:
                continue  # no trigger, already consumed earlier, or voided
            entry = float(cl[last])
            stop = A - d * c.choch_stop_buffer * rng  # buffer beyond A
            tp = A + d * c.choch_ext_r * rng
            stop_d = abs(entry - stop)
            if stop_d <= 0 or d * (tp - entry) <= 0 or \
                    stop_d / entry < c.min_move_cost_ratio * c.round_trip_cost:
                continue
            return self._make_signal(d, entry, stop, tp, stop_d, B,
                                     entry_type="market", expires=0)
        return None

    def _make_signal(self, d, entry, stop, tp, stop_d, B, entry_type, expires):
        return Signal(
            side="buy" if d == 1 else "sell",
            entry_ref=float(entry),
            stop_loss=float(stop),
            take_profit=float(tp),
            atr_value=stop_d,
            entry_type=entry_type,
            expires_bars=expires,
            context={
                "setup": f"choch_fib_{self.cfg.choch_entry_mode}",
                "level": float(B),
                "wick_ratio": None,
                "sweep_depth_atr": None,
                "vol_ratio": None,
                "trend_align": 1,
                "stop_pct": round(float(stop_d / entry * 100), 3),
            },
        )

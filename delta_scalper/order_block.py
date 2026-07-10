"""Order Block Retest strategy — live-bot port of the console/Pine logic.

The setup (see pine/order_block_retest.pine for the full description and
backtest numbers): when confirmed swing structure breaks with a displaced
move (>= ob_min_break_atr ATRs past the broken level), the last
opposite-colour candle before that break is the "order block". Price often
returns to that candle's [low, high] zone once before continuing; a
same-direction candle on that touch is the entry. Stop beyond the OB
zone's far extreme + an ATR buffer. Exit rides the swing trail (handled by
the bot's trend-ride exit, same mechanism as the choch strategy).

Causality note vs the backtest: the backtest engine scans for retests from
the break bar onward, but a setup only becomes *knowable* once the post-
break swing (B) confirms, k bars later. A retest that completes inside
that confirmation gap is visible to the backtest but not tradeable live —
this module simply misses those (slightly fewer trades live than the
backtest shows; the ones it does take are identical).
"""
import numpy as np
import pandas as pd

from .config import Config
from .choch import find_choch_setups
from .indicators import atr
from .strategy import Signal


class OrderBlockStrategy:
    """Same interface as the other strategies: signal(closed_candles)."""

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def signal(self, candles: pd.DataFrame) -> Signal | None:
        c = self.cfg
        k = c.ob_swing_k
        if len(candles) < 6 * k + 20:
            return None
        df = candles.reset_index(drop=True)
        o, h, l, cl = df["open"].values, df["high"].values, df["low"].values, \
            df["close"].values
        n = len(df)
        last = n - 1
        a = atr(df, c.atr_period).values

        for s in find_choch_setups(df, k):
            d, A_bar, bb = s["dir"], s["A_bar"], s["break_bar"]
            # setup must be live: confirmed, inside its retest window
            if not (s["ready_bar"] < last <= bb + c.ob_wait_bars):
                continue
            # displacement filter on the break candle
            if bb >= len(a) or np.isnan(a[bb]) or a[bb] <= 0:
                continue
            if abs(cl[bb] - s["B"]) / a[bb] < c.ob_min_break_atr:
                continue
            # order block: nearest opposite-colour candle before the break
            ob = None
            for j in range(bb - 1, A_bar, -1):
                is_counter = (cl[j] < o[j]) if d == 1 else (cl[j] > o[j])
                if is_counter:
                    ob = j
                    break
            if ob is None:
                continue
            ob_lo, ob_hi = l[ob], h[ob]
            # replay the retest scan; the trade only fires if the FIRST
            # confirming touch is exactly the newest closed bar
            trigger = None
            voided = False
            for j in range(bb + 1, last + 1):
                touched = (l[j] <= ob_hi) if d == 1 else (h[j] >= ob_lo)
                if not touched:
                    continue
                confirm = (cl[j] > o[j]) if d == 1 else (cl[j] < o[j])
                if confirm:
                    trigger = j
                    break
                if (d == 1 and cl[j] < ob_lo) or (d == -1 and cl[j] > ob_hi):
                    voided = True  # closed fully through the zone first
                    break
            if voided or trigger != last:
                continue  # no trigger yet, consumed earlier, or invalidated
            entry = float(cl[last])
            stop = float(ob_lo - c.ob_buf_atr * a[last]) if d == 1 else \
                float(ob_hi + c.ob_buf_atr * a[last])
            stop_d = abs(entry - stop)
            if stop_d <= 0 or \
                    stop_d / entry < c.min_move_cost_ratio * c.round_trip_cost:
                continue
            return Signal(
                side="buy" if d == 1 else "sell",
                entry_ref=entry,
                stop_loss=stop,
                take_profit=0.0,  # ride exit — no fixed TP leg
                atr_value=stop_d,
                entry_type="market",
                expires_bars=0,
                context={
                    "setup": "order_block_retest",
                    "level": float(s["B"]),
                    "wick_ratio": None,
                    "sweep_depth_atr": None,
                    "vol_ratio": None,
                    "trend_align": 1,
                    "stop_pct": round(stop_d / entry * 100, 3),
                },
            )
        return None

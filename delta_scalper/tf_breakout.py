"""Trend-following Bollinger Band breakout + EMA trend filter — live-bot
port of the logic replicated from a Claude+Jesse-MCP autonomous strategy-
development video (see reports/tf_breakout_jesse_replication_report.md
for the full write-up).

One entry rule, two exit modes:
    should_long:  close > BB upper AND close > trend EMA
    should_short: close < BB lower AND close < trend EMA
    fixed mode:  stop and target both fixed at entry (x ATR)
    trail mode:  stop only fixed at entry; ratchets toward the extreme
                 favorable price every closed bar using that bar's own
                 live ATR, never loosens (handled by bot.py's
                 _tfbreakout_trail_stop, same pattern as riley's trail).

HONEST RESULT (see the report): on real Delta Exchange India data,
neither exit mode cleared Sharpe>1 out-of-sample (trail: -0.35, fixed:
0.90) even though both passed an entry-rule significance test (p<0.01)
and Monte Carlo (worst-5% still positive) on the FULL period with no
train/test split — exactly what the source video's own methodology
would have called validated. That gap between "passes significance +
Monte Carlo" and "actually holds up out-of-sample" is the point of
including it here: paper-only, judge it by its own live journal, not by
the full-period backtest number.
"""
import numpy as np
import pandas as pd

from .config import Config
from .indicators import atr, ema, bollinger_bands
from .strategy import Signal


class TFBreakoutStrategy:
    """Same interface as the other strategies: signal(closed_candles)."""

    def __init__(self, cfg: Config):
        self.cfg = cfg

    def signal(self, candles: pd.DataFrame) -> Signal | None:
        c = self.cfg
        if len(candles) < c.tf_ema_period + 5:
            return None
        df = candles.reset_index(drop=True)
        upper, _, lower = bollinger_bands(df["close"], c.tf_bb_period, c.tf_bb_dev)
        trend = ema(df["close"], c.tf_ema_period)
        a = atr(df, 14)
        t = len(df) - 1
        if np.isnan(upper.iloc[t]) or np.isnan(trend.iloc[t]) or \
                np.isnan(a.iloc[t]) or a.iloc[t] <= 0:
            return None

        close = float(df["close"].iloc[t])
        long_sig = close > upper.iloc[t] and close > trend.iloc[t]
        short_sig = close < lower.iloc[t] and close < trend.iloc[t]
        if not (long_sig or short_sig):
            return None

        d = 1 if long_sig else -1
        entry = close
        atr_now = float(a.iloc[t])
        stop = entry - d * c.tf_stop_mult * atr_now
        stop_d = abs(entry - stop)
        if stop_d <= 0 or stop_d / entry < c.min_move_cost_ratio * c.round_trip_cost:
            return None
        tp = 0.0 if c.tf_exit_mode == "trail" else entry + d * c.tf_exit_mult * atr_now

        return Signal(
            side="buy" if d == 1 else "sell",
            entry_ref=entry,
            stop_loss=float(stop),
            take_profit=float(tp),
            atr_value=stop_d,
            entry_type="market",
            expires_bars=0,
            context={
                "setup": f"tf_breakout_{c.tf_exit_mode}",
                "level": None,
                "wick_ratio": None,
                "sweep_depth_atr": None,
                "vol_ratio": None,
                "trend_align": d,
                "stop_pct": round(stop_d / entry * 100, 3),
            },
        )

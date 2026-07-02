"""Trend-pullback scalping strategy.

Idea: only trade with the prevailing trend; enter when a short-term
pullback (RSI dip) resolves back in the trend direction; exit at an
ATR-scaled stop-loss / take-profit or after a time limit.

Long  when EMA20 > EMA50, close > EMA100, and RSI crosses back UP through 45.
Short when EMA20 < EMA50, close < EMA100, and RSI crosses back DOWN through 55.

A volatility filter skips trades whose stop distance is too small relative
to round-trip trading costs — fees are what kill scalping strategies.
"""
from dataclasses import dataclass

import pandas as pd

from .config import Config
from .indicators import atr, ema, rsi


@dataclass
class Signal:
    side: str          # "buy" | "sell"
    entry_ref: float   # reference price: last close (market) or limit level
    stop_loss: float
    take_profit: float
    atr_value: float
    entry_type: str = "market"   # "market" | "limit" (wait for a retest fill)
    expires_bars: int = 0        # cancel an unfilled limit after this many bars
    context: dict | None = None  # setup features recorded to the trade journal


class TrendPullbackStrategy:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    def compute_indicators(self, candles: pd.DataFrame) -> pd.DataFrame:
        c = self.cfg
        df = candles.copy()
        df["ema_fast"] = ema(df["close"], c.ema_fast)
        df["ema_slow"] = ema(df["close"], c.ema_slow)
        df["ema_trend"] = ema(df["close"], c.ema_trend)
        df["rsi"] = rsi(df["close"], c.rsi_period)
        df["atr"] = atr(df, c.atr_period)
        return df

    def signal(self, candles: pd.DataFrame) -> Signal | None:
        """Evaluate on the latest CLOSED candle. `candles` must be ascending
        and contain only closed candles."""
        c = self.cfg
        min_bars = c.ema_trend + 10
        if len(candles) < min_bars:
            return None
        df = self.compute_indicators(candles)
        last, prev = df.iloc[-1], df.iloc[-2]
        if pd.isna(last["atr"]) or last["atr"] <= 0:
            return None

        # volatility filter: the stop distance must dwarf round-trip costs
        sl_dist = c.sl_atr_mult * last["atr"]
        if sl_dist / last["close"] < c.min_move_cost_ratio * self.cfg.round_trip_cost:
            return None

        uptrend = last["ema_fast"] > last["ema_slow"] and last["close"] > last["ema_trend"]
        downtrend = last["ema_fast"] < last["ema_slow"] and last["close"] < last["ema_trend"]

        price = float(last["close"])
        if uptrend and prev["rsi"] < c.rsi_long_cross <= last["rsi"]:
            return Signal(
                side="buy",
                entry_ref=price,
                stop_loss=price - sl_dist,
                take_profit=price + c.tp_r_multiple * sl_dist,
                atr_value=float(last["atr"]),
            )
        if downtrend and prev["rsi"] > c.rsi_short_cross >= last["rsi"]:
            return Signal(
                side="sell",
                entry_ref=price,
                stop_loss=price + sl_dist,
                take_profit=price - c.tp_r_multiple * sl_dist,
                atr_value=float(last["atr"]),
            )
        return None

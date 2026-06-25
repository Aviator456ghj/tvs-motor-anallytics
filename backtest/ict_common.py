"""Shared utilities for ICT strategy backtests against Delta Exchange data.

Every strategy script in this directory (run_silver_bullet.py, run_judas_swing.py,
etc.) is an independent bar-by-bar state machine -- they intentionally don't share
a single mega-engine, because each ICT setup has different entry mechanics (resting
order into a zone vs. market entry on confirmation) and folding them into one
generic loop would obscure the actual trading logic. What *is* shared is pulled
in here: data loading, fractal detection, and the conservative same-bar SL/TP
resolution every script needs.
"""
import time

import numpy as np
import pandas as pd

from fetch_delta_data import fetch_candles


def load_data(symbol="BTCUSDT", resolution="5m", lookback_days=30, atr_period=100):
    end = int(time.time())
    start = end - lookback_days * 86400
    df = fetch_candles(symbol, resolution, start, end)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    df["atr"] = tr.rolling(atr_period).mean()
    return df


def is_fractal_high(highs, p, k):
    h = highs[p]
    for i in range(1, k + 1):
        if p - i >= 0 and highs[p - i] >= h:
            return False
        if p + i < len(highs) and highs[p + i] >= h:
            return False
    return True


def is_fractal_low(lows, p, k):
    l = lows[p]
    for i in range(1, k + 1):
        if p - i >= 0 and lows[p - i] <= l:
            return False
        if p + i < len(lows) and lows[p + i] <= l:
            return False
    return True


def resolve_sl_tp(highs, lows, i, is_bull, sl, tp):
    """Conservative same-bar resolution: if a bar's range could have hit
    both SL and TP, assume SL hit first (no intrabar tick data to disambiguate)."""
    hit_sl = (lows[i] <= sl) if is_bull else (highs[i] >= sl)
    hit_tp = (highs[i] >= tp) if is_bull else (lows[i] <= tp)
    if hit_sl and hit_tp:
        return True, False
    return hit_sl, hit_tp


def summarize(closed_trades, starting_balance, final_balance):
    """closed_trades: list of dicts with an 'outcome_r' key (only CLOSED trades)."""
    wins = [t for t in closed_trades if t["outcome_r"] > 0]
    total_r = sum(t["outcome_r"] for t in closed_trades)
    win_rate = (len(wins) / len(closed_trades) * 100) if closed_trades else 0.0
    return (f"Trades: {len(closed_trades)} | Win rate: {win_rate:.1f}% | Total R: {total_r:+.2f} | "
            f"Balance: ${starting_balance:,.0f} -> ${final_balance:,.0f} "
            f"({(final_balance / starting_balance - 1) * 100:+.2f}%)")

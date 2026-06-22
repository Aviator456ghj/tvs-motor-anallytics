"""Backtest a genuine, well-documented trend-following system instead of
a social-media formula: the Donchian-channel breakout ("Turtle Trading")
approach.

Rules (textbook Turtle System parameters, not fitted to this data):
  - Enter long when close breaks above the highest high of the prior
    ENTRY_N bars; enter short when close breaks below the lowest low of
    the prior ENTRY_N bars. Flat-to-position only, no pyramiding.
  - Initial stop = entry +/- ATR_MULT * ATR(ATR_PERIOD), fixed (not
    trailed) for R-multiple bookkeeping.
  - Exit (if not stopped first) when close breaks the opposite Donchian
    channel using the shorter EXIT_N lookback.
  - Two historical parameter sets are tested: System 1 (20/10) and
    System 2 (55/20), both from the original Turtle rules - chosen
    because they're a fixed, public, pre-existing spec, not optimized
    on this dataset.

Compared against:
  - a random-entry control with identical exit/stop logic and matching
    trade frequency (same number of long/short entries), to isolate
    whether breakout *timing* adds anything over just holding
    trend-sized, stop-managed positions at random times
  - buy-and-hold over the same window, since BTC/ETH/SOL all had large
    trends in this sample and any trend-following system will look
    good purely from beta exposure unless it beats that directly
"""
import random

import numpy as np
import pandas as pd

from smc_backtest import INSTRUMENTS, load

ATR_PERIOD = 14
ATR_MULT = 2.0
RISK_PCT_PER_TRADE = 0.01
STARTING_CAPITAL = 10_000.0
N_RANDOM_TRIALS = 100

SYSTEMS = [("System 1 (20/10)", 20, 10), ("System 2 (55/20)", 55, 20)]


def compute_atr(df, period=ATR_PERIOD):
    high, low, close = df["high"].values, df["low"].values, df["close"].values
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr = np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
    atr = np.full(len(df), np.nan)
    atr[period] = tr[1 : period + 1].mean()
    for i in range(period + 1, len(df)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr


def rolling_max(arr, n):
    return pd.Series(arr).shift(1).rolling(n).max().values


def rolling_min(arr, n):
    return pd.Series(arr).shift(1).rolling(n).min().values


def simulate(df, channels, atr, entry_n, exit_n, entry_signal_idx=None):
    """entry_signal_idx: optional dict {bar_idx: direction} to override
    breakout-based entries with externally chosen (e.g. random) entries,
    keeping exit/stop logic identical."""
    high, low, close = df["high"].values, df["low"].values, df["close"].values
    upper_entry, lower_entry, upper_exit, lower_exit = channels

    trades = []
    position = 0
    entry_price = stop_price = risk = 0.0
    start = max(entry_n, exit_n, ATR_PERIOD) + 1

    for i in range(start, len(df)):
        if position == 0:
            if entry_signal_idx is not None:
                direction = entry_signal_idx.get(i)
            else:
                if close[i] > upper_entry[i]:
                    direction = 1
                elif close[i] < lower_entry[i]:
                    direction = -1
                else:
                    direction = None
            if direction and not np.isnan(atr[i]):
                position = direction
                entry_price = close[i]
                risk = ATR_MULT * atr[i]
                stop_price = entry_price - risk if direction == 1 else entry_price + risk
                entry_idx = i
        else:
            exit_price = None
            if position == 1:
                if low[i] <= stop_price:
                    exit_price = stop_price
                elif close[i] < lower_exit[i]:
                    exit_price = close[i]
            else:
                if high[i] >= stop_price:
                    exit_price = stop_price
                elif close[i] > upper_exit[i]:
                    exit_price = close[i]
            if exit_price is not None:
                pnl = (exit_price - entry_price) * position
                r = pnl / risk if risk > 0 else 0.0
                trades.append({"entry_idx": entry_idx, "exit_idx": i, "direction": position, "r": r})
                position = 0

    return trades


def summarize(trades, label):
    if not trades:
        return {"label": label, "n": 0}
    rs = np.array([t["r"] for t in trades])
    wins = sum(1 for t in trades if t["r"] > 0)

    equity, peak, max_dd = STARTING_CAPITAL, STARTING_CAPITAL, 0.0
    for r in rs:
        equity *= (1 + RISK_PCT_PER_TRADE * r)
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak)

    return {
        "label": label,
        "n": len(trades),
        "win_rate": wins / len(trades),
        "avg_r": float(rs.mean()),
        "total_r": float(rs.sum()),
        "final_equity": equity,
        "total_return_pct": (equity / STARTING_CAPITAL - 1) * 100,
        "max_drawdown_pct": max_dd * 100,
    }


def print_summary(s):
    if s["n"] == 0:
        print(f"  {s['label']}: no trades")
        return
    print(f"  {s['label']}: n={s['n']} win_rate={s['win_rate']:.1%} avg_R={s['avg_r']:+.3f} "
          f"total_R={s['total_r']:+.1f} final_equity=${s['final_equity']:,.0f} "
          f"({s['total_return_pct']:+.1f}%) max_drawdown={s['max_drawdown_pct']:.1f}%")


def run_instrument(instrument):
    df = load(instrument)
    atr = compute_atr(df)
    close = df["close"].values
    buy_hold_return = (close[-1] / close[0] - 1) * 100

    print(f"\n=== {instrument} ({len(df)} candles) — buy_and_hold_return={buy_hold_return:+.1f}% ===")

    high, low = df["high"].values, df["low"].values
    for label, entry_n, exit_n in SYSTEMS:
        channels = (rolling_max(high, entry_n), rolling_min(low, entry_n),
                    rolling_max(high, exit_n), rolling_min(low, exit_n))
        trades = simulate(df, channels, atr, entry_n, exit_n)
        s = summarize(trades, label)
        print_summary(s)

        random.seed(42)
        rand_summaries = []
        n_signals = s["n"] if s["n"] else 1
        start_bar = max(entry_n, exit_n, ATR_PERIOD) + 1
        for _ in range(N_RANDOM_TRIALS):
            rand_entries = {}
            for _ in range(n_signals):
                idx = random.randint(start_bar, len(df) - 1)
                rand_entries[idx] = random.choice([1, -1])
            rand_trades = simulate(df, channels, atr, entry_n, exit_n, entry_signal_idx=rand_entries)
            if rand_trades:
                rand_summaries.append(summarize(rand_trades, "random"))

        if rand_summaries and s["n"]:
            rand_avg_rs = [r["avg_r"] for r in rand_summaries]
            rand_mean, rand_std = float(np.mean(rand_avg_rs)), float(np.std(rand_avg_rs))
            z = (s["avg_r"] - rand_mean) / rand_std if rand_std > 0 else float("nan")
            rand_returns = float(np.mean([r["total_return_pct"] for r in rand_summaries]))
            print(f"    random-entry control ({len(rand_summaries)} trials, same exit/stop rules): "
                  f"avg_R={rand_mean:+.3f}±{rand_std:.3f}  avg_total_return={rand_returns:+.1f}%  "
                  f"z={z:.2f}")

    return buy_hold_return


if __name__ == "__main__":
    for inst in INSTRUMENTS:
        run_instrument(inst)

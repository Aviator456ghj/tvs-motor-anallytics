"""Simulate actual trade P&L for the sweep/BOS + leg-range/2.6 strategy.

The hit-rate backtest (smc_backtest.py) showed the *raw price / 2.6*
interpretation almost never resolves in tradeable time, so only the
*leg-range / 2.6* (Fib-extension style) interpretation produces real
trades. This script takes each structure event, opens a trade:

- Entry: close of the event bar.
- Stop: just beyond the wick that triggered the event (invalidation).
- Target: the leg-range/2.6 projected level.

and walks forward bar by bar to see whether the stop or target is hit
first, producing a real R-multiple (and $ P&L under a fixed-fractional
risk assumption) per trade - not just "did price touch the level."
"""
import random

import numpy as np

from smc_backtest import (
    FIXED_BASELINES,
    HORIZON_BARS,
    INSTRUMENTS,
    N_RANDOM_TRIALS,
    RANDOM_RANGE,
    detect_events,
    load,
    project_level_range,
)

STOP_BUFFER = 0.0005       # 0.05% beyond the triggering wick
RISK_PCT_PER_TRADE = 0.01  # 1% of equity risked per trade
STARTING_CAPITAL = 10_000.0


def simulate_trades(df, events, divisor: float):
    high, low, close = df["high"].values, df["low"].values, df["close"].values
    trades = []

    for ev in events:
        target = project_level_range(ev, divisor)
        if target is None:
            continue

        entry = close[ev.idx]
        if ev.direction == "bearish":
            stop = high[ev.idx] * (1 + STOP_BUFFER)
            risk = stop - entry
            reward = entry - target
        else:
            stop = low[ev.idx] * (1 - STOP_BUFFER)
            risk = entry - stop
            reward = target - entry

        if risk <= 0 or reward <= 0:
            continue  # degenerate setup (target already on wrong side of entry)

        end = min(ev.idx + 1 + HORIZON_BARS, len(df))
        outcome, r_multiple = "timeout", None
        for j in range(ev.idx + 1, end):
            if ev.direction == "bearish":
                stopped = high[j] >= stop
                hit_target = low[j] <= target
            else:
                stopped = low[j] <= stop
                hit_target = high[j] >= target
            if stopped:
                outcome, r_multiple = "loss", -1.0
                break
            if hit_target:
                outcome, r_multiple = "win", reward / risk
                break
        if r_multiple is None:
            last_close = close[end - 1]
            pnl = (entry - last_close) if ev.direction == "bearish" else (last_close - entry)
            r_multiple = pnl / risk

        trades.append({"idx": ev.idx, "direction": ev.direction, "outcome": outcome, "r": r_multiple})

    return trades


def summarize(trades, label: str):
    if not trades:
        return {"label": label, "n": 0}
    rs = np.array([t["r"] for t in trades])
    wins = sum(1 for t in trades if t["outcome"] == "win")
    losses = sum(1 for t in trades if t["outcome"] == "loss")
    timeouts = sum(1 for t in trades if t["outcome"] == "timeout")

    equity = STARTING_CAPITAL
    peak = equity
    max_dd = 0.0
    for r in rs:
        equity *= (1 + RISK_PCT_PER_TRADE * r)
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak)

    return {
        "label": label,
        "n": len(trades),
        "win_rate": wins / len(trades),
        "loss_rate": losses / len(trades),
        "timeout_rate": timeouts / len(trades),
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
    print(
        f"  {s['label']}: n={s['n']} win_rate={s['win_rate']:.1%} "
        f"avg_R={s['avg_r']:+.3f} total_R={s['total_r']:+.1f} "
        f"final_equity=${s['final_equity']:,.0f} ({s['total_return_pct']:+.1f}%) "
        f"max_drawdown={s['max_drawdown_pct']:.1f}%"
    )


def run_instrument(instrument: str):
    df = load(instrument)
    events = detect_events(df)
    print(f"\n=== {instrument} ({len(events)} structure events, "
          f"risk={RISK_PCT_PER_TRADE:.0%}/trade, start=${STARTING_CAPITAL:,.0f}) ===")

    trades_26 = simulate_trades(df, events, 2.6)
    s26 = summarize(trades_26, "2.6 divisor")
    print_summary(s26)

    for d in FIXED_BASELINES:
        s = summarize(simulate_trades(df, events, d), f"{d} divisor")
        print_summary(s)

    random.seed(42)
    random_avg_rs, random_returns = [], []
    for _ in range(N_RANDOM_TRIALS):
        d = random.uniform(*RANDOM_RANGE)
        trades = simulate_trades(df, events, d)
        if trades:
            s = summarize(trades, "random")
            random_avg_rs.append(s["avg_r"])
            random_returns.append(s["total_return_pct"])

    rand_mean_r, rand_std_r = float(np.mean(random_avg_rs)), float(np.std(random_avg_rs))
    z = (s26["avg_r"] - rand_mean_r) / rand_std_r if rand_std_r > 0 else float("nan")
    print(f"  random divisor baseline ({len(random_avg_rs)} trials): "
          f"avg_R={rand_mean_r:+.3f}±{rand_std_r:.3f}  "
          f"avg_total_return={np.mean(random_returns):+.1f}%")
    print(f"  2.6 avg_R vs random baseline: z={z:.2f}")

    return {"instrument": instrument, "s26": s26, "rand_mean_r": rand_mean_r, "rand_std_r": rand_std_r, "z": z}


if __name__ == "__main__":
    summary = [run_instrument(inst) for inst in INSTRUMENTS]

    print("\n=== Combined verdict (profitability) ===")
    for s in summary:
        verdict = "real profitability edge" if abs(s["z"]) > 1.96 and s["s26"]["avg_r"] > 0 else "no statistically significant profit edge"
        print(f"  {s['instrument']}: 2.6 avg_R={s['s26']['avg_r']:+.3f} "
              f"total_return={s['s26']['total_return_pct']:+.1f}% "
              f"vs random avg_R={s['rand_mean_r']:+.3f}±{s['rand_std_r']:.3f} (z={s['z']:.2f}) -> {verdict}")

"""Check reaction rates for divisor 2.6 and 26, with both a strict and a
loose definition of 'reaction', against a random-divisor control."""
import random

import numpy as np

from smc_backtest import (
    HORIZON_BARS,
    INSTRUMENTS,
    N_RANDOM_TRIALS,
    RANDOM_RANGE,
    detect_events,
    load,
    project_level_range,
)


def test_reaction(df, event, target, move_threshold, reaction_bars):
    high, low, close = df["high"].values, df["low"].values, df["close"].values
    end = min(event.idx + 1 + HORIZON_BARS, len(df))
    tol = 0.0025
    lo_band, hi_band = target * (1 - tol), target * (1 + tol)

    for j in range(event.idx + 1, end):
        if low[j] <= hi_band and high[j] >= lo_band:
            r_end = min(j + 1 + reaction_bars, len(df))
            for k in range(j, r_end):
                if event.direction == "bearish" and close[k] >= target * (1 + move_threshold):
                    return True, True
                if event.direction == "bullish" and close[k] <= target * (1 - move_threshold):
                    return True, True
            return True, False
    return False, False


def evaluate(df, events, divisor, move_threshold, reaction_bars):
    hits = reactions = 0
    for ev in events:
        target = project_level_range(ev, divisor)
        if target is None:
            continue
        hit, reacted = test_reaction(df, ev, target, move_threshold, reaction_bars)
        if hit:
            hits += 1
            if reacted:
                reactions += 1
    return reactions / hits if hits else 0.0, hits


def run(label, move_threshold, reaction_bars):
    print(f"\n--- {label} (reaction = {move_threshold:.2%} move within {reaction_bars} bars of touch) ---")
    for instrument in INSTRUMENTS:
        df = load(instrument)
        events = detect_events(df)

        r26, n26 = evaluate(df, events, 2.6, move_threshold, reaction_bars)
        r260, n260 = evaluate(df, events, 26, move_threshold, reaction_bars)

        random.seed(42)
        rand_rates = [evaluate(df, events, random.uniform(*RANDOM_RANGE), move_threshold, reaction_bars)[0]
                      for _ in range(N_RANDOM_TRIALS)]
        rand_mean, rand_std = float(np.mean(rand_rates)), float(np.std(rand_rates))

        print(f"  {instrument}: divisor=2.6 reaction_rate={r26:.1%} (n={n26})  "
              f"divisor=26 reaction_rate={r260:.1%} (n={n260})  "
              f"random_baseline={rand_mean:.1%}±{rand_std:.1%}")


if __name__ == "__main__":
    run("Strict (matches earlier backtest)", move_threshold=0.01, reaction_bars=20)
    run("Loose (any pullback counts)", move_threshold=0.002, reaction_bars=50)

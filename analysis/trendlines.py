"""Backtest classic trendlines and Gann-style angle lines as
support/resistance and breakout-continuation signals.

Two distinct, mechanically-defined concepts:

1. Trendlines: connect the two most recent swing lows (ascending support)
   or two most recent swing highs (descending resistance), extend the
   line forward at that fixed slope, and test:
     (a) reaction: when price later touches the extended line, does it
         bounce off it (support/resistance holding)?
     (b) break+continuation: when price closes through the line, does
         price keep moving in the breakout direction afterward (the
         textbook "broken support becomes resistance, trend continues"
         claim)?

2. Gann angles: from major swing pivots, draw angle lines at fixed
   price-per-bar ratios (1x1, 2x1, 1x2, 4x1, 1x4) using the pivot's ATR
   as the price unit (so the "angle" is scale-invariant across
   instruments, unlike literal 45-degree Gann lines which assume 1
   price point = 1 time unit). Same reaction test as trendlines.

Baselines on the same line set, to isolate whether the specific
connect-the-dots slope (or specific Gann ratio) does anything over an
arbitrary line at that location:
  - reaction test: reshuffle slopes across same-side lines (same origin/
    anchor, swapped slope) and re-measure reaction-given-touch.
  - break+continuation test: plain 50% coin-flip baseline via z-score
    (direction either continues or doesn't, no inherent skew).
"""
import random

import numpy as np

from smc_backtest import INSTRUMENTS, find_fractals, load
from pressure_formula import build_alternating_swings
from donchian_breakout import compute_atr

FRACTAL_N = 2
MAJOR_FRACTAL_N = 5
GANN_RATIOS = [1.0, 2.0, 0.5, 4.0, 0.25]

TOUCH_TOL = 0.0015
CLEARANCE_TOL = 0.01    # price must move this far from the line before a later touch counts as a real retest
REACTION_BARS = 8
REACTION_MOVE = 0.003
BREAK_BUFFER = 0.0005
CONTINUATION_BARS = 20
MAX_LINE_BARS = 200
N_RANDOM_TRIALS = 50


def detect_trendlines(df, fractal_n=FRACTAL_N):
    swings = build_alternating_swings(df, fractal_n)
    lows = [(idx, price) for idx, t, price in swings if t == "low"]
    highs = [(idx, price) for idx, t, price in swings if t == "high"]

    lines = []
    for (idx1, p1), (idx2, p2) in zip(lows, lows[1:]):
        if p2 > p1:
            slope = (p2 - p1) / (idx2 - idx1)
            lines.append({"side": 1, "origin_idx": idx1, "origin_price": p1, "slope": slope, "start_idx": idx2})
    for (idx1, p1), (idx2, p2) in zip(highs, highs[1:]):
        if p2 < p1:
            slope = (p2 - p1) / (idx2 - idx1)
            lines.append({"side": -1, "origin_idx": idx1, "origin_price": p1, "slope": slope, "start_idx": idx2})
    return lines


def detect_gann_angles(df, fractal_n=MAJOR_FRACTAL_N, ratios=GANN_RATIOS):
    atr = compute_atr(df)
    high, low = df["high"].values, df["low"].values
    swing_high_idx, swing_low_idx = find_fractals(df, fractal_n)

    lines = []
    for idx in swing_low_idx:
        if np.isnan(atr[idx]):
            continue
        unit = atr[idx]
        for r in ratios:
            lines.append({"side": 1, "origin_idx": idx, "origin_price": low[idx],
                           "slope": r * unit, "start_idx": idx + 1, "ratio": r})
    for idx in swing_high_idx:
        if np.isnan(atr[idx]):
            continue
        unit = atr[idx]
        for r in ratios:
            lines.append({"side": -1, "origin_idx": idx, "origin_price": high[idx],
                           "slope": -r * unit, "start_idx": idx + 1, "ratio": r})
    return lines


def line_price(line, bar_idx):
    return line["origin_price"] + line["slope"] * (bar_idx - line["origin_idx"])


def test_line_reaction(df, line, horizon_bars=MAX_LINE_BARS):
    """A 'touch' only counts as a genuine retest if price first cleared
    away from the line by CLEARANCE_TOL at some earlier bar - otherwise
    every line trivially 'touches' at bar 1, since its anchor point IS
    the most recent price action that defined it."""
    high, low, close = df["high"].values, df["low"].values, df["close"].values
    side = line["side"]
    start = line["start_idx"]
    end = min(start + horizon_bars, len(df) - 1)

    cleared = False
    for j in range(start, end):
        level = line_price(line, j)
        if level <= 0:
            continue
        if not cleared:
            if abs(close[j] - level) / level > CLEARANCE_TOL:
                cleared = True
            continue
        lo_band, hi_band = level * (1 - TOUCH_TOL), level * (1 + TOUCH_TOL)
        if low[j] <= hi_band and high[j] >= lo_band:
            r_end = min(j + 1 + REACTION_BARS, len(df))
            for k in range(j, r_end):
                if (close[k] - level) * side >= REACTION_MOVE * level:
                    return True, True
            return True, False
    return False, False


def test_line_break(df, line, horizon_bars=MAX_LINE_BARS):
    close = df["close"].values
    side = line["side"]
    start = line["start_idx"]
    end = min(start + horizon_bars, len(df))

    break_idx = None
    for j in range(start, end):
        level = line_price(line, j)
        if level <= 0:
            continue
        if side == 1 and close[j] < level * (1 - BREAK_BUFFER):
            break_idx = j
            break
        if side == -1 and close[j] > level * (1 + BREAK_BUFFER):
            break_idx = j
            break
    if break_idx is None:
        return None

    target = min(break_idx + CONTINUATION_BARS, len(close) - 1)
    if target <= break_idx:
        return None
    predicted = "bearish" if side == 1 else "bullish"
    actual = "bullish" if close[target] > close[break_idx] else "bearish"
    return {"predicted": predicted, "actual": actual, "hit": predicted == actual}


def reaction_stats(df, lines, label):
    touches = reactions = 0
    for line in lines:
        touched, reacted = test_line_reaction(df, line)
        if touched:
            touches += 1
            if reacted:
                reactions += 1
    n = len(lines)
    rate = reactions / touches if touches else 0.0
    print(f"  {label}: n_lines={n} touch_rate={touches / n if n else 0:.1%} "
          f"reaction_given_touch={rate:.1%} (touches={touches})")
    return {"n": n, "touches": touches, "reactions": reactions, "reaction_rate": rate}


def random_reaction_baseline(df, lines, n_trials=N_RANDOM_TRIALS, seed=42):
    rng = random.Random(seed)
    by_side = {1: [l["slope"] for l in lines if l["side"] == 1],
               -1: [l["slope"] for l in lines if l["side"] == -1]}
    rates = []
    for _ in range(n_trials):
        shuffled_1 = by_side[1].copy()
        shuffled_m1 = by_side[-1].copy()
        rng.shuffle(shuffled_1)
        rng.shuffle(shuffled_m1)
        cursors = {1: iter(shuffled_1), -1: iter(shuffled_m1)}
        touches = reactions = 0
        for line in lines:
            rand_line = dict(line)
            rand_line["slope"] = next(cursors[line["side"]])
            touched, reacted = test_line_reaction(df, rand_line)
            if touched:
                touches += 1
                if reacted:
                    reactions += 1
        if touches:
            rates.append(reactions / touches)
    return float(np.mean(rates)), float(np.std(rates))


def break_continuation_stats(df, lines, label):
    results = [test_line_break(df, line) for line in lines]
    results = [r for r in results if r is not None]
    n = len(results)
    if n == 0:
        print(f"  {label}: no breaks found")
        return {"n": 0}
    hits = sum(r["hit"] for r in results)
    p = hits / n
    se = (0.5 * 0.5 / n) ** 0.5
    z = (p - 0.5) / se if se > 0 else float("nan")
    print(f"  {label}: n_breaks={n} continuation_hit_rate={p:.1%} (vs 50% random, z={z:.2f})")
    return {"n": n, "hit_rate": p, "z": z}


def run_instrument(instrument):
    df = load(instrument)
    print(f"\n=== {instrument} ({len(df)} candles) ===")

    trendlines = detect_trendlines(df)
    support = [l for l in trendlines if l["side"] == 1]
    resistance = [l for l in trendlines if l["side"] == -1]
    print(f" -- classic trendlines ({len(trendlines)} total: {len(support)} ascending support, "
          f"{len(resistance)} descending resistance) --")
    reaction_stats(df, support, "ascending support trendline")
    reaction_stats(df, resistance, "descending resistance trendline")
    all_stats = reaction_stats(df, trendlines, "ALL trendlines combined")
    rand_mean, rand_std = random_reaction_baseline(df, trendlines)
    print(f"  random-slope control ({N_RANDOM_TRIALS} trials, same anchors): "
          f"reaction_given_touch={rand_mean:.1%}±{rand_std:.1%}")

    z = (all_stats["reaction_rate"] - rand_mean) / rand_std if rand_std > 0 else float("nan")
    print(f"  trendlines vs random-slope control: z={z:.2f}")

    break_continuation_stats(df, support, "ascending support BREAK -> bearish continuation")
    break_continuation_stats(df, resistance, "descending resistance BREAK -> bullish continuation")
    break_continuation_stats(df, trendlines, "ALL trendline breaks combined")

    print(f" -- Gann-style ATR-scaled angle lines (ratios {GANN_RATIOS}) --")
    gann_lines = detect_gann_angles(df)
    for r in GANN_RATIOS:
        sub = [l for l in gann_lines if l["ratio"] == r]
        reaction_stats(df, sub, f"  ratio {r}x1" if r >= 1 else f"  ratio 1x{1/r:.0f}")
    gann_all_stats = reaction_stats(df, gann_lines, "ALL Gann angles combined")
    gr_mean, gr_std = random_reaction_baseline(df, gann_lines)
    print(f"  random-slope control ({N_RANDOM_TRIALS} trials, same pivots): "
          f"reaction_given_touch={gr_mean:.1%}±{gr_std:.1%}")
    gz = (gann_all_stats["reaction_rate"] - gr_mean) / gr_std if gr_std > 0 else float("nan")
    print(f"  Gann angles vs random-slope control: z={gz:.2f}")
    break_continuation_stats(df, gann_lines, "ALL Gann angle breaks combined")


if __name__ == "__main__":
    for inst in INSTRUMENTS:
        run_instrument(inst)

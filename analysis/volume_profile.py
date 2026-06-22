"""Backtest the 'previous-day fixed-range volume profile' strategy:

For each calendar day D, build a volume profile from D's bars and find:
  - POC (point of control): price level where the most volume traded
  - VAH / VAL (value area high/low): bounds of the range containing 70%
    of D's volume around the POC

Claim being tested: on day D+1, when price pulls back to POC/VAH/VAL it
"stalls, rejects, and moves with conviction" - i.e. it acts as support/
resistance more reliably than an arbitrary level, because it's backed by
real traded volume instead of being "just some line you drew."

Baselines run on the same days:
  - naive prior-day levels: prior day's high / low / close (lines anyone
    can draw without a volume profile)
  - random level: uniform random price within the prior day's range

A "touch" = price trades within HIT_TOL of the level on day D+1.
A "reaction" = within REACTION_BARS bars of the touch, price closes back
out to the side it approached from by REACTION_MOVE - i.e. the level held
as support/resistance rather than being punched through.
"""
import random
import sys

import numpy as np
import pandas as pd

from smc_backtest import INSTRUMENTS, load

N_BINS = 50
VALUE_AREA_PCT = 0.70
HIT_TOL = 0.0015
REACTION_BARS = 8          # ~2h on 15m
REACTION_MOVE = 0.003       # 0.3% close-back move counts as a rejection
N_RANDOM_LEVELS_PER_DAY = 3
N_RANDOM_TRIALS = 50


def split_by_day(df: pd.DataFrame):
    ts = pd.to_datetime(df["timestamp_ms"], unit="ms")
    day = ts.dt.date
    groups = df.groupby(day).indices  # date -> array of positional indices
    days = sorted(groups.keys())
    return [(d, groups[d]) for d in days]


def compute_profile(df, idx):
    high, low, vol = df["high"].values[idx], df["low"].values[idx], df["volume"].values[idx]
    day_low, day_high = low.min(), high.max()
    if day_high <= day_low:
        return None

    bin_edges = np.linspace(day_low, day_high, N_BINS + 1)
    bin_vol = np.zeros(N_BINS)
    for l, h, v in zip(low, high, vol):
        if h <= l:
            b = min(int((l - day_low) / (day_high - day_low) * N_BINS), N_BINS - 1)
            bin_vol[b] += v
            continue
        lo_b = max(int((l - day_low) / (day_high - day_low) * N_BINS), 0)
        hi_b = min(int((h - day_low) / (day_high - day_low) * N_BINS), N_BINS - 1)
        for b in range(lo_b, hi_b + 1):
            overlap_lo, overlap_hi = max(l, bin_edges[b]), min(h, bin_edges[b + 1])
            frac = max(overlap_hi - overlap_lo, 0) / (h - l)
            bin_vol[b] += v * frac

    total_vol = bin_vol.sum()
    if total_vol <= 0:
        return None

    poc_bin = int(np.argmax(bin_vol))
    lo_bound, hi_bound = poc_bin, poc_bin
    cum_vol = bin_vol[poc_bin]
    while cum_vol < VALUE_AREA_PCT * total_vol and (lo_bound > 0 or hi_bound < N_BINS - 1):
        vol_below = bin_vol[lo_bound - 1] if lo_bound > 0 else -1
        vol_above = bin_vol[hi_bound + 1] if hi_bound < N_BINS - 1 else -1
        if vol_above >= vol_below:
            hi_bound += 1
            cum_vol += bin_vol[hi_bound]
        else:
            lo_bound -= 1
            cum_vol += bin_vol[lo_bound]

    bin_mid = (bin_edges[:-1] + bin_edges[1:]) / 2
    return {
        "poc": float(bin_mid[poc_bin]),
        "vah": float(bin_edges[hi_bound + 1]),
        "val": float(bin_edges[lo_bound]),
        "day_high": float(day_high),
        "day_low": float(day_low),
    }


def test_level_reaction(df, start_idx, end_idx, level):
    high, low, close = df["high"].values, df["low"].values, df["close"].values
    lo_band, hi_band = level * (1 - HIT_TOL), level * (1 + HIT_TOL)

    for j in range(start_idx, end_idx):
        if low[j] <= hi_band and high[j] >= lo_band:
            side = 1 if close[j - 1] > level else -1  # approaching from above(+1) or below(-1)
            r_end = min(j + 1 + REACTION_BARS, end_idx)
            for k in range(j, r_end):
                if (close[k] - level) * side >= REACTION_MOVE * level:
                    return True, True
            return True, False
    return False, False


def evaluate_level_type(df, day_ranges, level_fn):
    touches = reactions = evaluated = 0
    for i in range(len(day_ranges) - 1):
        _, idx_today = day_ranges[i]
        _, idx_next = day_ranges[i + 1]
        profile = compute_profile(df, idx_today)
        if profile is None:
            continue
        level = level_fn(profile)
        if level is None:
            continue
        evaluated += 1
        start_idx, end_idx = idx_next[0], idx_next[-1] + 1
        touched, reacted = test_level_reaction(df, start_idx, end_idx, level)
        if touched:
            touches += 1
            if reacted:
                reactions += 1
    return {
        "n_days": evaluated,
        "touch_rate": touches / evaluated if evaluated else 0.0,
        "reaction_rate_given_touch": reactions / touches if touches else 0.0,
        "touches": touches,
    }


def run_instrument(instrument):
    df = load(instrument)
    day_ranges = split_by_day(df)
    print(f"\n=== {instrument} ({len(df)} candles, {len(day_ranges)} calendar days) ===")

    level_types = {
        "POC": lambda p: p["poc"],
        "VAH": lambda p: p["vah"],
        "VAL": lambda p: p["val"],
        "prior_high": lambda p: p["day_high"],
        "prior_low": lambda p: p["day_low"],
    }
    results = {}
    for name, fn in level_types.items():
        r = evaluate_level_type(df, day_ranges, fn)
        results[name] = r
        print(f"  {name}: n_days={r['n_days']} touch_rate={r['touch_rate']:.1%} "
              f"reaction_given_touch={r['reaction_rate_given_touch']:.1%} (touches={r['touches']})")

    random.seed(42)
    rand_reaction_rates = []
    for _ in range(N_RANDOM_TRIALS):
        def rand_level(p, _rng=random):
            return _rng.uniform(p["day_low"], p["day_high"])
        r = evaluate_level_type(df, day_ranges, rand_level)
        if r["touches"]:
            rand_reaction_rates.append(r["reaction_rate_given_touch"])
    rand_mean, rand_std = float(np.mean(rand_reaction_rates)), float(np.std(rand_reaction_rates))
    print(f"  random level in prior-day range ({len(rand_reaction_rates)} trials): "
          f"reaction_given_touch={rand_mean:.1%}±{rand_std:.1%}")

    for name in ["POC", "VAH", "VAL"]:
        rr = results[name]["reaction_rate_given_touch"]
        z = (rr - rand_mean) / rand_std if rand_std > 0 else float("nan")
        print(f"  {name} vs random level: z={z:.2f}")

    return {"instrument": instrument, "results": results, "rand_mean": rand_mean, "rand_std": rand_std}


if __name__ == "__main__":
    if len(sys.argv) > 2:
        REACTION_MOVE = float(sys.argv[1])
        REACTION_BARS = int(sys.argv[2])
        print(f"(override) REACTION_MOVE={REACTION_MOVE:.3%}  REACTION_BARS={REACTION_BARS}")
    summary = [run_instrument(inst) for inst in INSTRUMENTS]

    print("\n=== Combined verdict (does the level hold as support/resistance more than chance?) ===")
    for s in summary:
        print(f"\n  {s['instrument']}:")
        for name in ["POC", "VAH", "VAL", "prior_high", "prior_low"]:
            rr = s["results"][name]["reaction_rate_given_touch"]
            z = (rr - s["rand_mean"]) / s["rand_std"] if s["rand_std"] > 0 else float("nan")
            verdict = "edge over random level" if z > 1.96 else "no statistically significant edge"
            print(f"    {name}: reaction_rate={rr:.1%} vs random={s['rand_mean']:.1%}±{s['rand_std']:.1%} (z={z:.2f}) -> {verdict}")

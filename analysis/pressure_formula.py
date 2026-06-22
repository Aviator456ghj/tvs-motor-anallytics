"""Backtest the social-media 'Pressure formula' for projecting the next
swing extreme of a trend:

    Next Resistance (uptrend) = B * C / A
    Next Support    (downtrend) = B * C / A

where, for an uptrend leg: A = swing low that starts the trend,
B = swing high that ends the leg, C = the following higher-low
(retracement that does NOT break back below A). The claim is that the
next swing high will land near B*C/A.

For a downtrend the roles mirror: A = swing high that starts the trend,
B = swing low that ends the leg, C = the following lower-high
(retracement that does NOT break back above A); claim is the next swing
low will land near B*C/A.

Note B*C/A == C*(B/A): "the next leg gains the same % move (B/A) as the
previous leg, measured from the retracement point C." That's a real,
known concept (proportional / equal-percentage swing projection), so it
is tested here on real data against three baselines:

  - naive persistence:      predicted = B            (trend just stalls)
  - additive measured move: predicted = C + (B - A)  (equal *points*, not %)
  - random ratio:           predicted = C * (shuffled B/A from elsewhere)

using the same swing/fractal detection as smc_backtest.py.
"""
import random
import sys

import numpy as np

from smc_backtest import INSTRUMENTS, find_fractals, load

FRACTAL_N = 2
N_RANDOM_TRIALS = 200
TOLERANCES = [0.02, 0.05, 0.10]


def build_alternating_swings(df, fractal_n=FRACTAL_N):
    swing_high_idx, swing_low_idx = find_fractals(df, fractal_n)
    high, low = df["high"].values, df["low"].values

    points = [(i, "high", high[i]) for i in swing_high_idx] + \
              [(i, "low", low[i]) for i in swing_low_idx]
    points.sort(key=lambda p: p[0])

    alternating = []
    for p in points:
        if alternating and alternating[-1][1] == p[1]:
            prev = alternating[-1]
            if (p[1] == "high" and p[2] > prev[2]) or (p[1] == "low" and p[2] < prev[2]):
                alternating[-1] = p
            continue
        alternating.append(p)
    return alternating


def build_triples(swings):
    """Yield (A, B, C, actual_next) tuples for both uptrend and downtrend legs."""
    triples = []
    for i in range(len(swings) - 3):
        s0, s1, s2, s3 = swings[i], swings[i + 1], swings[i + 2], swings[i + 3]
        types = (s0[1], s1[1], s2[1], s3[1])
        if types == ("low", "high", "low", "high") and s2[2] > s0[2]:
            A, B, C, actual = s0[2], s1[2], s2[2], s3[2]
            triples.append({"direction": "up", "idx": s2[0], "A": A, "B": B, "C": C, "actual": actual})
        elif types == ("high", "low", "high", "low") and s2[2] < s0[2]:
            A, B, C, actual = s0[2], s1[2], s2[2], s3[2]
            triples.append({"direction": "down", "idx": s2[0], "A": A, "B": B, "C": C, "actual": actual})
    return triples


def pct_error(predicted, actual):
    return (predicted - actual) / actual


def summarize(label, errors):
    errors = np.array(errors)
    out = {"label": label, "n": len(errors), "mean_abs_pct_err": float(np.mean(np.abs(errors)))}
    for tol in TOLERANCES:
        out[f"hit_rate_{tol:.0%}"] = float(np.mean(np.abs(errors) <= tol))
    return out


def print_summary(s):
    tol_str = "  ".join(f"hit@{t:.0%}={s[f'hit_rate_{t:.0%}']:.1%}" for t in TOLERANCES)
    print(f"  {s['label']}: n={s['n']} mean_abs_err={s['mean_abs_pct_err']:.1%}  {tol_str}")


def run_instrument(instrument, fractal_n=FRACTAL_N):
    df = load(instrument)
    swings = build_alternating_swings(df, fractal_n)
    triples = build_triples(swings)
    print(f"\n=== {instrument} (fractal_n={fractal_n}, {len(df)} candles, {len(swings)} swings, {len(triples)} A-B-C trend legs) ===")

    if not triples:
        print("  no qualifying trend legs found")
        return None

    formula_err = [pct_error(t["B"] * t["C"] / t["A"], t["actual"]) for t in triples]
    naive_err = [pct_error(t["B"], t["actual"]) for t in triples]
    additive_err = [pct_error(t["C"] + (t["B"] - t["A"]), t["actual"]) for t in triples]

    s_formula = summarize("pressure formula (B*C/A)", formula_err)
    s_naive = summarize("naive persistence (B)", naive_err)
    s_additive = summarize("additive measured move (C+(B-A))", additive_err)
    print_summary(s_formula)
    print_summary(s_naive)
    print_summary(s_additive)

    ratios = [t["B"] / t["A"] for t in triples]
    random.seed(42)
    random_hit_rates = {tol: [] for tol in TOLERANCES}
    random_mean_abs_errs = []
    for _ in range(N_RANDOM_TRIALS):
        shuffled = ratios.copy()
        random.shuffle(shuffled)
        rand_err = [pct_error(t["C"] * r, t["actual"]) for t, r in zip(triples, shuffled)]
        s_rand = summarize("random", rand_err)
        random_mean_abs_errs.append(s_rand["mean_abs_pct_err"])
        for tol in TOLERANCES:
            random_hit_rates[tol].append(s_rand[f"hit_rate_{tol:.0%}"])

    rand_mean_err, rand_std_err = float(np.mean(random_mean_abs_errs)), float(np.std(random_mean_abs_errs))
    z_err = (s_formula["mean_abs_pct_err"] - rand_mean_err) / rand_std_err if rand_std_err > 0 else float("nan")
    print(f"  random ratio baseline ({N_RANDOM_TRIALS} shuffles): mean_abs_err={rand_mean_err:.1%}±{rand_std_err:.1%}  "
          + "  ".join(f"hit@{t:.0%}={np.mean(random_hit_rates[t]):.1%}±{np.std(random_hit_rates[t]):.1%}" for t in TOLERANCES))
    print(f"  formula vs random mean_abs_err: z={z_err:.2f} (negative z = formula has LOWER error than random, i.e. better)")

    return {
        "instrument": instrument,
        "s_formula": s_formula,
        "s_naive": s_naive,
        "s_additive": s_additive,
        "rand_mean_err": rand_mean_err,
        "rand_std_err": rand_std_err,
        "z_err": z_err,
    }


if __name__ == "__main__":
    fractal_n = int(sys.argv[1]) if len(sys.argv) > 1 else FRACTAL_N
    instruments = sys.argv[2].split(",") if len(sys.argv) > 2 else INSTRUMENTS
    summary = [run_instrument(inst, fractal_n) for inst in instruments]
    summary = [s for s in summary if s]

    print("\n=== Combined verdict ===")
    for s in summary:
        edge = abs(s["z_err"]) > 1.96 and s["z_err"] < 0
        verdict = "formula meaningfully beats random ratio projection" if edge else "no statistically significant edge over a random ratio"
        better_than_naive = s["s_formula"]["mean_abs_pct_err"] < s["s_naive"]["mean_abs_pct_err"]
        better_than_additive = s["s_formula"]["mean_abs_pct_err"] < s["s_additive"]["mean_abs_pct_err"]
        print(f"  {s['instrument']}: formula_err={s['s_formula']['mean_abs_pct_err']:.1%} "
              f"naive_err={s['s_naive']['mean_abs_pct_err']:.1%} "
              f"additive_err={s['s_additive']['mean_abs_pct_err']:.1%} "
              f"random_err={s['rand_mean_err']:.1%}±{s['rand_std_err']:.1%} (z={s['z_err']:.2f}) "
              f"-> {verdict}; beats naive={better_than_naive}; beats additive={better_than_additive}")

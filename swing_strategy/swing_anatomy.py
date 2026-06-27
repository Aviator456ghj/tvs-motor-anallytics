"""
Swing Anatomy: a full mathematical decode of every detected swing leg.

For each of the 69 swing legs (same 8% zig-zag pivots used by the
strategy backtests) this computes:
  - magnitude ($ and % / log-return), duration (days), velocity ($/day)
  - the ratio of this leg's range to the PRIOR leg's range, matched
    against the canonical Fibonacci ratio set
  - the ratio of this leg's DURATION to the prior leg's duration
    (Fibonacci time theory), matched the same way
  - which retracement "zone" this leg fell into relative to the
    immediately preceding leg (shallow / golden 38.2-61.8% / deep 78.6% /
    full 100% / extension >100%) - this is the direct, falsifiable test of
    the original strategy's Phase 2 premise that price "stalls" at those
    specific lines.

Then runs a Monte Carlo significance test: are real swings actually more
clustered around Fibonacci ratios than same-mean/variance random noise
would produce by chance?
"""
import csv
import math
import random
import statistics as stats

from measured_swing_backtest import load_data, find_pivots, ZIGZAG_THRESHOLD

DAILY_SRC = "data/btc_usd_daily.csv"
OUT_CSV = "results_swing_anatomy.csv"

FIB_RATIOS = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.414, 1.618, 2.0, 2.618, 3.618, 4.236]
RETRACE_ZONES = [
    (0.0, 0.382, "SHALLOW (<38.2%)"),
    (0.382, 0.618, "GOLDEN ZONE (38.2-61.8%)"),
    (0.618, 0.786, "DEEP (61.8-78.6%)"),
    (0.786, 1.0, "FULL (78.6-100%)"),
    (1.0, float("inf"), "EXTENSION (>100%)"),
]


def nearest_fib(ratio):
    best = min(FIB_RATIOS, key=lambda f: abs(math.log(ratio) - math.log(f)))
    dev_pct = (ratio - best) / best * 100
    return best, dev_pct


def zone_for(ratio):
    for lo, hi, name in RETRACE_ZONES:
        if lo <= ratio < hi:
            return name
    return "EXTENSION (>100%)"


def decode_swings(bars, pivots):
    rows = []
    for i in range(len(pivots) - 1):
        p0, p1 = pivots[i], pivots[i + 1]
        rng = abs(p1.price - p0.price)
        pct = rng / p0.price * 100
        log_ret = math.log(p1.price / p0.price)
        duration = p1.idx - p0.idx
        duration = max(duration, 1)
        velocity = rng / duration
        direction = "UP" if p1.price > p0.price else "DOWN"

        row = {
            "leg": i + 1, "direction": direction,
            "start_date": bars[p0.idx]["date"], "end_date": bars[p1.idx]["date"],
            "start_price": p0.price, "end_price": p1.price,
            "range_abs": rng, "range_pct": pct, "log_return": log_ret,
            "duration_days": duration, "velocity_per_day": velocity,
        }

        if i > 0:
            prev_rng = rows[i - 1]["range_abs"]
            prev_dur = rows[i - 1]["duration_days"]
            ratio = rng / prev_rng
            fib, dev = nearest_fib(ratio)
            time_ratio = duration / prev_dur
            tfib, tdev = nearest_fib(time_ratio)
            row.update({
                "ratio_to_prior_leg": ratio, "nearest_fib": fib, "fib_deviation_pct": dev,
                "zone_vs_prior": zone_for(ratio),
                "time_ratio_to_prior": time_ratio, "nearest_time_fib": tfib, "time_fib_deviation_pct": tdev,
            })
        else:
            row.update({
                "ratio_to_prior_leg": None, "nearest_fib": None, "fib_deviation_pct": None,
                "zone_vs_prior": None,
                "time_ratio_to_prior": None, "nearest_time_fib": None, "time_fib_deviation_pct": None,
            })
        rows.append(row)
    return rows


def monte_carlo_fib_clustering(ratios, tolerance=0.10, trials=50000, seed=42):
    """Are observed leg-to-leg ratios closer to Fibonacci levels than chance
    given the same underlying (lognormal) distribution would produce?"""
    log_ratios = [math.log(r) for r in ratios]
    mu = stats.mean(log_ratios)
    sigma = stats.pstdev(log_ratios)

    def frac_matching(sample):
        hits = 0
        for r in sample:
            for f in FIB_RATIOS:
                if abs(r - f) / f <= tolerance:
                    hits += 1
                    break
        return hits / len(sample)

    actual_frac = frac_matching(ratios)

    rng = random.Random(seed)
    sim_fracs = []
    n = len(ratios)
    for _ in range(trials):
        sample = [math.exp(rng.gauss(mu, sigma)) for _ in range(n)]
        sim_fracs.append(frac_matching(sample))

    exp_mean = stats.mean(sim_fracs)
    exp_std = stats.pstdev(sim_fracs)
    z = (actual_frac - exp_mean) / exp_std if exp_std else float("nan")
    p_value = sum(1 for f in sim_fracs if f >= actual_frac) / trials
    return actual_frac, exp_mean, exp_std, z, p_value


def linreg(xs, ys):
    n = len(xs)
    mx, my = stats.mean(xs), stats.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx
    a = my - b * mx
    yhat = [a + b * x for x in xs]
    ss_res = sum((y - h) ** 2 for y, h in zip(ys, yhat))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot else 0
    return a, b, r2


def write_csv(rows):
    cols = ["leg", "direction", "start_date", "end_date", "start_price", "end_price",
            "range_abs", "range_pct", "log_return", "duration_days", "velocity_per_day",
            "ratio_to_prior_leg", "nearest_fib", "fib_deviation_pct", "zone_vs_prior",
            "time_ratio_to_prior", "nearest_time_fib", "time_fib_deviation_pct"]
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            out = {}
            for c in cols:
                v = r[c]
                out[c] = f"{v:.4f}" if isinstance(v, float) else v
            w.writerow(out)


def main():
    bars = load_data(DAILY_SRC)
    pivots = find_pivots(bars, ZIGZAG_THRESHOLD)
    rows = decode_swings(bars, pivots)
    write_csv(rows)

    print("=" * 100)
    print(f"SWING ANATOMY - {len(rows)} legs decoded (8% zig-zag, {bars[0]['date']} -> {bars[-1]['date']})")
    print("=" * 100)
    print(f"{'#':>3} {'Dir':<4} {'Start':<11} {'End':<11} {'Range%':>8} {'Days':>5} {'$/day':>9} "
          f"{'Ratio->Prior':>12} {'Fib':>7} {'Dev%':>7} {'Zone':<24}")
    for r in rows:
        ratio_s = f"{r['ratio_to_prior_leg']:.3f}" if r['ratio_to_prior_leg'] else "-"
        fib_s = f"{r['nearest_fib']:.3f}" if r['nearest_fib'] else "-"
        dev_s = f"{r['fib_deviation_pct']:+.1f}" if r['fib_deviation_pct'] is not None else "-"
        zone_s = r['zone_vs_prior'] or "-"
        print(f"{r['leg']:>3} {r['direction']:<4} {r['start_date']:<11} {r['end_date']:<11} "
              f"{r['range_pct']:>7.1f}% {r['duration_days']:>5} {r['velocity_per_day']:>9.1f} "
              f"{ratio_s:>12} {fib_s:>7} {dev_s:>7} {zone_s:<24}")

    print()
    print("-" * 100)
    print("DISTRIBUTION STATISTICS")
    print("-" * 100)
    pcts = [r["range_pct"] for r in rows]
    durs = [r["duration_days"] for r in rows]
    vels = [r["velocity_per_day"] for r in rows]
    log_pcts = [math.log(r["range_abs"] / r["start_price"] + 1) for r in rows]
    print(f"Range %:    mean={stats.mean(pcts):.1f}%  median={stats.median(pcts):.1f}%  "
          f"stdev={stats.pstdev(pcts):.1f}%  min={min(pcts):.1f}%  max={max(pcts):.1f}%")
    print(f"Duration:   mean={stats.mean(durs):.1f}d  median={stats.median(durs):.1f}d  "
          f"stdev={stats.pstdev(durs):.1f}d  min={min(durs)}d  max={max(durs)}d")
    print(f"Velocity:   mean=${stats.mean(vels):,.0f}/day  median=${stats.median(vels):,.0f}/day  "
          f"stdev=${stats.pstdev(vels):,.0f}/day")

    # power-law scaling: log(duration) vs log(range_abs)
    log_range = [math.log(r["range_abs"]) for r in rows]
    log_dur = [math.log(r["duration_days"]) for r in rows]
    a, b, r2 = linreg(log_range, log_dur)
    print(f"\nScaling law  log(duration) = {a:.3f} + {b:.3f} * log(range$)   R^2={r2:.3f}")
    print(f"  -> duration scales roughly as range^{b:.2f}; "
          f"{'bigger swings take MORE than proportionally longer' if b>1 else 'bigger swings move FASTER than proportionally (higher velocity)'}")

    print()
    print("-" * 100)
    print("RETRACEMENT ZONE DISTRIBUTION (each leg vs. the leg immediately before it)")
    print("-" * 100)
    zone_counts = {}
    for r in rows[1:]:
        zone_counts[r["zone_vs_prior"]] = zone_counts.get(r["zone_vs_prior"], 0) + 1
    total = len(rows) - 1
    for _, _, name in RETRACE_ZONES:
        c = zone_counts.get(name, 0)
        print(f"  {name:<26} {c:>3}  ({c/total*100:5.1f}%)")

    print()
    print("-" * 100)
    print("MONTE CARLO: is leg-to-leg ratio clustering near Fibonacci levels REAL or chance?")
    print("-" * 100)
    ratios = [r["ratio_to_prior_leg"] for r in rows if r["ratio_to_prior_leg"]]
    actual, exp_mean, exp_std, z, p = monte_carlo_fib_clustering(ratios, tolerance=0.10)
    print(f"Observed legs within +/-10% of a classic Fib ratio : {actual*100:.1f}%  ({int(round(actual*len(ratios)))}/{len(ratios)})")
    print(f"Expected by chance (same lognormal, 50k sims)      : {exp_mean*100:.1f}%  (std {exp_std*100:.1f}%)")
    print(f"Z-score: {z:+.2f}   one-sided p-value: {p:.3f}")
    verdict = "SIGNIFICANT clustering (real effect)" if p < 0.05 else "NOT statistically significant — consistent with chance"
    print(f"Verdict: {verdict}")

    print()
    durations_only = [r["time_ratio_to_prior"] for r in rows if r["time_ratio_to_prior"]]
    actual_t, exp_mean_t, exp_std_t, z_t, p_t = monte_carlo_fib_clustering(durations_only, tolerance=0.10)
    print(f"Same test on TIME ratios (Fibonacci time theory):")
    print(f"Observed: {actual_t*100:.1f}%   Expected by chance: {exp_mean_t*100:.1f}% (std {exp_std_t*100:.1f}%)   "
          f"Z={z_t:+.2f}  p={p_t:.3f}")
    verdict_t = "SIGNIFICANT" if p_t < 0.05 else "NOT statistically significant — consistent with chance"
    print(f"Verdict: {verdict_t}")


if __name__ == "__main__":
    main()

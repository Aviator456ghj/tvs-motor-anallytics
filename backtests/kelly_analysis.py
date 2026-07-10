#!/usr/bin/env python3
"""Kelly-criterion + risk-of-ruin analysis of the five agent presets.

Answers, with the actual per-trade R-multiple distributions from each
preset's 540-day backtest (R = trade return / stop distance, i.e. -1R = a
full stop-out):

  1. Is the edge statistically real?  Win-rate confidence interval +
     bootstrap probability that the true profit factor is <= 1.
  2. What bet size does the math actually endorse?  Empirical Kelly
     optimum f* = argmax E[log(1 + f*R)] over the observed R distribution
     (the exact quantity growth-optimal betting maximizes), plus the
     half-Kelly size practitioners actually use.
  3. What does each risk% cost in drawdown?  Bootstrap-resampled equity
     paths -> median/95th-percentile max drawdown and P(maxDD >= 50%) at
     the preset's own risk setting vs Kelly / half-Kelly / 1%.

Honesty notes baked into the interpretation:
  - These distributions come from ONE historical backtest window. Kelly
    computed on backtest stats is an UPPER BOUND on sane sizing: if the
    live edge is even slightly worse than the backtest edge, true Kelly is
    lower, and betting above true Kelly mathematically REDUCES long-run
    growth while inflating drawdowns. This is why pros bet half-Kelly or
    less on much better-measured edges than these.
  - Small samples (the CHoCH presets have ~2 dozen trades) make every
    number here wide; the bootstrap CIs quantify exactly how wide.
  - The R math ignores whole-lot rounding and the 200x notional cap, both
    of which bind at extreme risk% (they made the 100%-risk screenshot's
    PF *lower* than the 10%-risk run of the same trades).

Usage:
    python backtests/kelly_analysis.py --data-dir <dir with SYMBOL_tf_540d.csv>
(or with no --data-dir, candles are fetched from Delta Exchange).
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import run_orderblock_screenshot_backtest as ob  # noqa: E402
import run_choch_ride_exit_screenshot_backtest as ch  # noqa: E402
import run_riley_v2_screenshot_backtest as ri  # noqa: E402
from _screenshot_common import fetch_candles  # noqa: E402

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")

# every preset: loader spec + the run() call reproducing it + its risk%
PRESETS = {
    "btc-orderblock-15": dict(
        data=("BTCUSD", "1h"), risk=0.15,
        run=lambda df: ob.run(df, k=4, buf_atr=0.9, min_break_atr=1.0,
                              wait=120, eq0=1000, risk_pct=0.15, leverage=200)),
    "btc-choch-100": dict(
        data=("BTCUSD", "1h"), risk=1.00,
        run=lambda df: ch.run(df, k=5, zone=0.5, buf=0.8, disrespect_r=0.786,
                              min_break_atr=1.0, wait=120, eq0=1000,
                              risk_pct=1.0, leverage=200)),
    "btc-riley-24": dict(
        data=("BTCUSD", "15m"), risk=0.24,
        run=lambda df: ri.run(df, k=3, fvg_mult=0.2, retest_window=12,
                              fill_window=12, eq0=1000, risk_pct=0.24,
                              leverage=200, use_p2=True, max_fill_delay=3,
                              min_vol_ratio=1.3)),
    "eth-choch-50": dict(
        data=("ETHUSD", "1h"), risk=0.50,
        run=lambda df: ch.run(df, k=5, zone=0.5, buf=0.10, disrespect_r=0.786,
                              min_break_atr=1.0, wait=120, eq0=1000,
                              risk_pct=0.5, leverage=200)),
    "eth-riley-26": dict(
        data=("ETHUSD", "15m"), risk=0.26,
        run=lambda df: ri.run(df, k=3, fvg_mult=0.2, retest_window=12,
                              fill_window=12, eq0=1000, risk_pct=0.26,
                              leverage=200, use_p2=True, max_fill_delay=3,
                              min_vol_ratio=1.3)),
}

RNG = np.random.default_rng(7)
N_BOOT = 10_000
F_GRID = np.concatenate([np.arange(0.001, 0.101, 0.001),
                         np.arange(0.105, 1.001, 0.005)])


def wilson_ci(wins, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - half, center + half


def profit_factor(r):
    w = r[r > 0].sum()
    l = -r[r <= 0].sum()
    return w / l if l > 0 else np.inf


def growth_per_trade(r, f):
    """E[log(1+f*R)] — the quantity Kelly maximizes. -inf once any single
    trade can wipe the account (1 + f*R <= 0)."""
    x = 1 + f * r
    if (x <= 0).any():
        return -np.inf
    return float(np.mean(np.log(x)))


def kelly_curve(r):
    return np.array([growth_per_trade(r, f) for f in F_GRID])


def bootstrap_pf_and_edge(r):
    n = len(r)
    idx = RNG.integers(0, n, size=(N_BOOT, n))
    samples = r[idx]
    wins = np.where(samples > 0, samples, 0).sum(axis=1)
    losses = -np.where(samples <= 0, samples, 0).sum(axis=1)
    pf = np.divide(wins, losses, out=np.full(N_BOOT, np.inf), where=losses > 0)
    return np.percentile(pf, [2.5, 97.5]), float((pf <= 1).mean())


def bootstrap_maxdd(r, f, n_paths=5000):
    """Max drawdown distribution of multiplicative equity paths built from
    iid resamples of the observed R sequence at risk fraction f."""
    n = len(r)
    idx = RNG.integers(0, n, size=(n_paths, n))
    growth = 1 + f * r[idx]
    growth = np.maximum(growth, 0.0)          # account can't go below zero
    eq = np.cumprod(growth, axis=1)
    peak = np.maximum.accumulate(eq, axis=1)
    dd = 1 - eq / np.maximum(peak, 1e-12)
    mdd = dd.max(axis=1)
    return {
        "median": float(np.median(mdd)),
        "p95": float(np.percentile(mdd, 95)),
        "p_dd50": float((mdd >= 0.50).mean()),
        "p_dd90": float((mdd >= 0.90).mean()),
    }


def analyze(name, spec, df):
    trades = spec["run"](df)
    r = (trades.ret_frac / trades.stop_frac).values
    n = len(r)
    wins = int((r > 0).sum())
    wr_lo, wr_hi = wilson_ci(wins, n)
    pf = profit_factor(r)
    (pf_lo, pf_hi), p_no_edge = bootstrap_pf_and_edge(r)
    curve = kelly_curve(r)
    f_star = float(F_GRID[np.argmax(curve)]) if np.isfinite(curve.max()) else 0.0
    g_star = curve.max()
    trades_per_year = n / 540 * 365
    out = {
        "name": name, "n": n, "wr": wins / n, "wr_lo": wr_lo, "wr_hi": wr_hi,
        "pf": pf, "pf_lo": pf_lo, "pf_hi": pf_hi, "p_no_edge": p_no_edge,
        "avg_win_R": float(r[r > 0].mean()) if wins else 0.0,
        "avg_loss_R": float(r[r <= 0].mean()) if wins < n else 0.0,
        "expectancy_R": float(r.mean()),
        "worst_R": float(r.min()),
        "kelly": f_star, "half_kelly": f_star / 2,
        "g_at_kelly": g_star,
        "g_at_preset": growth_per_trade(r, spec["risk"]),
        "preset_risk": spec["risk"],
        "trades_per_year": trades_per_year,
        "curve": curve, "r": r,
        "dd": {f: bootstrap_maxdd(r, f) for f in
               sorted({0.01, spec["risk"], f_star / 2, f_star})},
    }
    return out


def make_chart(results, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e1e0d9"
    SERIES = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7"]

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    for ax in axes:
        ax.set_facecolor(SURFACE)
        ax.grid(True, color=GRID, linewidth=0.7)
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.tick_params(colors=MUTED, labelsize=8.5)

    ax = axes[0]
    ymin, ymax = -15, 12
    for i, res in enumerate(results):
        g_ann = res["curve"] * res["trades_per_year"]  # log growth per year
        pct = 100 * F_GRID
        finite = np.isfinite(g_ann)
        ax.plot(pct[finite], np.clip(g_ann[finite], ymin, None),
                color=SERIES[i], linewidth=2, label=res["name"])
        k = res["kelly"]
        if k > 0:
            ax.plot(100 * k, min(res["g_at_kelly"] * res["trades_per_year"], ymax),
                    "o", color=SERIES[i], markersize=8, markeredgecolor=SURFACE,
                    markeredgewidth=2)
        gp = res["g_at_preset"] * res["trades_per_year"]
        ax.plot(100 * res["preset_risk"],
                np.clip(gp, ymin, ymax) if np.isfinite(gp) else ymin, "x",
                color=SERIES[i], markersize=9, markeredgewidth=2.5)
    ax.axhline(0, color=MUTED, linewidth=1)
    ax.set_xscale("log")
    ax.set_ylim(ymin, ymax)
    ax.set_xlabel("risk per trade (% of equity, log scale)", color=MUTED, fontsize=9)
    ax.set_ylabel("expected log-growth per year", color=MUTED, fontsize=9)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK, loc="lower left")
    ax.set_title("The Kelly curve: growth vs bet size\n"
                 "● = Kelly optimum   ✕ = preset risk   (curves clipped at -15)",
                 loc="left", color=INK, fontsize=10.5)

    ax = axes[1]
    dd_levels = [0.005, 0.01, 0.02, 0.05, 0.10, 0.15, 0.25, 0.50, 1.00]
    for i, res in enumerate(results):
        probs = [bootstrap_maxdd(res["r"], f, n_paths=2000)["p_dd50"]
                 for f in dd_levels]
        ax.plot([100 * f for f in dd_levels], [100 * p for p in probs],
                color=SERIES[i], linewidth=2, marker="o", markersize=4,
                label=res["name"])
    ax.legend(frameon=False, fontsize=8, labelcolor=INK, loc="upper left")
    ax.set_xscale("log")
    ax.set_xlabel("risk per trade (% of equity, log scale)", color=MUTED, fontsize=9)
    ax.set_ylabel("P(max drawdown ≥ 50%), %", color=MUTED, fontsize=9)
    ax.set_title("Probability of losing half the account\n"
                 "bootstrap of each preset's own backtest trades",
                 loc="left", color=INK, fontsize=10.5)

    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    print(f"chart -> {path}")


def fmt_pct(x):
    return f"{100 * x:.1f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None,
                    help="dir containing SYMBOL_tf_540d.csv files (else fetch)")
    args = ap.parse_args()

    frames = {}
    for sym, tf in {s["data"] for s in PRESETS.values()}:
        key = (sym, tf)
        if args.data_dir:
            frames[key] = pd.read_csv(os.path.join(args.data_dir, f"{sym}_{tf}_540d.csv"))
        else:
            from delta_scalper.config import Config
            from delta_scalper.delta_client import DeltaClient
            client = DeltaClient(Config().base_url)
            print(f"fetching {sym} {tf} x 540d ...")
            frames[key] = fetch_candles(client, sym, tf, 540)

    results = []
    for name, spec in PRESETS.items():
        res = analyze(name, spec, frames[spec["data"]])
        results.append(res)

    os.makedirs(REPORT_DIR, exist_ok=True)
    make_chart(results, os.path.join(REPORT_DIR, "kelly_analysis.png"))

    lines = ["# Kelly / risk-of-ruin analysis of the five agent presets", ""]
    for res in results:
        gp = res["g_at_preset"]
        lines += [
            f"## {res['name']}  (preset risk {fmt_pct(res['preset_risk'])})", "",
            f"- trades: {res['n']}  |  win rate {fmt_pct(res['wr'])} "
            f"(95% CI {fmt_pct(res['wr_lo'])}–{fmt_pct(res['wr_hi'])})",
            f"- profit factor {res['pf']:.2f} (bootstrap 95% CI "
            f"{res['pf_lo']:.2f}–{res['pf_hi']:.2f})  |  "
            f"**P(no real edge) = {fmt_pct(res['p_no_edge'])}**",
            f"- avg win {res['avg_win_R']:+.2f}R, avg loss {res['avg_loss_R']:+.2f}R, "
            f"worst single trade {res['worst_R']:+.2f}R, "
            f"expectancy {res['expectancy_R']:+.3f}R/trade",
            f"- **Kelly optimum f\\* = {fmt_pct(res['kelly'])}** risk/trade, "
            f"half-Kelly = {fmt_pct(res['half_kelly'])}",
            f"- growth at preset risk: "
            + ("**CERTAIN RUIN** (one full stop-out can zero the account)"
               if not np.isfinite(gp) else
               f"{gp:+.4f} log/trade vs {res['g_at_kelly']:+.4f} at Kelly"),
            "",
            "| risk/trade | median maxDD | 95th pct maxDD | P(maxDD>=50%) | P(maxDD>=90%) |",
            "|---|---|---|---|---|",
        ]
        for f, dd in sorted(res["dd"].items()):
            tag = " (preset)" if abs(f - res["preset_risk"]) < 1e-9 else \
                  (" (Kelly)" if abs(f - res["kelly"]) < 1e-9 else
                   (" (half-Kelly)" if abs(f - res["half_kelly"]) < 1e-9 else ""))
            lines.append(f"| {fmt_pct(f)}{tag} | {fmt_pct(dd['median'])} | "
                         f"{fmt_pct(dd['p95'])} | {fmt_pct(dd['p_dd50'])} | "
                         f"{fmt_pct(dd['p_dd90'])} |")
        lines.append("")
    lines += [
        "![kelly](kelly_analysis.png)", "",
        "## How to read this",
        "",
        "Kelly f\\* is the bet size that maximizes long-run compound growth *if*",
        "the live edge equals the backtest edge exactly. It is an upper bound,",
        "not a target: overestimating the edge (guaranteed to some degree with",
        "backtest-fit parameters and 2-dozen-trade samples) means true Kelly is",
        "lower, and betting above true Kelly reduces growth while inflating",
        "drawdowns. Practitioners size at half-Kelly or below. Note also that",
        "every preset's own risk setting sits at or beyond its Kelly optimum —",
        "the screenshot returns were bought with mathematically excessive risk.",
        "",
        "**The btc-choch-100 'Kelly = 100%' is a small-sample artifact, not a",
        "license.** Its worst loss in 27 backtest trades was only -0.3R (the",
        "0.8x-leg stop is so wide the trail exit always fired first, so the",
        "hard stop was never actually hit in-sample). Empirical Kelly only",
        "knows the losses it has seen: a distribution whose observed losses",
        "are tiny 'supports' any bet size. One future trade that gaps to the",
        "full stop — which the eth-choch variant DID take (worst -1.13R) —",
        "zeroes a 100%-risk account. The honest ceiling for the choch presets",
        "is set by the sibling's worst loss, not their own: half-Kelly on the",
        "pooled worst case, i.e. single-digit-to-low-teens percent at most.",
    ]
    out = os.path.join(REPORT_DIR, "kelly_report.md")
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"report -> {out}\n")

    for res in results:
        gp = res["g_at_preset"]
        print(f"{res['name']:20s} n={res['n']:3d}  PF={res['pf']:5.2f} "
              f"(CI {res['pf_lo']:.2f}-{res['pf_hi']:.2f})  "
              f"P(no edge)={fmt_pct(res['p_no_edge']):>6s}  "
              f"Kelly={fmt_pct(res['kelly']):>6s}  "
              f"preset={fmt_pct(res['preset_risk']):>6s}  "
              + ("RUIN-POSSIBLE" if not np.isfinite(gp) else
                 f"g(preset)={gp:+.4f} vs g(Kelly)={res['g_at_kelly']:+.4f}"))


if __name__ == "__main__":
    main()

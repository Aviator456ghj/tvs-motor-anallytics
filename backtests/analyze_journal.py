#!/usr/bin/env python3
"""Post-mortem tool for the trade journal.

Reads trade_journal.csv (written by the paper broker as the bot trades) and
contrasts winners vs losers across the recorded setup features, so failure
patterns surface instead of being repeated.

Usage:  python backtests/analyze_journal.py [path/to/trade_journal.csv]
"""
import sys

import pandas as pd


def bucket(t: pd.DataFrame, feature: str, edges: list[float]) -> pd.DataFrame:
    if feature not in t or t[feature].dropna().empty:
        return pd.DataFrame()
    labels = [f"{a}-{b}" for a, b in zip(edges[:-1], edges[1:])]
    groups = pd.cut(t[feature].astype(float), bins=edges, labels=labels)
    rows = []
    for name, sel in t.groupby(groups, observed=True):
        if len(sel) < 3:
            continue
        rows.append({
            "feature": feature, "bucket": str(name), "n": len(sel),
            "win%": round(100 * (sel.pnl > 0).mean(), 1),
            "avgR": round(sel.r_outcome.mean(), 2),
            "sumR": round(sel.r_outcome.sum(), 1),
        })
    return pd.DataFrame(rows)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "trade_journal.csv"
    t = pd.read_csv(path)
    if t.empty:
        sys.exit("journal is empty")
    print(f"{len(t)} trades | win rate "
          f"{100 * (t.pnl > 0).mean():.1f}% | total pnl {t.pnl.sum():.2f} | "
          f"avg R {t.r_outcome.mean():.2f}\n")

    print("=== exits ===")
    print(t.groupby("exit_reason").agg(
        n=("pnl", "size"), total_pnl=("pnl", "sum"),
        avgR=("r_outcome", "mean")).round(2).to_string(), "\n")

    print("=== losers vs winners by setup feature ===")
    parts = [
        bucket(t, "vol_ratio", [0, 1, 2, 100]),
        bucket(t, "wick_ratio", [0, 0.6, 0.75, 1.0]),
        bucket(t, "sweep_depth_atr", [0, 0.5, 1.5, 100]),
        bucket(t, "stop_pct", [0, 0.45, 0.8, 100]),
    ]
    if "trend_align" in t:
        g = t.groupby("trend_align").agg(
            n=("pnl", "size"), **{"win%": ("pnl", lambda s: round(100 * (s > 0).mean(), 1))},
            avgR=("r_outcome", "mean")).round(2).reset_index()
        g["feature"] = "trend_align"
        g["bucket"] = g.pop("trend_align").map({1: "with_trend", 0: "against"})
        parts.append(g)
    rep = pd.concat([p for p in parts if not p.empty], ignore_index=True)
    cols = ["feature", "bucket", "n", "win%", "avgR"] + (
        ["sumR"] if "sumR" in rep else [])
    print(rep[cols].to_string(index=False))
    print("\nRead this like a post-mortem: buckets with low win% and negative"
          "\navgR are the situations to stop trading — tighten the matching"
          "\nfilter in delta_scalper/config.py rather than hoping they improve.")


if __name__ == "__main__":
    main()

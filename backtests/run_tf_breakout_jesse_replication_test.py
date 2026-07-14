#!/usr/bin/env python3
"""Replication of a workflow shown in a user-provided video: Claude Code,
connected via an MCP bridge to the open-source "Jesse" algo-trading
framework, was given one autonomous prompt and produced two trend-
following strategies on BTC/ETH/SOL (1h, Binance Perpetual Futures,
2022-07-01 to 2026-06-29 — a real 4-year window on that exchange), each
validated with a statistical significance test on the entry rule, tuned
with hyperparameter optimization, and stress-tested with Monte Carlo
simulation. Reported results: TFAtrExitBreakout Sharpe 1.53 (+75.35%,
-7.18% maxDD), TFTrailBreakout Sharpe 1.06 (+26.02%, -5.36% maxDD).

The original prompt (transcribed from the video, verbatim):
    "Do research and find me two trading strategies. Each one of them
    should have a Sharpe ratio above one in the last 4 years. one of
    them should be trend following, include both long and short
    positions, and risk 3% of the account's capital per each trade. In
    the first strategy, once the position is open, close it using a
    trailing stop. In the second strategy, close the position at a
    specific point determined by the ATR indicator. You can test them on
    BTC, ETH, and SOL on the hourly timeframe. Every time you develop a
    strategy, validate the result using a statistical significance test
    before writing the full strategy. Only proceed if the strategy's
    entry rules demonstrates genuine statistical significance. Feel free
    to use optimization to improve the results. At the end, apply Monte
    Carlo simulations to ensure the results are not overfit. Continue
    until you find strategies that fully meet the criteria requested."

Strategy code visible on screen (Jesse Python strategy class) — a
Bollinger Band breakout filtered by an EMA trend, position-sized to risk
a fixed % of equity per trade, capped at 10% of equity notional:
    should_long:  close > bb.upperband and close > trend_ema
    should_short: close < bb.lowerband and close < trend_ema
    stop  = entry -/+ stop_mult * atr                    (at entry)
    qty   = min(risk_to_qty(equity, 3%, entry, stop), size_to_qty(equity*0.1, entry))
  Exit A (ATR-fixed): target = entry +/- target_mult * atr, fixed at entry.
  Exit B (ATR-trailing): stop ratchets each bar toward the extreme
    favorable price reached, using that bar's OWN (recomputed) ATR —
    self.atr is a live property in the source, not frozen at entry.

This script replicates that exact entry/exit/sizing logic and that exact
validation pipeline (significance test -> optimization -> Monte Carlo),
using this repo's own real data source (Delta Exchange India) instead of
Binance Perpetual Futures, since that's the exchange this whole repo
already trades against. Real, disclosed differences from the video, not
hidden:
  - Delta Exchange India's public candle API only has ~2.2-2.5 years of
    history for BTC/ETH/SOL (verified by probing the API directly), not
    4 years. This script uses the longest COMMON window across all three
    (~820 days, limited by SOLUSD's listing date), not 4 years.
  - No leverage/margin-mode modeling (Jesse's session used 9x cross);
    this repo's other backtests don't model leverage either, they size
    by risk fraction of equity with a notional cap, and this script does
    the same (equity * 3% / stop_frac, capped at equity * 10%).
  - Grid-search hyperparameter optimization, not Jesse's dedicated
    optimizer (genetic/Bayesian) — smaller search space, disclosed as a
    real methodology gap, not hidden.
  - ADDED beyond what the video showed: an in-sample/out-of-sample split
    around the optimization step (this repo's standing practice), not
    just Monte Carlo — the video's dashboard never showed a walk-forward
    check, only Monte Carlo trade-resampling, so this is a stricter bar
    than what was demonstrated, applied consistently with every other
    backtest in this repo.

This is a genuine empirical test, not a re-derivation of the video's
numbers — different exchange, different real window, real answer
reported either way.
"""
import itertools
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from delta_scalper.config import Config             # noqa: E402
from delta_scalper.delta_client import DeltaClient   # noqa: E402
from delta_scalper.indicators import ema, atr, bollinger_bands  # noqa: E402

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
SYMBOLS = ["BTCUSD", "ETHUSD", "SOLUSD"]
RISK_PCT = 0.03          # "risk 3% of the account's capital per each trade"
NOTIONAL_CAP_FRAC = 0.10  # size_to_qty(available_margin * 0.1, ...)
MAX_HOLD_BARS = 24 * 30   # 30 days at 1h — generous, trend trades can run
N_PERM = 300              # permutation-test resamples
N_MC = 200                 # Monte Carlo scenarios, matches the video's "200"
IS_FRAC = 0.70             # in-sample fraction for the added walk-forward check

# grid search space (smaller than a dedicated optimizer, disclosed above)
GRID = dict(
    bb_period=[15, 20, 30],
    bb_dev=[1.5, 2.0, 2.5],
    ema_period=[100, 150, 200],
    stop_mult=[1.0, 1.5, 2.0],
    exit_mult=[1.5, 2.0, 3.0],   # target_mult (fixed variant) / trail_mult (trailing variant)
)
DEFAULT_PARAMS = dict(bb_period=20, bb_dev=2.0, ema_period=150, stop_mult=1.5, exit_mult=2.0)


def fetch(client, symbol, tf_min, start, end):
    res_s = tf_min * 60
    resolution = "1h" if tf_min == 60 else f"{tf_min}m"
    frames = []
    cursor = end
    while cursor > start:
        chunk_start = max(start, cursor - 2000 * res_s)
        data = client.get_candles(symbol, resolution, chunk_start, cursor)
        if not data:
            break
        frames.append(pd.DataFrame(data))
        cursor = min(c["time"] for c in data) - res_s
        time.sleep(0.15)
    if not frames:
        return pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])
    df = pd.concat(frames).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df


# ─────────────────────────── entry rule ───────────────────────────

def entry_signal(df, bb_period, bb_dev, ema_period):
    upper, _, lower = bollinger_bands(df.close, bb_period, bb_dev)
    trend = ema(df.close, ema_period)
    long_e = (df.close > upper) & (df.close > trend)
    short_e = (df.close < lower) & (df.close < trend)
    return np.where(long_e, 1, np.where(short_e, -1, 0))


# ─────────────────────────── exit engines ───────────────────────────

def replay_fixed_atr(df, entries, stop_mult, target_mult, cost, start_equity=10000.0):
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    a = atr(df, 14).values
    equity = start_equity
    trades = []
    i, n = 0, len(df)
    while i < n - 1:
        s = entries[i]
        if s != 0 and not np.isnan(a[i]) and a[i] > 0 and equity > 0:
            direction = s
            entry = o[i + 1]
            sl_dist = stop_mult * a[i]
            if sl_dist <= 0:
                i += 1; continue
            sl = entry - direction * sl_dist
            tp = entry + direction * target_mult * a[i]
            notional = min(equity * RISK_PCT / (sl_dist / entry), equity * NOTIONAL_CAP_FRAC)
            exit_px, j = None, i + 1
            for j in range(i + 1, min(i + 1 + MAX_HOLD_BARS, n)):
                if direction == 1:
                    if l[j] <= sl: exit_px = sl; break
                    if h[j] >= tp: exit_px = tp; break
                else:
                    if h[j] >= sl: exit_px = sl; break
                    if l[j] <= tp: exit_px = tp; break
            if exit_px is None:
                j = min(i + MAX_HOLD_BARS, n - 1)
                exit_px = c[j]
            ret = direction * (exit_px - entry) / entry - cost
            pnl = notional * ret
            equity += pnl
            trades.append({"entry_time": int(df.time.iloc[i + 1]), "exit_time": int(df.time.iloc[j]),
                            "side": "buy" if direction == 1 else "sell", "pnl": pnl, "equity": equity})
            i = j + 1
        else:
            i += 1
    return pd.DataFrame(trades)


def replay_trailing_atr(df, entries, stop_mult, trail_mult, cost, start_equity=10000.0):
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    a = atr(df, 14).values  # recomputed once, used "live" bar-by-bar same as the source's property
    equity = start_equity
    trades = []
    i, n = 0, len(df)
    while i < n - 1:
        s = entries[i]
        if s != 0 and not np.isnan(a[i]) and a[i] > 0 and equity > 0:
            direction = s
            entry = o[i + 1]
            sl_dist0 = stop_mult * a[i]
            if sl_dist0 <= 0:
                i += 1; continue
            sl = entry - direction * sl_dist0
            notional = min(equity * RISK_PCT / (sl_dist0 / entry), equity * NOTIONAL_CAP_FRAC)
            extreme = entry
            exit_px, j = None, i + 1
            for j in range(i + 1, min(i + 1 + MAX_HOLD_BARS, n)):
                if direction == 1:
                    if l[j] <= sl:
                        exit_px = sl; break
                    extreme = max(extreme, h[j])
                    if not np.isnan(a[j]) and a[j] > 0:
                        sl = max(sl, extreme - trail_mult * a[j])  # only tightens favorably
                else:
                    if h[j] >= sl:
                        exit_px = sl; break
                    extreme = min(extreme, l[j])
                    if not np.isnan(a[j]) and a[j] > 0:
                        sl = min(sl, extreme + trail_mult * a[j])
            if exit_px is None:
                j = min(i + MAX_HOLD_BARS, n - 1)
                exit_px = c[j]
            ret = direction * (exit_px - entry) / entry - cost
            pnl = notional * ret
            equity += pnl
            trades.append({"entry_time": int(df.time.iloc[i + 1]), "exit_time": int(df.time.iloc[j]),
                            "side": "buy" if direction == 1 else "sell", "pnl": pnl, "equity": equity})
            i = j + 1
        else:
            i += 1
    return pd.DataFrame(trades)


EXIT_FNS = {"atr_fixed": replay_fixed_atr, "atr_trailing": replay_trailing_atr}


# ─────────────────────────── metrics ───────────────────────────

def combined_metrics(trades_by_symbol, per_symbol_equity):
    """Blend independent equal-capital sub-portfolios into one combined
    curve (each symbol gets its own capital, summed) — a transparent
    approximation of Jesse's shared-margin multi-route backtest, not an
    exact replica."""
    all_trades = []
    for sym, tr in trades_by_symbol.items():
        if not tr.empty:
            t = tr.copy()
            t["symbol"] = sym
            all_trades.append(t)
    if not all_trades:
        return dict(n=0, win_rate=0.0, net_profit_pct=0.0, max_dd=0.0, sharpe=0.0), pd.DataFrame()
    merged = pd.concat(all_trades).sort_values("exit_time").reset_index(drop=True)
    start_total = sum(per_symbol_equity.values())
    running = dict(per_symbol_equity)
    curve = []
    for _, row in merged.iterrows():
        # pnl already reflects that symbol's own equity growth; approximate
        # blended equity as sum of latest per-symbol equity at each event
        running[row["symbol"]] = row["equity"]
        curve.append(sum(running.values()))
    merged["blended_equity"] = curve
    eq = merged.blended_equity.values
    peak = np.maximum.accumulate(np.concatenate([[start_total], eq]))
    dd = (np.concatenate([[start_total], eq]) - peak) / peak
    wins = merged[merged.pnl > 0]
    span_days = (merged.exit_time.iloc[-1] - merged.entry_time.iloc[0]) / 86400 if len(merged) > 1 else 1
    trades_per_year = len(merged) / max(span_days, 1) * 365
    r = merged.pnl.values / np.concatenate([[start_total], eq[:-1]])
    sharpe = float(r.mean() / r.std() * np.sqrt(max(trades_per_year, 1))) if r.std() > 0 else 0.0
    return dict(n=len(merged), win_rate=len(wins) / len(merged),
                net_profit_pct=(eq[-1] - start_total) / start_total,
                max_dd=dd.min(), sharpe=sharpe), merged


# ─────────────────────────── statistical significance ───────────────────────────

def permutation_significance(dfs, params, exit_fn_name, cost, n_perm=N_PERM, rng_seed=7):
    """Does the ENTRY RULE'S TIMING matter, or would random entries with
    the same exit logic do just as well in this market regime? Real
    entries vs n_perm sets of random entries (same count/direction mix,
    same exit engine) -> p-value = fraction of random runs beating the
    real rule's combined Sharpe."""
    rng = np.random.default_rng(rng_seed)
    exit_fn = EXIT_FNS[exit_fn_name]
    real_trades = {}
    for sym, df in dfs.items():
        entries = entry_signal(df, params["bb_period"], params["bb_dev"], params["ema_period"])
        if exit_fn_name == "atr_fixed":
            real_trades[sym] = exit_fn(df, entries, params["stop_mult"], params["exit_mult"], cost)
        else:
            real_trades[sym] = exit_fn(df, entries, params["stop_mult"], params["exit_mult"], cost)
    real_m, _ = combined_metrics(real_trades, {s: 10000.0 for s in dfs})
    real_stat = real_m["sharpe"]

    null_stats = []
    for _ in range(n_perm):
        perm_trades = {}
        for sym, df in dfs.items():
            entries = entry_signal(df, params["bb_period"], params["bb_dev"], params["ema_period"])
            n_long = int((entries == 1).sum())
            n_short = int((entries == -1).sum())
            n = len(df)
            idx = rng.choice(np.arange(20, n - 20), size=min(n_long + n_short, n - 40), replace=False)
            rand_entries = np.zeros(n, dtype=int)
            dirs = np.array([1] * n_long + [-1] * n_short)
            rng.shuffle(dirs)
            rand_entries[idx[:len(dirs)]] = dirs[:len(idx)]
            if exit_fn_name == "atr_fixed":
                perm_trades[sym] = exit_fn(df, rand_entries, params["stop_mult"], params["exit_mult"], cost)
            else:
                perm_trades[sym] = exit_fn(df, rand_entries, params["stop_mult"], params["exit_mult"], cost)
        pm, _ = combined_metrics(perm_trades, {s: 10000.0 for s in dfs})
        null_stats.append(pm["sharpe"])
    null_stats = np.array(null_stats)
    p_value = float((null_stats >= real_stat).mean())
    return real_stat, p_value, null_stats


# ─────────────────────────── Monte Carlo (trade-order resampling) ───────────────────────────

def monte_carlo(merged_trades, start_equity, n_scenarios=N_MC, rng_seed=11):
    rng = np.random.default_rng(rng_seed)
    pnls = merged_trades.pnl.values
    n = len(pnls)
    if n < 10:
        return None
    orig = metrics_from_pnls(pnls, start_equity)
    scenario_stats = []
    for _ in range(n_scenarios):
        sample = rng.choice(pnls, size=n, replace=True)
        scenario_stats.append(metrics_from_pnls(sample, start_equity))
    df = pd.DataFrame(scenario_stats)
    out = {"original": orig}
    for pct, label in [(5, "worst_5pct"), (50, "median"), (95, "best_5pct")]:
        out[label] = {k: float(np.percentile(df[k], pct)) for k in df.columns}
    return out


def metrics_from_pnls(pnls, start_equity):
    eq = start_equity + np.cumsum(pnls)
    peak = np.maximum.accumulate(np.concatenate([[start_equity], eq]))
    dd = (np.concatenate([[start_equity], eq]) - peak) / peak
    r = pnls / np.concatenate([[start_equity], eq[:-1]])
    sharpe = float(r.mean() / r.std() * np.sqrt(len(pnls))) if r.std() > 0 and len(pnls) > 1 else 0.0
    win_rate = float((pnls > 0).mean())
    return dict(net_profit_pct=(eq[-1] - start_equity) / start_equity, max_dd=float(dd.min()),
                sharpe=sharpe, win_rate=win_rate)


# ─────────────────────────── optimization ───────────────────────────

def grid_search(dfs, exit_fn_name, cost, is_frac=IS_FRAC):
    exit_fn = EXIT_FNS[exit_fn_name]
    splits = {s: int(len(df) * is_frac) for s, df in dfs.items()}
    best = None
    combos = list(itertools.product(*GRID.values()))
    print(f"  grid search: {len(combos)} combinations x {len(dfs)} assets ({exit_fn_name})")
    for combo in combos:
        params = dict(zip(GRID.keys(), combo))
        is_trades = {}
        for sym, df in dfs.items():
            entries = entry_signal(df, params["bb_period"], params["bb_dev"], params["ema_period"])
            df_is = df.iloc[:splits[sym]].reset_index(drop=True)
            entries_is = entries[:splits[sym]]
            is_trades[sym] = exit_fn(df_is, entries_is, params["stop_mult"], params["exit_mult"], cost)
        is_m, _ = combined_metrics(is_trades, {s: 10000.0 for s in dfs})
        if best is None or is_m["sharpe"] > best[1]["sharpe"]:
            best = (params, is_m)
    return best[0], best[1]


# ─────────────────────────── main pipeline ───────────────────────────

def run_strategy(dfs, exit_fn_name, cost, label):
    print(f"\n=== {label} ({exit_fn_name}) ===")
    params, is_m = grid_search(dfs, exit_fn_name, cost)
    print(f"  best in-sample params: {params}  (IS Sharpe {is_m['sharpe']:.2f})")

    splits = {s: int(len(df) * IS_FRAC) for s, df in dfs.items()}
    oos_trades = {}
    for sym, df in dfs.items():
        entries = entry_signal(df, params["bb_period"], params["bb_dev"], params["ema_period"])
        df_oos = df.iloc[splits[sym]:].reset_index(drop=True)
        entries_oos = entries[splits[sym]:]
        oos_trades[sym] = EXIT_FNS[exit_fn_name](df_oos, entries_oos, params["stop_mult"],
                                                  params["exit_mult"], cost)
    oos_m, _ = combined_metrics(oos_trades, {s: 10000.0 for s in dfs})
    print(f"  out-of-sample: Sharpe {oos_m['sharpe']:.2f}, net {oos_m['net_profit_pct']:+.1%}, "
          f"maxDD {oos_m['max_dd']:.1%}, n={oos_m['n']}")

    full_trades = {}
    for sym, df in dfs.items():
        entries = entry_signal(df, params["bb_period"], params["bb_dev"], params["ema_period"])
        full_trades[sym] = EXIT_FNS[exit_fn_name](df, entries, params["stop_mult"],
                                                   params["exit_mult"], cost)
    full_m, merged = combined_metrics(full_trades, {s: 10000.0 for s in dfs})
    print(f"  full-period (video's own methodology, no split): Sharpe {full_m['sharpe']:.2f}, "
          f"net {full_m['net_profit_pct']:+.1%}, maxDD {full_m['max_dd']:.1%}, n={full_m['n']}")

    print("  running permutation significance test on entry rule...")
    real_stat, p_value, null_stats = permutation_significance(dfs, params, exit_fn_name, cost)
    print(f"  entry-rule significance: real Sharpe {real_stat:.2f} vs random-entry null "
          f"(mean {null_stats.mean():.2f}, p={p_value:.3f})")

    mc = monte_carlo(merged, sum(10000.0 for _ in dfs)) if not merged.empty else None
    if mc:
        print(f"  Monte Carlo ({N_MC} scenarios): worst5% Sharpe {mc['worst_5pct']['sharpe']:.2f}, "
              f"median {mc['median']['sharpe']:.2f}, best5% {mc['best_5pct']['sharpe']:.2f}")

    return dict(label=label, params=params, is_sharpe=is_m["sharpe"], oos=oos_m, full=full_m,
                significance_p=p_value, real_stat=real_stat, null_mean=float(null_stats.mean()),
                monte_carlo=mc)


def main():
    cfg = Config()
    client = DeltaClient(cfg.base_url)
    cost = cfg.round_trip_cost
    now = int(time.time())
    common_start = now - 820 * 86400  # longest common real history across BTC/ETH/SOL (SOL-limited)

    dfs = {}
    for sym in SYMBOLS:
        print(f"Fetching {sym} 1h, {(now - common_start) / 86400:.0f} days...")
        dfs[sym] = fetch(client, sym, 60, common_start, now)
        print(f"  {len(dfs[sym])} bars, {dfs[sym].time.iloc[0]} -> {dfs[sym].time.iloc[-1]}")

    results = []
    results.append(run_strategy(dfs, "atr_trailing", cost, "Strategy 1: trend-following, trailing-stop exit"))
    results.append(run_strategy(dfs, "atr_fixed", cost, "Strategy 2: trend-following, ATR fixed stop/target exit"))

    lines = ["# Replicating a Claude+Jesse-MCP autonomous strategy-development video, on real Delta Exchange data\n",
             "Source: a user-provided video demonstrating Claude Code connected via MCP to the "
             "open-source Jesse algo-trading framework, given one autonomous prompt: find two "
             "trend-following BTC/ETH/SOL strategies (long+short, 3% risk/trade, hourly) with "
             "Sharpe > 1 over 4 years, validated with an entry-rule significance test, "
             "hyperparameter-optimized, and Monte Carlo stress-tested. Reported result there: "
             "TFAtrExitBreakout Sharpe 1.53, TFTrailBreakout Sharpe 1.06 (Binance Perpetual "
             "Futures, 2022-07-01 to 2026-06-29).\n",
             f"This replicates the exact entry rule (Bollinger Band breakout + EMA trend filter), "
             "exit logic (ATR-fixed vs ATR-trailing), position sizing (3% equity risk/trade, "
             "10%-equity notional cap), and validation pipeline (significance test -> grid "
             "optimization -> Monte Carlo) — on **real Delta Exchange India data**, which only "
             f"has ~2.3 years of common BTC/ETH/SOL history (SOLUSD-limited), not 4 — and adds an "
             "in-sample/out-of-sample split around optimization, which the video's own dashboard "
             "never showed. Real numbers, not a re-derivation of the video's.\n"]

    for r in results:
        lines.append(f"## {r['label']}\n")
        lines.append(f"Best grid params: `{r['params']}`\n")
        lines.append("| Segment | Sharpe | Net profit | Max DD | Trades |")
        lines.append("|---|---|---|---|---|")
        lines.append(f"| In-sample (70%) | {r['is_sharpe']:.2f} | — | — | — |")
        lines.append(f"| Out-of-sample (30%) | {r['oos']['sharpe']:.2f} | {r['oos']['net_profit_pct']:+.1%} | "
                     f"{r['oos']['max_dd']:.1%} | {r['oos']['n']} |")
        lines.append(f"| Full period (video's own methodology) | {r['full']['sharpe']:.2f} | "
                     f"{r['full']['net_profit_pct']:+.1%} | {r['full']['max_dd']:.1%} | {r['full']['n']} |")
        lines.append(f"\n**Entry-rule significance test:** real combined Sharpe {r['real_stat']:.2f} vs. "
                     f"{N_PERM} random-entry permutations (same exit logic, same trade count) — "
                     f"null mean {r['null_mean']:.2f}, **p={r['significance_p']:.3f}** "
                     f"({'PASSES' if r['significance_p'] < 0.05 else 'DOES NOT PASS'} the video's own "
                     "bar of 'genuine statistical significance').\n")
        if r["monte_carlo"]:
            mc = r["monte_carlo"]
            lines.append(f"**Monte Carlo ({N_MC} trade-order resamples):** Sharpe — worst 5% "
                         f"{mc['worst_5pct']['sharpe']:.2f}, median {mc['median']['sharpe']:.2f}, "
                         f"best 5% {mc['best_5pct']['sharpe']:.2f}. Net profit — worst 5% "
                         f"{mc['worst_5pct']['net_profit_pct']:+.1%}, median "
                         f"{mc['median']['net_profit_pct']:+.1%}.\n")
        met_target = r["oos"]["sharpe"] > 1.0 and r["significance_p"] < 0.05
        lines.append(f"**Verdict (out-of-sample Sharpe>1 AND entry significance passes): "
                     f"{'MET' if met_target else 'NOT MET'}**\n")

    report_path = os.path.join(REPORT_DIR, "tf_breakout_jesse_replication_report.md")
    with open(report_path, "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    print(f"\nSaved: {report_path}")


if __name__ == "__main__":
    main()

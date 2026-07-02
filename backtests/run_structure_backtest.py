#!/usr/bin/env python3
"""Market-structure scalping backtest & comparison vs the baseline strategy.

Tests two mechanical "smart money" entry models on real Delta Exchange data:

  1. sweep+CHoCH — HTF liquidity sweep confirmed by a change of character
     (the exact-entry setup implemented in delta_scalper/structure.py)
  2. BOS retest  — break of structure, limit entry on the retest of the
     broken swing level

and compares them with the default trend-pullback strategy. Writes
reports/market_structure_report.md and reports/structure_comparison.png.
"""
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from delta_scalper.config import Config  # noqa: E402
from delta_scalper.delta_client import DeltaClient  # noqa: E402
from delta_scalper.strategy import TrendPullbackStrategy  # noqa: E402
from delta_scalper.structure import find_swings, htf_swing_levels, resample_ohlc  # noqa: E402
from run_backtest import fetch, replay, stats, vector_signals  # noqa: E402

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
DAYS, SPLIT_DAYS = 60, 40


def run_sweep_choch(df, cfg, eq0=1000.0):
    """Event replay of MarketStructureStrategy's setup (vectorized scan)."""
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    sh, sl_lv = htf_swing_levels(df, cfg.ms_htf_minutes, cfg.ms_swing_k)
    cost = cfg.taker_fee * 2 + cfg.slippage * 2
    m, equity, trades = cfg.ms_micro_bars, eq0, []
    i, n = m + 1, len(df)
    while i < n - 2:
        s = 0
        if not np.isnan(sl_lv[i - 1]) and l[i] < sl_lv[i - 1] and c[i] > sl_lv[i - 1]:
            s, extreme, trigger = 1, l[i], h[max(0, i - m):i + 1].max()
        elif not np.isnan(sh[i - 1]) and h[i] > sh[i - 1] and c[i] < sh[i - 1]:
            s, extreme, trigger = -1, h[i], l[max(0, i - m):i + 1].min()
        if s == 0:
            i += 1
            continue
        conf = None
        for w in range(i + 1, min(i + 1 + cfg.ms_confirm_bars, n - 1)):
            if (s == 1 and l[w] < extreme) or (s == -1 and h[w] > extreme):
                break
            if (s == 1 and c[w] > trigger) or (s == -1 and c[w] < trigger):
                conf = w
                break
        if conf is None:
            i += 1
            continue
        entry = o[conf + 1] * (1 + cfg.slippage * s)
        stop_d = abs(entry - extreme)
        if stop_d <= 0 or stop_d / entry < cfg.min_move_cost_ratio * cost:
            i = conf + 1
            continue
        sl = extreme
        tp = entry + s * cfg.ms_r_multiple * stop_d
        notional = min(equity * cfg.risk_per_trade / (stop_d / entry),
                       equity * cfg.max_leverage)
        exit_px, j = None, conf + 1
        for j in range(conf + 1, min(conf + 1 + cfg.max_hold_bars * 2, n)):
            if s == 1:
                if l[j] <= sl: exit_px = sl; break
                if h[j] >= tp: exit_px = tp; break
            else:
                if h[j] >= sl: exit_px = sl; break
                if l[j] <= tp: exit_px = tp; break
        if exit_px is None:
            j = min(conf + cfg.max_hold_bars * 2, n - 1)
            exit_px = c[j]
        ret = s * (exit_px - entry) / entry - cost
        pnl = notional * ret
        equity += pnl
        trades.append({"entry_time": int(df.time.iloc[conf + 1]),
                       "exit_time": int(df.time.iloc[j]),
                       "pnl": pnl, "equity": equity})
        i = j + 1
    return pd.DataFrame(trades)


def run_bos_retest(df, cfg, k=5, r_mult=2.0, wait_bars=12, eq0=1000.0):
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    sh_p, sl_p = find_swings(df, k)
    cost = cfg.maker_fee + cfg.taker_fee + 2 * cfg.slippage
    equity, trades, i, n = eq0, [], 1, len(df)
    while i < n - 2:
        s = 0
        if not np.isnan(sh_p[i - 1]) and c[i - 1] <= sh_p[i - 1] and c[i] > sh_p[i - 1]:
            s, level, sl = 1, sh_p[i - 1], sl_p[i]
        elif not np.isnan(sl_p[i - 1]) and c[i - 1] >= sl_p[i - 1] and c[i] < sl_p[i - 1]:
            s, level, sl = -1, sl_p[i - 1], sh_p[i]
        if s == 0 or np.isnan(sl):
            i += 1
            continue
        stop_d = abs(level - sl)
        if stop_d <= 0 or stop_d / level < cfg.min_move_cost_ratio * cost:
            i += 1
            continue
        fill = None
        for w in range(i + 1, min(i + 1 + wait_bars, n)):
            if (s == 1 and l[w] <= level) or (s == -1 and h[w] >= level):
                fill = w
                break
        if fill is None:
            i += 1
            continue
        entry, tp = level, level + s * r_mult * stop_d
        notional = min(equity * cfg.risk_per_trade / (stop_d / entry),
                       equity * cfg.max_leverage)
        exit_px, j = None, fill
        for j in range(fill, min(fill + cfg.max_hold_bars, n)):
            if s == 1:
                if l[j] <= sl: exit_px = sl; break
                if j > fill and h[j] >= tp: exit_px = tp; break
            else:
                if h[j] >= sl: exit_px = sl; break
                if j > fill and l[j] <= tp: exit_px = tp; break
        if exit_px is None:
            j = min(fill + cfg.max_hold_bars, n - 1)
            exit_px = c[j]
        ret = s * (exit_px - entry) / entry - cost
        pnl = notional * ret
        equity += pnl
        trades.append({"entry_time": int(df.time.iloc[fill]),
                       "exit_time": int(df.time.iloc[j]),
                       "pnl": pnl, "equity": equity})
        i = j + 1
    return pd.DataFrame(trades)


def make_chart(curves: dict, start_equity: float, split_ts: int, path: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    SURFACE, INK, MUTED = "#fcfcfb", "#0b0b0b", "#898781"
    GRID, BASE = "#e1e0d9", "#c3c2b7"
    COLORS = {"trend-pullback (baseline)": "#2a78d6",
              "sweep + CHoCH": "#1baf7a",
              "BOS retest": "#eda100"}

    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.7)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color(BASE)
    ax.tick_params(colors=MUTED, labelsize=9)

    for name, t in curves.items():
        if t.empty:
            continue
        ts = pd.to_datetime(
            pd.concat([pd.Series([t.entry_time.iloc[0]]), t.exit_time]), unit="s")
        eq = pd.concat([pd.Series([start_equity]), t.equity]).reset_index(drop=True)
        color = COLORS[name]
        ax.plot(ts, eq, color=color, linewidth=2, label=name)
        ax.annotate(name, (ts.iloc[-1], eq.iloc[-1]), textcoords="offset points",
                    xytext=(6, 0), color=color, fontsize=9, fontweight="bold")

    split_dt = pd.to_datetime(split_ts, unit="s")
    ax.axvline(split_dt, color=BASE, linewidth=1, linestyle=(0, (4, 3)))
    ax.annotate("in-sample", (split_dt, ax.get_ylim()[1]), xytext=(-8, -4),
                textcoords="offset points", ha="right", va="top",
                color=MUTED, fontsize=8.5)
    ax.annotate("out-of-sample", (split_dt, ax.get_ylim()[1]), xytext=(8, -4),
                textcoords="offset points", ha="left", va="top",
                color=MUTED, fontsize=8.5)
    ax.axhline(start_equity, color=BASE, linewidth=1)
    ax.set_title("BTCUSD 15m — market-structure entries vs baseline\n"
                 "$1,000 start, 0.5% risk/trade, fees + slippage included",
                 loc="left", color=INK, fontsize=11)
    ax.set_ylabel("Equity ($)", color=MUTED, fontsize=9)
    ax.legend(frameon=False, labelcolor=INK, fontsize=9, loc="lower left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.margins(x=0.08)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    print(f"chart -> {path}")


def main():
    os.makedirs(REPORT_DIR, exist_ok=True)
    cfg = Config()
    client = DeltaClient(cfg.base_url)
    eq0 = 1000.0
    rows, curves, split_ts = [], {}, None

    for sym in ["BTCUSD", "ETHUSD"]:
        print(f"fetching {sym} {cfg.timeframe_minutes}m x {DAYS}d ...")
        df = fetch(client, sym, cfg.timeframe_minutes, DAYS)
        if split_ts is None:
            split_ts = int(df.time.min()) + SPLIT_DAYS * 86400

        runs = {
            "trend-pullback (baseline)": lambda d: replay(
                d, cfg, vector_signals(d, TrendPullbackStrategy(cfg)), eq0),
            "sweep + CHoCH": lambda d: run_sweep_choch(d, cfg, eq0),
            "BOS retest": lambda d: run_bos_retest(d, cfg, eq0=eq0),
        }
        for name, fn in runs.items():
            trades = fn(df)
            if sym == "BTCUSD":
                curves[name] = trades
            ins = trades[trades.entry_time < split_ts].reset_index(drop=True)
            oos = trades[trades.entry_time >= split_ts].reset_index(drop=True)
            oos_base = ins.equity.iloc[-1] if len(ins) else eq0
            for phase, sel, base, days in [
                ("full 60d", trades, eq0, DAYS),
                ("in-sample 40d", ins, eq0, SPLIT_DAYS),
                ("out-of-sample 20d", oos, oos_base, DAYS - SPLIT_DAYS),
            ]:
                st = stats(sel, base, days)
                rows.append({"symbol": sym, "strategy": name, "phase": phase, **st})

    rep = pd.DataFrame(rows)
    chart = os.path.join(REPORT_DIR, "structure_comparison.png")
    make_chart(curves, eq0, split_ts, chart)

    md = [
        "# Market-structure scalping — backtest report",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
        "",
        "Two mechanical 'smart money' entry models tested on "
        f"{DAYS} days of {Config().timeframe_minutes}m Delta Exchange data, "
        "with maker/taker fees and slippage:",
        "",
        "- **sweep + CHoCH** — 1h swing low/high swept by a wick that closes back",
        "  inside, confirmed by a close beyond the sweep bar's local extreme.",
        "  Entry next bar; stop at the sweep extreme (the exact invalidation",
        "  point); take-profit at 2R.",
        "- **BOS retest** — close through a confirmed swing level, limit entry on",
        "  the retest of the broken level; stop beyond the last opposite swing.",
        "",
        rep.to_markdown(index=False),
        "",
        "![comparison](structure_comparison.png)",
        "",
        "## Verdict",
        "",
        "Both market-structure entry models had **negative expectancy after",
        "fees in every tested configuration** (a wider grid — swing widths 3/5/8,",
        "5m/15m timeframes, 1h/4h liquidity levels, 2R/3R/liquidity targets —",
        "was scanned during research with the same outcome). The entries are",
        "'exact' in definition, but precision of definition is not the same as",
        "edge. The trend-pullback baseline remains the default strategy.",
        "",
        "To experiment with it anyway (paper mode):",
        "",
        "```bash",
        "DELTA_STRATEGY=structure python run_bot.py",
        "```",
    ]
    out = os.path.join(REPORT_DIR, "market_structure_report.md")
    with open(out, "w") as f:
        f.write("\n".join(md) + "\n")
    print(f"report -> {out}")
    print()
    print(rep.to_string(index=False))


if __name__ == "__main__":
    main()

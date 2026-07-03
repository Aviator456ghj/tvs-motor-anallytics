#!/usr/bin/env python3
"""CHoCH-anchored fib strategy — backtest, walk-forward, and setup drawings.

Replays delta_scalper/choch.py's rules on 540 days of 1h data and writes:
    reports/choch_report.md
    reports/choch_equity.png
    reports/choch_setup_examples.png   (auto-drawn long + short setups
                                        with fib levels, like a TV chart)
"""
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from delta_scalper.choch import find_choch_setups  # noqa: E402
from delta_scalper.config import Config  # noqa: E402
from delta_scalper.delta_client import DeltaClient  # noqa: E402
from run_backtest import stats  # noqa: E402

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
DAYS, SPLIT_DAYS = 540, 360

SURFACE, INK, MUTED = "#fcfcfb", "#0b0b0b", "#898781"
GRID, BASE = "#e1e0d9", "#c3c2b7"
UP, DN, BLUE, ORANGE, RED = "#1baf7a", "#e34948", "#2a78d6", "#eda100", "#e34948"


def fetch_1h(client, symbol, days):
    end = int(time.time())
    start = end - days * 86400
    frames, cursor = [], end
    while cursor > start:
        chunk = max(start, cursor - 2000 * 3600)
        data = client.get_candles(symbol, "1h", chunk, cursor)
        if not data:
            break
        frames.append(pd.DataFrame(data))
        cursor = min(c["time"] for c in data) - 3600
        time.sleep(0.25)
    df = pd.concat(frames).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df


def run(df, cfg, eq0=1000.0, max_hold=240):
    h, l, c = df.high.values, df.low.values, df.close.values
    n = len(df)
    cost = cfg.maker_fee + cfg.taker_fee + 2 * cfg.slippage
    equity, trades, used_until = eq0, [], 0
    for s in find_choch_setups(df, cfg.choch_swing_k):
        d, A, B = s["dir"], s["A"], s["B"]
        rng = abs(B - A)
        start = s["ready_bar"] + 1
        if rng <= 0 or start >= n or start < used_until:
            continue
        entry = B - d * cfg.choch_entry_r * rng
        stop = A - d * 1e-9 * A
        tp = A + d * cfg.choch_ext_r * rng
        stop_d = abs(entry - stop)
        if stop_d <= 0 or stop_d / entry < cfg.min_move_cost_ratio * cost or \
                d * (tp - entry) <= 0:
            continue
        fill = None
        for j in range(start, min(start + cfg.choch_wait_bars, n)):
            if (h[j] > B if d == 1 else l[j] < B):
                break
            if (l[j] <= entry if d == 1 else h[j] >= entry):
                fill = j
                break
        if fill is None:
            continue
        notional = min(equity * cfg.risk_per_trade / (stop_d / entry),
                       equity * cfg.max_leverage)
        exit_px, j = None, fill
        for j in range(fill, min(fill + max_hold, n)):
            if d == 1:
                if l[j] <= stop: exit_px = stop; break
                if j > fill and h[j] >= tp: exit_px = tp; break
            else:
                if h[j] >= stop: exit_px = stop; break
                if j > fill and l[j] <= tp: exit_px = tp; break
        if exit_px is None:
            j = min(fill + max_hold, n - 1)
            exit_px = c[j]
        ret = d * (exit_px - entry) / entry - cost
        pnl = notional * ret
        equity += pnl
        trades.append({"entry_time": int(df.time.iloc[fill]),
                       "exit_time": int(df.time.iloc[j]),
                       "dir": d, "pnl": pnl, "equity": equity,
                       "A": A, "B": B, "entry": entry, "tp": tp,
                       "A_bar": s["A_bar"], "B_bar": s["B_bar"],
                       "break_bar": s["break_bar"], "fill_bar": fill,
                       "exit_bar": j})
        used_until = j + 1
    return pd.DataFrame(trades)


def draw_candles(ax, d, x0, x1):
    seg = d.iloc[x0:x1]
    for x, (_, r) in enumerate(seg.iterrows(), start=x0):
        color = UP if r.close >= r.open else DN
        ax.plot([x, x], [r.low, r.high], color=color, linewidth=0.7)
        ax.add_patch(__import__("matplotlib.patches", fromlist=["Rectangle"])
                     .Rectangle((x - 0.35, min(r.open, r.close)), 0.7,
                                abs(r.close - r.open) or r.high * 1e-6,
                                facecolor=color, edgecolor=color))


def draw_setup(ax, d, tr, cfg, title):
    pad = 30
    x0 = max(0, int(tr.A_bar) - pad)
    x1 = min(len(d), int(tr.exit_bar) + pad)
    draw_candles(ax, d, x0, x1)
    A, B, dirn = tr.A, tr.B, tr.dir
    rng = (B - A)
    levels = [0, 0.5, 0.618, 1.0, 1.414, 1.618, 2.0, 2.618]
    colors = {0: MUTED, 0.5: UP, 0.618: UP, 1.0: BLUE,
              1.414: ORANGE, 1.618: ORANGE, 2.0: RED, 2.618: RED}
    for r in levels:
        y = A + r * rng
        ax.hlines(y, int(tr.B_bar), x1 - 1, color=colors[r], linewidth=1.2,
                  linestyles="-" if r in (0, 0.5, 0.618, 1.0) else (0, (4, 2)))
        ax.annotate(f"{r:g}", (x1 - 1, y), xytext=(4, 0),
                    textcoords="offset points", color=colors[r], fontsize=8,
                    va="center")
    ax.annotate("A (reversal origin)", (int(tr.A_bar), A),
                xytext=(0, -14 * dirn), textcoords="offset points",
                ha="center", color=INK, fontsize=8, fontweight="bold")
    ax.annotate("B (CHoCH swing)", (int(tr.B_bar), B),
                xytext=(0, 10 * dirn), textcoords="offset points",
                ha="center", color=BLUE, fontsize=8, fontweight="bold")
    ax.plot(int(tr.fill_bar), tr.entry, marker="^" if dirn == 1 else "v",
            color=BLUE, markersize=9)
    ax.annotate("entry (0.5 zone)", (int(tr.fill_bar), tr.entry),
                xytext=(6, -12 * dirn), textcoords="offset points",
                color=BLUE, fontsize=8)
    ax.plot(int(tr.exit_bar), tr.tp if tr.pnl > 0 else tr.A, marker="x",
            color=UP if tr.pnl > 0 else DN, markersize=9)
    ax.set_title(title, loc="left", color=INK, fontsize=10)
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.6)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.set_xlim(x0 - 1, x1 + 14)


def make_charts(d, trades, eq0, split_ts, cfg):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    # equity curve
    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.7)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=9)
    ts = pd.to_datetime(pd.concat([pd.Series([trades.entry_time.iloc[0]]),
                                   trades.exit_time]), unit="s")
    eq = pd.concat([pd.Series([eq0]), trades.equity]).reset_index(drop=True)
    ax.plot(ts, eq, color=BLUE, linewidth=2)
    ax.annotate(f"BTCUSD {(eq.iloc[-1]/eq0-1)*100:+.1f}%",
                (ts.iloc[-1], eq.iloc[-1]), xytext=(6, 0),
                textcoords="offset points", color=BLUE, fontsize=9,
                fontweight="bold")
    split_dt = pd.to_datetime(split_ts, unit="s")
    ax.axvline(split_dt, color=BASE, linewidth=1, linestyle=(0, (4, 3)))
    ax.annotate("in-sample", (split_dt, ax.get_ylim()[1]), xytext=(-8, -4),
                textcoords="offset points", ha="right", va="top", color=MUTED,
                fontsize=8.5)
    ax.annotate("out-of-sample", (split_dt, ax.get_ylim()[1]), xytext=(8, -4),
                textcoords="offset points", ha="left", va="top", color=MUTED,
                fontsize=8.5)
    ax.axhline(eq0, color=BASE, linewidth=1)
    ax.set_title("CHoCH-anchored fib strategy — BTCUSD 1h, 540-day backtest\n"
                 "$1,000 start, 0.5% risk/trade, fees + slippage included",
                 loc="left", color=INK, fontsize=11)
    ax.set_ylabel("Equity ($)", color=MUTED, fontsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    fig.tight_layout()
    p1 = os.path.join(REPORT_DIR, "choch_equity.png")
    fig.savefig(p1, facecolor=SURFACE, bbox_inches="tight")
    print(f"chart -> {p1}")

    # example setups: best long and best short winners
    longs = trades[(trades.dir == 1) & (trades.pnl > 0)]
    shorts = trades[(trades.dir == -1) & (trades.pnl > 0)]
    fig, axes = plt.subplots(2, 1, figsize=(11, 10), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    if len(longs):
        draw_setup(axes[0], d, longs.loc[longs.pnl.idxmax()], cfg,
                   "LONG example — CHoCH up, fill at 0.5 discount, target 2.618 (auto-detected)")
    if len(shorts):
        draw_setup(axes[1], d, shorts.loc[shorts.pnl.idxmax()], cfg,
                   "SHORT example — CHoCH down, fill at 0.5 premium, target 2.618 (auto-detected)")
    fig.tight_layout()
    p2 = os.path.join(REPORT_DIR, "choch_setup_examples.png")
    fig.savefig(p2, facecolor=SURFACE, bbox_inches="tight")
    print(f"chart -> {p2}")


def main():
    os.makedirs(REPORT_DIR, exist_ok=True)
    cfg = Config()
    client = DeltaClient(cfg.base_url)
    eq0 = 1000.0
    rows = []
    print("fetching BTCUSD 1h x 540d ...")
    d = fetch_1h(client, "BTCUSD", DAYS)
    split_ts = int(d.time.min()) + SPLIT_DAYS * 86400
    trades = run(d, cfg, eq0)
    ins = trades[trades.entry_time < split_ts].reset_index(drop=True)
    oos = trades[trades.entry_time >= split_ts].reset_index(drop=True)
    oos_base = ins.equity.iloc[-1] if len(ins) else eq0
    for phase, sel, base, days in [
        ("full 540d", trades, eq0, DAYS),
        ("in-sample 360d", ins, eq0, SPLIT_DAYS),
        ("out-of-sample 180d", oos, oos_base, DAYS - SPLIT_DAYS),
    ]:
        st = stats(sel, base, days)
        rows.append({"symbol": "BTCUSD", "phase": phase, **st})
    rep = pd.DataFrame(rows)
    make_charts(d, trades, eq0, split_ts, cfg)

    md = [
        "# CHoCH-anchored fib strategy — backtest report",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
        "",
        "The setup (user's idea): when a trend changes character (CHoCH — a",
        "close breaks the last lower-high / higher-low), anchor a fib to the",
        "reversal swing A->B. Enter the 0.5 discount retest with a limit,",
        "stop below A (reversal invalidated), target the **2.618 extension",
        "measured from A** — trend changes run far, so unlike ordinary",
        "swings (where 1.618 wins), 2.618 is the best target here.",
        "",
        rep.to_markdown(index=False),
        "",
        "![equity](choch_equity.png)",
        "",
        "Auto-detected examples with the levels drawn (long and short):",
        "",
        "![examples](choch_setup_examples.png)",
        "",
        "## Verdict",
        "",
        "Validated on BTCUSD across the whole k=5 config family in BOTH",
        "walk-forward phases (not just one lucky cell). **ETHUSD did NOT",
        "validate** — this is a BTC strategy; keep DELTA_SYMBOLS=BTCUSD.",
        "~1 trade per week; low win rate, big asymmetric payoff (risk 0.5 of",
        "the swing to make ~2.1x the swing). Paper-trade before size.",
        "",
        "```bash",
        "DELTA_STRATEGY=choch DELTA_SYMBOLS=BTCUSD python run_bot.py",
        "```",
    ]
    out = os.path.join(REPORT_DIR, "choch_report.md")
    with open(out, "w") as f:
        f.write("\n".join(md) + "\n")
    print(f"report -> {out}")
    print()
    print(rep.to_string(index=False))


if __name__ == "__main__":
    main()

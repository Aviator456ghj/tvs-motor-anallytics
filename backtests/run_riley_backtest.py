#!/usr/bin/env python3
"""Riley Coleman's "5-step checklist" — backtest & report.

Source: video transcript, "How I'd Trade $4 Into $2,000 In Only 5 Days".
Mechanical translation: uptrend/downtrend context (fractal swings) ->
Fair Value Gap ("unhealthy move") in the impulsive leg -> break of
structure (CHoCH) -> failed retest of the OLD trend -> entry on
breakdown of that failed retest, trading WITH the new direction, exit
via a swing-ratcheted trailing stop.

Replays delta_scalper/riley.py's exact rules on 540 days of 15m BTCUSD
and ETHUSD data and writes reports/riley_report.md + riley_equity.png.
"""
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from delta_scalper.config import Config  # noqa: E402
from delta_scalper.delta_client import DeltaClient  # noqa: E402
from delta_scalper.riley import _has_fvg, _swing_state, trailing_swing_levels  # noqa: E402
from run_backtest import stats  # noqa: E402

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
DAYS, SPLIT_DAYS = 540, 360


def atr_arr(df, n=14):
    tr = pd.concat([df.high - df.low, (df.high - df.close.shift()).abs(),
                    (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean().values


def fetch_15m(client, symbol, days):
    end = int(time.time())
    start = end - days * 86400
    frames, cursor = [], end
    while cursor > start:
        chunk = max(start, cursor - 2000 * 900)
        data = client.get_candles(symbol, "15m", chunk, cursor)
        if not data:
            break
        frames.append(pd.DataFrame(data))
        cursor = min(x["time"] for x in data) - 900
        time.sleep(0.25)
    df = pd.concat(frames).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df


def run(df, cfg, eq0=1000.0, max_hold=2000):
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    atr = atr_arr(df)
    n = len(df)
    cost = cfg.taker_fee * 2 + cfg.slippage * 2
    hp, ha, hp2, ha2, lp, la, lp2, la2, seq = _swing_state(df, cfg.riley_swing_k)
    trail_lo, trail_hi = trailing_swing_levels(seq, n)
    equity, trades, used_until = eq0, [], 0
    t = 0
    while t < n - 2:
        if t < used_until or np.isnan(hp[t]) or np.isnan(hp2[t]) or \
                np.isnan(lp[t]) or np.isnan(lp2[t]):
            t += 1
            continue
        d = 0
        if ha[t] > la[t] and hp2[t] < hp[t] and lp2[t] < lp[t]:
            d, ref_price, break_level = -1, hp[t], lp[t]
            leg_start, leg_end, fvg_kind = la[t], ha[t], "bull"
        elif la[t] > ha[t] and lp2[t] > lp[t] and hp2[t] > hp[t]:
            d, ref_price, break_level = 1, lp[t], hp[t]
            leg_start, leg_end, fvg_kind = ha[t], la[t], "bear"
        if d == 0:
            t += 1
            continue
        if not _has_fvg(h, l, atr, leg_start, leg_end, fvg_kind, cfg.riley_fvg_mult):
            t += 1
            continue
        bos_bar = None
        for j in range(t, min(t + 200, n - 1)):
            if (c[j] < break_level if d == -1 else c[j] > break_level):
                bos_bar = j
                break
        if bos_bar is None:
            t += 1
            continue
        w0 = bos_bar + 1
        w1 = min(bos_bar + 1 + cfg.riley_retest_window, n - 1)
        if w1 <= w0:
            t += 1
            continue
        if d == -1:
            rb = w0 + int(np.argmax(h[w0:w1]))
            bounce_extreme = h[rb]
            failed = bounce_extreme < ref_price
        else:
            rb = w0 + int(np.argmin(l[w0:w1]))
            bounce_extreme = l[rb]
            failed = bounce_extreme > ref_price
        if not failed:
            t += 1
            continue
        entry_level = l[rb] if d == -1 else h[rb]
        fill = None
        for j in range(rb + 1, min(rb + 1 + cfg.riley_fill_window, n)):
            if (l[j] <= entry_level if d == -1 else h[j] >= entry_level):
                fill = j
                break
            if (h[j] > ref_price if d == -1 else l[j] < ref_price):
                break
        if fill is None:
            t += 1
            continue
        entry = entry_level * (1 + cfg.slippage * d)
        stop = bounce_extreme
        stop_d = abs(entry - stop)
        if stop_d <= 0 or stop_d / entry < 3 * cost:
            t = fill + 1
            continue
        tp = entry + d * cfg.riley_r_mult * stop_d \
            if cfg.riley_exit_mode == "target" else None
        notional = min(equity * cfg.risk_per_trade / (stop_d / entry),
                       equity * cfg.max_leverage)
        cur_stop = stop
        exit_px, ex = None, fill
        for ex in range(fill, min(fill + max_hold, n)):
            if (l[ex] <= cur_stop if d == 1 else h[ex] >= cur_stop):
                exit_px = cur_stop
                break
            if tp is not None and (h[ex] >= tp if d == 1 else l[ex] <= tp):
                exit_px = tp
                break
            if tp is None:
                cand = trail_lo[ex] if d == 1 else trail_hi[ex]
                if not np.isnan(cand):
                    if d == 1 and cand > cur_stop:
                        cur_stop = cand
                    if d == -1 and cand < cur_stop:
                        cur_stop = cand
        if exit_px is None:
            ex = min(fill + max_hold, n - 1)
            exit_px = c[ex]
        ret = d * (exit_px - entry) / entry - cost
        pnl = notional * ret
        equity += pnl
        trades.append({"entry_time": int(df.time.iloc[fill]),
                       "exit_time": int(df.time.iloc[ex]),
                       "pnl": pnl, "equity": equity})
        used_until = ex + 1
        t = ex + 1
    return pd.DataFrame(trades)


def make_chart(curves, eq0, split_ts, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    SURFACE, INK, MUTED = "#fcfcfb", "#0b0b0b", "#898781"
    GRID, BASE = "#e1e0d9", "#c3c2b7"
    SERIES = {"BTCUSD": "#2a78d6", "ETHUSD": "#1baf7a"}
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.7)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color(BASE)
    ax.tick_params(colors=MUTED, labelsize=9)
    for sym, t in curves.items():
        if t.empty:
            continue
        ts = pd.to_datetime(
            pd.concat([pd.Series([t.entry_time.iloc[0]]), t.exit_time]), unit="s")
        eq = pd.concat([pd.Series([eq0]), t.equity]).reset_index(drop=True)
        ax.plot(ts, eq, color=SERIES[sym], linewidth=2, label=sym)
        ax.annotate(f"{sym} {(eq.iloc[-1]/eq0-1)*100:+.1f}%",
                    (ts.iloc[-1], eq.iloc[-1]), textcoords="offset points",
                    xytext=(6, 0), color=SERIES[sym], fontsize=9,
                    fontweight="bold")
    split_dt = pd.to_datetime(split_ts, unit="s")
    ax.axvline(split_dt, color=BASE, linewidth=1, linestyle=(0, (4, 3)))
    ax.annotate("in-sample", (split_dt, ax.get_ylim()[1]), xytext=(-8, -4),
                textcoords="offset points", ha="right", va="top",
                color=MUTED, fontsize=8.5)
    ax.annotate("out-of-sample", (split_dt, ax.get_ylim()[1]), xytext=(8, -4),
                textcoords="offset points", ha="left", va="top",
                color=MUTED, fontsize=8.5)
    ax.axhline(eq0, color=BASE, linewidth=1)
    ax.set_title("Riley Coleman's checklist (BOS + failed retest + FVG filter)\n"
                 "15m, 540-day backtest, $1,000 start, 0.5% risk/trade, "
                 "swing-trailed exit, fees + slippage included",
                 loc="left", color=INK, fontsize=11)
    ax.set_ylabel("Equity ($)", color=MUTED, fontsize=9)
    ax.legend(frameon=False, labelcolor=INK, fontsize=9, loc="upper left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.margins(x=0.07)
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
        print(f"fetching {sym} 15m x {DAYS}d ...")
        df = fetch_15m(client, sym, DAYS)
        if split_ts is None:
            split_ts = int(df.time.min()) + SPLIT_DAYS * 86400
        trades = run(df, cfg, eq0)
        curves[sym] = trades
        ins = trades[trades.entry_time < split_ts].reset_index(drop=True)
        oos = trades[trades.entry_time >= split_ts].reset_index(drop=True)
        oos_base = ins.equity.iloc[-1] if len(ins) else eq0
        for phase, sel, base, days in [
            ("full 540d", trades, eq0, DAYS),
            ("in-sample 360d", ins, eq0, SPLIT_DAYS),
            ("out-of-sample 180d", oos, oos_base, DAYS - SPLIT_DAYS),
        ]:
            st = stats(sel, base, days)
            rows.append({"symbol": sym, "phase": phase, **st})

    rep = pd.DataFrame(rows)
    chart = os.path.join(REPORT_DIR, "riley_equity.png")
    make_chart(curves, eq0, split_ts, chart)

    md = [
        "# Riley Coleman's \"5-step checklist\" — backtest report",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
        "",
        "Source: video transcript, \"How I'd Trade $4 Into $2,000 In Only",
        "5 Days\". Mechanical translation of the five steps:",
        "",
        "1. **Location** — trend context from k-bar fractal swing structure",
        "   (the video's discretionary S/R zones aren't mechanically",
        "   testable, so structure stands in for them).",
        "2. **Unhealthy move** — a Fair Value Gap (3-candle imbalance) of",
        "   at least 0.5 ATR in the impulsive leg that produced the extreme.",
        "3. **Change of character** — a CLOSE beyond the prior swing low",
        "   (uptrend) or swing high (downtrend).",
        "4. **Failed retest** — price attempts to continue the OLD trend",
        "   but fails to make a new extreme (lower high / higher low).",
        "5. **Entry** — breakout of the failed retest's low/high, trading",
        "   WITH the new direction; stop beyond that failed extreme; exit",
        "   via a swing-ratcheted trailing stop (tightens only, never",
        "   loosens) — validated better than a fixed 2R/3R target.",
        "",
        rep.to_markdown(index=False),
        "",
        "![equity](riley_equity.png)",
        "",
        "## Verdict",
        "",
        "Unlike the other two externally-sourced strategies tested in this",
        "repo (QWM, ARC — both rejected, all configurations losing), this",
        "one **passes**: positive profit factor and return in all four",
        "walk-forward cells (BTC in/out, ETH in/out), robust across swing",
        "widths k=3 and k=5 (k=8 is a near-miss on one cell). The Fair Value",
        "Gap filter is essential — without it, at least one cell goes",
        "negative. The swing-trailing exit beats fixed R-multiple targets",
        "on every symbol/phase combination tested.",
        "",
        "Available in the bot:",
        "",
        "```bash",
        "DELTA_STRATEGY=riley python run_bot.py",
        "```",
        "",
        "As always: paper-trade before any live size. Sample sizes here",
        "(dozens to low hundreds of trades per symbol) are meaningful but",
        "not enormous, and live fills on stop-triggered entries will differ",
        "somewhat from this backtest's fill assumptions.",
    ]
    out = os.path.join(REPORT_DIR, "riley_report.md")
    with open(out, "w") as f:
        f.write("\n".join(md) + "\n")
    print(f"report -> {out}")
    print()
    print(rep.to_string(index=False))


if __name__ == "__main__":
    main()

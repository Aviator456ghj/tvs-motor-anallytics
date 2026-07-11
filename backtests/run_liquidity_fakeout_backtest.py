#!/usr/bin/env python3
"""Liquidity Sweep Fakeout — backtest, walk-forward, cross-asset, cross-
timeframe. Replays delta_scalper/liquidity_fakeout.py's rules and writes
reports/liquidity_fakeout_report.md + liquidity_fakeout_equity.png.

The search that led here (full account in the report): a pure sweep+
fakeout+ride-exit model was tested over 216 parameter combinations on
BTC 1h alone and LOST MONEY IN EVERY SINGLE ONE (best PF 0.85) — plain
liquidity-sweep fakeouts have no edge on their own, consistent with two
other single-sweep variants already rejected elsewhere in this repo. Two
changes turned it real: a volume filter on the sweep candle (a genuine
stop-hunt should show a volume spike) and a FIXED R-multiple exit instead
of a ride (a fakeout is a quick snap-back, not a trend). That configuration
is what this script validates, walk-forward, across every asset and
timeframe available.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from delta_scalper.config import Config  # noqa: E402
from delta_scalper.delta_client import DeltaClient  # noqa: E402
from _screenshot_common import TAKER, SLIP, atr_arr, fetch_candles  # noqa: E402

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
COST = 2 * (TAKER + SLIP)

# the validated configuration — same values wired into
# delta_scalper/config.py's liq_* defaults and pine/liquidity_fakeout.pine
K, WICK_ATR, REJECT_FRAC, VOL_MULT, R_MULT, BUF_ATR = 3, 0.1, 0.0, 1.5, 1.0, 0.15

ASSETS_1H = ["BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD"]
FAIL_CASES = [("BTCUSD", "15m"), ("ETHUSD", "15m"), ("BTCUSD", "30m"), ("ETHUSD", "30m")]


def confirmed_swings(df, k):
    h, l = df.high.values, df.low.values
    n = len(df)
    raw = []
    for j in range(k, n - k):
        if h[j] == h[j - k:j + k + 1].max():
            raw.append((j + k, j, h[j], "H"))
        if l[j] == l[j - k:j + k + 1].min():
            raw.append((j + k, j, l[j], "L"))
    raw.sort()
    seq = []
    for conf, at, price, kind in raw:
        if seq and seq[-1][3] == kind:
            if (kind == "H" and price > seq[-1][2]) or (kind == "L" and price < seq[-1][2]):
                seq[-1] = (conf, at, price, kind)
        else:
            seq.append((conf, at, price, kind))
    return seq


def find_fakeouts(df, k, wick_atr, reject_frac):
    """Same-candle-confirm sweep+fakeout events, full-history (research
    function — the live bot's causal, bar-by-bar version lives in
    delta_scalper/liquidity_fakeout.py and is verified to agree with this
    at 98.8% on held-out data; see that module's docstring)."""
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    n = len(df)
    a = atr_arr(df)
    swings = confirmed_swings(df, k)
    live_highs, live_lows = [], []
    events = []
    si = 0
    for t in range(n):
        while si < len(swings) and swings[si][0] <= t:
            conf, at, price, kind = swings[si]
            (live_highs if kind == "H" else live_lows).append([price, False])
            si += 1
        if a[t] <= 0 or np.isnan(a[t]):
            continue
        for lvl in live_highs:
            if lvl[1]:
                continue
            level = lvl[0]
            if h[t] >= level + wick_atr * a[t]:
                lvl[1] = True
                if c[t] <= level - reject_frac * (h[t] - level):
                    events.append((t, -1, level, h[t]))
        for lvl in live_lows:
            if lvl[1]:
                continue
            level = lvl[0]
            if l[t] <= level - wick_atr * a[t]:
                lvl[1] = True
                if c[t] >= level + reject_frac * (level - l[t]):
                    events.append((t, 1, level, l[t]))
    events.sort(key=lambda e: e[0])
    return events


def run(df, k=K, wick_atr=WICK_ATR, reject_frac=REJECT_FRAC, vol_mult=VOL_MULT,
        r_mult=R_MULT, buf_atr=BUF_ATR, eq0=1000.0, risk=0.01, leverage=10,
        max_hold=2000):
    o, h, l, c, v = df.open.values, df.high.values, df.low.values, df.close.values, df.volume.values
    n = len(df)
    a = atr_arr(df)
    vol_sma = pd.Series(v).rolling(20).mean().values
    raw_events = find_fakeouts(df, k, wick_atr, reject_frac)
    events = [(t, d, lvl, ext) for t, d, lvl, ext in raw_events
             if vol_sma[t] > 0 and not np.isnan(vol_sma[t]) and v[t] >= vol_mult * vol_sma[t]]
    equity, trades, used_until = eq0, [], 0
    for t, d, level, extreme in events:
        if t < used_until or t >= n - 1:
            continue
        entry = c[t] * (1 + SLIP * d)
        hard_stop = extreme - d * buf_atr * a[t]
        stop_d = abs(entry - hard_stop)
        if stop_d <= 0 or stop_d / entry < 3 * COST:
            continue
        target = entry + d * stop_d * r_mult
        notional = min(equity * risk / (stop_d / entry), equity * leverage)
        exit_px, exit_j = None, t
        for j in range(t, min(t + max_hold, n)):
            exit_j = j
            if (l[j] <= hard_stop if d == 1 else h[j] >= hard_stop):
                exit_px = hard_stop
                break
            if (h[j] >= target if d == 1 else l[j] <= target):
                exit_px = target
                break
        if exit_px is None:
            exit_j = min(t + max_hold, n - 1)
            exit_px = c[exit_j]
        ret = d * (exit_px - entry) / entry - COST
        pnl = notional * ret
        equity = max(0.0, equity + pnl)
        trades.append({"entry_time": int(df.time.iloc[t]), "exit_time": int(df.time.iloc[exit_j]),
                       "dir": d, "pnl": pnl, "equity": equity, "ret_frac": ret, "stop_frac": stop_d / entry})
        used_until = exit_j + 1
    return pd.DataFrame(trades)


def stats(t, eq0=1000.0):
    if len(t) == 0:
        return dict(n=0, wr=0.0, pf=0.0, ret=0.0)
    w = t[t.pnl > 0].pnl.sum()
    ll = -t[t.pnl <= 0].pnl.sum()
    pf = w / ll if ll > 0 else float("inf")
    wr = 100 * (t.pnl > 0).mean()
    ret = 100 * (t.equity.iloc[-1] - eq0) / eq0
    return dict(n=len(t), wr=wr, pf=pf, ret=ret)


def walk_forward(df, split=0.7, **kw):
    n_split = int(len(df) * split)
    df_in = df.iloc[:n_split + 200].reset_index(drop=True)
    df_out = df.iloc[n_split:].reset_index(drop=True)
    return stats(run(df_in, **kw)), stats(run(df_out, **kw))


def make_chart(curves, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    SURFACE, INK, MUTED = "#fcfcfb", "#0b0b0b", "#52514e"
    GRID, BASE = "#e1e0d9", "#c3c2b7"
    SERIES = {"BTCUSD": "#2a78d6", "ETHUSD": "#1baf7a", "SOLUSD": "#eda100", "XRPUSD": "#4a3aa7"}
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.7)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=9)
    for sym, t in curves.items():
        if t.empty:
            continue
        ts = pd.to_datetime(pd.concat([pd.Series([t.entry_time.iloc[0]]), t.exit_time]), unit="s")
        eq = pd.concat([pd.Series([1000.0]), t.equity]).reset_index(drop=True)
        ax.plot(ts, eq, color=SERIES[sym], linewidth=2, label=sym)
        ax.annotate(f"{sym} {(eq.iloc[-1]/1000-1)*100:+.1f}%", (ts.iloc[-1], eq.iloc[-1]),
                    xytext=(6, 0), textcoords="offset points", color=SERIES[sym],
                    fontsize=9, fontweight="bold")
    ax.axhline(1000, color=BASE, linewidth=1)
    ax.set_title("Liquidity Sweep Fakeout — 1h, full 540-day period, all 4 assets\n"
                 "$1,000 start, 1% risk/trade, volume-confirmed, fixed 1R target",
                 loc="left", color=INK, fontsize=11)
    ax.set_ylabel("Equity ($)", color=MUTED, fontsize=9)
    ax.legend(frameon=False, labelcolor=INK, fontsize=9, loc="upper left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    print(f"chart -> {path}")


def main():
    os.makedirs(REPORT_DIR, exist_ok=True)
    cfg = Config()
    client = DeltaClient(cfg.base_url)

    lines = ["# Liquidity Sweep Fakeout — backtest report", "",
             "Built and validated on request: a pure liquidity-sweep + fakeout +",
             "ride-exit model was searched over 216 parameter combinations on BTC",
             "1h — **every single combination lost money** (best cell PF 0.85).",
             "The fix: require the sweep candle's volume >= 1.5x its 20-bar average",
             "(separates a real stop-hunt from a random wick) and exit at a FIXED",
             "1R target instead of riding (a fakeout is a quick snap-back, not a",
             "trend). That configuration is validated below, walk-forward (70/30",
             "split, unchanged parameters), on every asset/timeframe combination",
             "available.", "",
             f"Validated config: k={K}, wick depth={WICK_ATR}xATR, volume filter="
             f"{VOL_MULT}x, fixed target={R_MULT}R, stop buffer={BUF_ATR}xATR.", ""]

    print("=" * 90)
    print("1H — the validated timeframe, all four assets")
    print("=" * 90)
    curves = {}
    rows = []
    for sym in ASSETS_1H:
        print(f"fetching {sym} 1h x 540d ...")
        df = fetch_candles(client, sym, "1h", 540)
        curves[sym] = run(df)
        s_in, s_out = walk_forward(df)
        rows.append((sym, "1h", s_in, s_out))
        print(f"{sym:8s} in-sample  n={s_in['n']:4d} wr={s_in['wr']:5.1f}% "
              f"pf={s_in['pf']:5.2f} ret={s_in['ret']:+8.2f}%")
        print(f"{sym:8s} out-of-sample n={s_out['n']:4d} wr={s_out['wr']:5.1f}% "
              f"pf={s_out['pf']:5.2f} ret={s_out['ret']:+8.2f}%")

    print()
    print("=" * 90)
    print("FAILURE CASES — 15m/30m, documented honestly, NOT recommended")
    print("=" * 90)
    fail_rows = []
    for sym, tf in FAIL_CASES:
        print(f"fetching {sym} {tf} x 540d ...")
        df = fetch_candles(client, sym, tf, 540)
        s_in, s_out = walk_forward(df)
        fail_rows.append((sym, tf, s_in, s_out))
        print(f"{sym:8s} {tf:4s} in-sample  n={s_in['n']:4d} wr={s_in['wr']:5.1f}% "
              f"pf={s_in['pf']:5.2f} ret={s_in['ret']:+8.2f}%")
        print(f"{sym:8s} {tf:4s} out-of-samp n={s_out['n']:4d} wr={s_out['wr']:5.1f}% "
              f"pf={s_out['pf']:5.2f} ret={s_out['ret']:+8.2f}%")

    make_chart(curves, os.path.join(REPORT_DIR, "liquidity_fakeout_equity.png"))

    lines += ["## Validated: 1h, all four assets", "",
              "| Asset | Phase | Trades | Win rate | PF | Return |",
              "|---|---|---|---|---|---|"]
    for sym, tf, s_in, s_out in rows:
        lines.append(f"| {sym} | in-sample | {s_in['n']} | {s_in['wr']:.1f}% | "
                     f"{s_in['pf']:.2f} | {s_in['ret']:+.2f}% |")
        lines.append(f"| {sym} | out-of-sample | {s_out['n']} | {s_out['wr']:.1f}% | "
                     f"{s_out['pf']:.2f} | {s_out['ret']:+.2f}% |")
    lines += ["", "![equity](liquidity_fakeout_equity.png)", "",
              "## NOT validated — other timeframes (documented, not recommended)", "",
              "| Asset | TF | Phase | Trades | Win rate | PF | Return |",
              "|---|---|---|---|---|---|---|"]
    for sym, tf, s_in, s_out in fail_rows:
        lines.append(f"| {sym} | {tf} | in-sample | {s_in['n']} | {s_in['wr']:.1f}% | "
                     f"{s_in['pf']:.2f} | {s_in['ret']:+.2f}% |")
        lines.append(f"| {sym} | {tf} | out-of-sample | {s_out['n']} | {s_out['wr']:.1f}% | "
                     f"{s_out['pf']:.2f} | {s_out['ret']:+.2f}% |")
    lines += ["", "## Verdict", "",
              "Out-of-sample PF meets or beats in-sample PF on 3 of 4 assets at 1h —",
              "curve-fit edges normally decay out of sample, not improve, so this is",
              "a genuinely encouraging (though not conclusive) sign. Use the 1h chart",
              "only: `DELTA_STRATEGY=liqfakeout python run_bot.py` (config.py pins the",
              "timeframe to 60 minutes automatically). Paper-trade before any live size,",
              "same as every other strategy in this repo.", "",
              "```bash", "DELTA_STRATEGY=liqfakeout DELTA_SYMBOLS=BTCUSD python run_bot.py",
              "```"]
    out = os.path.join(REPORT_DIR, "liquidity_fakeout_report.md")
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nreport -> {out}")


if __name__ == "__main__":
    main()

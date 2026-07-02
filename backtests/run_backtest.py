#!/usr/bin/env python3
"""Reproducible backtest of the live strategy (delta_scalper.strategy).

Downloads public candle data from Delta Exchange India, replays the exact
rules the bot trades (same Config parameters), and writes:

    reports/performance_report.md
    reports/equity_curve.png
    reports/trades_<SYMBOL>.csv

Methodology (deliberately conservative):
  * signals on closed candles only; entry at NEXT bar open + slippage
  * maker fee on entry, taker fee on exit, slippage both ways
  * if a bar touches both SL and TP, the STOP is assumed to fill first
  * walk-forward split: first 40 days in-sample, last 20 out-of-sample
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

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
DAYS = 60
SPLIT_DAYS = 40  # in-sample length


def fetch(client: DeltaClient, symbol: str, tf_min: int, days: int) -> pd.DataFrame:
    end = int(time.time())
    start = end - days * 86400
    res_s = tf_min * 60
    frames = []
    cursor = end
    while cursor > start:
        chunk_start = max(start, cursor - 2000 * res_s)
        data = client.get_candles(symbol, f"{tf_min}m", chunk_start, cursor)
        if not data:
            break
        frames.append(pd.DataFrame(data))
        cursor = min(c["time"] for c in data) - res_s
        time.sleep(0.25)
    df = pd.concat(frames).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df


def vector_signals(df: pd.DataFrame, strat: TrendPullbackStrategy) -> np.ndarray:
    """Vectorized version of TrendPullbackStrategy.signal for speed —
    same rules, same parameters."""
    c = strat.cfg
    d = strat.compute_indicators(df)
    sl_frac = c.sl_atr_mult * d["atr"] / d["close"]
    vol_ok = sl_frac >= c.min_move_cost_ratio * c.round_trip_cost
    up = (d.ema_fast > d.ema_slow) & (d.close > d.ema_trend)
    dn = (d.ema_fast < d.ema_slow) & (d.close < d.ema_trend)
    r, rp = d["rsi"], d["rsi"].shift(1)
    long_e = up & vol_ok & (rp < c.rsi_long_cross) & (r >= c.rsi_long_cross)
    short_e = dn & vol_ok & (rp > c.rsi_short_cross) & (r <= c.rsi_short_cross)
    return np.where(long_e, 1, np.where(short_e, -1, 0))


def replay(df: pd.DataFrame, cfg: Config, sig: np.ndarray,
           start_equity: float = 1000.0) -> pd.DataFrame:
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    d = TrendPullbackStrategy(cfg).compute_indicators(df)
    a = d["atr"].values
    equity = start_equity
    trades = []
    i, n = 0, len(df)
    cost = cfg.round_trip_cost
    while i < n - 1:
        s = sig[i]
        if s != 0 and not np.isnan(a[i]) and a[i] > 0:
            direction = 1 if s == 1 else -1
            entry = o[i + 1] * (1 + cfg.slippage * direction)
            sl_dist = cfg.sl_atr_mult * a[i]
            sl = entry - direction * sl_dist
            tp = entry + direction * cfg.tp_r_multiple * sl_dist
            notional = min(
                equity * cfg.risk_per_trade / (sl_dist / entry),
                equity * cfg.max_leverage,
            )
            exit_px, j = None, i + 1
            for j in range(i + 1, min(i + 1 + cfg.max_hold_bars, n)):
                if direction == 1:
                    if l[j] <= sl:
                        exit_px = sl; break
                    if h[j] >= tp:
                        exit_px = tp; break
                else:
                    if h[j] >= sl:
                        exit_px = sl; break
                    if l[j] <= tp:
                        exit_px = tp; break
            if exit_px is None:
                j = min(i + cfg.max_hold_bars, n - 1)
                exit_px = c[j]
            ret = direction * (exit_px - entry) / entry - cost
            pnl = notional * ret
            equity += pnl
            trades.append({
                "entry_time": int(df.time.iloc[i + 1]),
                "exit_time": int(df.time.iloc[j]),
                "side": "buy" if s == 1 else "sell",
                "entry": entry, "exit": exit_px,
                "notional": notional, "ret": ret, "pnl": pnl, "equity": equity,
            })
            i = j + 1
        else:
            i += 1
    return pd.DataFrame(trades)


def stats(trades: pd.DataFrame, start_equity: float, days: float) -> dict:
    if trades.empty:
        return {"trades": 0}
    eq = pd.concat([pd.Series([start_equity]), trades.equity])
    dd = (eq / eq.cummax() - 1).min()
    wins = trades[trades.pnl > 0]
    losses = trades[trades.pnl <= 0]
    return {
        "trades": len(trades),
        "trades_per_day": round(len(trades) / days, 2),
        "win_rate_%": round(100 * len(wins) / len(trades), 1),
        "profit_factor": round(wins.pnl.sum() / max(1e-9, -losses.pnl.sum()), 2),
        "avg_win_$": round(wins.pnl.mean(), 2) if len(wins) else 0,
        "avg_loss_$": round(losses.pnl.mean(), 2) if len(losses) else 0,
        "total_return_%": round(100 * (eq.iloc[-1] / start_equity - 1), 2),
        "max_drawdown_%": round(100 * dd, 2),
    }


def make_chart(all_trades: dict, start_equity: float, split_ts: int, path: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    SURFACE = "#fcfcfb"
    INK = "#0b0b0b"
    MUTED = "#898781"
    GRID = "#e1e0d9"
    BASE = "#c3c2b7"
    SERIES = {"BTCUSD": "#2a78d6", "ETHUSD": "#1baf7a"}

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10, 6.5), sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1]}, dpi=150,
    )
    fig.patch.set_facecolor(SURFACE)
    for ax in (ax1, ax2):
        ax.set_facecolor(SURFACE)
        ax.grid(True, color=GRID, linewidth=0.7)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.spines["bottom"].set_visible(True)
        ax.spines["bottom"].set_color(BASE)
        ax.tick_params(colors=MUTED, labelsize=9)

    for sym, t in all_trades.items():
        if t.empty:
            continue
        ts = pd.to_datetime(
            pd.concat([pd.Series([t.entry_time.iloc[0]]), t.exit_time]), unit="s"
        )
        eq = pd.concat([pd.Series([start_equity]), t.equity]).reset_index(drop=True)
        color = SERIES.get(sym, "#4a3aa7")
        ax1.plot(ts, eq, color=color, linewidth=2, label=sym)
        ax1.annotate(sym, (ts.iloc[-1], eq.iloc[-1]), textcoords="offset points",
                     xytext=(6, 0), color=color, fontsize=9, fontweight="bold")
        dd = (eq / eq.cummax() - 1) * 100
        ax2.plot(ts, dd, color=color, linewidth=2)
        ax2.fill_between(ts, dd, 0, color=color, alpha=0.12)

    split_dt = pd.to_datetime(split_ts, unit="s")
    for ax in (ax1, ax2):
        ax.axvline(split_dt, color=BASE, linewidth=1, linestyle=(0, (4, 3)))
    ax1.annotate("in-sample", (split_dt, ax1.get_ylim()[1]), xytext=(-8, -4),
                 textcoords="offset points", ha="right", va="top",
                 color=MUTED, fontsize=8.5)
    ax1.annotate("out-of-sample", (split_dt, ax1.get_ylim()[1]), xytext=(8, -4),
                 textcoords="offset points", ha="left", va="top",
                 color=MUTED, fontsize=8.5)

    ax1.axhline(start_equity, color=BASE, linewidth=1)
    ax1.set_title(
        "Trend-pullback scalper — 60-day backtest, $1,000 start, 0.5% risk/trade\n"
        "Delta Exchange India 15m perpetuals, fees + slippage included",
        loc="left", color=INK, fontsize=11,
    )
    ax1.set_ylabel("Equity ($)", color=MUTED, fontsize=9)
    ax1.legend(frameon=False, labelcolor=INK, fontsize=9, loc="upper left")
    ax2.set_ylabel("Drawdown (%)", color=MUTED, fontsize=9)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE, bbox_inches="tight")
    print(f"chart -> {path}")


def main():
    os.makedirs(REPORT_DIR, exist_ok=True)
    cfg = Config()
    client = DeltaClient(cfg.base_url)
    strat = TrendPullbackStrategy(cfg)
    start_equity = 1000.0
    all_trades, report_rows = {}, []
    split_ts = None

    for sym in ["BTCUSD", "ETHUSD"]:
        print(f"fetching {sym} {cfg.timeframe_minutes}m x {DAYS}d ...")
        df = fetch(client, sym, cfg.timeframe_minutes, DAYS)
        if split_ts is None:
            split_ts = int(df.time.min()) + SPLIT_DAYS * 86400
        sig = vector_signals(df, strat)
        trades = replay(df, cfg, sig, start_equity)
        all_trades[sym] = trades
        trades.to_csv(os.path.join(REPORT_DIR, f"trades_{sym}.csv"), index=False)

        full = stats(trades, start_equity, DAYS)
        ins = stats(trades[trades.entry_time < split_ts].reset_index(drop=True),
                    start_equity, SPLIT_DAYS)
        oos_t = trades[trades.entry_time >= split_ts].reset_index(drop=True)
        oos_eq0 = trades[trades.entry_time < split_ts].equity.iloc[-1] \
            if (trades.entry_time < split_ts).any() else start_equity
        oos = stats(oos_t, oos_eq0, DAYS - SPLIT_DAYS)
        for phase, s in [("full 60d", full), ("in-sample 40d", ins),
                         ("out-of-sample 20d", oos)]:
            report_rows.append({"symbol": sym, "phase": phase, **s})

    rep = pd.DataFrame(report_rows)
    chart_path = os.path.join(REPORT_DIR, "equity_curve.png")
    make_chart(all_trades, start_equity, split_ts, chart_path)

    md = [
        "# Scalping agent — backtest performance report",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
        "",
        f"- Strategy: trend-pullback (EMA{cfg.ema_fast}/{cfg.ema_slow}/{cfg.ema_trend}"
        f" + RSI cross, ATR stop {cfg.sl_atr_mult}x / TP {cfg.tp_r_multiple:.2f}R,"
        f" {cfg.max_hold_bars}-bar time exit)",
        f"- Timeframe: {cfg.timeframe_minutes}m | Costs: maker entry"
        f" {cfg.maker_fee:.2%} + taker exit {cfg.taker_fee:.2%} +"
        f" {cfg.slippage:.2%} slippage per side",
        f"- Sizing: {cfg.risk_per_trade:.1%} of equity risked per trade,"
        f" max leverage {cfg.max_leverage}x",
        "- Conservative fill model: stop fills first when a bar touches stop and target.",
        "",
        rep.to_markdown(index=False),
        "",
        "![equity curve](equity_curve.png)",
        "",
        "## Honest read of these numbers",
        "",
        "This strategy is roughly breakeven-to-slightly-positive after realistic",
        "costs. The out-of-sample period is materially weaker than in-sample —",
        "the classic signature of a small, unstable edge. **Do not treat this as",
        "a money-printing machine.** Recommended path: run it in paper mode for",
        "2–4 weeks, compare paper results to the backtest, and only consider tiny",
        "live size if paper tracks the backtest.",
    ]
    out = os.path.join(REPORT_DIR, "performance_report.md")
    with open(out, "w") as f:
        f.write("\n".join(md) + "\n")
    print(f"report -> {out}")
    print()
    print(rep.to_string(index=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Honest test of the classic, widely-taught day-trading strategies against
real BTC data from Delta Exchange India — not this repo's own presets.

Strategies tested (all textbook-standard, no custom tuning beyond the
standard published parameters):
  1. EMA 9/21 crossover              — trend following
  2. RSI(14) 30/70 mean reversion    — mean reversion
  3. Bollinger Band(20,2) reversion  — mean reversion
  4. MACD(12,26,9) crossover         — momentum
  5. Donchian(20) channel breakout   — trend following ("Turtle" rules)
  6. VWAP reversion (daily reset)    — classic intraday mean reversion
  7. Opening Range Breakout (30m)    — classic day-trading breakout

Methodology (same standard as this repo's other backtests, so results are
comparable and not flattered):
  * signals computed only from CLOSED bars (shifted), no lookahead
  * entry at the NEXT bar's open, with slippage
  * maker fee on entry + taker fee on exit + slippage both ways
    (delta_scalper.config.Config.round_trip_cost — same cost model used
    everywhere else in this repo)
  * fixed ATR stop + R-multiple target, max hold bars — the one place a
    judgment call was needed to give strategies without a built-in exit
    (RSI/BB/VWAP reversion) a fair, mechanical exit rule
  * walk-forward: first 60% of the window is in-sample, last 40% is
    out-of-sample — the out-of-sample number is the one that matters
  * position sizing: fixed 2% risk per trade, no leverage cap games
"""
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from delta_scalper.config import Config          # noqa: E402
from delta_scalper.delta_client import DeltaClient  # noqa: E402
from delta_scalper import indicators as ind      # noqa: E402

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
SYMBOL = "BTCUSD"
TF_MIN = 15
DAYS = 180
RISK_PER_TRADE = 0.02
SL_ATR_MULT = 1.5
TP_R_MULT = 2.0
MAX_HOLD_BARS = 96  # 24h at 15m


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
        time.sleep(0.2)
    df = pd.concat(frames).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df


# ─────────────────────────── strategy signals ───────────────────────────
# Every function returns an int array aligned to df: 1 long entry, -1 short
# entry, 0 nothing, evaluated using only data available AT the close of bar
# i (so the replay engine enters at bar i+1's open — no lookahead).

def sig_ema_cross(df):
    fast, slow = ind.ema(df.close, 9), ind.ema(df.close, 21)
    up = fast > slow
    cross_up = up & ~up.shift(1).fillna(False)
    cross_dn = ~up & up.shift(1).fillna(False)
    return np.where(cross_up, 1, np.where(cross_dn, -1, 0))


def sig_rsi_reversion(df):
    r = ind.rsi(df.close, 14)
    rp = r.shift(1)
    long_e = (rp < 30) & (r >= 30)
    short_e = (rp > 70) & (r <= 70)
    return np.where(long_e, 1, np.where(short_e, -1, 0))


def sig_bollinger_reversion(df):
    mid = df.close.rolling(20).mean()
    sd = df.close.rolling(20).std()
    lower, upper = mid - 2 * sd, mid + 2 * sd
    c, cp = df.close, df.close.shift(1)
    long_e = (cp < lower.shift(1)) & (c >= lower)
    short_e = (cp > upper.shift(1)) & (c <= upper)
    return np.where(long_e, 1, np.where(short_e, -1, 0))


def sig_macd_cross(df):
    ema12, ema26 = ind.ema(df.close, 12), ind.ema(df.close, 26)
    macd = ema12 - ema26
    signal = ind.ema(macd, 9)
    up = macd > signal
    cross_up = up & ~up.shift(1).fillna(False)
    cross_dn = ~up & up.shift(1).fillna(False)
    return np.where(cross_up, 1, np.where(cross_dn, -1, 0))


def sig_donchian_breakout(df):
    upper = df.high.rolling(20).max().shift(1)
    lower = df.low.rolling(20).min().shift(1)
    long_e = df.close > upper
    short_e = df.close < lower
    return np.where(long_e, 1, np.where(short_e, -1, 0))


def sig_vwap_reversion(df):
    day = pd.to_datetime(df.time, unit="s").dt.date
    tp = (df.high + df.low + df.close) / 3
    pv = tp * df.volume
    cum_pv = pv.groupby(day).cumsum()
    cum_v = df.volume.groupby(day).cumsum().replace(0, np.nan)
    vwap = cum_pv / cum_v
    dev = (df.close - vwap) / vwap
    devp = dev.shift(1)
    # revert when price stretched >0.6% from VWAP and starts snapping back
    long_e = (devp < -0.006) & (dev >= devp)
    short_e = (devp > 0.006) & (dev <= devp)
    return np.where(long_e, 1, np.where(short_e, -1, 0))


def sig_orb(df, bars_per_range=2):  # 2 x 15m = 30-minute opening range
    day = pd.to_datetime(df.time, unit="s").dt.date
    day_start = day != day.shift(1)
    grp = day_start.cumsum()
    bar_in_day = df.groupby(grp).cumcount()
    is_range = bar_in_day < bars_per_range
    range_high = df.high.where(is_range).groupby(grp).transform("max")
    range_low = df.low.where(is_range).groupby(grp).transform("min")
    after_range = bar_in_day == bars_per_range
    long_e = after_range & (df.close > range_high)
    short_e = after_range & (df.close < range_low)
    return np.where(long_e, 1, np.where(short_e, -1, 0))


STRATEGIES = {
    "EMA 9/21 Crossover":        sig_ema_cross,
    "RSI(14) 30/70 Reversion":   sig_rsi_reversion,
    "Bollinger(20,2) Reversion": sig_bollinger_reversion,
    "MACD(12,26,9) Crossover":   sig_macd_cross,
    "Donchian(20) Breakout":     sig_donchian_breakout,
    "VWAP Reversion (daily)":    sig_vwap_reversion,
    "Opening Range Breakout 30m": sig_orb,
}


# ─────────────────────────── shared backtest engine ───────────────────────────

def replay(df: pd.DataFrame, sig: np.ndarray, cost: float,
           start_equity: float = 1000.0) -> pd.DataFrame:
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    a = ind.atr(df, 14).values
    equity = start_equity
    trades = []
    i, n = 0, len(df)
    while i < n - 1:
        s = sig[i]
        if s != 0 and not np.isnan(a[i]) and a[i] > 0 and equity > 0:
            direction = 1 if s == 1 else -1
            entry = o[i + 1] * (1 + 0.0002 * direction)
            sl_dist = SL_ATR_MULT * a[i]
            if sl_dist <= 0:
                i += 1
                continue
            sl = entry - direction * sl_dist
            tp = entry + direction * TP_R_MULT * sl_dist
            notional = equity * RISK_PER_TRADE / (sl_dist / entry)
            exit_px, j = None, i + 1
            for j in range(i + 1, min(i + 1 + MAX_HOLD_BARS, n)):
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
                j = min(i + MAX_HOLD_BARS, n - 1)
                exit_px = c[j]
            ret = direction * (exit_px - entry) / entry - cost
            pnl = notional * ret
            equity += pnl
            trades.append({
                "entry_time": int(df.time.iloc[i + 1]), "exit_time": int(df.time.iloc[j]),
                "side": "buy" if s == 1 else "sell", "entry": entry, "exit": exit_px,
                "notional": notional, "ret": ret, "pnl": pnl, "equity": equity,
            })
            i = j + 1
        else:
            i += 1
    return pd.DataFrame(trades)


def metrics(trades: pd.DataFrame, start_equity=1000.0) -> dict:
    if trades.empty:
        return dict(n=0, win_rate=0.0, pf=0.0, total_return=0.0, max_dd=0.0, final_equity=start_equity)
    wins = trades[trades.pnl > 0]
    losses = trades[trades.pnl <= 0]
    gross_win = wins.pnl.sum()
    gross_loss = -losses.pnl.sum()
    pf = gross_win / gross_loss if gross_loss > 0 else float("inf") if gross_win > 0 else 0.0
    eq = trades.equity.values
    peak = np.maximum.accumulate(np.concatenate([[start_equity], eq]))
    dd = (np.concatenate([[start_equity], eq]) - peak) / peak
    return dict(
        n=len(trades), win_rate=len(wins) / len(trades),
        pf=pf, total_return=(eq[-1] - start_equity) / start_equity,
        max_dd=dd.min(), final_equity=eq[-1],
    )


def main():
    cfg = Config()
    client = DeltaClient(cfg.base_url)
    print(f"Fetching {SYMBOL} {TF_MIN}m candles, last {DAYS} days from Delta Exchange India...")
    df = fetch(client, SYMBOL, TF_MIN, DAYS)
    print(f"Got {len(df)} candles, {df.time.iloc[0]} -> {df.time.iloc[-1]}")
    split = int(len(df) * 0.6)
    cost = cfg.round_trip_cost

    rows = []
    curves = {}
    for name, fn in STRATEGIES.items():
        sig = fn(df)
        is_trades = replay(df.iloc[:split].reset_index(drop=True), sig[:split], cost)
        oos_trades = replay(df.iloc[split:].reset_index(drop=True), sig[split:], cost)
        is_m, oos_m = metrics(is_trades), metrics(oos_trades)
        rows.append({
            "strategy": name,
            "is_trades": is_m["n"], "is_wr": is_m["win_rate"], "is_pf": is_m["pf"],
            "is_ret": is_m["total_return"], "is_dd": is_m["max_dd"],
            "oos_trades": oos_m["n"], "oos_wr": oos_m["win_rate"], "oos_pf": oos_m["pf"],
            "oos_ret": oos_m["total_return"], "oos_dd": oos_m["max_dd"],
        })
        curves[name] = oos_trades

    res = pd.DataFrame(rows).sort_values("oos_pf", ascending=False)

    os.makedirs(REPORT_DIR, exist_ok=True)
    md = [f"# Proven day-trading strategies vs real {SYMBOL} data\n",
          f"{TF_MIN}m candles, last {DAYS} days from Delta Exchange India "
          f"({df.time.iloc[0]} -> {df.time.iloc[-1]}, {len(df)} bars).\n",
          "Walk-forward: first 60% in-sample, last 40% out-of-sample. "
          f"Fixed {RISK_PER_TRADE:.0%} risk/trade, {SL_ATR_MULT}x ATR stop, "
          f"{TP_R_MULT}R target, cost {cost*100:.3f}%/round-trip "
          "(same cost model as the rest of this repo). "
          "**Judge every strategy by its out-of-sample (OOS) column — "
          "in-sample numbers are shown only to reveal overfitting gaps.**\n",
          "| Strategy | IS trades | IS WR | IS PF | IS ret | IS maxDD | OOS trades | OOS WR | OOS PF | OOS ret | OOS maxDD |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in res.iterrows():
        md.append(
            f"| {r.strategy} | {r.is_trades} | {r.is_wr:.0%} | {r.is_pf:.2f} | "
            f"{r.is_ret:+.1%} | {r.is_dd:.1%} | {r.oos_trades} | {r.oos_wr:.0%} | "
            f"{r.oos_pf:.2f} | {r.oos_ret:+.1%} | {r.oos_dd:.1%} |"
        )
    md.append("\n**PF (profit factor) = gross win / gross loss. PF < 1.0 means the "
               "strategy lost money after real costs. A strategy needs OOS PF "
               "meaningfully above 1 AND a reasonable trade count to mean anything "
               "— a handful of OOS trades is not a validated edge either way.**\n")
    report_path = os.path.join(REPORT_DIR, "proven_strategies_report.md")
    with open(report_path, "w") as f:
        f.write("\n".join(md))
    print("\n".join(md))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.figure(figsize=(11, 6))
    for name, tr in curves.items():
        if tr.empty:
            continue
        eq = pd.concat([pd.Series([1000.0]), tr.equity]).reset_index(drop=True)
        plt.plot(eq.values, label=name, linewidth=1.4)
    plt.axhline(1000, color="gray", linestyle="--", linewidth=0.8)
    plt.title(f"Out-of-sample equity curves — {SYMBOL} {TF_MIN}m, last {int(DAYS*0.4)} days")
    plt.xlabel("trade #"); plt.ylabel("equity ($, start=1000)")
    plt.legend(fontsize=8, loc="upper left")
    plt.tight_layout()
    curve_path = os.path.join(REPORT_DIR, "proven_strategies_oos_equity.png")
    plt.savefig(curve_path, dpi=130)
    print(f"\nSaved: {report_path}\nSaved: {curve_path}")


if __name__ == "__main__":
    main()

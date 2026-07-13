#!/usr/bin/env python3
"""Literal implementation of the triple-timeframe "Daily MACD bias -> 1H
50 EMA pullback -> 15m MSS" blueprint, exactly as specified. This is a
new strategy, not a re-test of anything already in this repo — tested
cross-asset from the start (BTC/ETH/SOL/XRP), because the last two
literal-recipe tests (Strategy A/B) both showed that heavily-conditioned
multi-timeframe setups are rare enough that single-asset BTC alone
doesn't give a trustworthy sample.

Literal rules, as given:
  Phase 1 (Daily): MACD(12,26,9) on the daily chart sets the day's bias —
    MACD line above signal = longs only that day, below = shorts only.
    Uses the most recently CLOSED daily candle (yesterday's), since a
    trader checking the daily chart intraday cannot see today's candle
    finish — no lookahead.
  Phase 2 (1H): wait for price to pull back and touch/pierce the 1H
    50 EMA, in the direction that fights the daily bias (price was above
    the EMA and drops to it, for a bullish bias; mirrored for bearish).
  Phase 3 (15m): the moment the 1H EMA is touched, look for a Market
    Structure Shift on the 15m chart — a minor opposite pivot forms, then
    a single 15m candle closes completely past it.
  Phase 4 (entry/risk):
    Step 7: Limit entry at the open of the 15m candle that caused the
      MSS. Tested with this repo's standard no-lookahead convention (fill
      at the NEXT bar's open after that candle's close is what confirms
      it as "the structural candle" — you cannot know in advance which
      candle that will be), same disclosed concession as the Strategy A/B
      literal tests.
    Step 8: stop-loss $15 below/above the absolute swing extreme of the
      pullback (the lowest low / highest high between the EMA touch and
      the MSS confirmation). Tested literally AND at a realistic 0.15%
      buffer, same reasoning as the other two literal tests (BTC's price
      scale makes a flat $15 a few basis points).
    Step 9: take-profit is a literal fixed 2R (exactly 2x the stop's
      distance from entry) — not a filter against a natural level, unlike
      Strategy B's target; this one is unambiguous.
  Safeguards: no entries between 00:00-07:00 UTC (the "dead zone"), and
    1% risk per trade (this spec states 1% explicitly, unlike the 2%
    convention used in the earlier two literal tests — kept as specified
    here for fidelity).
"""
import bisect
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from delta_scalper.config import Config             # noqa: E402
from delta_scalper.delta_client import DeltaClient  # noqa: E402
from delta_scalper.indicators import ema             # noqa: E402

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
SYMBOLS = ["BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD"]
DAYS = 365  # daily-chart bias needs a much longer window to get enough signal
RISK_PER_TRADE = 0.01  # literal: "exactly 1% of total trading equity"
CONFIRM_K = 1
MSS_WAIT_15M_BARS = 4 * 24
MAX_HOLD_BARS_15M = 4 * 48
DEAD_ZONE_UTC = (0, 7)  # [00:00, 07:00) UTC — no entries in this window
SL_BUFFERS = {"literal $15": 15.0, "realistic 0.15%": None}


def fetch(client: DeltaClient, symbol: str, resolution: str, days: int) -> pd.DataFrame:
    end = int(time.time())
    start = end - days * 86400
    res_s = {"1d": 86400, "1h": 3600, "15m": 900}[resolution]
    frames = []
    cursor = end
    while cursor > start:
        chunk_start = max(start, cursor - 2000 * res_s)
        data = client.get_candles(symbol, resolution, chunk_start, cursor)
        if not data:
            break
        frames.append(pd.DataFrame(data))
        cursor = min(c["time"] for c in data) - res_s
        time.sleep(0.2)
    df = pd.concat(frames).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df


def daily_bias_series(df1d: pd.DataFrame):
    """bias[day] = +1 bullish / -1 bearish, using that day's own CLOSED
    candle. A trade occurring on calendar day D uses bias[D-1]."""
    macd = ema(df1d.close, 12) - ema(df1d.close, 26)
    signal = ema(macd, 9)
    bias = np.where(macd > signal, 1, -1)
    day = pd.to_datetime(df1d.time, unit="s").dt.date
    return dict(zip(day, bias))


def simulate(df15, o15, h15, l15, c15, t15, touch_i, direction, sl_buffer_usd):
    n = len(df15)
    pivot_price = None
    confirm_i = None
    search_end = min(touch_i + MSS_WAIT_15M_BARS, n - 1)
    j = touch_i
    while j < search_end:
        k = CONFIRM_K
        if pivot_price is None and k <= j - touch_i and j + k < n:
            if direction == 1:
                if h15[j] == h15[j - k:j + k + 1].max():
                    pivot_price = h15[j]
            else:
                if l15[j] == l15[j - k:j + k + 1].min():
                    pivot_price = l15[j]
        elif pivot_price is not None:
            broke = (c15[j] > pivot_price) if direction == 1 else (c15[j] < pivot_price)
            if broke:
                confirm_i = j
                break
        j += 1
    if confirm_i is None:
        return None

    entry_i = confirm_i + 1
    if entry_i >= n:
        return None
    entry_hour = pd.to_datetime(int(t15[entry_i]), unit="s").hour
    if DEAD_ZONE_UTC[0] <= entry_hour < DEAD_ZONE_UTC[1]:
        return None  # dead-zone safeguard: do not execute this entry

    entry = o15[entry_i]
    pullback_extreme = (l15[touch_i:confirm_i + 1].min() if direction == 1
                        else h15[touch_i:confirm_i + 1].max())
    buffer_ = sl_buffer_usd if sl_buffer_usd is not None else 0.0015 * entry
    sl = pullback_extreme - buffer_ if direction == 1 else pullback_extreme + buffer_
    risk_dist = abs(entry - sl)
    if risk_dist <= 0:
        return None
    tp = entry + 2 * risk_dist if direction == 1 else entry - 2 * risk_dist

    exit_px, exit_j, exit_reason = None, entry_i, "timeout"
    for j in range(entry_i + 1, min(entry_i + 1 + MAX_HOLD_BARS_15M, n)):
        if direction == 1:
            if l15[j] <= sl:
                exit_px, exit_j, exit_reason = sl, j, "SL"; break
            if h15[j] >= tp:
                exit_px, exit_j, exit_reason = tp, j, "TP"; break
        else:
            if h15[j] >= sl:
                exit_px, exit_j, exit_reason = sl, j, "SL"; break
            if l15[j] <= tp:
                exit_px, exit_j, exit_reason = tp, j, "TP"; break
    if exit_px is None:
        exit_j = min(entry_i + MAX_HOLD_BARS_15M, n - 1)
        exit_px = c15[exit_j]

    return dict(entry_time=int(t15[entry_i]), exit_time=int(t15[exit_j]),
                side="buy" if direction == 1 else "sell", entry=entry, sl=sl, tp=tp,
                exit=exit_px, exit_reason=exit_reason, risk_dist=risk_dist)


def run_variant(df1d, df1h, df15, sl_buffer_usd, cost, start_equity=1000.0):
    bias_map = daily_bias_series(df1d)
    days_sorted = sorted(bias_map)

    ema50 = ema(df1h.close, 50).values
    o1, h1, l1, c1, t1 = (df1h.open.values, df1h.high.values, df1h.low.values,
                           df1h.close.values, df1h.time.values)
    day1h = pd.to_datetime(df1h.time, unit="s").dt.date.values

    o15, h15, l15, c15, t15 = (df15.open.values, df15.high.values, df15.low.values,
                                df15.close.values, df15.time.values)

    equity = start_equity
    trades = []
    next_free_time = 0
    for i in range(1, len(df1h)):
        d = day1h[i]
        idx = bisect.bisect_left(days_sorted, d)
        if idx == 0:
            continue  # no prior closed daily candle yet
        bias = bias_map[days_sorted[idx - 1]]
        if np.isnan(ema50[i]) or np.isnan(ema50[i - 1]):
            continue
        if bias == 1:
            touched = c1[i - 1] > ema50[i - 1] and l1[i] <= ema50[i]
            direction = 1
        else:
            touched = c1[i - 1] < ema50[i - 1] and h1[i] >= ema50[i]
            direction = -1
        if not touched:
            continue
        if t1[i] < next_free_time:
            continue
        start_idx = np.searchsorted(t15, t1[i])
        if start_idx >= len(df15):
            continue
        trade = simulate(df15, o15, h15, l15, c15, t15, start_idx, direction, sl_buffer_usd)
        if trade is None:
            continue
        ret = direction * (trade["exit"] - trade["entry"]) / trade["entry"] - cost
        notional = equity * RISK_PER_TRADE / (trade["risk_dist"] / trade["entry"])
        pnl = notional * ret
        equity += pnl
        trades.append({**trade, "pnl": pnl, "equity": equity})
        next_free_time = trade["exit_time"] + 1
    return pd.DataFrame(trades)


def metrics(trades: pd.DataFrame, start_equity=1000.0) -> dict:
    if trades.empty:
        return dict(n=0, win_rate=0.0, pf=0.0, total_return=0.0, max_dd=0.0)
    wins = trades[trades.pnl > 0]
    losses = trades[trades.pnl <= 0]
    gross_win = wins.pnl.sum()
    gross_loss = -losses.pnl.sum()
    pf = gross_win / gross_loss if gross_loss > 0 else float("inf") if gross_win > 0 else 0.0
    eq = trades.equity.values
    peak = np.maximum.accumulate(np.concatenate([[start_equity], eq]))
    dd = (np.concatenate([[start_equity], eq]) - peak) / peak
    return dict(n=len(trades), win_rate=len(wins) / len(trades), pf=pf,
                total_return=(eq[-1] - start_equity) / start_equity, max_dd=dd.min())


def main():
    cfg = Config()
    client = DeltaClient(cfg.base_url)
    cost = cfg.round_trip_cost

    lines = ["# Daily MACD bias -> 1H 50EMA pullback -> 15m MSS — literal recipe, cross-asset\n",
             f"Daily MACD(12,26,9) bias, 1H 50 EMA pullback zone, 15m MSS confirmation, "
             f"1% risk/trade, dead-zone filter (no entries 00:00-07:00 UTC), fixed 2R target, "
             f"last {DAYS} days, tested on {', '.join(SYMBOLS)}.\n",
             "**Disclosed conventions:** entry fills at the next 15m bar's open after the "
             "structure-shift candle closes (this repo's standard no-lookahead rule — you can't "
             "pre-place a limit at a candle's open before its close is what makes it "
             "'the' structural candle). Stop tested both literally ($15) and at a realistic "
             "0.15% buffer, same reasoning as the other two literal tests. Daily bias uses the "
             "most recently CLOSED daily candle, never the forming one.\n",
             "Walk-forward: 60% in-sample / 40% out-of-sample by time, cost "
             f"{cost*100:.3f}%/round-trip, {RISK_PER_TRADE:.0%} risk/trade (as literally "
             "specified, not this repo's usual 2%).\n",
             "| Symbol | Stop buffer | IS trades | IS WR | IS PF | IS ret | OOS trades | "
             "OOS WR | OOS PF | OOS ret | OOS maxDD |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]

    pooled_is_n = pooled_oos_n = pooled_oos_wins = 0
    for symbol in SYMBOLS:
        print(f"Fetching {symbol} daily/1h/15m candles, last {DAYS} days...")
        df1d = fetch(client, symbol, "1d", DAYS)
        df1h = fetch(client, symbol, "1h", DAYS)
        df15 = fetch(client, symbol, "15m", DAYS)
        print(f"  daily: {len(df1d)}, 1h: {len(df1h)}, 15m: {len(df15)}")
        split_ts = int(df15.time.iloc[int(len(df15) * 0.6)])

        for label, buf in SL_BUFFERS.items():
            all_trades = run_variant(df1d, df1h, df15, buf, cost)
            if all_trades.empty:
                is_trades = oos_trades = all_trades
            else:
                is_trades = all_trades[all_trades.entry_time < split_ts].reset_index(drop=True)
                oos_trades = all_trades[all_trades.entry_time >= split_ts].reset_index(drop=True)
            oos_eq0 = is_trades.equity.iloc[-1] if len(is_trades) else 1000.0
            is_m = metrics(is_trades, start_equity=1000.0)
            oos_m = metrics(oos_trades, start_equity=oos_eq0)
            pooled_is_n += is_m["n"]
            pooled_oos_n += oos_m["n"]
            pooled_oos_wins += int(round(oos_m["win_rate"] * oos_m["n"]))
            lines.append(
                f"| {symbol} | {label} | {is_m['n']} | {is_m['win_rate']:.0%} | {is_m['pf']:.2f} | "
                f"{is_m['total_return']:+.1%} | {oos_m['n']} | {oos_m['win_rate']:.0%} | "
                f"{oos_m['pf']:.2f} | {oos_m['total_return']:+.1%} | {oos_m['max_dd']:.1%} |"
            )

    pooled_oos_wr = pooled_oos_wins / pooled_oos_n if pooled_oos_n else 0.0
    lines.append(f"\n**Pooled: {pooled_is_n} in-sample trades, {pooled_oos_n} out-of-sample "
                 f"trades across all 4 assets x 2 stop variants (pooled OOS win rate "
                 f"{pooled_oos_wr:.0%}).**\n")

    report_path = os.path.join(REPORT_DIR, "daily_bias_mtf_literal_report.md")
    with open(report_path, "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    print(f"\nSaved: {report_path}")


if __name__ == "__main__":
    main()

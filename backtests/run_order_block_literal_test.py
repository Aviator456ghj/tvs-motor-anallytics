#!/usr/bin/env python3
"""Literal implementation of "Strategy B: Order Block Execution" exactly as
specified by the user's Google AI Mode research transcript — NOT the
similar-but-different delta_scalper/order_block.py module already in this
repo (that one was found/validated independently earlier and differs in
real ways: single-timeframe wick-to-wick zone + same-bar retest entry +
ride exit, vs this strategy's 1h-zone/15m-confirmation, body-only zone,
fixed-dollar stop, and fixed 1:3-minimum R:R target). This script tests
the AI Mode recipe on its own terms, the same way
run_liquidation_hunt_literal_test.py did for Strategy A.

Literal rules, as given:
  Phase 4 (identification, 1h):
    - Displacement / Market Structure Shift -> reused via this repo's own
      confirmed-swing CHoCH detector (delta_scalper.choch.find_choch_setups),
      which is the same "swing breaks with a displaced move" concept the
      spec describes, filtered by the existing ob_min_break_atr threshold.
    - Order block = the last opposite-colour candle before the break
      (same definition as order_block.py, reused as-is).
    - "Verify the CME Gap" — no historical CME futures data is available
      from Delta Exchange's public API; NOT applied, flagged as an
      untested piece of the spec (same honesty approach as Strategy A's
      unavailable funding-rate/historical-OI pieces).

  Phase 5 (execution):
    Step 1: the zone is the OB candle's BODY only (open to close) — a
      real, literal difference from order_block.py, which uses the full
      wick-to-wick range.
    Step 2: wait for price to organically return into the zone (scanned
      on 15m data for precision, from the moment the 1h break candle
      closes onward). If a candle closes completely through the zone
      before it's touched, the setup is void (order_block.py's own
      "voided" concept, reused).
    Step 3: on the 15m chart, after the zone is touched, wait for a minor
      opposite pivot (a 1-bar fractal) to form and then get broken by a
      close — this is a small-scale CHoCH on the 15m chart, confirming
      "institutional buyers/sellers are defending the block."
    Step 4: entry is a limit order, tested as TWO variants since the spec
      gives two options: (a) at the confirming 15m candle's open — this
      script fills at the NEXT bar's open after confirmation (this repo's
      standard no-lookahead convention: you cannot legally pre-place a
      limit at "the structural candle's open" before that candle's close
      is what makes it structural), and (b) at the 1h zone's 50%
      equilibrium, filled only if/when price returns to that exact level
      after confirmation (a real limit order that may simply never fill).
    Step 5: stop-loss "$10 below/above the absolute boundary of the box"
      — tested literally AND with a realistic 0.15% buffer, same
      disclosed reasoning as Strategy A (a flat $10 is a few basis points
      at current BTC prices). Take-profit = the nearest unmitigated swing
      (the pre-pullback origin, CHoCH setup's "B" level) — ONLY taken if
      that level implies at least the spec's stated minimum 1:3 R:R;
      otherwise the setup is skipped, since "aiming for a minimum 1:3"
      reads as a qualifying filter, not a suggestion.

Cost model, risk sizing (2%/trade), and walk-forward split are identical
to this repo's other backtests for direct comparability.
"""
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from delta_scalper.config import Config             # noqa: E402
from delta_scalper.delta_client import DeltaClient  # noqa: E402
from delta_scalper.choch import find_choch_setups    # noqa: E402
from delta_scalper.indicators import atr             # noqa: E402

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
SYMBOLS = ["BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD"]
DAYS = 180
RISK_PER_TRADE = 0.02
MIN_RR = 3.0
CONFIRM_K = 1          # "minor" pivot on 15m = a 1-bar fractal
TOUCH_WAIT_1H_BARS = 120   # ob_wait_bars default, reused
CONFIRM_WAIT_15M_BARS = 4 * 24  # give the 15m confirmation up to a day
EQ_FILL_WAIT_BARS = 4 * 12      # give the equilibrium limit up to 12h to fill
MAX_HOLD_BARS_15M = 4 * 96      # generous hold cap post-entry (4 days)
SL_BUFFERS = {"literal $10": 10.0, "realistic 0.15%": None}


def fetch(client: DeltaClient, symbol: str, tf_min: int, days: int) -> pd.DataFrame:
    end = int(time.time())
    start = end - days * 86400
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
        time.sleep(0.2)
    df = pd.concat(frames).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df


def find_ob_candle(o, cl, break_bar, A_bar, direction):
    for j in range(break_bar - 1, A_bar, -1):
        is_counter = (cl[j] < o[j]) if direction == 1 else (cl[j] > o[j])
        if is_counter:
            return j
    return None


def simulate_setup(df15, o15, h15, l15, c15, t15, start_idx, direction,
                    zone_lo, zone_hi, target_level, sl_buffer_usd, entry_variant):
    """Runs one literal Strategy-B setup forward on 15m bars starting at
    start_idx (first 15m bar at/after the 1h break candle's close).
    Returns a trade dict or None if the setup never triggers."""
    n = len(df15)
    mid = (zone_lo + zone_hi) / 2

    # Step 2: wait for touch, watching for a close-through invalidation first
    touch_i = None
    for i in range(start_idx, min(start_idx + TOUCH_WAIT_1H_BARS * 4, n)):
        closed_through = (c15[i] < zone_lo) if direction == 1 else (c15[i] > zone_hi)
        if closed_through:
            return None  # order block invalidated before ever being touched
        touched = (l15[i] <= zone_hi) if direction == 1 else (h15[i] >= zone_lo)
        if touched:
            touch_i = i
            break
    if touch_i is None:
        return None

    # Step 3: minor opposite pivot on 15m, then a close breaking it
    pivot_price = None
    confirm_i = None
    search_end = min(touch_i + CONFIRM_WAIT_15M_BARS, n - 1)
    j = touch_i
    while j < search_end:
        closed_through = (c15[j] < zone_lo) if direction == 1 else (c15[j] > zone_hi)
        if closed_through:
            return None  # invalidated while waiting for confirmation
        k = CONFIRM_K
        if pivot_price is None and k <= j - touch_i and j + k < n:
            if direction == 1:  # bullish OB -> look for a minor LOWER HIGH pivot
                if h15[j] == h15[j - k:j + k + 1].max():
                    pivot_price = h15[j]
            else:               # bearish OB -> minor HIGHER LOW pivot
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

    # Step 4: entry
    if entry_variant == "structural_open":
        entry_i = confirm_i + 1
        if entry_i >= n:
            return None
        entry = o15[entry_i]
    else:  # "equilibrium"
        entry_i = None
        for j in range(confirm_i + 1, min(confirm_i + 1 + EQ_FILL_WAIT_BARS, n)):
            reached = (l15[j] <= mid) if direction == 1 else (h15[j] >= mid)
            if reached:
                entry_i = j
                entry = mid
                break
        if entry_i is None:
            return None  # limit never filled

    # Step 5: risk/target
    buffer_ = sl_buffer_usd if sl_buffer_usd is not None else 0.0015 * entry
    sl = zone_lo - buffer_ if direction == 1 else zone_hi + buffer_
    risk_dist = abs(entry - sl)
    if risk_dist <= 0:
        return None
    reward_dist = abs(target_level - entry)
    if reward_dist / risk_dist < MIN_RR:
        return None  # doesn't meet the spec's stated minimum 1:3 R:R

    tp = target_level
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
                exit=exit_px, exit_reason=exit_reason, exit_idx=exit_j, risk_dist=risk_dist)


def run_variant(df1h, df15, entry_variant, sl_buffer_usd, cost, start_equity=1000.0):
    o1, h1, l1, c1, t1 = (df1h.open.values, df1h.high.values, df1h.low.values,
                           df1h.close.values, df1h.time.values)
    o15, h15, l15, c15, t15 = (df15.open.values, df15.high.values, df15.low.values,
                                df15.close.values, df15.time.values)
    a1 = atr(df1h, 14).values
    k = 4  # ob_swing_k default
    setups = sorted(find_choch_setups(df1h, k), key=lambda s: s["break_bar"])

    equity = start_equity
    trades = []
    next_free_time = 0
    for s in setups:
        d, A_bar, bb = s["dir"], s["A_bar"], s["break_bar"]
        if bb >= len(a1) or np.isnan(a1[bb]) or a1[bb] <= 0:
            continue
        if abs(c1[bb] - s["B"]) / a1[bb] < 1.0:  # ob_min_break_atr default
            continue
        ob = find_ob_candle(o1, c1, bb, A_bar, d)
        if ob is None:
            continue
        zone_lo, zone_hi = min(o1[ob], c1[ob]), max(o1[ob], c1[ob])
        break_close_time = t1[bb] + 3600
        if break_close_time < next_free_time:
            continue
        start_idx = np.searchsorted(t15, break_close_time, side="left")
        if start_idx >= len(df15):
            continue
        trade = simulate_setup(df15, o15, h15, l15, c15, t15, start_idx, d,
                                zone_lo, zone_hi, s["B"], sl_buffer_usd, entry_variant)
        if trade is None:
            continue
        ret = d * (trade["exit"] - trade["entry"]) / trade["entry"] - cost
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

    lines = ["# Strategy B (Order Block Execution) — literal AI-Mode recipe, cross-asset\n",
             f"1h structure + 15m execution, last {DAYS} days, tested on {', '.join(SYMBOLS)} — "
             "cross-asset, the same way this repo's other validated strategies are tested, "
             "because (as the single-BTC run showed) this literal recipe's setup is rare enough "
             "that one symbol alone doesn't produce a trustworthy sample size.\n",
             "**Disclosed substitutions:** \"Verify the CME Gap\" is not testable — Delta "
             "Exchange's public API has no historical CME futures data; not applied. The zone "
             "is the OB candle's BODY only (open-close), exactly as Step 1 specifies — a real "
             "difference from this repo's existing order_block.py, which uses the full wick "
             "range. Entry is tested as both options the spec gives (structural-candle-open and "
             "1h-zone 50% equilibrium); stop is tested both literally ($10) and at a realistic "
             "0.15%, same reasoning as the Strategy A test. Take-profit is the CHoCH setup's "
             "pre-pullback swing origin, but ONLY taken when it clears the spec's own stated "
             "minimum 1:3 R:R — otherwise the setup is skipped, not force-fit.\n",
             "Walk-forward: 60% in-sample / 40% out-of-sample by time, 2% risk/trade, cost "
             f"{cost*100:.3f}%/round-trip.\n",
             "| Symbol | Entry variant | Stop buffer | IS trades | IS WR | IS PF | IS ret | "
             "OOS trades | OOS WR | OOS PF | OOS ret | OOS maxDD |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]

    pooled_is_n = pooled_oos_n = 0
    pooled_oos_wins = 0
    for symbol in SYMBOLS:
        print(f"Fetching {symbol} 1h and 15m candles, last {DAYS} days...")
        df1h = fetch(client, symbol, 60, DAYS)
        df15 = fetch(client, symbol, 15, DAYS)
        print(f"  1h bars: {len(df1h)}, 15m bars: {len(df15)}")
        split_ts = int(df15.time.iloc[int(len(df15) * 0.6)])

        for entry_variant, ev_label in [("structural_open", "15m structural open"),
                                         ("equilibrium", "1h 50% equilibrium")]:
            for label, buf in SL_BUFFERS.items():
                all_trades = run_variant(df1h, df15, entry_variant, buf, cost)
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
                    f"| {symbol} | {ev_label} | {label} | {is_m['n']} | {is_m['win_rate']:.0%} | "
                    f"{is_m['pf']:.2f} | {is_m['total_return']:+.1%} | {oos_m['n']} | "
                    f"{oos_m['win_rate']:.0%} | {oos_m['pf']:.2f} | {oos_m['total_return']:+.1%} | "
                    f"{oos_m['max_dd']:.1%} |"
                )

    pooled_oos_wr = pooled_oos_wins / pooled_oos_n if pooled_oos_n else 0.0
    lines.append(f"\n**Pooled sample size across all 4 assets x 4 variants: {pooled_is_n} "
                 f"in-sample trades, {pooled_oos_n} out-of-sample trades (pooled OOS win rate "
                 f"{pooled_oos_wr:.0%}).** Even pooled across every asset and every entry/stop "
                 "variant tested, this is still a thin sample — treat every number in this "
                 "report as directional, not statistically conclusive, and weight it far below "
                 "the already-validated strategies in this repo.\n")
    lines.append("For comparison, the already-validated `delta_scalper/order_block.py` "
                  "(full wick-to-wick zone, same-bar retest entry, ATR stop, ride exit) scores "
                  "**106 trades, PF 1.28, +3,076% (at 15% risk/trade), -77.0% max DD** on the "
                  "same underlying setup family, and it earned that grade on a real sample size "
                  "— kept here as the benchmark this literal recipe is being measured against.\n")

    report_path = os.path.join(REPORT_DIR, "order_block_literal_report.md")
    with open(report_path, "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    print(f"\nSaved: {report_path}")


if __name__ == "__main__":
    main()

"""Backtest the ICT 'Power of 3' (AMD - Accumulation/Manipulation/
Distribution) session model:

  Accumulation (19:00-01:00 EST): low-volatility range forms.
  Manipulation (01:00-07:00 EST): price sweeps beyond the accumulation
      range (a false breakout / liquidity trap) and closes back inside.
  Distribution (07:00-13:00 EST): the claim is that the *real* directional
      move happens here, in the OPPOSITE direction of the manipulation
      sweep (sweep up + close back in => expect distribution down; sweep
      down + close back in => expect distribution up).

This is fully mechanical and testable: for every day, classify the
manipulation-phase behavior, predict the distribution-phase direction,
and check it against what actually happened - plus simulate an actual
trade taken at the accumulation/manipulation handoff.

Note: EST is treated as a fixed UTC-5 offset (matching the indicator's
literal "1900-0100 EST" settings, no DST adjustment), since the
indicator's own settings are stated as fixed hours.
"""
import numpy as np
import pandas as pd

from smc_backtest import INSTRUMENTS, load
from full_ict_strategy import walk_trade, summarize, print_summary, RISK_PCT_PER_TRADE, STARTING_CAPITAL

EST_OFFSET_HOURS = 5
ACC_START_H, ACC_END_H = 19, 1
MANIP_START_H, MANIP_END_H = 1, 7
DIST_START_H, DIST_END_H = 7, 13
SWEEP_BUFFER = 0.0005
TARGET_RR = 2.0


def add_est_time(df):
    df = df.copy()
    df["est_ts"] = pd.to_datetime(df["timestamp_ms"], unit="ms") - pd.Timedelta(hours=EST_OFFSET_HOURS)
    return df


def bars_in(df, start, end):
    mask = (df["est_ts"] >= start) & (df["est_ts"] < end)
    return df[mask]


def classify_manipulation(acc_high, acc_low, manip_df):
    if manip_df.empty:
        return None
    manip_high, manip_low = manip_df["high"].max(), manip_df["low"].min()
    last_close = manip_df["close"].iloc[-1]
    swept_up = manip_high > acc_high
    swept_down = manip_low < acc_low

    if swept_up and swept_down:
        return {"kind": "ambiguous"}
    if swept_up:
        if last_close < acc_high * (1 - SWEEP_BUFFER):
            return {"kind": "bearish_trap", "predicted": "bearish", "sweep_extreme": manip_high}
        return {"kind": "breakout_up", "predicted": "bullish", "sweep_extreme": acc_low}
    if swept_down:
        if last_close > acc_low * (1 + SWEEP_BUFFER):
            return {"kind": "bullish_trap", "predicted": "bullish", "sweep_extreme": manip_low}
        return {"kind": "breakout_down", "predicted": "bearish", "sweep_extreme": acc_high}
    return {"kind": "no_sweep"}


def run_instrument(instrument):
    df = add_est_time(load(instrument))
    dates = sorted(df["est_ts"].dt.date.unique())

    records = []
    for d in dates:
        d_ts = pd.Timestamp(d)
        acc = bars_in(df, d_ts - pd.Timedelta(days=1) + pd.Timedelta(hours=ACC_START_H), d_ts + pd.Timedelta(hours=ACC_END_H))
        manip = bars_in(df, d_ts + pd.Timedelta(hours=MANIP_START_H), d_ts + pd.Timedelta(hours=MANIP_END_H))
        dist = bars_in(df, d_ts + pd.Timedelta(hours=DIST_START_H), d_ts + pd.Timedelta(hours=DIST_END_H))
        if acc.empty or manip.empty or dist.empty:
            continue

        acc_high, acc_low = acc["high"].max(), acc["low"].min()
        cls = classify_manipulation(acc_high, acc_low, manip)
        if cls is None or cls["kind"] in ("ambiguous", "no_sweep"):
            continue

        dist_open, dist_close = dist["open"].iloc[0], dist["close"].iloc[-1]
        actual = "bullish" if dist_close > dist_open else "bearish"
        records.append({
            "date": d, "kind": cls["kind"], "predicted": cls["predicted"], "actual": actual,
            "hit": cls["predicted"] == actual, "sweep_extreme": cls["sweep_extreme"],
            "entry_idx": dist.index[0], "dist_end_idx": dist.index[-1],
            "acc_range_pct": (acc_high - acc_low) / acc_low,
            "dist_range_pct": (dist["high"].max() - dist["low"].min()) / dist_open,
        })

    print(f"\n=== {instrument} ({len(dates)} EST calendar days, {len(records)} classifiable AMD days) ===")
    rec_df = pd.DataFrame(records)
    if rec_df.empty:
        print("  no classifiable days")
        return

    print(f"  avg accumulation-phase range: {rec_df['acc_range_pct'].mean():.2%}  "
          f"avg distribution-phase range: {rec_df['dist_range_pct'].mean():.2%}")

    for kind in ["bearish_trap", "bullish_trap", "breakout_up", "breakout_down"]:
        sub = rec_df[rec_df["kind"] == kind]
        if sub.empty:
            continue
        n, hits = len(sub), sub["hit"].sum()
        p = hits / n
        se = (0.5 * 0.5 / n) ** 0.5
        z = (p - 0.5) / se
        print(f"  {kind}: n={n} direction_hit_rate={p:.1%} (vs 50% random, z={z:.2f})")

    trap_df = rec_df[rec_df["kind"].isin(["bearish_trap", "bullish_trap"])]
    n, hits = len(trap_df), trap_df["hit"].sum()
    if n:
        p = hits / n
        se = (0.5 * 0.5 / n) ** 0.5
        z = (p - 0.5) / se
        print(f"  ALL TRAPS combined (the core AMD reversal claim): n={n} hit_rate={p:.1%} z={z:.2f}")

    high, low, close = df["high"].values, df["low"].values, df["close"].values
    trades = []
    for _, r in trap_df.iterrows():
        direction = r["predicted"]
        entry_price = df["open"].values[r["entry_idx"]]
        if direction == "bullish":
            stop_price = r["sweep_extreme"] * (1 - SWEEP_BUFFER)
            risk = entry_price - stop_price
            if risk <= 0:
                continue
            target_price = entry_price + TARGET_RR * risk
        else:
            stop_price = r["sweep_extreme"] * (1 + SWEEP_BUFFER)
            risk = stop_price - entry_price
            if risk <= 0:
                continue
            target_price = entry_price - TARGET_RR * risk
        horizon = r["dist_end_idx"] - r["entry_idx"]
        r_mult, outcome = walk_trade(df, r["entry_idx"], entry_price, stop_price, target_price, direction, horizon)
        trades.append({"r": r_mult, "outcome": outcome})

    s = summarize(trades, f"AMD trap reversal trade ({TARGET_RR}R, stop=open exit at dist end)")
    print_summary(s)


if __name__ == "__main__":
    for inst in INSTRUMENTS:
        run_instrument(inst)

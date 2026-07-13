#!/usr/bin/env python3
"""Literal implementation of "Strategy A: The Liquidation Hunt" exactly as
specified by the user's Google AI Mode research transcript — NOT the
similar-but-different delta_scalper/liquidity_fakeout.py module (that one
was found independently earlier and differs in real ways: same-bar entry
vs this strategy's 2-bar confirmation, ATR stop vs this strategy's fixed
buffer, single R-multiple target vs this strategy's 50%/100%-of-range
partial exits). This script tests the AI Mode recipe on its own terms.

Literal rules, as given:
  Phase 1 (identification):
    - Liquidity pool = yesterday's high and yesterday's low (PDH/PDL) —
      Phase 2 Step 1 says this explicitly ("mark the exact dollar level
      of yesterday's high and yesterday's low")
    - "Watch Open Interest... a true liquidation hunt shows OI crash as
      price pierces the level" — Delta Exchange only exposes CURRENT open
      interest, not a historical per-candle OI series, so this cannot be
      backtested literally. Substituted with the spec's own fallback
      confirmation signal, volume: "a massive volume spike" (Phase 2
      Step 2). This substitution is disclosed, not hidden.
    - Funding-rate directional bias (positive funding -> look for
      downside hunt) has the same problem: no historical funding-rate
      time series per candle is available from Delta's public candle
      API. Not applied here — flagged as an untested piece of the spec.

  Phase 2 (execution), applied on the 15m chart:
    Step 2: a 15m candle's wick pierces PDH or PDL, with that candle's
      volume >= 2x its 20-bar average (the volume-spike proxy above).
    Step 3: entry triggers "the exact moment a 15-minute candle closes
      back inside the previous range" — i.e. the NEXT 15m candle after
      the sweep candle must close back inside PDH/PDL. Entry is at the
      following bar's open (this script's one no-lookahead concession:
      the spec says entry "the moment" the confirming candle closes,
      which in live trading is buyable at that close; the backtest enters
      at the next open instead, which is at least as conservative).
      Direction: swept the high -> short (fade); swept the low -> long.
    Step 4: stop-loss "5 to 10 USD past the absolute peak of the wick".
      At BTC's current price (tens of thousands of dollars), $5-10 is a
      few basis points — tighter than normal 15m noise, so this is
      tested literally AND with a more realistic 0.15% buffer, with both
      reported so the literal number's practicality is not obscured.
      Take profit: 50% of the position at the midpoint of yesterday's
      range, the other 50% at the opposite extreme of the range.

Cost model, risk sizing, and walk-forward split are identical to this
repo's other backtests (delta_scalper.config.Config, 2% risk/trade,
60/40 in-sample/out-of-sample) for direct comparability.
"""
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from delta_scalper.config import Config             # noqa: E402
from delta_scalper.delta_client import DeltaClient  # noqa: E402

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
SYMBOL = "BTCUSD"
TF_MIN = 15
DAYS = 180
RISK_PER_TRADE = 0.02
VOL_SPIKE_MULT = 2.0
VOL_AVG_WINDOW = 20
MAX_HOLD_BARS = 96  # 24h at 15m, same cap used elsewhere in this repo
SL_BUFFERS = {"literal $5-10": 7.5, "realistic 0.15%": None}  # None = pct-based


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


def add_pdh_pdl(df: pd.DataFrame) -> pd.DataFrame:
    """Previous-day high/low, mapped onto every 15m bar of the following day."""
    day = pd.to_datetime(df.time, unit="s").dt.date
    daily_high = df.groupby(day).high.max()
    daily_low = df.groupby(day).low.min()
    prev_high = daily_high.shift(1)
    prev_low = daily_low.shift(1)
    df = df.copy()
    df["pdh"] = day.map(prev_high).values
    df["pdl"] = day.map(prev_low).values
    return df


def build_signals(df: pd.DataFrame):
    """Returns (sweep_dir, confirm_ok) arrays: sweep_dir[i] = +1 means bar
    i swept the HIGH (candidate short-fade), -1 means swept the LOW
    (candidate long-fade), 0 = no sweep. confirm_ok[i+1] True means bar
    i+1 closed back inside the range -> entry fires at bar i+2's open."""
    vol_avg = df.volume.rolling(VOL_AVG_WINDOW).mean()
    vol_spike = df.volume >= VOL_SPIKE_MULT * vol_avg
    swept_high = (df.high > df.pdh) & vol_spike & df.pdh.notna()
    swept_low = (df.low < df.pdl) & vol_spike & df.pdl.notna()
    sweep_dir = np.where(swept_high, 1, np.where(swept_low, -1, 0))

    n = len(df)
    entries = np.zeros(n, dtype=int)  # +1 long entry at this bar's open, -1 short
    entry_ctx = {}  # bar index -> (pdh, pdl) range used, for TP/SL calc
    for i in range(n - 2):
        if sweep_dir[i] == 1:  # swept high -> want short if next candle closes back under pdh
            if df.close.iloc[i + 1] < df.pdh.iloc[i]:
                entries[i + 2] = -1
                entry_ctx[i + 2] = (df.pdh.iloc[i], df.pdl.iloc[i], df.high.iloc[i])
        elif sweep_dir[i] == -1:  # swept low -> want long if next candle closes back over pdl
            if df.close.iloc[i + 1] > df.pdl.iloc[i]:
                entries[i + 2] = 1
                entry_ctx[i + 2] = (df.pdh.iloc[i], df.pdl.iloc[i], df.low.iloc[i])
    return entries, entry_ctx


def replay(df: pd.DataFrame, entries: np.ndarray, entry_ctx: dict, cost: float,
           sl_buffer_usd, start_equity: float = 1000.0) -> pd.DataFrame:
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    equity = start_equity
    trades = []
    i, n = 0, len(df)
    while i < n - 1:
        e = entries[i]
        if e != 0 and i in entry_ctx and equity > 0:
            pdh, pdl, wick_extreme = entry_ctx[i]
            direction = e
            entry = o[i]
            rng = pdh - pdl
            if rng <= 0:
                i += 1
                continue
            buffer_ = sl_buffer_usd if sl_buffer_usd is not None else 0.0015 * entry
            sl = wick_extreme + buffer_ if direction == -1 else wick_extreme - buffer_
            mid = (pdh + pdl) / 2
            tp1 = mid
            tp2 = pdl if direction == -1 else pdh
            sl_dist = abs(entry - sl)
            if sl_dist <= 0:
                i += 1
                continue
            notional = equity * RISK_PER_TRADE / (sl_dist / entry)
            remaining = notional
            tp1_done = False
            realized = 0.0
            exit_j, exit_reason = i, "timeout"
            for j in range(i + 1, min(i + 1 + MAX_HOLD_BARS, n)):
                if direction == 1:
                    hit_sl = l[j] <= sl
                    hit_tp1 = (not tp1_done) and h[j] >= tp1
                    hit_tp2 = tp1_done and h[j] >= tp2
                else:
                    hit_sl = h[j] >= sl
                    hit_tp1 = (not tp1_done) and l[j] <= tp1
                    hit_tp2 = tp1_done and l[j] <= tp2

                if not tp1_done:
                    if hit_sl:
                        ret = direction * (sl - entry) / entry - cost
                        realized += remaining * ret
                        remaining = 0.0
                        exit_j, exit_reason = j, "SL"
                        break
                    if hit_tp1:
                        half = remaining / 2
                        ret = direction * (tp1 - entry) / entry - cost
                        realized += half * ret
                        remaining -= half
                        tp1_done = True
                else:
                    if hit_sl:
                        ret = direction * (sl - entry) / entry - cost
                        realized += remaining * ret
                        remaining = 0.0
                        exit_j, exit_reason = j, "SL after TP1"
                        break
                    if hit_tp2:
                        ret = direction * (tp2 - entry) / entry - cost
                        realized += remaining * ret
                        remaining = 0.0
                        exit_j, exit_reason = j, "TP2"
                        break
            if remaining > 0:
                j = min(i + MAX_HOLD_BARS, n - 1)
                ret = direction * (c[j] - entry) / entry - cost
                realized += remaining * ret
                exit_j = j
            equity += realized
            trades.append({
                "entry_time": int(df.time.iloc[i]), "exit_time": int(df.time.iloc[exit_j]),
                "side": "buy" if direction == 1 else "sell", "entry": entry,
                "pnl": realized, "exit_reason": exit_reason, "equity": equity,
            })
            i = exit_j + 1
        else:
            i += 1
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
    print(f"Fetching {SYMBOL} {TF_MIN}m candles, last {DAYS} days...")
    df = fetch(client, SYMBOL, TF_MIN, DAYS)
    df = add_pdh_pdl(df)
    print(f"Got {len(df)} candles, {df.time.iloc[0]} -> {df.time.iloc[-1]}")
    entries, entry_ctx = build_signals(df)
    n_sweeps = int((entries != 0).sum())
    print(f"Signals found: {n_sweeps} confirmed sweep-and-close-back entries "
          f"over {DAYS} days")

    split_ts = int(df.time.iloc[int(len(df) * 0.6)])
    cost = cfg.round_trip_cost

    lines = [f"# Strategy A (Liquidation Hunt) — literal AI-Mode recipe vs real {SYMBOL} data\n",
             f"{TF_MIN}m execution bars, PDH/PDL from the prior UTC day, last {DAYS} days "
             f"({df.time.iloc[0]} -> {df.time.iloc[-1]}, {len(df)} bars).\n",
             "**Disclosed substitution:** the spec's \"OI crash confirmation\" needs a historical "
             "open-interest series Delta Exchange's public API doesn't expose; replaced with the "
             f"spec's own volume-spike confirmation ({VOL_SPIKE_MULT}x the {VOL_AVG_WINDOW}-bar "
             "average, exactly as written in Phase 2 Step 2). Funding-rate directional bias is "
             "also unavailable historically and was not applied — flagged as an untested piece of "
             "the spec, not silently dropped.\n",
             f"Total confirmed entries (sweep + volume spike + close-back-inside) over {DAYS} days: "
             f"**{n_sweeps}**.\n",
             "Walk-forward: 60% in-sample, 40% out-of-sample, 2% risk/trade, cost "
             f"{cost*100:.3f}%/round-trip. TP1/TP2 = 50%/100% of yesterday's range, exactly as "
             "specified. Two stop-buffer variants tested since the literal \"$5-10\" figure is a "
             "few basis points at current BTC prices (below normal 15m noise):\n",
             "| Stop buffer | IS trades | IS WR | IS PF | IS ret | IS maxDD | "
             "OOS trades | OOS WR | OOS PF | OOS ret | OOS maxDD |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]

    for label, buf in SL_BUFFERS.items():
        all_trades = replay(df, entries, entry_ctx, cost, buf)
        is_trades = all_trades[all_trades.entry_time < split_ts].reset_index(drop=True)
        oos_trades = all_trades[all_trades.entry_time >= split_ts].reset_index(drop=True)
        oos_eq0 = is_trades.equity.iloc[-1] if len(is_trades) else 1000.0
        is_m = metrics(is_trades, start_equity=1000.0)
        oos_m = metrics(oos_trades, start_equity=oos_eq0)
        lines.append(
            f"| {label} | {is_m['n']} | {is_m['win_rate']:.0%} | {is_m['pf']:.2f} | "
            f"{is_m['total_return']:+.1%} | {is_m['max_dd']:.1%} | {oos_m['n']} | "
            f"{oos_m['win_rate']:.0%} | {oos_m['pf']:.2f} | {oos_m['total_return']:+.1%} | "
            f"{oos_m['max_dd']:.1%} |"
        )

    lines.append("\nFor comparison, the already-validated `delta_scalper/liquidity_fakeout.py` "
                  "(same-bar entry, ATR stop, single R-multiple target, 1h timeframe) scores "
                  "BTCUSD OOS PF **1.42** — kept here as the benchmark this literal recipe is "
                  "being measured against, not just against breakeven.\n")

    report_path = os.path.join(REPORT_DIR, "liquidation_hunt_literal_report.md")
    with open(report_path, "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    print(f"\nSaved: {report_path}")


if __name__ == "__main__":
    main()

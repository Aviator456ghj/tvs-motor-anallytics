"""
Mechanical backtest proxy for the NYS Markets "REM" liquidity-sweep + Fair
Value Gap strategy (Asian/London/NY AMD model, 1% risk, Tue/Wed/Thu only).

Simplifications vs. the real (taught) strategy:
- The real strategy drills the same body>50%/sweep pattern fractally across
  4H -> 15m -> 5m -> 3m before executing. Free historical intraday data only
  gives us one finer timeframe below the 4H (1h for FX/Gold, 30m for BTC),
  so the multi-timeframe drill-down is collapsed into a single entry
  timeframe.
- Stop buffer is approximated as a flat 0.08% of the sweep extreme for all
  instruments, rather than his instrument-specific 4-5 pips (FX) / $1 (Gold).
- "Take only the single best R:R trade per day across pairs" is not modeled;
  each instrument is backtested independently, so combined trade counts will
  run higher than his real one-trade-a-day practice.
"""
import sys
import numpy as np
import pandas as pd


def load_csv(path):
    df = pd.read_csv(path)
    df["ts"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
    df = df.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    return df[["ts", "open", "high", "low", "close", "volume"]]


def resample_ohlc(df, rule="4h"):
    d = df.set_index("ts")
    out = pd.DataFrame({
        "open": d["open"].resample(rule).first(),
        "high": d["high"].resample(rule).max(),
        "low": d["low"].resample(rule).min(),
        "close": d["close"].resample(rule).last(),
        "volume": d["volume"].resample(rule).sum(),
    }).dropna().reset_index()
    return out


def body_ratio(o, h, l, c):
    rng = h - l
    if rng <= 0:
        return 0.0
    return abs(c - o) / rng


def is_london_session(ts_utc, start_h=7, end_h=11):
    return start_h <= ts_utc.hour < end_h


def is_valid_trading_day(ts_utc):
    # Tue=1, Wed=2, Thu=3 (Mon=0 ... Sun=6) -- he explicitly skips Mon/Fri
    return ts_utc.dayofweek in (1, 2, 3)


def run_backtest(df4h, df_entry, rr_target=2.0, stop_buffer_pct=0.0008,
                  use_session_filter=True, use_day_filter=True,
                  max_fvg_scan=10, max_retest_scan=30, body_thresh=0.5):
    trades = []
    n4 = len(df4h)
    i = 0
    while i < n4 - 2:
        c1 = df4h.iloc[i]
        if body_ratio(c1.open, c1.high, c1.low, c1.close) < body_thresh:
            i += 1
            continue
        c2 = df4h.iloc[i + 1]
        body_inside = (max(c2.open, c2.close) <= c1.high) and (min(c2.open, c2.close) >= c1.low)
        swept_low = c2.low < c1.low
        swept_high = c2.high > c1.high
        if not body_inside or not (swept_low ^ swept_high):
            i += 1
            continue

        bias_long = swept_low
        sweep_extreme = c2.low if bias_long else c2.high
        ts_pattern = c2.ts

        if use_day_filter and not is_valid_trading_day(ts_pattern):
            i += 1
            continue
        if use_session_filter and not is_london_session(ts_pattern):
            i += 1
            continue

        entry_start_idx = df_entry["ts"].searchsorted(c2.ts, side="right")

        fvg = None
        for k in range(entry_start_idx + 2, min(entry_start_idx + 2 + max_fvg_scan, len(df_entry))):
            a = df_entry.iloc[k - 2]
            b = df_entry.iloc[k]
            if bias_long and b.low > a.high:
                fvg = (a.high, b.low, k)
                break
            if not bias_long and b.high < a.low:
                fvg = (b.high, a.low, k)
                break
        if fvg is None:
            i += 1
            continue
        gap_lo, gap_hi, fvg_idx = fvg

        entry_trade = None
        for m in range(fvg_idx + 1, min(fvg_idx + 1 + max_retest_scan, len(df_entry) - 1)):
            rm = df_entry.iloc[m]
            touched = (rm.low <= gap_hi) and (rm.high >= gap_lo)
            if touched:
                confirm = df_entry.iloc[m + 1]
                if bias_long and confirm.close > rm.close:
                    entry_trade = (m + 1, confirm.close)
                    break
                if not bias_long and confirm.close < rm.close:
                    entry_trade = (m + 1, confirm.close)
                    break
        if entry_trade is None:
            i += 1
            continue
        entry_idx, entry_price = entry_trade

        if bias_long:
            stop = sweep_extreme * (1 - stop_buffer_pct)
            risk = entry_price - stop
        else:
            stop = sweep_extreme * (1 + stop_buffer_pct)
            risk = stop - entry_price
        if risk <= 0:
            i += 1
            continue
        target = entry_price + rr_target * risk if bias_long else entry_price - rr_target * risk

        trades.append(_manage_trade(df_entry, entry_idx, entry_price, stop, target, risk, bias_long))
        i += 1
    return trades


def _manage_trade(df, entry_idx, entry, stop, target, risk, bias_long):
    n = len(df)
    for k in range(entry_idx + 1, n):
        rk = df.iloc[k]
        if bias_long:
            stopped = rk.low <= stop
            hit_target = rk.high >= target
        else:
            stopped = rk.high >= stop
            hit_target = rk.low <= target
        if stopped:
            return dict(entry_idx=entry_idx, exit_idx=k, entry=entry, exit=stop,
                        r_multiple=-1.0, outcome="stop", bars_held=k - entry_idx)
        if hit_target:
            r_mult = (target - entry) / risk if bias_long else (entry - target) / risk
            return dict(entry_idx=entry_idx, exit_idx=k, entry=entry, exit=target,
                        r_multiple=r_mult, outcome="target", bars_held=k - entry_idx)
    last = df.iloc[-1]
    r_mult = (last.close - entry) / risk if bias_long else (entry - last.close) / risk
    return dict(entry_idx=entry_idx, exit_idx=n - 1, entry=entry, exit=last.close,
                r_multiple=r_mult, outcome="end_of_data", bars_held=n - 1 - entry_idx)


def summarize(trades, years, label=""):
    if not trades:
        print(f"{label}: No trades generated.")
        return
    rs = np.array([t["r_multiple"] for t in trades])
    wins = rs > 0
    print(f"--- {label} ---")
    print(f"Trades: {len(trades)}  ({len(trades)/years:.1f}/year)")
    print(f"Win rate: {wins.mean()*100:.1f}%")
    print(f"Avg R: {rs.mean():.2f}   Total R: {rs.sum():.2f}")
    outcomes = pd.Series([t["outcome"] for t in trades]).value_counts()
    print("Outcomes:", outcomes.to_dict())
    equity = np.cumsum(rs)
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    print(f"Max drawdown: {dd.min():.2f}R")
    print()


if __name__ == "__main__":
    path_entry = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else path_entry
    use_filters = (len(sys.argv) <= 3) or (sys.argv[3] != "nofilters")

    df_entry = load_csv(path_entry)
    df4h = resample_ohlc(df_entry, "4h")
    years = (df_entry["ts"].iloc[-1] - df_entry["ts"].iloc[0]).days / 365.25

    trades = run_backtest(df4h, df_entry, use_session_filter=use_filters, use_day_filter=use_filters)
    summarize(trades, years, f"{label} (filters {'ON' if use_filters else 'OFF'})")

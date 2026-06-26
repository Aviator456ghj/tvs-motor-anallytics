"""
Mechanical backtest proxy for the TG Capital "Trident FVG + Doji" long-only
trend-continuation strategy (London kill zone, EMA stack, FVG, doji confirmation).

This is a rule-based approximation of a strategy that the original trader
describes as ~80% mechanical / ~20% discretionary. Discretionary trade
management (exact trailing, "feel" for when to cut) is approximated with
fixed rules below and will not match his real results.
"""
import sys
import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
IST = ZoneInfo("Asia/Kolkata")


def load_csv(path):
    df = pd.read_csv(path)
    df["ts"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
    df = df.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    return df[["ts", "open", "high", "low", "close", "volume"]]


def add_emas(df, periods=(5, 9, 13, 21, 200)):
    for p in periods:
        df[f"ema{p}"] = df["close"].ewm(span=p, adjust=False).mean()
    return df


def daily_bias_series(df_30m, df_daily, ema_period=200):
    """Map each 30m bar to the *previous completed day's* close-vs-EMA200 bias (no lookahead)."""
    d = df_daily.copy()
    d["ema200"] = d["close"].ewm(span=ema_period, adjust=False).mean()
    d["bias_long"] = d["close"] > d["ema200"]
    d["date"] = d["ts"].dt.date
    bias_map = d.set_index("date")["bias_long"].shift(1)  # use prior day's verdict
    df_30m = df_30m.copy()
    df_30m["date"] = df_30m["ts"].dt.date
    df_30m["bias_long"] = df_30m["date"].map(bias_map).fillna(False)
    return df_30m


def in_kill_zone(ts_utc, start_h=3, start_m=0, end_h=6, end_m=30, tz=NY):
    t = ts_utc.tz_convert(tz)
    minutes = t.hour * 60 + t.minute
    return (start_h * 60 + start_m) <= minutes < (end_h * 60 + end_m)


def in_nse_open_session(ts_utc, start_h=9, start_m=15, end_h=10, end_m=30):
    """NSE has no London-style overlap session; use the opening-range window
    (9:15-10:30 IST), the highest-volume/most-directional part of the NSE day,
    as the structural analogue to the London kill zone."""
    return in_kill_zone(ts_utc, start_h, start_m, end_h, end_m, tz=IST)


def is_doji(o, h, l, c, body_ratio=0.25):
    rng = h - l
    if rng <= 0:
        return False
    body = abs(c - o)
    return body <= body_ratio * rng


def ema_stack_bullish(row, tol=0.0):
    return row["ema5"] > row["ema9"] > row["ema13"] > row["ema21"]


def add_swing_structure(df, fractal_window=2):
    """Fractal swing-high detection + bullish BOS flag, computed without
    lookahead: a swing high at bar p is only "known" once fractal_window
    bars have printed after it, matching when a real-time chart would
    actually confirm the fractal. bos_up marks the first bar whose close
    breaks above the most recently confirmed swing high -- the structural
    break visible as BOS/ChoCh labels in the trader's chart markup."""
    df = df.copy()
    h = df["high"].values
    c = df["close"].values
    n = len(df)

    is_swing_high = np.zeros(n, dtype=bool)
    for k in range(fractal_window, n - fractal_window):
        seg = h[k - fractal_window:k + fractal_window + 1]
        if h[k] == seg.max() and (seg == h[k]).sum() == 1:
            is_swing_high[k] = True

    last_level = np.full(n, np.nan)
    confirmed_level = np.nan
    for k in range(n):
        p = k - fractal_window
        if p >= 0 and is_swing_high[p]:
            confirmed_level = h[p]
        last_level[k] = confirmed_level

    bos_up = np.zeros(n, dtype=bool)
    for k in range(1, n):
        lvl, prev_lvl = last_level[k], last_level[k - 1]
        broke_now = not np.isnan(lvl) and c[k] > lvl
        broke_before = not np.isnan(prev_lvl) and c[k - 1] > prev_lvl
        if broke_now and not broke_before:
            bos_up[k] = True

    df["last_swing_high"] = last_level
    df["bos_up"] = bos_up
    return df


def recent_bos(df, end_idx, lookback=6):
    """True if a fresh bullish BOS occurred in the lookback bars up to and
    including end_idx (inclusive)."""
    start = max(0, end_idx - lookback + 1)
    return bool(df["bos_up"].iloc[start:end_idx + 1].any())


def run_backtest(df, use_kill_zone=True, use_close_stop=True, max_scan_bars=20,
                  rr_cap=20.0, min_rr=20.0, stop_buffer=0.0005, kill_zone_fn=in_kill_zone,
                  zone_frac=0.5, legacy_midline=False, require_bos=False, bos_lookback=6):
    """
    df: 30m OHLC with emas + bias_long + ts (UTC), already cleaned & indexed 0..n-1.
    Returns list of trade dicts.
    """
    n = len(df)
    trades = []
    in_position = False
    i = 2
    while i < n - 1:
        if in_position:
            i += 1
            continue

        row_i = df.iloc[i]
        c_im2 = df.iloc[i - 2]

        bullish_fvg = row_i["low"] > c_im2["high"]
        if not bullish_fvg:
            i += 1
            continue

        if use_kill_zone and not kill_zone_fn(row_i["ts"]):
            i += 1
            continue

        if not row_i["bias_long"] or not ema_stack_bullish(row_i):
            i += 1
            continue

        if require_bos and not recent_bos(df, i, bos_lookback):
            i += 1
            continue

        gap_lo, gap_hi = c_im2["high"], row_i["low"]
        mid = (gap_lo + gap_hi) / 2.0
        # the FVG's lower zone_frac (default lower half, i.e. the "discount" zone
        # below consequent encroachment) -- a band, not a single 50% line, per
        # the trader's chart markup (a drawn rectangle, not a level)
        zone_hi = gap_lo + zone_frac * (gap_hi - gap_lo)
        zone_lo = gap_lo

        # scan forward for the doji that wicks into the zone
        found = False
        for j in range(i + 1, min(i + 1 + max_scan_bars, n - 1)):
            rj = df.iloc[j]
            if not (rj["bias_long"] and ema_stack_bullish(rj)):
                continue
            if legacy_midline:
                # original logic: require an exact wick-touch of the 50% line
                wicks_zone = rj["low"] <= mid <= rj["high"]
            else:
                # current logic: doji wicks anywhere into the lower-half zone band
                wicks_zone = (rj["low"] <= zone_hi) and (rj["high"] >= zone_lo)
            if wicks_zone and is_doji(rj["open"], rj["high"], rj["low"], rj["close"]):
                confirm = df.iloc[j + 1]
                if confirm["close"] < rj["high"]:
                    entry = confirm["close"]
                    stop = rj["low"] * (1 - stop_buffer)
                    risk = entry - stop
                    if risk > 0:
                        trades.append(_manage_trade(df, j + 1, entry, stop, risk,
                                                      use_close_stop, rr_cap, min_rr))
                        in_position = True
                        i = trades[-1]["exit_idx"]
                    found = True
                    break
                else:
                    # invalidated per his rule; keep scanning later bars for a fresh doji
                    continue
        i += 1
        if in_position:
            in_position = False  # release lock; loop continues after exit_idx
    return trades


def _manage_trade(df, entry_idx, entry, stop, risk, use_close_stop, rr_cap, min_rr):
    n = len(df)
    target = entry + rr_cap * risk
    for k in range(entry_idx + 1, n):
        rk = df.iloc[k]
        # stop check
        if use_close_stop:
            stopped = rk["close"] < stop
        else:
            stopped = rk["low"] <= stop
        if stopped:
            exit_price = stop if not use_close_stop else rk["close"]
            r_mult = (exit_price - entry) / risk
            return dict(entry_idx=entry_idx, exit_idx=k, entry_ts=df.iloc[entry_idx]["ts"],
                        exit_ts=rk["ts"], entry=entry, exit=exit_price, stop=stop,
                        r_multiple=r_mult, outcome="stop", bars_held=k - entry_idx)
        # target check
        if rk["high"] >= target:
            r_mult = rr_cap
            return dict(entry_idx=entry_idx, exit_idx=k, entry_ts=df.iloc[entry_idx]["ts"],
                        exit_ts=rk["ts"], entry=entry, exit=target, stop=stop,
                        r_multiple=r_mult, outcome="target", bars_held=k - entry_idx)
        # trend-break exit: EMA5 closes back below EMA21 -> trail out at close
        if rk["ema5"] < rk["ema21"] and k > entry_idx + 1:
            r_mult = (rk["close"] - entry) / risk
            return dict(entry_idx=entry_idx, exit_idx=k, entry_ts=df.iloc[entry_idx]["ts"],
                        exit_ts=rk["ts"], entry=entry, exit=rk["close"], stop=stop,
                        r_multiple=r_mult, outcome="trend_break", bars_held=k - entry_idx)
    last = df.iloc[-1]
    r_mult = (last["close"] - entry) / risk
    return dict(entry_idx=entry_idx, exit_idx=n - 1, entry_ts=df.iloc[entry_idx]["ts"],
                exit_ts=last["ts"], entry=entry, exit=last["close"], stop=stop,
                r_multiple=r_mult, outcome="end_of_data", bars_held=n - 1 - entry_idx)


def summarize(trades, years):
    if not trades:
        print("No trades generated.")
        return
    rs = np.array([t["r_multiple"] for t in trades])
    wins = rs > 0
    print(f"Trades: {len(trades)}  ({len(trades)/years:.1f}/year)")
    print(f"Win rate: {wins.mean()*100:.1f}%")
    print(f"Avg R (all trades): {rs.mean():.2f}")
    print(f"Median R: {np.median(rs):.2f}")
    print(f"Total R (sum): {rs.sum():.2f}")
    print(f"Best trade: {rs.max():.2f}R   Worst trade: {rs.min():.2f}R")
    outcomes = pd.Series([t["outcome"] for t in trades]).value_counts()
    print("Outcome breakdown:")
    print(outcomes.to_string())
    # equity curve in R, and max drawdown in R
    equity = np.cumsum(rs)
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    print(f"Max drawdown: {dd.min():.2f}R")


if __name__ == "__main__":
    path_30m = sys.argv[1]
    path_daily = sys.argv[2]
    use_kz = (len(sys.argv) <= 3) or (sys.argv[3] != "nokillzone")

    df30 = load_csv(path_30m)
    dfd = load_csv(path_daily)
    df30 = add_emas(df30, periods=(5, 9, 13, 21))
    df30 = daily_bias_series(df30, dfd)
    df30 = add_swing_structure(df30)

    print(f"Bars: {len(df30)}  range: {df30['ts'].iloc[0]} -> {df30['ts'].iloc[-1]}")
    years = (df30["ts"].iloc[-1] - df30["ts"].iloc[0]).days / 365.25

    print(f"\n=== Kill zone filter: {use_kz}, BOS filter: off ===")
    trades = run_backtest(df30, use_kill_zone=use_kz)
    summarize(trades, years)

    print(f"\n=== Kill zone filter: {use_kz}, BOS filter: on ===")
    trades_bos = run_backtest(df30, use_kill_zone=use_kz, require_bos=True)
    summarize(trades_bos, years)

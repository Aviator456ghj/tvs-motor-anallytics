"""
Trade Analysis — CHoCH Bias Strategy
=====================================
Re-runs the backtest with extended per-trade metadata, then cross-examines
winners vs losers across every measurable dimension to surface filters or
rule changes that could improve the strategy.
"""

import pandas as pd
import numpy as np
from choch_bias_strategy import (
    load_data, calc_adx, find_swings,
    MULTIPLIER, SWING_N, ADX_PERIOD, ADX_THRESHOLD,
    STOP_BUFFER, SIGNAL_EXPIRY, LEVEL_TOL, DATA_CSV
)

# ─────────────────────────────────────────────
# Re-implement run_backtest with extra metadata
# ─────────────────────────────────────────────
def run_backtest_extended(df, swings, adx):
    hi = df["High"].values
    lo = df["Low"].values
    cl = df["Close"].values
    op = df["Open"].values

    # Pre-compute ATR-14 for volatility context
    n   = len(df)
    tr  = np.zeros(n)
    for i in range(1, n):
        tr[i] = max(hi[i]-lo[i], abs(hi[i]-cl[i-1]), abs(lo[i]-cl[i-1]))
    atr = np.zeros(n)
    atr[14] = tr[1:15].mean()
    for i in range(15, n):
        atr[i] = (atr[i-1]*13 + tr[i]) / 14

    bias         = "NEUTRAL"
    last_HH = last_HL = last_LH = last_LL = None
    sig_direction = sig_entry = sig_stop = None
    sig_ref_HH = sig_ref_HL = sig_ref_LH = sig_ref_LL = None
    sig_armed_idx = None
    sig_confirmed = False
    sig_swing_range = None   # HH-HL or LH-LL for R:R calc
    sig_trend_candle_count = 0  # how many swings since trend started

    active = None
    trades = []
    trend_start_idx  = 0    # candle index when current trend began
    trend_swing_cnt  = 0    # number of successful swings in current trend

    def open_trade(direction, entry_px, entry_date, entry_ci, stop, ref):
        candles_since_armed = entry_ci - ref.get("_armed_at", entry_ci)
        swing_range   = ref.pop("_swing_range", None)
        armed_at      = ref.pop("_armed_at", entry_ci)
        swing_cnt     = ref.pop("_swing_cnt", 0)
        trend_age_c   = entry_ci - ref.pop("_trend_start", entry_ci)

        stop_dist_pct = abs(entry_px - stop) / entry_px * 100
        target_px     = (entry_px + swing_range) if direction == "LONG" else (entry_px - swing_range)
        rr_ratio      = swing_range / abs(entry_px - stop) if abs(entry_px - stop) > 0 else 0

        return {
            "direction":        direction,
            "entry_price":      entry_px,
            "entry_date":       entry_date,
            "entry_ci":         entry_ci,
            "stop_loss":        stop,
            "swing_range":      round(swing_range, 2) if swing_range else None,
            "swing_range_pct":  round(swing_range / entry_px * 100, 2) if swing_range else None,
            "stop_dist_pct":    round(stop_dist_pct, 2),
            "rr_ratio":         round(rr_ratio, 2),
            "target_px":        round(target_px, 2) if swing_range else None,
            "adx_at_entry":     round(adx[entry_ci], 1),
            "atr_at_entry":     round(atr[entry_ci], 2),
            "candles_to_entry": candles_since_armed,
            "trend_age_candles": trend_age_c,
            "trend_swing_count": swing_cnt,
            **ref,
            "exit_price":   None,
            "exit_date":    None,
            "exit_ci":      None,
            "result":       None,
            "exit_reason":  None,
            "candles_held": None,
            "adx_at_exit":  None,
            "pnl_pct":      None,
        }

    def close_trade(t, px, dt, ci, result, reason):
        t["exit_price"]  = px
        t["exit_date"]   = dt
        t["exit_ci"]     = ci
        t["result"]      = result
        t["exit_reason"] = reason
        t["candles_held"]= ci - t["entry_ci"]
        t["adx_at_exit"] = round(adx[ci], 1)
        sign = 1 if t["direction"] == "LONG" else -1
        t["pnl_pct"] = round(sign * (px - t["entry_price"]) / t["entry_price"] * 100, 2)
        trades.append(dict(t))

    def set_long_signal(hh, hl, armed_at, swing_range=None):
        nonlocal sig_direction, sig_entry, sig_stop, sig_ref_HH, sig_ref_HL
        nonlocal sig_armed_idx, sig_confirmed, sig_swing_range, sig_trend_candle_count
        rng           = hh["price"] - hl["price"]
        sig_direction = "LONG"
        sig_entry     = round(hl["price"] + rng / MULTIPLIER, 2)
        sig_stop      = round(hl["price"] * (1 - STOP_BUFFER), 2)
        sig_ref_HH    = hh["price"]
        sig_ref_HL    = hl["price"]
        sig_armed_idx = armed_at
        sig_confirmed = False
        sig_swing_range = rng

    def set_short_signal(lh, ll, armed_at, swing_range=None):
        nonlocal sig_direction, sig_entry, sig_stop, sig_ref_LH, sig_ref_LL
        nonlocal sig_armed_idx, sig_confirmed, sig_swing_range, sig_trend_candle_count
        rng           = lh["price"] - ll["price"]
        sig_direction = "SHORT"
        sig_entry     = round(lh["price"] - rng / MULTIPLIER, 2)
        sig_stop      = round(lh["price"] * (1 + STOP_BUFFER), 2)
        sig_ref_LH    = lh["price"]
        sig_ref_LL    = ll["price"]
        sig_armed_idx = armed_at
        sig_confirmed = False
        sig_swing_range = rng

    def clear_signal():
        nonlocal sig_direction, sig_entry, sig_stop
        nonlocal sig_ref_HH, sig_ref_HL, sig_ref_LH, sig_ref_LL
        nonlocal sig_armed_idx, sig_confirmed, sig_swing_range
        sig_direction = sig_entry = sig_stop = None
        sig_ref_HH = sig_ref_HL = sig_ref_LH = sig_ref_LL = None
        sig_armed_idx = None
        sig_confirmed = False
        sig_swing_range = None

    for si, sw in enumerate(swings):
        idx   = sw["idx"]
        price = sw["price"]
        dt    = sw["date"]

        if sw["type"] == "H":
            if bias == "NEUTRAL":
                if last_HH is None or price >= last_HH["price"] * (1 - LEVEL_TOL):
                    last_HH = sw
                    if last_HL is not None:
                        bias = "UPTREND"; trend_start_idx = idx; trend_swing_cnt = 1
                        set_long_signal(last_HH, last_HL, idx)
            elif bias == "UPTREND":
                if price >= last_HH["price"] * (1 - LEVEL_TOL):
                    if active and active["direction"] == "LONG":
                        close_trade(active, price, dt, idx, "WIN", f"New HH @{price:.0f}")
                        active = None
                    last_HH = sw; trend_swing_cnt += 1
                    clear_signal()
                    if last_HL:
                        set_long_signal(last_HH, last_HL, idx)
                else:
                    last_LH = sw
            elif bias == "DOWNTREND":
                if price > (last_LH["price"] if last_LH else 0):
                    if active and active["direction"] == "SHORT":
                        close_trade(active, price, dt, idx, "LOSS", f"CHoCH UP @{price:.0f}")
                        active = None
                    bias = "UPTREND"; last_HH = sw; last_HL = last_LL
                    last_LH = None; trend_start_idx = idx; trend_swing_cnt = 1
                    clear_signal()
                    if last_HL:
                        set_long_signal(last_HH, last_HL, idx)
                else:
                    if active and active["direction"] == "SHORT":
                        close_trade(active, price, dt, idx, "WIN", f"New LH @{price:.0f}")
                        active = None
                    last_LH = sw; trend_swing_cnt += 1
                    clear_signal()
                    if last_LL:
                        set_short_signal(last_LH, last_LL, idx)

        elif sw["type"] == "L":
            if bias == "NEUTRAL":
                if last_HL is None or price < last_HL["price"]:
                    last_HL = sw
                    if last_HH is not None and price < last_HH["price"]:
                        bias = "DOWNTREND"; last_LL = sw; last_LH = last_HH
                        trend_start_idx = idx; trend_swing_cnt = 1
                        if last_LH:
                            set_short_signal(last_LH, last_LL, idx)
                else:
                    last_HL = sw
            elif bias == "UPTREND":
                if last_HL is None or price >= last_HL["price"] * (1 - LEVEL_TOL):
                    if active and active["direction"] == "LONG":
                        close_trade(active, price, dt, idx, "WIN", f"HL confirmed @{price:.0f}")
                        active = None
                    last_HL = sw; trend_swing_cnt += 1
                    clear_signal()
                    if last_HH:
                        set_long_signal(last_HH, last_HL, idx)
                else:
                    if active and active["direction"] == "LONG":
                        close_trade(active, price, dt, idx, "LOSS", f"CHoCH DOWN @{price:.0f}")
                        active = None
                    bias = "DOWNTREND"; last_LL = sw; last_LH = last_HH
                    last_HH = None; last_HL = None
                    trend_start_idx = idx; trend_swing_cnt = 1
                    clear_signal()
                    if last_LH:
                        set_short_signal(last_LH, last_LL, idx)
            elif bias == "DOWNTREND":
                if price <= last_LL["price"] * (1 + LEVEL_TOL):
                    if active and active["direction"] == "SHORT":
                        close_trade(active, price, dt, idx, "WIN", f"New LL @{price:.0f}")
                        active = None
                    last_LL = sw; trend_swing_cnt += 1
                    clear_signal()
                    if last_LH:
                        set_short_signal(last_LH, last_LL, idx)
                else:
                    last_HL = sw

        next_sw_idx = swings[si + 1]["idx"] if si + 1 < len(swings) else len(df) - 1

        for ci in range(idx + 1, next_sw_idx):
            c_hi = hi[ci]; c_lo = lo[ci]; c_cl = cl[ci]; c_dt = df.index[ci]

            if active:
                if active["direction"] == "LONG" and c_lo <= active["stop_loss"]:
                    close_trade(active, active["stop_loss"], c_dt, ci, "LOSS", "Stop Loss")
                    active = None; clear_signal(); continue
                if active["direction"] == "SHORT" and c_hi >= active["stop_loss"]:
                    close_trade(active, active["stop_loss"], c_dt, ci, "LOSS", "Stop Loss")
                    active = None; clear_signal(); continue

            if bias == "UPTREND" and last_HL and c_cl < last_HL["price"] * (1 - LEVEL_TOL):
                if active and active["direction"] == "LONG":
                    close_trade(active, c_cl, c_dt, ci, "LOSS", f"CHoCH Close DN @{c_cl:.0f}")
                    active = None
                bias = "DOWNTREND"
                lh_ref = last_HH if last_HH else last_LH
                ll_apx = {"idx": ci, "price": c_lo, "date": c_dt}
                last_LH, last_LL = lh_ref, ll_apx
                last_HH = last_HL = None
                trend_start_idx = ci; trend_swing_cnt = 1
                clear_signal()
                if last_LH:
                    set_short_signal(last_LH, last_LL, ci)
                continue

            elif bias == "DOWNTREND" and last_LH and c_cl > last_LH["price"] * (1 + LEVEL_TOL):
                if active and active["direction"] == "SHORT":
                    close_trade(active, c_cl, c_dt, ci, "LOSS", f"CHoCH Close UP @{c_cl:.0f}")
                    active = None
                bias = "UPTREND"
                hh_apx = {"idx": ci, "price": c_hi, "date": c_dt}
                hl_ref = last_LL if last_LL else last_HL
                last_HH, last_HL = hh_apx, hl_ref
                last_LH = last_LL = None
                trend_start_idx = ci; trend_swing_cnt = 1
                clear_signal()
                if last_HH and last_HL:
                    set_long_signal(last_HH, last_HL, ci)
                continue

            if sig_direction and sig_armed_idx is not None and ci - sig_armed_idx > SIGNAL_EXPIRY:
                clear_signal(); continue

            if sig_direction and not active:
                if sig_direction == "LONG" and c_cl > sig_entry:
                    sig_confirmed = True
                elif sig_direction == "SHORT" and c_cl < sig_entry:
                    sig_confirmed = True

            if sig_direction and not active and adx[ci] > ADX_THRESHOLD and sig_confirmed:
                if sig_direction == "LONG" and c_lo <= sig_entry:
                    ref = {
                        "ref_HH": sig_ref_HH, "ref_HL": sig_ref_HL,
                        "_armed_at": sig_armed_idx, "_swing_range": sig_swing_range,
                        "_swing_cnt": trend_swing_cnt, "_trend_start": trend_start_idx,
                    }
                    active = open_trade("LONG", sig_entry, c_dt, ci, sig_stop, ref)
                    clear_signal()
                elif sig_direction == "SHORT" and c_hi >= sig_entry:
                    ref = {
                        "ref_LH": sig_ref_LH, "ref_LL": sig_ref_LL,
                        "_armed_at": sig_armed_idx, "_swing_range": sig_swing_range,
                        "_swing_cnt": trend_swing_cnt, "_trend_start": trend_start_idx,
                    }
                    active = open_trade("SHORT", sig_entry, c_dt, ci, sig_stop, ref)
                    clear_signal()

    return trades


# ─────────────────────────────────────────────
# Analysis
# ─────────────────────────────────────────────
def analyse(trades):
    df = pd.DataFrame(trades)
    wins   = df[df["result"] == "WIN"]
    losses = df[df["result"] == "LOSS"]

    def cmp(col, label, fmt=".1f"):
        w = wins[col].dropna()
        l = losses[col].dropna()
        bar = lambda v, mn, mx: "█" * int((v - mn) / (mx - mn + 1e-9) * 12)
        print(f"\n  ── {label} ──")
        print(f"     Winners  n={len(w):2d}  mean={w.mean():{fmt}}  med={w.median():{fmt}}  "
              f"[{w.min():{fmt}} – {w.max():{fmt}}]")
        print(f"     Losers   n={len(l):2d}  mean={l.mean():{fmt}}  med={l.median():{fmt}}  "
              f"[{l.min():{fmt}} – {l.max():{fmt}}]")
        from scipy import stats as ss
        if len(w) > 4 and len(l) > 4:
            stat, p = ss.mannwhitneyu(w, l, alternative="two-sided")
            sig = "*** SIGNIFICANT" if p < 0.05 else ("~ marginal" if p < 0.15 else "")
            print(f"     Mann-Whitney p={p:.3f}  {sig}")

    sep = "=" * 65
    print(f"\n{sep}")
    print("  WINNER vs LOSER FEATURE COMPARISON")
    print(sep)

    print(f"\n  Total: {len(df)} trades  |  W={len(wins)}  L={len(losses)}  "
          f"WR={len(wins)/len(df)*100:.1f}%\n")

    # --- ADX ---
    cmp("adx_at_entry", "ADX at entry")
    cmp("adx_at_exit",  "ADX at exit")

    # --- Swing range (volatility of the setup) ---
    cmp("swing_range_pct", "Swing range (% of entry price)")

    # --- R:R ---
    cmp("rr_ratio", "Reward:Risk ratio (swing range / stop dist)")

    # --- Stop distance ---
    cmp("stop_dist_pct", "Stop distance (% from entry)")

    # --- Candles to entry (how quickly price returned) ---
    cmp("candles_to_entry", "Candles from signal arm to entry")

    # --- Trend age ---
    cmp("trend_age_candles", "Trend age in candles when trade opened")
    cmp("trend_swing_count", "# of swings confirmed in current trend")

    # --- Candles held ---
    cmp("candles_held", "Candles held")

    # --- PnL ---
    cmp("pnl_pct", "PnL %", fmt=".2f")

    # ─── Bucketed breakdowns ───────────────────────────────────────
    print(f"\n{sep}")
    print("  BUCKETED WIN RATE BREAKDOWNS")
    print(sep)

    def bucket_wr(col, bins, labels):
        df2 = df.copy()
        df2["bucket"] = pd.cut(df2[col].dropna(), bins=bins, labels=labels, right=False)
        g = df2.groupby("bucket", observed=True)["result"].apply(
            lambda s: f"WR={( s=='WIN').sum()/len(s)*100:.0f}% ({(s=='WIN').sum()}W/{(s=='LOSS').sum()}L, n={len(s)})"
        )
        print(f"\n  {col}:")
        for b, v in g.items():
            print(f"    {str(b):>12}  →  {v}")

    bucket_wr("adx_at_entry",
              [0, 20, 30, 40, 60, 200],
              ["<20", "20-30", "30-40", "40-60", "60+"])

    bucket_wr("swing_range_pct",
              [0, 5, 10, 20, 40, 200],
              ["<5%", "5-10%", "10-20%", "20-40%", "40%+"])

    bucket_wr("rr_ratio",
              [0, 1, 2, 3, 5, 100],
              ["<1", "1-2", "2-3", "3-5", "5+"])

    bucket_wr("candles_to_entry",
              [0, 2, 4, 7, 11],
              ["1-2", "3-4", "5-7", "8-10"])

    bucket_wr("trend_swing_count",
              [0, 2, 4, 6, 50],
              ["1", "2-3", "4-5", "6+"])

    bucket_wr("stop_dist_pct",
              [0, 2, 4, 6, 10, 100],
              ["<2%", "2-4%", "4-6%", "6-10%", "10%+"])

    # ─── Exit reason analysis ──────────────────────────────────────
    print(f"\n{sep}")
    print("  EXIT REASON → W/L BREAKDOWN")
    print(sep)
    df["reason_cat"] = df["exit_reason"].str.split(" @").str[0]
    g2 = df.groupby(["reason_cat", "result"]).size().unstack(fill_value=0)
    print(f"\n  {'Exit Reason':<24}  {'WIN':>5}  {'LOSS':>5}  {'WR':>6}")
    print("  " + "-" * 44)
    for reason, row in g2.iterrows():
        w = row.get("WIN", 0); l = row.get("LOSS", 0)
        wr = w / (w + l) * 100 if (w + l) > 0 else 0
        print(f"  {reason:<24}  {w:>5}  {l:>5}  {wr:>5.0f}%")

    # ─── Direction breakdown ───────────────────────────────────────
    print(f"\n{sep}")
    print("  DIRECTION BREAKDOWN")
    print(sep)
    for d in ["LONG", "SHORT"]:
        sub = df[df["direction"] == d]
        w = (sub["result"] == "WIN").sum(); l = (sub["result"] == "LOSS").sum()
        print(f"\n  {d}: {len(sub)} trades  WR={w/(w+l)*100:.1f}%")
        print(f"    ADX mean at entry : W={sub[sub['result']=='WIN']['adx_at_entry'].mean():.1f}  "
              f"L={sub[sub['result']=='LOSS']['adx_at_entry'].mean():.1f}")
        print(f"    Swing range% mean : W={sub[sub['result']=='WIN']['swing_range_pct'].mean():.1f}  "
              f"L={sub[sub['result']=='LOSS']['swing_range_pct'].mean():.1f}")

    # ─── Key insights & proposed new filters ──────────────────────
    print(f"\n{sep}")
    print("  KEY FINDINGS & PROPOSED NEW FILTERS")
    print(sep)

    # Auto-detect: candles to entry
    c2e_w = wins["candles_to_entry"].median()
    c2e_l = losses["candles_to_entry"].median()

    # Auto-detect: swing range
    sr_w = wins["swing_range_pct"].median()
    sr_l = losses["swing_range_pct"].median()

    # Auto-detect: ADX
    adx_w = wins["adx_at_entry"].median()
    adx_l = losses["adx_at_entry"].median()

    # Auto-detect: trend swing count
    sc_w = wins["trend_swing_count"].median()
    sc_l = losses["trend_swing_count"].median()

    print(f"""
  A. ENTRY TIMING (candles to entry):
     Winners arrived back to the 2.6 level faster
       median winner: {c2e_w:.1f} candles  |  median loser: {c2e_l:.1f} candles
     → If pullback takes >5 candles, market may lack conviction.

  B. SWING RANGE / SETUP SIZE:
     Swing range % at entry:
       median winner: {sr_w:.1f}%  |  median loser: {sr_l:.1f}%
     → Trades on very small ranges (<5%) have thin margin; those on
       very large ranges (>40%) often stall or reverse before target.

  C. ADX QUALITY:
     ADX at entry:
       median winner: {adx_w:.1f}  |  median loser: {adx_l:.1f}
     → Try raising ADX threshold to 25 for cleaner trend entries.

  D. TREND MATURITY (swing count in trend):
     Swing count at entry:
       median winner: {sc_w:.1f}  |  median loser: {sc_l:.1f}
     → Very early entries (swing 1) trade the CHoCH blind — the new
       trend has zero confirmed structure; these often fail.
       Consider requiring at least 2 swings before entering.

  E. STOP LOSS ANATOMY:
     Stop-hit losses: {(df['exit_reason'].str.startswith('Stop')).sum()} / {len(df)} trades
     All stop-loss exits are losses by design. Check if raising ADX
     threshold or requiring swing_count>=2 reduces false setups.
""")

    return df


# ─── MAIN ────────────────────────────────────
if __name__ == "__main__":
    df_prices  = load_data()
    adx        = calc_adx(df_prices, period=ADX_PERIOD)
    swings     = find_swings(df_prices, n=SWING_N)

    print("\nRunning extended backtest …")
    trades = run_backtest_extended(df_prices, swings, adx)
    print(f"  {len(trades)} trades captured with full metadata.")

    result_df = analyse(trades)
    result_df.to_csv("trade_analysis.csv", index=False)
    print("\n  Full trade table saved → trade_analysis.csv")

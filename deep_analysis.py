"""
Deep candle-level analysis on 77 trades — find all confirmations separating
winners from losers in the 64.9% WR run.

Examines:
  - Entry candle direction & wick ratio
  - Confirmation candle body quality
  - MA context (price above/below 20/50/200 EMA)
  - RSI at entry
  - Price momentum (% change over prior 5 candles)
  - Entry bounce strength (how firmly price rejected entry level)
  - Volume spike vs average
  - Candle body vs range (is it a decisive candle?)
"""

import pandas as pd
import numpy as np
from scipy import stats as ss

# ── Load price data and trade CSV ─────────────────────────────
df_p = pd.read_csv("btc_daily.csv", parse_dates=["Date"], index_col="Date")
df_t = pd.read_csv("trade_analysis.csv", parse_dates=["entry_date", "exit_date"])
df_t = df_t.sort_values("entry_date").reset_index(drop=True)

hi = df_p["High"].values
lo = df_p["Low"].values
cl = df_p["Close"].values
op = df_p["Open"].values
vol= df_p["Volume"].values if "Volume" in df_p.columns else np.ones(len(df_p))
n  = len(df_p)

# ── Compute indicators on full price series ────────────────────
def ema(arr, period):
    out = np.zeros(n)
    k   = 2 / (period + 1)
    out[period - 1] = arr[:period].mean()
    for i in range(period, n):
        out[i] = arr[i] * k + out[i-1] * (1 - k)
    return out

ema20  = ema(cl, 20)
ema50  = ema(cl, 50)
ema200 = ema(cl, 200)

def rsi(arr, period=14):
    out  = np.zeros(n)
    gain = np.zeros(n)
    loss = np.zeros(n)
    for i in range(1, n):
        d = arr[i] - arr[i-1]
        gain[i] = d if d > 0 else 0
        loss[i] = -d if d < 0 else 0
    ag = gain[1:period+1].mean()
    al = loss[1:period+1].mean()
    out[period] = 100 - 100 / (1 + ag / al) if al > 0 else 100
    for i in range(period + 1, n):
        ag = (ag * (period-1) + gain[i]) / period
        al = (al * (period-1) + loss[i]) / period
        out[i] = 100 - 100 / (1 + ag / al) if al > 0 else 100
    return out

rsi14 = rsi(cl, 14)

# avg volume (20-bar)
vol20 = np.zeros(n)
for i in range(20, n):
    vol20[i] = vol[i-20:i].mean()

# ── Feature extraction per trade ───────────────────────────────
features = []

for _, t in df_t.iterrows():
    ci  = int(t["entry_ci"])   # entry candle index
    res = t["result"]
    dirn= t["direction"]
    entry_px = t["entry_price"]
    stop_px  = t["stop_loss"]

    if ci < 5 or ci >= n:
        continue

    # --- Entry candle ---
    ec_open  = op[ci];  ec_close = cl[ci]
    ec_high  = hi[ci];  ec_low   = lo[ci]
    ec_range = ec_high - ec_low if ec_high != ec_low else 1e-9
    ec_body  = abs(ec_close - ec_open)
    ec_body_pct  = ec_body / ec_range * 100   # body as % of candle range
    ec_bullish   = ec_close > ec_open         # True if green candle
    # upper and lower wick sizes
    ec_upper_wick = ec_high - max(ec_open, ec_close)
    ec_lower_wick = min(ec_open, ec_close) - ec_low
    ec_wick_ratio = (ec_upper_wick + ec_lower_wick) / ec_range * 100  # % of range that is wick

    # For LONG: did price close ABOVE entry on entry candle? (immediate rejection bounce)
    # For SHORT: did price close BELOW entry on entry candle?
    if dirn == "LONG":
        immediate_rejection = ec_close > entry_px   # closed back above entry
        wick_through = ec_low <= entry_px            # wicked down to entry
    else:
        immediate_rejection = ec_close < entry_px
        wick_through = ec_high >= entry_px

    # --- Confirmation candle (the candle that set sig_confirmed) ---
    # It must have been 1-4 candles before entry (since expiry=4)
    # Find it by scanning back max 4 candles
    conf_ci = None
    for back in range(1, 5):
        ci_back = ci - back
        if ci_back < 0:
            break
        c_cl = cl[ci_back]; c_op = op[ci_back]
        if dirn == "LONG" and c_cl > entry_px:
            conf_ci = ci_back; break
        elif dirn == "SHORT" and c_cl < entry_px:
            conf_ci = ci_back; break

    if conf_ci is not None:
        conf_body_pct  = abs(cl[conf_ci] - op[conf_ci]) / (hi[conf_ci] - lo[conf_ci] + 1e-9) * 100
        conf_bullish   = cl[conf_ci] > op[conf_ci]
        conf_distance_from_entry = abs(cl[conf_ci] - entry_px) / entry_px * 100
        # how far close is beyond entry (bigger = stronger confirmation)
        conf_strength  = (cl[conf_ci] - entry_px) / entry_px * 100 if dirn == "LONG" \
                    else (entry_px - cl[conf_ci]) / entry_px * 100
    else:
        conf_body_pct = conf_bullish = conf_distance_from_entry = conf_strength = np.nan

    # --- MA context ---
    above_ema20  = cl[ci] > ema20[ci]
    above_ema50  = cl[ci] > ema50[ci]
    above_ema200 = cl[ci] > ema200[ci]
    # MA alignment (all three stacked bullishly)
    ma_aligned_bull = ema20[ci] > ema50[ci] > ema200[ci]
    ma_aligned_bear = ema20[ci] < ema50[ci] < ema200[ci]
    # Entry aligned with MA direction
    if dirn == "LONG":
        ma_aligned_with_trade = ma_aligned_bull
        above_key_ma = above_ema50[0] if isinstance(above_ema50, np.ndarray) else above_ema50
    else:
        ma_aligned_with_trade = ma_aligned_bear

    # --- RSI at entry ---
    rsi_val = rsi14[ci]
    if dirn == "LONG":
        rsi_extreme = rsi_val < 40   # oversold for long
        rsi_momentum= rsi_val > 50   # RSI above mid = bullish momentum
    else:
        rsi_extreme = rsi_val > 60   # overbought for short
        rsi_momentum= rsi_val < 50

    # --- Price momentum (5-candle return before entry) ---
    momentum_5c = (cl[ci] - cl[ci-5]) / cl[ci-5] * 100
    if dirn == "LONG":
        momentum_with_trade = momentum_5c > 0
        momentum_against_trade = momentum_5c < -5   # strong move against us
    else:
        momentum_with_trade = momentum_5c < 0
        momentum_against_trade = momentum_5c > 5

    # --- Volume context ---
    vol_ratio = vol[ci] / vol20[ci] if vol20[ci] > 0 else 1.0
    high_volume = vol_ratio > 1.5

    # --- EMA distance (how far is entry from EMA50) ---
    ema50_dist_pct = (entry_px - ema50[ci]) / ema50[ci] * 100

    # --- Candle-to-entry bounce (did next candle after entry close favorably?) ---
    if ci + 1 < n:
        next_cl  = cl[ci+1]
        next_dir = (next_cl > entry_px) if dirn == "LONG" else (next_cl < entry_px)
    else:
        next_dir = np.nan

    features.append({
        "result":           res,
        "direction":        dirn,
        "pnl_pct":          t["pnl_pct"],
        "adx_at_entry":     t["adx_at_entry"],
        "candles_to_entry": t["candles_to_entry"],
        # Entry candle
        "ec_body_pct":          ec_body_pct,
        "ec_bullish":           ec_bullish,
        "ec_wick_ratio":        ec_wick_ratio,
        "immediate_rejection":  immediate_rejection,
        "wick_through":         wick_through,
        # Confirmation candle
        "conf_body_pct":        conf_body_pct,
        "conf_bullish":         conf_bullish,
        "conf_strength":        conf_strength,
        "conf_distance":        conf_distance_from_entry,
        # MA context
        "above_ema20":      above_ema20,
        "above_ema50":      above_ema50,
        "above_ema200":     above_ema200,
        "ma_aligned_bull":  ma_aligned_bull,
        "ma_aligned_bear":  ma_aligned_bear,
        "ma_aligned_trade": ma_aligned_with_trade,
        # RSI
        "rsi":              rsi_val,
        "rsi_extreme":      rsi_extreme,
        "rsi_momentum":     rsi_momentum,
        # Momentum
        "momentum_5c":      momentum_5c,
        "momentum_with":    momentum_with_trade,
        "momentum_against": momentum_against_trade,
        # Volume
        "vol_ratio":        vol_ratio,
        "high_volume":      high_volume,
        # Follow-through
        "next_candle_ok":   next_dir,
        # EMA distance
        "ema50_dist_pct":   ema50_dist_pct,
    })

df_f = pd.DataFrame(features)
wins   = df_f[df_f["result"] == "WIN"]
losses = df_f[df_f["result"] == "LOSS"]

SEP = "=" * 65

def bool_wr(col, label):
    """Win rate split by a boolean feature."""
    t = df_f[df_f[col].notna()]
    grp = t.groupby(col)["result"].apply(
        lambda s: f"WR={( s=='WIN').sum()/len(s)*100:.0f}%  ({(s=='WIN').sum()}W/{(s=='LOSS').sum()}L, n={len(s)})"
    )
    print(f"\n  {label}:")
    for k, v in grp.items():
        lbl = "YES" if k else "NO "
        print(f"    {lbl}  →  {v}")
    # significance
    yes = t[t[col] == True]["result"] == "WIN"
    no  = t[t[col] == False]["result"] == "WIN"
    if len(yes) > 2 and len(no) > 2:
        _, p = ss.fisher_exact([[yes.sum(), (~yes).sum()], [no.sum(), (~no).sum()]])
        sig = "*** SIGNIFICANT" if p < 0.05 else ("~ marginal" if p < 0.10 else "")
        print(f"    Fisher p={p:.3f}  {sig}")

def num_cmp(col, label, fmt=".1f"):
    """Compare numeric feature between winners and losers."""
    w = wins[col].dropna(); l = losses[col].dropna()
    if len(w) < 2 or len(l) < 2:
        return
    _, p = ss.mannwhitneyu(w, l, alternative="two-sided")
    sig = "*** SIGNIFICANT" if p < 0.05 else ("~ marginal" if p < 0.10 else "")
    print(f"\n  {label}:")
    print(f"    WIN  n={len(w):2d}  mean={w.mean():{fmt}}  med={w.median():{fmt}}")
    print(f"    LOSS n={len(l):2d}  mean={l.mean():{fmt}}  med={l.median():{fmt}}")
    print(f"    Mann-Whitney p={p:.3f}  {sig}")

print(f"\n{SEP}")
print("  DEEP CANDLE + CONTEXT ANALYSIS  (77 trades, 64.9% WR)")
print(SEP)
print(f"  Winners: {len(wins)}  |  Losers: {len(losses)}")

# ──────────────────────────────────────────────────────────────
print(f"\n{'─'*65}")
print("  A. ENTRY CANDLE QUALITY")
print(f"{'─'*65}")

bool_wr("ec_bullish",          "Entry candle is GREEN (bullish close)")
bool_wr("immediate_rejection", "Price closed back beyond entry on entry candle")
bool_wr("wick_through",        "Entry reached via wick (wicked to level, didn't close there)")
num_cmp("ec_body_pct",         "Entry candle body % of range")
num_cmp("ec_wick_ratio",       "Entry candle wick % of range (less = better body)")

# ──────────────────────────────────────────────────────────────
print(f"\n{'─'*65}")
print("  B. CONFIRMATION CANDLE QUALITY")
print(f"{'─'*65}")

bool_wr("conf_bullish", "Confirmation candle is bullish")
num_cmp("conf_body_pct",  "Confirmation candle body %")
num_cmp("conf_strength",  "How far conf close went beyond entry level (%)")
num_cmp("conf_distance",  "Conf close distance from entry (%)")

# ──────────────────────────────────────────────────────────────
print(f"\n{'─'*65}")
print("  C. MA CONTEXT")
print(f"{'─'*65}")

bool_wr("above_ema20",      "Price above EMA-20 at entry")
bool_wr("above_ema50",      "Price above EMA-50 at entry")
bool_wr("above_ema200",     "Price above EMA-200 at entry")
bool_wr("ma_aligned_trade", "All 3 EMAs aligned with trade direction")

# ──────────────────────────────────────────────────────────────
print(f"\n{'─'*65}")
print("  D. RSI AT ENTRY")
print(f"{'─'*65}")

num_cmp("rsi", "RSI-14 at entry")
bool_wr("rsi_extreme",  "RSI extreme (oversold LONG / overbought SHORT)")
bool_wr("rsi_momentum", "RSI momentum agrees with trade direction (>50 LONG / <50 SHORT)")

# ──────────────────────────────────────────────────────────────
print(f"\n{'─'*65}")
print("  E. PRICE MOMENTUM (5-candle)")
print(f"{'─'*65}")

num_cmp("momentum_5c",     "5-candle momentum % before entry")
bool_wr("momentum_with",   "5c momentum agrees with trade direction")
bool_wr("momentum_against","5c momentum strongly against trade (sharp counter-move)")

# ──────────────────────────────────────────────────────────────
print(f"\n{'─'*65}")
print("  F. VOLUME")
print(f"{'─'*65}")

num_cmp("vol_ratio", "Volume vs 20-bar avg at entry candle")
bool_wr("high_volume","Entry candle volume > 1.5× avg")

# ──────────────────────────────────────────────────────────────
print(f"\n{'─'*65}")
print("  G. EMA-50 DISTANCE")
print(f"{'─'*65}")

num_cmp("ema50_dist_pct", "% distance of entry from EMA-50 (signed, LONG +ve)")

# ──────────────────────────────────────────────────────────────
print(f"\n{'─'*65}")
print("  H. NEXT-CANDLE FOLLOW-THROUGH")
print(f"{'─'*65}")

bool_wr("next_candle_ok", "Candle after entry closes in trade direction")

# ──────────────────────────────────────────────────────────────
# Bucketed WR by RSI
print(f"\n{SEP}")
print("  RSI BUCKETS → WIN RATE")
print(SEP)
df_f["rsi_bucket"] = pd.cut(df_f["rsi"], bins=[0,30,40,50,60,70,100],
                             labels=["<30","30-40","40-50","50-60","60-70","70+"])
g = df_f.groupby("rsi_bucket", observed=True)["result"].apply(
    lambda s: f"WR={(s=='WIN').sum()/len(s)*100:.0f}%  ({(s=='WIN').sum()}W/{(s=='LOSS').sum()}L, n={len(s)})"
)
for b, v in g.items():
    print(f"  RSI {str(b):>6}  →  {v}")

# Bucketed WR by EMA-50 distance
print(f"\n{SEP}")
print("  EMA-50 DISTANCE BUCKETS → WIN RATE")
print(SEP)
df_f["ema50_bucket"] = pd.cut(df_f["ema50_dist_pct"].abs(),
                               bins=[0, 5, 10, 20, 50, 200],
                               labels=["<5%","5-10%","10-20%","20-50%","50%+"])
g2 = df_f.groupby("ema50_bucket", observed=True)["result"].apply(
    lambda s: f"WR={(s=='WIN').sum()/len(s)*100:.0f}%  ({(s=='WIN').sum()}W/{(s=='LOSS').sum()}L, n={len(s)})"
)
for b, v in g2.items():
    print(f"  EMA50 dist {str(b):>6}  →  {v}")

# ──────────────────────────────────────────────────────────────
# Multi-factor summary
print(f"\n{SEP}")
print("  TOP CONFIRMED PATTERNS  (statistically significant)")
print(SEP)

sigs = []
for col, label in [
    ("immediate_rejection", "Immediate rejection off entry level"),
    ("ma_aligned_trade",    "EMAs aligned with trade direction"),
    ("above_ema200",        "Price above EMA-200"),
    ("rsi_momentum",        "RSI on correct side of 50"),
    ("momentum_with",       "5c momentum agrees with trade"),
    ("ec_bullish",          "Entry candle bullish"),
    ("conf_bullish",        "Confirmation candle bullish"),
    ("next_candle_ok",      "Next candle follows through"),
    ("high_volume",         "High volume at entry"),
]:
    col_data = df_f[df_f[col].notna()]
    yes = col_data[col_data[col] == True]["result"] == "WIN"
    no  = col_data[col_data[col] == False]["result"] == "WIN"
    if len(yes) > 2 and len(no) > 2:
        _, p = ss.fisher_exact([[yes.sum(), (~yes).sum()], [no.sum(), (~no).sum()]])
        wr_yes = yes.sum() / len(yes) * 100
        wr_no  = no.sum() / len(no) * 100
        sigs.append((p, col, label, wr_yes, wr_no, len(yes), len(no)))

sigs.sort()
print()
for p, col, label, wr_yes, wr_no, ny, nn in sigs:
    flag = "***" if p < 0.05 else ("~" if p < 0.10 else "   ")
    print(f"  {flag} p={p:.3f}  {label}")
    print(f"         YES: WR={wr_yes:.0f}% (n={ny})   NO: WR={wr_no:.0f}% (n={nn})")

print(f"\n{SEP}")
print("  COMBINED FILTER TEST")
print(SEP)
# Test stacking the top confirmed filters
df_f["ema_ok"] = df_f["ma_aligned_trade"]
df_f["rsi_ok"] = df_f["rsi_momentum"]
df_f["rej_ok"] = df_f["immediate_rejection"]

masks = {
    "All 77 trades":         pd.Series([True]*len(df_f)),
    "+ EMA aligned":         df_f["ema_ok"] == True,
    "+ RSI momentum":        df_f["rsi_ok"] == True,
    "+ EMA + RSI":           (df_f["ema_ok"] == True) & (df_f["rsi_ok"] == True),
    "+ EMA + RSI + Rej":     (df_f["ema_ok"] == True) & (df_f["rsi_ok"] == True) & (df_f["rej_ok"] == True),
}
print()
print(f"  {'Filter':<28}  {'Trades':>7}  {'Win%':>6}  {'Removed':>8}")
print("  " + "-"*55)
base_n = len(df_f)
for label, mask in masks.items():
    sub = df_f[mask]
    w = (sub["result"] == "WIN").sum()
    total = len(sub)
    wr = w / total * 100 if total > 0 else 0
    removed = base_n - total
    print(f"  {label:<28}  {total:>7}  {wr:>5.1f}%  {removed:>8}")

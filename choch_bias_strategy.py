"""
CHoCH Bias Strategy Backtest — BTCUSD
======================================
Strategy Rules:
  - Detect PURE structural Swing Highs (SH) and Swing Lows (SL) — no internal structure.
  - Maintain market bias: UPTREND (HH+HL) or DOWNTREND (LH+LL).
  - CHoCH (Change of Character):
      Uptrend  → Downtrend : price closes below the most recent HL → LL confirmed
      Downtrend → Uptrend  : price closes above the most recent LH → HH confirmed

Entry Calculation (2.6 multiplier):
  LONG  (uptrend)  : range = HH − HL  →  entry = HL + range / 2.6   (~38.5 % up from HL)
  SHORT (downtrend): range = LH − LL  →  entry = LH − range / 2.6   (~38.5 % down from LH)

  Wait for price to pull back / bounce to that level, then enter.

Exit:
  WIN  — price forms a new HH (long) or new LL (short) after entry.
  LOSS — CHoCH fires before new HH/LL; stop is below HL (long) or above LH (short).
"""

import pandas as pd
import numpy as np

# ─────────────────────────────────────────────
MULTIPLIER     = 2.6
SWING_N        = 5     # candles each side required to confirm a structural pivot
ADX_PERIOD     = 14
ADX_THRESHOLD  = 20    # only enter when ADX > this (trending environment)
STOP_BUFFER    = 0.005 # 0.5 % buffer beyond HL/LH to absorb wick noise
SIGNAL_EXPIRY  = 10    # max candles an untriggered entry signal stays live (#1)
LEVEL_TOL      = 0.001 # 0.1 % tolerance for near-equal HH/HL/LH/LL pivots (#4)
DATA_CSV       = "btc_daily.csv"
# ─────────────────────────────────────────────


# ── 1. DATA ──────────────────────────────────
def load_data():
    print("Loading BTC-USD daily data from CSV …")
    df = pd.read_csv(DATA_CSV, parse_dates=["Date"], index_col="Date")
    df = df[["Open", "High", "Low", "Close"]].dropna()
    print(f"  {len(df)} candles  |  {df.index[0].date()} → {df.index[-1].date()}")
    return df


# ── 2. ADX ───────────────────────────────────
def calc_adx(df, period=ADX_PERIOD):
    """Wilder-smoothed ADX (standard 14-period)."""
    hi = df["High"].values
    lo = df["Low"].values
    cl = df["Close"].values
    n  = len(df)

    tr   = np.zeros(n)
    pdm  = np.zeros(n)   # +DM
    ndm  = np.zeros(n)   # -DM

    for i in range(1, n):
        h_diff = hi[i] - hi[i - 1]
        l_diff = lo[i - 1] - lo[i]
        tr[i]  = max(hi[i] - lo[i], abs(hi[i] - cl[i - 1]), abs(lo[i] - cl[i - 1]))
        pdm[i] = h_diff if h_diff > l_diff and h_diff > 0 else 0.0
        ndm[i] = l_diff if l_diff > h_diff and l_diff > 0 else 0.0

    # Wilder smoothing
    def wilder(arr, p):
        out = np.zeros(n)
        out[p] = arr[1: p + 1].sum()
        for i in range(p + 1, n):
            out[i] = out[i - 1] - out[i - 1] / p + arr[i]
        return out

    atr  = wilder(tr,  period)
    pDM  = wilder(pdm, period)
    nDM  = wilder(ndm, period)

    with np.errstate(divide="ignore", invalid="ignore"):
        pDI = np.where(atr > 0, 100 * pDM / atr, 0.0)
        nDI = np.where(atr > 0, 100 * nDM / atr, 0.0)
        dx  = np.where(pDI + nDI > 0, 100 * np.abs(pDI - nDI) / (pDI + nDI), 0.0)

    # wilder() accumulates a running sum ≈ period × true_value.
    # Dividing by period converts it to the proper 0-100 ADX scale.
    adx = wilder(dx, period) / period
    return adx


# ── 3. SWING DETECTION ───────────────────────
def find_swings(df, n=SWING_N):
    """
    Return list of dicts {idx, date, type:'H'|'L', price} — alternating,
    keeping the most extreme pivot when two of the same type are adjacent.
    """
    highs, lows = [], []
    hi = df["High"].values
    lo = df["Low"].values

    for i in range(n, len(df) - n):
        if hi[i] == max(hi[i - n: i + n + 1]):
            highs.append(i)
        if lo[i] == min(lo[i - n: i + n + 1]):
            lows.append(i)

    raw = []
    for i in highs:
        raw.append({"idx": i, "date": df.index[i], "type": "H", "price": float(hi[i])})
    for i in lows:
        raw.append({"idx": i, "date": df.index[i], "type": "L", "price": float(lo[i])})
    raw.sort(key=lambda x: x["idx"])

    # keep alternating; on same-type run, keep more extreme
    alt = []
    for s in raw:
        if not alt:
            alt.append(s)
        elif s["type"] != alt[-1]["type"]:
            alt.append(s)
        else:
            if s["type"] == "H" and s["price"] > alt[-1]["price"]:
                alt[-1] = s
            elif s["type"] == "L" and s["price"] < alt[-1]["price"]:
                alt[-1] = s
    return alt


# ── 4. BACKTEST ENGINE ───────────────────────
def run_backtest(df, swings, adx):
    hi = df["High"].values
    lo = df["Low"].values
    cl = df["Close"].values

    bias         = "NEUTRAL"
    last_HH      = None   # dict with idx+price
    last_HL      = None
    last_LH      = None
    last_LL      = None

    # pending signal
    sig_direction   = None
    sig_entry       = None
    sig_stop        = None
    sig_ref_HH      = None
    sig_ref_HL      = None
    sig_ref_LH      = None
    sig_ref_LL      = None
    sig_armed_idx   = None   # candle index when signal was armed (for expiry #1)
    sig_confirmed   = False  # True once close passed through entry side (#6)

    active  = None   # open trade dict
    trades  = []

    def open_trade(direction, entry_px, entry_date, stop, ref):
        return {
            "direction":   direction,
            "entry_price": entry_px,
            "entry_date":  entry_date,
            "stop_loss":   stop,
            **ref,
            "exit_price":  None,
            "exit_date":   None,
            "result":      None,
            "exit_reason": None,
        }

    def close_trade(t, px, dt, result, reason):
        t["exit_price"]  = px
        t["exit_date"]   = dt
        t["result"]      = result
        t["exit_reason"] = reason
        trades.append(dict(t))

    def set_long_signal(hh, hl, armed_at):
        nonlocal sig_direction, sig_entry, sig_stop, sig_ref_HH, sig_ref_HL
        nonlocal sig_armed_idx, sig_confirmed
        rng            = hh["price"] - hl["price"]
        sig_direction  = "LONG"
        sig_entry      = round(hl["price"] + rng / MULTIPLIER, 2)
        sig_stop       = round(hl["price"] * (1 - STOP_BUFFER), 2)
        sig_ref_HH     = hh["price"]
        sig_ref_HL     = hl["price"]
        sig_armed_idx  = armed_at
        sig_confirmed  = False   # must see close above entry first (#6)

    def set_short_signal(lh, ll, armed_at):
        nonlocal sig_direction, sig_entry, sig_stop, sig_ref_LH, sig_ref_LL
        nonlocal sig_armed_idx, sig_confirmed
        rng            = lh["price"] - ll["price"]
        sig_direction  = "SHORT"
        sig_entry      = round(lh["price"] - rng / MULTIPLIER, 2)
        sig_stop       = round(lh["price"] * (1 + STOP_BUFFER), 2)
        sig_ref_LH     = lh["price"]
        sig_ref_LL     = ll["price"]
        sig_armed_idx  = armed_at
        sig_confirmed  = False   # must see close below entry first (#6)

    def clear_signal():
        nonlocal sig_direction, sig_entry, sig_stop
        nonlocal sig_ref_HH, sig_ref_HL, sig_ref_LH, sig_ref_LL
        nonlocal sig_armed_idx, sig_confirmed
        sig_direction = sig_entry = sig_stop = None
        sig_ref_HH = sig_ref_HL = sig_ref_LH = sig_ref_LL = None
        sig_armed_idx = None
        sig_confirmed = False

    # ── scan swings ──
    for si, sw in enumerate(swings):
        idx   = sw["idx"]
        price = sw["price"]
        dt    = sw["date"]

        # ────────────────────────────────────────
        # SWING HIGH arrived
        # ────────────────────────────────────────
        if sw["type"] == "H":

            if bias == "NEUTRAL":
                if last_HH is None or price >= last_HH["price"] * (1 - LEVEL_TOL):
                    last_HH = sw
                    if last_HL is not None:
                        bias = "UPTREND"
                        set_long_signal(last_HH, last_HL, idx)

            elif bias == "UPTREND":
                if price >= last_HH["price"] * (1 - LEVEL_TOL):   # near-equal counts as HH
                    # ✓ New HH — WIN for any open LONG
                    if active and active["direction"] == "LONG":
                        close_trade(active, price, dt, "WIN", f"New HH @{price:.0f}")
                        active = None
                    last_HH = sw
                    clear_signal()
                    if last_HL:
                        set_long_signal(last_HH, last_HL, idx)
                else:
                    # LH inside uptrend — just track; CHoCH confirmed only on LL
                    last_LH = sw

            elif bias == "DOWNTREND":
                if price > (last_LH["price"] if last_LH else 0):   # CHoCH: strict break above LH
                    # CHoCH UP — new HH above last LH
                    if active and active["direction"] == "SHORT":
                        close_trade(active, price, dt, "LOSS", f"CHoCH UP @{price:.0f}")
                        active = None
                    bias    = "UPTREND"
                    last_HH = sw
                    last_HL = last_LL  # prior LL becomes new HL
                    last_LH = None
                    clear_signal()
                    if last_HL:
                        set_long_signal(last_HH, last_HL, idx)
                else:
                    # Continuation LH in downtrend — WIN for active SHORT
                    if active and active["direction"] == "SHORT":
                        close_trade(active, price, dt, "WIN", f"New LH @{price:.0f}")
                        active = None
                    last_LH = sw
                    clear_signal()
                    if last_LL:
                        set_short_signal(last_LH, last_LL, idx)

        # ────────────────────────────────────────
        # SWING LOW arrived
        # ────────────────────────────────────────
        elif sw["type"] == "L":

            if bias == "NEUTRAL":
                if last_HL is None or price < last_HL["price"]:
                    last_HL = sw
                    if last_HH is not None and price < last_HH["price"]:
                        bias    = "DOWNTREND"
                        last_LL = sw
                        last_LH = last_HH
                        if last_LH:
                            set_short_signal(last_LH, last_LL, idx)
                else:
                    last_HL = sw

            elif bias == "UPTREND":
                if last_HL is None or price >= last_HL["price"] * (1 - LEVEL_TOL):  # near-equal = HL
                    # New HL — update structure, refresh signal
                    if active and active["direction"] == "LONG":
                        close_trade(active, price, dt, "WIN", f"HL confirmed @{price:.0f}")
                        active = None
                    last_HL = sw
                    clear_signal()
                    if last_HH:
                        set_long_signal(last_HH, last_HL, idx)
                else:
                    # LL → CHoCH DOWN (strict: must be clearly below HL)
                    if active and active["direction"] == "LONG":
                        close_trade(active, price, dt, "LOSS", f"CHoCH DOWN @{price:.0f}")
                        active = None
                    bias    = "DOWNTREND"
                    last_LL = sw
                    last_LH = last_HH
                    last_HH = None
                    last_HL = None
                    clear_signal()
                    if last_LH:
                        set_short_signal(last_LH, last_LL, idx)

            elif bias == "DOWNTREND":
                if price <= last_LL["price"] * (1 + LEVEL_TOL):   # near-equal counts as LL
                    # ✓ New LL — WIN for any open SHORT
                    if active and active["direction"] == "SHORT":
                        close_trade(active, price, dt, "WIN", f"New LL @{price:.0f}")
                        active = None
                    last_LL = sw
                    clear_signal()
                    if last_LH:
                        set_short_signal(last_LH, last_LL, idx)
                else:
                    # HL inside downtrend — just track
                    last_HL = sw

        # ──────────────────────────────────────────────────────────
        # Scan candles between this swing and the NEXT swing
        # looking for (a) entry trigger  (b) stop loss hit
        # ──────────────────────────────────────────────────────────
        next_sw_idx = swings[si + 1]["idx"] if si + 1 < len(swings) else len(df) - 1

        for ci in range(idx + 1, next_sw_idx):
            c_hi = hi[ci]
            c_lo = lo[ci]
            c_cl = cl[ci]
            c_dt = df.index[ci]

            # ── Stop loss check ──────────────────────────────────────
            if active:
                if active["direction"] == "LONG" and c_lo <= active["stop_loss"]:
                    close_trade(active, active["stop_loss"], c_dt, "LOSS", "Stop Loss")
                    active = None
                    clear_signal()
                    continue
                if active["direction"] == "SHORT" and c_hi >= active["stop_loss"]:
                    close_trade(active, active["stop_loss"], c_dt, "LOSS", "Stop Loss")
                    active = None
                    clear_signal()
                    continue

            # ── Close-based CHoCH (fixes detection lag) ──────────────
            # Fire the moment a daily close breaks the structural HL/LH,
            # rather than waiting N more candles for swing confirmation.
            # tolerance applied: require close clearly beyond the level (#4)
            if bias == "UPTREND" and last_HL and c_cl < last_HL["price"] * (1 - LEVEL_TOL):
                if active and active["direction"] == "LONG":
                    close_trade(active, c_cl, c_dt, "LOSS",
                                f"CHoCH Close DN @{c_cl:.0f}")
                    active = None
                bias    = "DOWNTREND"
                lh_ref  = last_HH if last_HH else last_LH
                ll_apx  = {"idx": ci, "price": c_lo, "date": c_dt}
                last_LH, last_LL = lh_ref, ll_apx
                last_HH = last_HL = None
                clear_signal()
                if last_LH:
                    set_short_signal(last_LH, last_LL, ci)
                continue  # don't enter on the same candle CHoCH fired

            elif bias == "DOWNTREND" and last_LH and c_cl > last_LH["price"] * (1 + LEVEL_TOL):
                if active and active["direction"] == "SHORT":
                    close_trade(active, c_cl, c_dt, "LOSS",
                                f"CHoCH Close UP @{c_cl:.0f}")
                    active = None
                bias    = "UPTREND"
                hh_apx  = {"idx": ci, "price": c_hi, "date": c_dt}
                hl_ref  = last_LL if last_LL else last_HL
                last_HH, last_HL = hh_apx, hl_ref
                last_LH = last_LL = None
                clear_signal()
                if last_HH and last_HL:
                    set_long_signal(last_HH, last_HL, ci)
                continue  # don't enter on the same candle CHoCH fired

            # ── Signal expiry (#1) ──────────────────────────────────
            if sig_direction and sig_armed_idx is not None and ci - sig_armed_idx > SIGNAL_EXPIRY:
                clear_signal()
                continue

            # ── Price-confirmation tracking (#6) ─────────────────────
            # Require at least one close on the entry side before we open.
            if sig_direction and not active:
                if sig_direction == "LONG" and c_cl > sig_entry:
                    sig_confirmed = True
                elif sig_direction == "SHORT" and c_cl < sig_entry:
                    sig_confirmed = True

            # ── Entry trigger — ADX + confirmation guard ───────────────
            if sig_direction and not active and adx[ci] > ADX_THRESHOLD and sig_confirmed:
                if sig_direction == "LONG" and c_lo <= sig_entry:
                    ref = {"ref_HH": sig_ref_HH, "ref_HL": sig_ref_HL, "adx_at_entry": round(adx[ci], 1)}
                    active = open_trade("LONG", sig_entry, c_dt, sig_stop, ref)
                    clear_signal()
                elif sig_direction == "SHORT" and c_hi >= sig_entry:
                    ref = {"ref_LH": sig_ref_LH, "ref_LL": sig_ref_LL, "adx_at_entry": round(adx[ci], 1)}
                    active = open_trade("SHORT", sig_entry, c_dt, sig_stop, ref)
                    clear_signal()

    return trades


# ── 4. RESULTS ───────────────────────────────
def print_results(trades):
    if not trades:
        print("\nNo trades generated.")
        return

    df_t = pd.DataFrame(trades)
    total  = len(df_t)
    wins   = (df_t["result"] == "WIN").sum()
    losses = (df_t["result"] == "LOSS").sum()
    wr     = wins / total * 100 if total else 0

    longs  = df_t[df_t["direction"] == "LONG"]
    shorts = df_t[df_t["direction"] == "SHORT"]

    print("\n" + "=" * 60)
    print("  CHoCH BIAS STRATEGY  |  BTCUSD DAILY  |  2.6x  |  ADX  |  CLOSE CHoCH  |  ALL FIXES")
    print("=" * 60)
    period = f"{df_t['entry_date'].min().date()} → {df_t['entry_date'].max().date()}"
    print(f"  Period          : {period}")
    print(f"  Swing lookback  : {SWING_N} candles each side")
    print(f"  Multiplier      : {MULTIPLIER}  (entry ≈ 38.5 % into swing)")
    print(f"  ADX filter      : period={ADX_PERIOD}, threshold={ADX_THRESHOLD} (trend-only entries)")
    print(f"  Stop buffer     : {STOP_BUFFER*100:.1f}% beyond HL/LH (wick absorption)")
    print(f"  Signal expiry   : {SIGNAL_EXPIRY} candles (stale signals auto-clear)")
    print(f"  Level tolerance : {LEVEL_TOL*100:.1f}% (near-equal HH/HL/LH/LL accepted)")
    print(f"  Entry guard     : requires a confirming close before stop-side fill")
    print("-" * 60)
    print(f"  Total Trades    : {total}")
    print(f"  Wins            : {wins}")
    print(f"  Losses          : {losses}")
    print(f"  Win Rate        : {wr:.1f} %")
    print("-" * 60)
    print(f"  LONG  trades    : {len(longs)}  "
          f"| W {(longs['result']=='WIN').sum()}  L {(longs['result']=='LOSS').sum()}")
    print(f"  SHORT trades    : {len(shorts)}  "
          f"| W {(shorts['result']=='WIN').sum()}  L {(shorts['result']=='LOSS').sum()}")

    # Exit reason breakdown
    print("\n  Exit Reason Breakdown:")
    for reason, cnt in df_t["exit_reason"].str.split(" @").str[0].value_counts().items():
        print(f"    {reason:<22} : {cnt}")

    print("\n  Trade Log (last 20):")
    print(f"  {'Date':>12}  {'Dir':>5}  {'Entry':>9}  {'Exit':>9}  {'Result':>6}  Reason")
    print("  " + "-" * 70)
    for _, r in df_t.tail(20).iterrows():
        ed = str(r["entry_date"])[:10]
        print(f"  {ed:>12}  {r['direction']:>5}  "
              f"{r['entry_price']:>9,.0f}  {r['exit_price']:>9,.0f}  "
              f"{r['result']:>6}  {r['exit_reason']}")

    # ── Loophole / Edge Analysis ──
    print("\n" + "=" * 60)
    print("  LOOPHOLES / REFINEMENT OBSERVATIONS")
    print("=" * 60)

    # 1. Trades that never got an entry (signal expired)
    #    (these are not in the trade log — we note it)
    print("""
  1. ENTRY LEVEL EXPIRY  [APPLIED]
     The 2.6 level is computed from the latest HH/LL at that moment.
     If price never pulls back to that level before the next structural
     swing fires, the signal expires silently.  This can cause missed
     trades during strong momentum legs, or stale signals from a long
     time ago getting filled out of context.
     FIX (applied) → Signal auto-expires after SIGNAL_EXPIRY (10)
           candles if untriggered; we then wait for the next HH/LL to
           reset it.

  2. STOP LOSS TOO TIGHT  [APPLIED]
     Stop is placed just below the HL (or above LH).  On highly
     volatile assets like BTC, wicks can pierce the HL without a real
     CHoCH, causing unnecessary losses.
     FIX (applied) → Stop is now 0.5 % (STOP_BUFFER) beyond the
           HL/LH level, absorbing normal wick noise before triggering.

  3. CHOCH DETECTION LAG  [APPLIED]
     On daily bars, a CHoCH is confirmed only after the candle closes
     below the HL.  The entry signal for the new direction is then set
     only for the next swing — meaning the first swing of the new
     trend is always missed.
     FIX (applied) → Close-based CHoCH now fires the moment a daily
           candle closes below the structural HL (or above the LH),
           immediately switching bias and arming the entry signal.
           No longer waits N extra candles for swing confirmation.

  4. EQUAL HIGH / EQUAL LOW AMBIGUITY  [APPLIED]
     When a new SH exactly equals the prior SH it is not counted as
     a HH.  In reality "liquidity grabs" often produce near-equal
     highs before reversing.
     FIX (applied) → LEVEL_TOL (0.1 %) tolerance band applied when
           comparing HH/HL/LH/LL swing levels and close-based CHoCH.

  5. SINGLE-DIRECTION BIAS DURING RANGING MARKETS  [APPLIED]
     The strategy forces either UPTREND or DOWNTREND.  During sideways
     consolidation, many CHoCH events fire rapidly, generating a run
     of losses.
     FIX (applied) → Entry is now gated by ADX(14) > 20.  Entries
           during low-ADX (choppy/ranging) candles are skipped.

  6. ENTRY LEVEL INSIDE THE SIGNAL CANDLE  [APPLIED]
     If the entry level falls within the range of the swing/CHoCH
     candle itself, the naive trigger can open the trade immediately
     on noise, with no confirmation the new structure actually holds.
     FIX (applied) → A confirming close on the signal side (close above
           entry for LONG, below for SHORT) is now required before the
           stop-side fill is allowed to open a trade (sig_confirmed).
""")
    print("=" * 60)

    return df_t


# ── MAIN ─────────────────────────────────────
if __name__ == "__main__":
    df     = load_data()
    adx    = calc_adx(df, period=ADX_PERIOD)
    swings = find_swings(df, n=SWING_N)
    print(f"\n  Structural swings detected: {len(swings)} "
          f"({sum(1 for s in swings if s['type']=='H')} highs, "
          f"{sum(1 for s in swings if s['type']=='L')} lows)")
    adx_gt20 = (adx > ADX_THRESHOLD).sum()
    print(f"  ADX > {ADX_THRESHOLD} on {adx_gt20}/{len(df)} candles "
          f"({adx_gt20/len(df)*100:.1f}% of bars — tradeable)")

    trades = run_backtest(df, swings, adx)
    result_df = print_results(trades)

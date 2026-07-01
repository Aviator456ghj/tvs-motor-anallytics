"""
Multi-Timeframe Backtest — CHoCH Bias Strategy
Fetches BTC/USDT data for 1H, 4H, 1D, 1W and runs V1, V2, V3 on each.
"""

import requests, time, pandas as pd, numpy as np

CA_BUNDLE = "/root/.ccr/ca-bundle.crt"
BASE_URL  = "https://api.crypto.com/exchange/v1/public/get-candlestick"

# ── Constants (shared) ──────────────────────────────────────
MULTIPLIER  = 2.6
SWING_N     = 5
STOP_BUFFER = 0.005
LEVEL_TOL   = 0.001
ADX_PERIOD  = 14
RSI_PERIOD  = 14

# ── Variant parameter sets ───────────────────────────────────
VARIANTS = {
    "V1": dict(adx_thr=20, expiry=10, min_swing=1, rejection=False, rsi_side=False, early_exit=False),
    "V2": dict(adx_thr=25, expiry=4,  min_swing=2, rejection=False, rsi_side=False, early_exit=False),
    "V3": dict(adx_thr=25, expiry=4,  min_swing=2, rejection=True,  rsi_side=True,  early_exit=True),
}

# ── 1. DATA FETCH ────────────────────────────────────────────
def fetch_candles(timeframe, n_pages):
    print(f"  Fetching {timeframe} ({n_pages} pages) …", end="", flush=True)
    all_c = []
    end_ts = None
    for _ in range(n_pages):
        params = {"instrument_name": "BTC_USDT", "timeframe": timeframe, "count": 300}
        if end_ts:
            params["end_ts"] = end_ts
        try:
            r = requests.get(BASE_URL, params=params, verify=CA_BUNDLE, timeout=15)
            candles = r.json()["result"]["data"]
        except Exception as e:
            print(f" [err: {e}]", end="")
            break
        if not candles:
            break
        all_c.extend(candles)
        end_ts = candles[0]["t"] - 1
        time.sleep(0.15)
    rows = [{"Date": pd.Timestamp(c["t"], unit="ms"),
             "Open": float(c["o"]), "High": float(c["h"]),
             "Low":  float(c["l"]), "Close": float(c["c"]),
             "Volume": float(c["v"])} for c in all_c]
    if not rows:
        print(" [no data returned]")
        return pd.DataFrame(columns=["Open","High","Low","Close","Volume"])
    df = pd.DataFrame(rows).drop_duplicates("Date").sort_values("Date").set_index("Date")
    print(f" {len(df)} candles  {df.index[0].date()} → {df.index[-1].date()}")
    return df

# ── 2. INDICATORS ────────────────────────────────────────────
def calc_adx(df, period=ADX_PERIOD):
    hi = df["High"].values; lo = df["Low"].values; cl = df["Close"].values
    n  = len(df)
    tr = np.zeros(n); pdm = np.zeros(n); ndm = np.zeros(n)
    for i in range(1, n):
        h_diff = hi[i]-hi[i-1]; l_diff = lo[i-1]-lo[i]
        tr[i]  = max(hi[i]-lo[i], abs(hi[i]-cl[i-1]), abs(lo[i]-cl[i-1]))
        pdm[i] = h_diff if h_diff > l_diff and h_diff > 0 else 0.0
        ndm[i] = l_diff if l_diff > h_diff and l_diff > 0 else 0.0
    def wilder(arr, p):
        out = np.zeros(n); out[p] = arr[1:p+1].sum()
        for i in range(p+1, n): out[i] = out[i-1] - out[i-1]/p + arr[i]
        return out
    atr = wilder(tr, period); pDM = wilder(pdm, period); nDM = wilder(ndm, period)
    with np.errstate(divide="ignore", invalid="ignore"):
        pDI = np.where(atr>0, 100*pDM/atr, 0.0)
        nDI = np.where(atr>0, 100*nDM/atr, 0.0)
        dx  = np.where(pDI+nDI>0, 100*np.abs(pDI-nDI)/(pDI+nDI), 0.0)
    return wilder(dx, period) / period

def calc_rsi(df, period=RSI_PERIOD):
    cl = df["Close"].values; n = len(cl)
    out = np.zeros(n); gain = np.zeros(n); loss = np.zeros(n)
    for i in range(1, n):
        d = cl[i]-cl[i-1]; gain[i] = d if d>0 else 0.0; loss[i] = -d if d<0 else 0.0
    ag = gain[1:period+1].mean(); al = loss[1:period+1].mean()
    out[period] = 100-100/(1+ag/al) if al>0 else 100.0
    for i in range(period+1, n):
        ag = (ag*(period-1)+gain[i])/period; al = (al*(period-1)+loss[i])/period
        out[i] = 100-100/(1+ag/al) if al>0 else 100.0
    return out

# ── 3. SWING DETECTION ───────────────────────────────────────
def find_swings(df, n=SWING_N):
    hi = df["High"].values; lo = df["Low"].values
    raw = []
    for i in range(n, len(df)-n):
        if hi[i] == max(hi[i-n:i+n+1]):
            raw.append({"idx":i,"date":df.index[i],"type":"H","price":float(hi[i])})
        if lo[i] == min(lo[i-n:i+n+1]):
            raw.append({"idx":i,"date":df.index[i],"type":"L","price":float(lo[i])})
    raw.sort(key=lambda x: x["idx"])
    alt = []
    for s in raw:
        if not alt: alt.append(s)
        elif s["type"] != alt[-1]["type"]: alt.append(s)
        else:
            if s["type"]=="H" and s["price"]>alt[-1]["price"]: alt[-1]=s
            elif s["type"]=="L" and s["price"]<alt[-1]["price"]: alt[-1]=s
    return alt

# ── 4. BACKTEST ──────────────────────────────────────────────
def run_backtest(df, swings, adx, rsi, p):
    hi = df["High"].values; lo = df["Low"].values
    cl = df["Close"].values; op = df["Open"].values

    bias=  "NEUTRAL"
    last_HH=last_HL=last_LH=last_LL=None
    trend_sw_cnt=0
    sig_dir=sig_entry=sig_stop=None
    sig_ref_HH=sig_ref_HL=sig_ref_LH=sig_ref_LL=None
    sig_armed=None; sig_conf=False; sig_sw_cnt=0
    active=None; trades=[]

    def open_t(dirn,px,dt,ci,stop,ref):
        return {"direction":dirn,"entry_price":px,"entry_date":dt,"entry_ci":ci,
                "stop_loss":stop,**ref,"exit_price":None,"exit_date":None,
                "result":None,"exit_reason":None}

    def close_t(t,px,dt,res,reason):
        t["exit_price"]=px; t["exit_date"]=dt; t["result"]=res; t["exit_reason"]=reason
        trades.append(dict(t))

    def set_long(hh,hl,at):
        nonlocal sig_dir,sig_entry,sig_stop,sig_ref_HH,sig_ref_HL,sig_armed,sig_conf,sig_sw_cnt
        rng=hh["price"]-hl["price"]
        sig_dir="LONG"; sig_entry=round(hl["price"]+rng/MULTIPLIER,2)
        sig_stop=round(hl["price"]*(1-STOP_BUFFER),2)
        sig_ref_HH=hh["price"]; sig_ref_HL=hl["price"]
        sig_armed=at; sig_conf=False; sig_sw_cnt=trend_sw_cnt

    def set_short(lh,ll,at):
        nonlocal sig_dir,sig_entry,sig_stop,sig_ref_LH,sig_ref_LL,sig_armed,sig_conf,sig_sw_cnt
        rng=lh["price"]-ll["price"]
        sig_dir="SHORT"; sig_entry=round(lh["price"]-rng/MULTIPLIER,2)
        sig_stop=round(lh["price"]*(1+STOP_BUFFER),2)
        sig_ref_LH=lh["price"]; sig_ref_LL=ll["price"]
        sig_armed=at; sig_conf=False; sig_sw_cnt=trend_sw_cnt

    def clear():
        nonlocal sig_dir,sig_entry,sig_stop,sig_ref_HH,sig_ref_HL
        nonlocal sig_ref_LH,sig_ref_LL,sig_armed,sig_conf,sig_sw_cnt
        sig_dir=sig_entry=sig_stop=None
        sig_ref_HH=sig_ref_HL=sig_ref_LH=sig_ref_LL=None
        sig_armed=None; sig_conf=False; sig_sw_cnt=0

    for si,sw in enumerate(swings):
        idx=sw["idx"]; price=sw["price"]; dt=sw["date"]

        if sw["type"]=="H":
            if bias=="NEUTRAL":
                if last_HH is None or price>=last_HH["price"]*(1-LEVEL_TOL):
                    last_HH=sw
                    if last_HL:
                        bias="UPTREND"; trend_sw_cnt=1; set_long(last_HH,last_HL,idx)
            elif bias=="UPTREND":
                if price>=last_HH["price"]*(1-LEVEL_TOL):
                    if active and active["direction"]=="LONG":
                        close_t(active,price,dt,"WIN",f"New HH"); active=None
                    last_HH=sw; trend_sw_cnt+=1; clear()
                    if last_HL: set_long(last_HH,last_HL,idx)
                else:
                    last_LH=sw
            elif bias=="DOWNTREND":
                if price>(last_LH["price"] if last_LH else 0):
                    if active and active["direction"]=="SHORT":
                        close_t(active,price,dt,"LOSS",f"CHoCH UP"); active=None
                    bias="UPTREND"; last_HH=sw; last_HL=last_LL; last_LH=None
                    trend_sw_cnt=1; clear()
                    if last_HL: set_long(last_HH,last_HL,idx)
                else:
                    if active and active["direction"]=="SHORT":
                        close_t(active,price,dt,"WIN",f"New LH"); active=None
                    last_LH=sw; trend_sw_cnt+=1; clear()
                    if last_LL: set_short(last_LH,last_LL,idx)

        elif sw["type"]=="L":
            if bias=="NEUTRAL":
                if last_HL is None or price<last_HL["price"]:
                    last_HL=sw
                    if last_HH and price<last_HH["price"]:
                        bias="DOWNTREND"; last_LL=sw; last_LH=last_HH
                        trend_sw_cnt=1
                        if last_LH: set_short(last_LH,last_LL,idx)
                else:
                    last_HL=sw
            elif bias=="UPTREND":
                if last_HL is None or price>=last_HL["price"]*(1-LEVEL_TOL):
                    if active and active["direction"]=="LONG":
                        close_t(active,price,dt,"WIN",f"HL confirmed"); active=None
                    last_HL=sw; trend_sw_cnt+=1; clear()
                    if last_HH: set_long(last_HH,last_HL,idx)
                else:
                    if active and active["direction"]=="LONG":
                        close_t(active,price,dt,"LOSS",f"CHoCH DN"); active=None
                    bias="DOWNTREND"; last_LL=sw; last_LH=last_HH
                    last_HH=None; last_HL=None; trend_sw_cnt=1; clear()
                    if last_LH: set_short(last_LH,last_LL,idx)
            elif bias=="DOWNTREND":
                if price<=last_LL["price"]*(1+LEVEL_TOL):
                    if active and active["direction"]=="SHORT":
                        close_t(active,price,dt,"WIN",f"New LL"); active=None
                    last_LL=sw; trend_sw_cnt+=1; clear()
                    if last_LH: set_short(last_LH,last_LL,idx)
                else:
                    last_HL=sw

        nxt = swings[si+1]["idx"] if si+1<len(swings) else len(df)-1

        for ci in range(idx+1, nxt):
            c_hi=hi[ci]; c_lo=lo[ci]; c_cl=cl[ci]; c_op=op[ci]; c_dt=df.index[ci]

            # Stop loss
            if active:
                if active["direction"]=="LONG" and c_lo<=active["stop_loss"]:
                    close_t(active,active["stop_loss"],c_dt,"LOSS","Stop Loss"); active=None; clear(); continue
                if active["direction"]=="SHORT" and c_hi>=active["stop_loss"]:
                    close_t(active,active["stop_loss"],c_dt,"LOSS","Stop Loss"); active=None; clear(); continue

            # Close-based CHoCH
            if bias=="UPTREND" and last_HL and c_cl<last_HL["price"]*(1-LEVEL_TOL):
                if active and active["direction"]=="LONG":
                    close_t(active,c_cl,c_dt,"LOSS","CHoCH Close DN"); active=None
                bias="DOWNTREND"
                lh_ref=last_HH if last_HH else last_LH
                last_LH,last_LL=lh_ref,{"idx":ci,"price":c_lo,"date":c_dt}
                last_HH=last_HL=None; trend_sw_cnt=1; clear()
                if last_LH: set_short(last_LH,last_LL,ci)
                continue
            elif bias=="DOWNTREND" and last_LH and c_cl>last_LH["price"]*(1+LEVEL_TOL):
                if active and active["direction"]=="SHORT":
                    close_t(active,c_cl,c_dt,"LOSS","CHoCH Close UP"); active=None
                bias="UPTREND"
                hh_apx={"idx":ci,"price":c_hi,"date":c_dt}
                hl_ref=last_LL if last_LL else last_HL
                last_HH,last_HL=hh_apx,hl_ref; last_LH=last_LL=None; trend_sw_cnt=1; clear()
                if last_HH and last_HL: set_long(last_HH,last_HL,ci)
                continue

            # Signal expiry
            if sig_dir and sig_armed is not None and ci-sig_armed>p["expiry"]:
                clear(); continue

            # Confirmation tracking
            if sig_dir and not active:
                if sig_dir=="LONG" and c_cl>sig_entry: sig_conf=True
                elif sig_dir=="SHORT" and c_cl<sig_entry: sig_conf=True

            # Entry trigger
            if sig_dir and not active and adx[ci]>p["adx_thr"] and sig_conf and sig_sw_cnt>=p["min_swing"]:
                rsi_ok = True
                if p["rsi_side"]:
                    rsi_ok = (rsi[ci]>50) if sig_dir=="LONG" else (rsi[ci]<50)

                if sig_dir=="LONG" and c_lo<=sig_entry and rsi_ok:
                    if p["rejection"] and c_cl<=sig_entry:
                        pass
                    else:
                        ref={"ref_HH":sig_ref_HH,"ref_HL":sig_ref_HL}
                        active=open_t("LONG",sig_entry,c_dt,ci,sig_stop,ref); clear()
                elif sig_dir=="SHORT" and c_hi>=sig_entry and rsi_ok:
                    if p["rejection"] and c_cl>=sig_entry:
                        pass
                    else:
                        ref={"ref_LH":sig_ref_LH,"ref_LL":sig_ref_LL}
                        active=open_t("SHORT",sig_entry,c_dt,ci,sig_stop,ref); clear()

            # Early exit: next-candle follow-through
            if p["early_exit"] and active and ci==active.get("entry_ci", -1)+1:
                failed=((active["direction"]=="LONG" and c_cl<active["entry_price"]) or
                        (active["direction"]=="SHORT" and c_cl>active["entry_price"]))
                if failed:
                    close_t(active,c_cl,c_dt,"LOSS","No Follow-Through"); active=None

    return trades

# ── 5. SUMMARISE ONE RUN ─────────────────────────────────────
def summarise(trades, df_price):
    if len(trades) < 3:
        return {"trades":len(trades),"wr":0,"final":1.0,"cagr":0,"maxdd":0,
                "avg_win":0,"avg_loss":0,"rr":0,"expectancy":0}
    df = pd.DataFrame(trades).sort_values("entry_date").reset_index(drop=True)
    df["pnl"] = df.apply(
        lambda r: (r["exit_price"]-r["entry_price"])/r["entry_price"]*100
                  if r["direction"]=="LONG"
                  else (r["entry_price"]-r["exit_price"])/r["entry_price"]*100, axis=1)
    bal=1.0; peak=1.0; max_dd=0.0
    for pct in df["pnl"]:
        bal*=(1+pct/100); peak=max(peak,bal); max_dd=max(max_dd,(peak-bal)/peak*100)
    wins=df[df["result"]=="WIN"]["pnl"]; losses=df[df["result"]=="LOSS"]["pnl"].abs()
    wr=len(wins)/len(df)*100
    avg_w=wins.mean() if len(wins) else 0; avg_l=losses.mean() if len(losses) else 0
    rr=avg_w/avg_l if avg_l>0 else 0
    exp=wr/100*avg_w-(1-wr/100)*avg_l
    t0=df["entry_date"].min(); t1=df["entry_date"].max()
    years=(t1-t0).days/365.25
    cagr=(bal**(1/years)-1)*100 if years>0.1 else 0
    return {"trades":len(df),"wr":wr,"final":bal,"cagr":cagr,"maxdd":max_dd,
            "avg_win":avg_w,"avg_loss":avg_l,"rr":rr,"expectancy":exp}

# ── 6. MAIN ──────────────────────────────────────────────────
TF_PAGES = {
    "1h":  60,   # ~18,000 candles ≈ 2 years
    "4h":  25,   # ~7,500  candles ≈ 3.5 years
    "1D":  0,    # load from CSV
    "7D":  2,    # ~600    weeks   ≈ 11 years (limited by exchange history)
}

results = {}   # {tf: {variant: stats}}

print("\n=== Fetching data ===")
dfs = {}
for tf, pages in TF_PAGES.items():
    if tf == "1D":
        dfs[tf] = pd.read_csv("btc_daily.csv", parse_dates=["Date"], index_col="Date")
        dfs[tf] = dfs[tf][["Open","High","Low","Close","Volume"]].dropna()
        print(f"  Loaded 1D from CSV: {len(dfs[tf])} candles  "
              f"{dfs[tf].index[0].date()} → {dfs[tf].index[-1].date()}")
    else:
        dfs[tf] = fetch_candles(tf, pages)

print("\n=== Running backtests ===")
for tf, df in dfs.items():
    results[tf] = {}
    adx = calc_adx(df); rsi_arr = calc_rsi(df); swings = find_swings(df)
    for vname, vp in VARIANTS.items():
        t = run_backtest(df, swings, adx, rsi_arr, vp)
        results[tf][vname] = summarise(t, df)
        s = results[tf][vname]
        print(f"  {tf:>4}  {vname}  trades={s['trades']:>4}  "
              f"WR={s['wr']:>5.1f}%  $1→${s['final']:>6.2f}  "
              f"CAGR={s['cagr']:>6.1f}%  DD={s['maxdd']:>5.1f}%  R:R={s['rr']:.2f}")

# ── 7. PRINT FULL TABLE ───────────────────────────────────────
SEP = "═" * 100
print(f"\n\n{SEP}")
print("  FULL COMPARISON TABLE — All Timeframes × All Variants")
print(SEP)
hdr = f"  {'TF':>4}  {'Variant':>7}  {'Trades':>7}  {'WR':>6}  {'$1 →':>7}  {'CAGR':>7}  {'MaxDD':>7}  {'Avg Win':>8}  {'Avg Loss':>9}  {'R:R':>5}  {'Expect':>8}"
print(hdr)
print("  " + "─"*97)
for tf in ["1h","4h","1D","7D"]:
    for vname in ["V1","V2","V3"]:
        s = results[tf][vname]
        print(f"  {tf:>4}  {vname:>7}  {s['trades']:>7}  {s['wr']:>5.1f}%  "
              f"${s['final']:>6.2f}  {s['cagr']:>6.1f}%  {s['maxdd']:>6.1f}%  "
              f"{s['avg_win']:>7.1f}%  {s['avg_loss']:>8.1f}%  "
              f"{s['rr']:>5.2f}  {s['expectancy']:>+7.2f}%")
    print("  " + "─"*97)

print(f"\n  Legend:")
print(f"  V1 = All 6 loopholes (ADX>20, expiry=10, no candle filters)")
print(f"  V2 = Data-driven filters (ADX>25, expiry=4, min_swing=2)")
print(f"  V3 = V2 + candle rejection + RSI side + early exit")
print(SEP)

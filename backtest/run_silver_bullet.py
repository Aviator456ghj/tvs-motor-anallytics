"""ICT FVG Silver Bullet backtest + visual artifact, run against real
BTCUSDT data pulled from Delta Exchange's public API.

This is a bar-by-bar (not tick-by-tick) re-implementation of the exact
same state machine as MQL5/Experts/ICT_FVG_SilverBullet.ea: day high/low
locked at a cutoff, first liquidity sweep of the day, fractal-based
market structure shift confirmed on a close, ATR-filtered fair value
gaps scoped to the day range, midpoint activation -> stop order, close
-based invalidation, and risk-decayed position sizing with a fixed
per-trade risk:reward target.

Simplification vs the live EA: the EA recomputes one *unified* TP across
all concurrently open trades for the day; this backtest scores each
FVG's trade independently against its own RR target. That keeps the
bar-level simulation honest (we only have OHLC, not tick data) without
guessing intrabar fill order across multiple positions at once.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from fetch_delta_data import fetch_candles
import time

# ------------------------------------------------------------------
# Strategy configuration (mirrors the EA's inputs)
# ------------------------------------------------------------------
SYMBOL = "BTCUSDT"
RESOLUTION = "5m"
LOOKBACK_DAYS = 30

CUTOFF_HOUR_UTC = 13          # day's high/low locks here (~9am NY / pre NY-AM kill zone)
CUTOFF_MIN_UTC = 30
MAX_SWEEP_CANDLES = 24        # sweep must occur within this many candles after cutoff (2h @5m)
FRACTAL_STRENGTH = 2
MSS_LOOKBACK_CANDLES = 30
MSS_CONFIRM_MAX_CANDLES = 24  # 0 = no expiry

ATR_PERIOD = 100
FVG_MIN_ATR_MULT = 0.5
FVG_MAX_ATR_MULT = 0.0        # 0 = no max

RISK_PCT = 1.0
RISK_DECAY = 0.5
SL_BUFFER_WIDTH_MULT = 1.0
RISK_REWARD = 2.0
MAX_TRADES_PER_DAY = 3

STARTING_BALANCE = 10_000.0

BULL_COLOR = "rgba(0,230,118,0.35)"
BEAR_COLOR = "rgba(255,20,147,0.35)"
INVALID_COLOR = "rgba(128,128,128,0.35)"


# ------------------------------------------------------------------
def load_data():
    end = int(time.time())
    start = end - LOOKBACK_DAYS * 86400
    df = fetch_candles(SYMBOL, RESOLUTION, start, end)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    df["atr"] = tr.rolling(ATR_PERIOD).mean()
    return df


def is_fractal_high(highs, p, k):
    h = highs[p]
    for i in range(1, k + 1):
        if p - i >= 0 and highs[p - i] >= h:
            return False
        if p + i < len(highs) and highs[p + i] >= h:
            return False
    return True


def is_fractal_low(lows, p, k):
    l = lows[p]
    for i in range(1, k + 1):
        if p - i >= 0 and lows[p - i] <= l:
            return False
        if p + i < len(lows) and lows[p + i] <= l:
            return False
    return True


# ------------------------------------------------------------------
def run_backtest(df: pd.DataFrame):
    n = len(df)
    o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    atr = df["atr"].values
    times = df.index

    day_start_idx = 0
    day_high = -np.inf
    day_low = np.inf
    day_range_locked = False
    cutoff_idx = None

    sweep_found = False
    sweep_is_sell = False
    sweep_idx = None

    mss_found = False
    mss_level = None
    mss_fractal_idx = None
    mss_confirmed = False
    mss_invalidated = False

    fvg_search_closed = False
    fvg_seq = 0
    fvgs = []          # list of dicts, full lifecycle log
    open_fvgs = []      # indices into fvgs still PENDING/ACTIVE

    balance = STARTING_BALANCE
    equity_curve = []   # (time, balance)
    trades_today = 0

    annotations = {"day_lines": [], "cutoff_lines": [], "sweeps": [], "mss_lines": []}

    cur_day = None

    def reset_day(day_date):
        nonlocal day_high, day_low, day_range_locked, cutoff_idx
        nonlocal sweep_found, sweep_is_sell, sweep_idx
        nonlocal mss_found, mss_level, mss_fractal_idx, mss_confirmed, mss_invalidated
        nonlocal fvg_search_closed, fvg_seq, open_fvgs, trades_today, day_start_idx
        day_high, day_low = -np.inf, np.inf
        day_range_locked = False
        cutoff_idx = None
        sweep_found, sweep_is_sell, sweep_idx = False, False, None
        mss_found, mss_level, mss_fractal_idx = False, None, None
        mss_confirmed, mss_invalidated = False, False
        fvg_search_closed = False
        fvg_seq = 0
        open_fvgs = []
        trades_today = 0
        day_start_idx = i

    for i in range(n):
        t = times[i]
        day_date = t.normalize()
        if day_date != cur_day:
            if cur_day is not None and day_range_locked:
                annotations["day_lines"].append((cur_day, day_high, day_low,
                                                  cur_day + pd.Timedelta(hours=CUTOFF_HOUR_UTC, minutes=CUTOFF_MIN_UTC)))
                if mss_found:
                    annotations["mss_lines"].append((times[mss_fractal_idx], t, mss_level,
                                                      sweep_is_sell, mss_confirmed))
            cur_day = day_date
            reset_day(day_date)

        cutoff_dt = day_date + pd.Timedelta(hours=CUTOFF_HOUR_UTC, minutes=CUTOFF_MIN_UTC)

        if not day_range_locked:
            if h[i] > day_high: day_high = h[i]
            if l[i] < day_low: day_low = l[i]
            if t >= cutoff_dt:
                day_range_locked = True
                cutoff_idx = i
            equity_curve.append((t, balance))
            continue

        # ---- liquidity sweep (first of the day only) ------------------
        if not sweep_found and (i - cutoff_idx) <= MAX_SWEEP_CANDLES:
            swept_high = h[i] > day_high and day_low <= c[i] <= day_high
            swept_low = l[i] < day_low and day_low <= c[i] <= day_high
            if swept_high:
                sweep_found, sweep_is_sell, sweep_idx = True, True, i
                annotations["sweeps"].append((t, h[i], True))
            elif swept_low:
                sweep_found, sweep_is_sell, sweep_idx = True, False, i
                annotations["sweeps"].append((t, l[i], False))

        # ---- market structure shift: most recent fractal before sweep --
        if sweep_found and not mss_found:
            k = FRACTAL_STRENGTH
            lo_bound = max(day_start_idx, sweep_idx - MSS_LOOKBACK_CANDLES)
            for p in range(sweep_idx - 1, lo_bound - 1, -1):
                if p - k < day_start_idx or p + k > i:
                    continue
                if sweep_is_sell:
                    if is_fractal_high(h, p, k) and day_low <= h[p] <= day_high:
                        mss_found, mss_level, mss_fractal_idx = True, h[p], p
                        break
                else:
                    if is_fractal_low(l, p, k) and day_low <= l[p] <= day_high:
                        mss_found, mss_level, mss_fractal_idx = True, l[p], p
                        break

        # ---- MSS confirmation (close through the level) ---------------
        if mss_found and not mss_confirmed and not mss_invalidated and i > sweep_idx:
            closed_through = (c[i] < mss_level) if sweep_is_sell else (c[i] > mss_level)
            if closed_through:
                mss_confirmed = True
            elif MSS_CONFIRM_MAX_CANDLES > 0 and (i - sweep_idx) > MSS_CONFIRM_MAX_CANDLES:
                mss_invalidated = True
                fvg_search_closed = True

        # ---- FVG detection (3-candle gap, scoped to day range/ATR) -----
        if mss_confirmed and not fvg_search_closed and i >= 2:
            want_bull = not sweep_is_sell
            i2, i0 = i - 2, i
            if i2 >= sweep_idx:
                a = atr[i] if not np.isnan(atr[i]) else 0
                min_size = a * FVG_MIN_ATR_MULT if FVG_MIN_ATR_MULT > 0 else 0
                max_size = a * FVG_MAX_ATR_MULT if FVG_MAX_ATR_MULT > 0 else np.inf
                gap = None
                if want_bull and h[i2] < l[i0]:
                    gap = (h[i2], l[i0], True)
                elif not want_bull and l[i2] > h[i0]:
                    gap = (h[i0], l[i2], False)
                if gap:
                    lower, upper, is_bull = gap
                    width = upper - lower
                    overlaps_day = not (lower > day_high or upper < day_low)
                    if min_size <= width <= max_size and overlaps_day and trades_today < MAX_TRADES_PER_DAY * 3:
                        mid_time = times[i - 1]
                        if not any(f["created_time"] == mid_time for f in fvgs):
                            fvg = dict(is_bull=is_bull, upper=upper, lower=lower,
                                       mid=(upper + lower) / 2, created_time=mid_time,
                                       created_idx=i - 1, state="PENDING", sequence=fvg_seq,
                                       entry=None, sl=None, tp=None, risk=None,
                                       trigger_time=None, exit_time=None, exit_price=None,
                                       outcome_r=None)
                            fvg_seq += 1
                            fvgs.append(fvg)
                            open_fvgs.append(len(fvgs) - 1)

        # ---- activation / trigger / invalidation / exit ----------------
        still_open = []
        for fi in open_fvgs:
            f = fvgs[fi]
            if f["state"] == "PENDING":
                mid_hit = (l[i] <= f["mid"] <= h[i])
                if mid_hit:
                    width = f["upper"] - f["lower"]
                    buf = width * SL_BUFFER_WIDTH_MULT
                    if f["is_bull"]:
                        f["entry"] = f["upper"]
                        f["sl"] = f["lower"] - buf
                    else:
                        f["entry"] = f["lower"]
                        f["sl"] = f["upper"] + buf
                    dist = abs(f["entry"] - f["sl"])
                    f["tp"] = f["entry"] + dist * RISK_REWARD if f["is_bull"] else f["entry"] - dist * RISK_REWARD
                    f["risk"] = balance * (RISK_PCT * (RISK_DECAY ** f["sequence"])) / 100.0
                    f["state"] = "ACTIVE"

            if f["state"] == "ACTIVE":
                broken = (c[i] < f["lower"]) if f["is_bull"] else (c[i] > f["upper"])
                triggered = (h[i] >= f["entry"]) if f["is_bull"] else (l[i] <= f["entry"])
                if triggered and trades_today < MAX_TRADES_PER_DAY:
                    f["state"] = "TRIGGERED"
                    f["trigger_time"] = t
                    trades_today += 1
                elif broken:
                    f["state"] = "INVALIDATED"
                    f["exit_time"] = t

            if f["state"] == "TRIGGERED":
                hit_sl = (l[i] <= f["sl"]) if f["is_bull"] else (h[i] >= f["sl"])
                hit_tp = (h[i] >= f["tp"]) if f["is_bull"] else (l[i] <= f["tp"])
                if hit_sl and hit_tp:
                    hit_sl, hit_tp = True, False  # conservative: assume SL hit first
                if hit_sl or hit_tp:
                    outcome_r = -1.0 if hit_sl else RISK_REWARD
                    f["outcome_r"] = outcome_r
                    f["exit_price"] = f["sl"] if hit_sl else f["tp"]
                    f["exit_time"] = t
                    balance += f["risk"] * outcome_r
                    f["state"] = "CLOSED"

            if f["state"] not in ("CLOSED", "INVALIDATED", "EXPIRED"):
                still_open.append(fi)
        open_fvgs = still_open

        # ---- day-end expiry for anything still dangling -----------------
        is_last_bar_of_day = (i == n - 1) or (times[i + 1].normalize() != day_date)
        if is_last_bar_of_day:
            for fi in open_fvgs:
                f = fvgs[fi]
                if f["state"] in ("PENDING", "ACTIVE"):
                    f["state"] = "EXPIRED"
                    f["exit_time"] = t
            open_fvgs = []

        equity_curve.append((t, balance))

    if cur_day is not None and day_range_locked:
        annotations["day_lines"].append((cur_day, day_high, day_low,
                                          cur_day + pd.Timedelta(hours=CUTOFF_HOUR_UTC, minutes=CUTOFF_MIN_UTC)))

    return fvgs, annotations, equity_curve, balance


# ------------------------------------------------------------------
def build_chart(df, fvgs, annotations, equity_curve, final_balance):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color="#00e676", decreasing_line_color="#ff1744",
        increasing_fillcolor="#00e676", decreasing_fillcolor="#ff1744",
        name="BTCUSDT 5m"))

    for day, dhigh, dlow, cutoff in annotations["day_lines"]:
        day_end = day + pd.Timedelta(hours=23, minutes=59)
        fig.add_shape(type="line", x0=day, x1=day_end, y0=dhigh, y1=dhigh,
                      line=dict(color="gold", dash="dash", width=1))
        fig.add_shape(type="line", x0=day, x1=day_end, y0=dlow, y1=dlow,
                      line=dict(color="gold", dash="dash", width=1))
        fig.add_shape(type="line", x0=cutoff, x1=cutoff, y0=dlow, y1=dhigh,
                      line=dict(color="gold", dash="dash", width=1))

    sweep_up_x, sweep_up_y, sweep_dn_x, sweep_dn_y = [], [], [], []
    for tt, price, is_high_sweep in annotations["sweeps"]:
        if is_high_sweep:
            sweep_dn_x.append(tt); sweep_dn_y.append(price)
        else:
            sweep_up_x.append(tt); sweep_up_y.append(price)
    fig.add_trace(go.Scatter(x=sweep_dn_x, y=sweep_dn_y, mode="markers",
                              marker=dict(symbol="triangle-down", size=12, color="red"),
                              name="Sweep (day high)"))
    fig.add_trace(go.Scatter(x=sweep_up_x, y=sweep_up_y, mode="markers",
                              marker=dict(symbol="triangle-up", size=12, color="lime"),
                              name="Sweep (day low)"))

    for t1, t2, level, is_sell, confirmed in annotations["mss_lines"]:
        fig.add_shape(type="line", x0=t1, x1=t2, y0=level, y1=level,
                      line=dict(color="dodgerblue", dash="dash", width=1))
        label = ("MSS Sell " if is_sell else "MSS Buy ") + ("Confirmed" if confirmed else "Unconfirmed")
        fig.add_annotation(x=t1, y=level, text=label, showarrow=False,
                            font=dict(color="dodgerblue", size=9), yshift=10, xanchor="left")

    for f in fvgs:
        end_t = f["exit_time"] if f["exit_time"] else df.index[-1]
        color = INVALID_COLOR if f["state"] in ("INVALIDATED", "EXPIRED") else (BULL_COLOR if f["is_bull"] else BEAR_COLOR)
        fig.add_shape(type="rect", x0=f["created_time"], x1=end_t, y0=f["lower"], y1=f["upper"],
                      fillcolor=color, line=dict(width=0), layer="below")

    win_x, win_y, loss_x, loss_y, entry_x, entry_y = [], [], [], [], [], []
    for f in fvgs:
        if f["state"] == "CLOSED":
            entry_x.append(f["trigger_time"]); entry_y.append(f["entry"])
            if f["outcome_r"] > 0:
                win_x.append(f["exit_time"]); win_y.append(f["exit_price"])
            else:
                loss_x.append(f["exit_time"]); loss_y.append(f["exit_price"])
    fig.add_trace(go.Scatter(x=entry_x, y=entry_y, mode="markers",
                              marker=dict(symbol="circle", size=8, color="white", line=dict(color="black", width=1)),
                              name="Entry"))
    fig.add_trace(go.Scatter(x=win_x, y=win_y, mode="markers",
                              marker=dict(symbol="star", size=11, color="#00e676"),
                              name="TP hit"))
    fig.add_trace(go.Scatter(x=loss_x, y=loss_y, mode="markers",
                              marker=dict(symbol="x", size=10, color="#ff1744"),
                              name="SL hit"))

    closed = [f for f in fvgs if f["state"] == "CLOSED"]
    wins = [f for f in closed if f["outcome_r"] > 0]
    total_r = sum(f["outcome_r"] for f in closed)
    win_rate = (len(wins) / len(closed) * 100) if closed else 0
    summary = (f"Trades: {len(closed)} | Win rate: {win_rate:.1f}% | Total R: {total_r:+.2f} | "
               f"Balance: ${STARTING_BALANCE:,.0f} -> ${final_balance:,.0f} "
               f"({(final_balance / STARTING_BALANCE - 1) * 100:+.2f}%)")

    fig.update_layout(
        title=f"ICT FVG Silver Bullet - {SYMBOL} 5m (Delta Exchange)<br><sub>{summary}</sub>",
        template="plotly_dark",
        xaxis_rangeslider_visible=True,
        height=850,
        legend=dict(orientation="h", y=1.05),
    )
    return fig, summary


def main():
    df = load_data()
    fvgs, annotations, equity_curve, final_balance = run_backtest(df)
    fig, summary = build_chart(df, fvgs, annotations, equity_curve, final_balance)

    out_html = "/home/user/tvs-motor-anallytics/backtest/ict_silver_bullet_btcusdt.html"
    fig.write_html(out_html, include_plotlyjs="cdn")

    trades = pd.DataFrame([f for f in fvgs if f["state"] in ("CLOSED", "INVALIDATED", "EXPIRED")])
    trades.to_csv("/home/user/tvs-motor-anallytics/backtest/trades.csv", index=False)

    eq = pd.DataFrame(equity_curve, columns=["time", "balance"]).drop_duplicates("time")
    eq.to_csv("/home/user/tvs-motor-anallytics/backtest/equity_curve.csv", index=False)

    print(summary)
    print(f"Chart written to {out_html}")
    print(f"Candles analyzed: {len(df)} ({df.index.min()} -> {df.index.max()})")
    print(f"Total FVGs detected: {len(fvgs)}")


if __name__ == "__main__":
    main()

"""ICT Optimal Trade Entry (OTE) backtest against real BTCUSDT data from Delta
Exchange.

Concept: after a displacement leg confirms a break of structure (BOS), price
frequently doesn't reverse all the way back to the leg's origin -- it retraces
into the 61.8%-79% Fibonacci zone of that leg (the "OTE zone") before
continuing in the direction of the break. That zone is treated as a
discounted/premium re-entry into the move, not a reversal trade like Judas
Swing or Turtle Soup.

This is continuous (no day/session scoping), same as Order Block:

  1. STRUCTURE   - track the most recent unbroken fractal swing high/low
                   (FRACTAL_STRENGTH bars on each side), exactly like
                   run_order_block.py.
  2. BOS         - a close beyond that fractal level starts a displacement
                   leg. Origin = the opposite swing extreme that preceded the
                   break (the leg's structural start). Destination starts as
                   the breakout bar's extreme.
  3. EXTEND      - causally extend the destination forward one bar at a time
                   for as long as new highs/lows keep printing. The first bar
                   that fails to extend further finalizes the leg -- no
                   lookahead, the leg is "done" the moment momentum stalls.
  4. OTE ZONE    - fib_618/fib_79 retracement of the finalized leg becomes a
                   resting zone: [fib_79, fib_618] for a bullish leg (mirrored
                   for bearish). Entry at the shallow edge (fib_618) on touch,
                   same proximal-edge convention as the Order Block scripts.
  5. INVALIDATION - a close back through the leg's origin before the zone is
                   touched means the structure failed -- cancel the setup.
                   Untouched zones also expire after OTE_EXPIRE_CANDLES.
  6. EXIT        - stop beyond the origin (+ ATR buffer), fixed R:R target,
                   same mechanics as Order Block/Breaker for comparability.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ict_common import load_data, is_fractal_high, is_fractal_low, resolve_sl_tp, summarize

SYMBOL = "BTCUSDT"
RESOLUTION = "5m"
LOOKBACK_DAYS = 30

FRACTAL_STRENGTH = 2
OTE_EXPIRE_CANDLES = 288     # ~1 day @5m -- untouched zones go stale

FIB_SHALLOW = 0.618          # proximal edge -- entry trigger
FIB_DEEP = 0.79              # distal edge -- zone boundary

ATR_PERIOD = 100
SL_BUFFER_ATR_MULT = 0.25
RISK_REWARD = 2.0
RISK_PCT = 1.0
MAX_CONCURRENT = 3

STARTING_BALANCE = 10_000.0

BULL_COLOR = "rgba(0,230,118,0.30)"
BEAR_COLOR = "rgba(255,20,147,0.30)"
INVALID_COLOR = "rgba(128,128,128,0.25)"


def run_backtest(df: pd.DataFrame):
    n = len(df)
    o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    atr = df["atr"].values
    times = df.index
    k = FRACTAL_STRENGTH

    last_fh_level, last_fh_idx, fh_broken = None, None, True
    last_fl_level, last_fl_idx, fl_broken = None, None, True

    leg = None          # in-progress displacement leg being causally extended
    zones = []           # full lifecycle log of finalized OTE zones
    open_zones = []       # indices into zones still PENDING/ACTIVE

    balance = STARTING_BALANCE
    equity_curve = []
    trades_open = 0

    for i in range(n):
        t = times[i]

        # ---- update most recent confirmable fractal (needs k bars after it)
        p = i - k
        if p >= k:
            if is_fractal_high(h, p, k):
                last_fh_level, last_fh_idx, fh_broken = h[p], p, False
            if is_fractal_low(l, p, k):
                last_fl_level, last_fl_idx, fl_broken = l[p], p, False

        # ---- extend the in-progress leg, finalize the moment it stalls ----
        if leg is not None:
            if leg["is_bull"]:
                if h[i] > leg["dest"]:
                    leg["dest"] = h[i]
                    leg["dest_idx"] = i
                else:
                    leg_dist = leg["dest"] - leg["origin"]
                    fib618 = leg["dest"] - leg_dist * FIB_SHALLOW
                    fib79 = leg["dest"] - leg_dist * FIB_DEEP
                    zones.append(dict(is_bull=True, origin=leg["origin"], dest=leg["dest"],
                                       created_time=times[leg["dest_idx"]], created_idx=leg["dest_idx"],
                                       fib618=fib618, fib79=fib79, state="PENDING", entry=None, sl=None,
                                       tp=None, risk=None, trigger_time=None, exit_time=None,
                                       exit_price=None, outcome_r=None))
                    open_zones.append(len(zones) - 1)
                    leg = None
            else:
                if l[i] < leg["dest"]:
                    leg["dest"] = l[i]
                    leg["dest_idx"] = i
                else:
                    leg_dist = leg["origin"] - leg["dest"]
                    fib618 = leg["dest"] + leg_dist * FIB_SHALLOW
                    fib79 = leg["dest"] + leg_dist * FIB_DEEP
                    zones.append(dict(is_bull=False, origin=leg["origin"], dest=leg["dest"],
                                       created_time=times[leg["dest_idx"]], created_idx=leg["dest_idx"],
                                       fib618=fib618, fib79=fib79, state="PENDING", entry=None, sl=None,
                                       tp=None, risk=None, trigger_time=None, exit_time=None,
                                       exit_price=None, outcome_r=None))
                    open_zones.append(len(zones) - 1)
                    leg = None

        # ---- break of structure -> start a new displacement leg -----------
        if leg is None and last_fh_level is not None and not fh_broken and c[i] > last_fh_level and last_fl_level is not None:
            fh_broken = True
            leg = dict(is_bull=True, origin=last_fl_level, dest=h[i], dest_idx=i)

        if leg is None and last_fl_level is not None and not fl_broken and c[i] < last_fl_level and last_fh_level is not None:
            fl_broken = True
            leg = dict(is_bull=False, origin=last_fh_level, dest=l[i], dest_idx=i)

        # ---- manage every tracked OTE zone --------------------------------
        still_open = []
        for zi in open_zones:
            z = zones[zi]
            if z["state"] == "PENDING":
                touched = (l[i] <= z["fib618"]) if z["is_bull"] else (h[i] >= z["fib618"])
                invalidated = (c[i] < z["origin"]) if z["is_bull"] else (c[i] > z["origin"])
                if invalidated and i > z["created_idx"]:
                    z["state"] = "INVALIDATED"
                    z["exit_time"] = t
                elif touched and i > z["created_idx"]:
                    buf = atr[i] * SL_BUFFER_ATR_MULT if not np.isnan(atr[i]) else 0
                    if z["is_bull"]:
                        z["entry"] = z["fib618"]
                        z["sl"] = z["origin"] - buf
                    else:
                        z["entry"] = z["fib618"]
                        z["sl"] = z["origin"] + buf
                    dist = abs(z["entry"] - z["sl"])
                    z["tp"] = z["entry"] + dist * RISK_REWARD if z["is_bull"] else z["entry"] - dist * RISK_REWARD
                    z["state"] = "ACTIVE"
                elif (i - z["created_idx"]) > OTE_EXPIRE_CANDLES:
                    z["state"] = "EXPIRED"
                    z["exit_time"] = t

            if z["state"] == "ACTIVE":
                invalidated = (c[i] < z["origin"]) if z["is_bull"] else (c[i] > z["origin"])
                if invalidated:
                    z["state"] = "INVALIDATED"
                    z["exit_time"] = t
                elif trades_open < MAX_CONCURRENT:
                    z["state"] = "TRIGGERED"
                    z["trigger_time"] = t
                    z["risk"] = balance * RISK_PCT / 100.0
                    trades_open += 1
                elif (i - z["created_idx"]) > OTE_EXPIRE_CANDLES:
                    z["state"] = "EXPIRED"
                    z["exit_time"] = t

            if z["state"] == "TRIGGERED":
                hit_sl, hit_tp = resolve_sl_tp(h, l, i, z["is_bull"], z["sl"], z["tp"])
                if hit_sl or hit_tp:
                    outcome_r = -1.0 if hit_sl else RISK_REWARD
                    z["outcome_r"] = outcome_r
                    z["exit_price"] = z["sl"] if hit_sl else z["tp"]
                    z["exit_time"] = t
                    balance += z["risk"] * outcome_r
                    z["state"] = "CLOSED"
                    trades_open -= 1

            if z["state"] not in ("CLOSED", "INVALIDATED", "EXPIRED"):
                still_open.append(zi)
        open_zones = still_open

        equity_curve.append((t, balance))

    return zones, equity_curve, balance


def build_chart(df, zones, equity_curve, final_balance):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color="#00e676", decreasing_line_color="#ff1744",
        increasing_fillcolor="#00e676", decreasing_fillcolor="#ff1744",
        name=f"{SYMBOL} {RESOLUTION}"))

    for z in zones:
        end_t = z["exit_time"] if z["exit_time"] else df.index[-1]
        color = INVALID_COLOR if z["state"] in ("INVALIDATED", "EXPIRED") else (BULL_COLOR if z["is_bull"] else BEAR_COLOR)
        y0, y1 = (z["fib79"], z["fib618"]) if z["is_bull"] else (z["fib618"], z["fib79"])
        fig.add_shape(type="rect", x0=z["created_time"], x1=end_t, y0=y0, y1=y1,
                      fillcolor=color, line=dict(width=0), layer="below")

    entry_x, entry_y, win_x, win_y, loss_x, loss_y = [], [], [], [], [], []
    for z in zones:
        if z["state"] == "CLOSED":
            entry_x.append(z["trigger_time"]); entry_y.append(z["entry"])
            if z["outcome_r"] > 0:
                win_x.append(z["exit_time"]); win_y.append(z["exit_price"])
            else:
                loss_x.append(z["exit_time"]); loss_y.append(z["exit_price"])
    fig.add_trace(go.Scatter(x=entry_x, y=entry_y, mode="markers",
                              marker=dict(symbol="circle", size=8, color="white", line=dict(color="black", width=1)),
                              name="Entry"))
    fig.add_trace(go.Scatter(x=win_x, y=win_y, mode="markers",
                              marker=dict(symbol="star", size=11, color="#00e676"), name="Win"))
    fig.add_trace(go.Scatter(x=loss_x, y=loss_y, mode="markers",
                              marker=dict(symbol="x", size=10, color="#ff1744"), name="Loss"))

    closed = [z for z in zones if z["state"] == "CLOSED"]
    summary = summarize(closed, STARTING_BALANCE, final_balance)
    fig.update_layout(
        title=f"ICT Optimal Trade Entry (OTE) - {SYMBOL} {RESOLUTION} (Delta Exchange)<br><sub>{summary}</sub>",
        template="plotly_dark",
        xaxis_rangeslider_visible=True,
        height=850,
        legend=dict(orientation="h", y=1.05),
    )
    return fig, summary


def main():
    df = load_data(SYMBOL, RESOLUTION, LOOKBACK_DAYS, ATR_PERIOD)
    zones, equity_curve, final_balance = run_backtest(df)
    fig, summary = build_chart(df, zones, equity_curve, final_balance)

    out_html = "/home/user/tvs-motor-anallytics/backtest/ict_ote_btcusdt.html"
    fig.write_html(out_html, include_plotlyjs="cdn")

    pd.DataFrame(zones).to_csv("/home/user/tvs-motor-anallytics/backtest/ote_trades.csv", index=False)
    eq = pd.DataFrame(equity_curve, columns=["time", "balance"]).drop_duplicates("time")
    eq.to_csv("/home/user/tvs-motor-anallytics/backtest/ote_equity_curve.csv", index=False)

    print(summary)
    print(f"Chart written to {out_html}")
    print(f"Candles analyzed: {len(df)} ({df.index.min()} -> {df.index.max()})")
    print(f"Total OTE zones detected: {len(zones)}")


if __name__ == "__main__":
    main()

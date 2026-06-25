"""ICT Order Block backtest against real BTCUSDT data from Delta Exchange.

Concept: the last opposite-colored candle right before a structural break is
the "order block" -- the footprint of the institutional orders that fueled
the move. A bullish order block is the last *down*-close candle before price
breaks above a recent swing high (a bullish break of structure); a bearish
order block is the last *up*-close candle before price breaks below a recent
swing low. The trade is the retracement back into that candle's range after
the break -- price tends to react there on the way to continuing the move.

Unlike the other scripts in this directory, Order Block is not session/day
scoped -- swing structure and its order blocks persist across day boundaries,
so this runs as one continuous scan over the whole dataset:

  1. STRUCTURE  - track the most recent unbroken fractal swing high/low
                  (FRACTAL_STRENGTH bars on each side).
  2. BOS        - a close beyond that fractal level is a break of structure.
  3. ORDER BLOCK - scan backward up to OB_LOOKBACK_CANDLES from the BOS bar
                  for the last opposite-colored candle; that candle's
                  high-low range is the order block zone.
  4. ENTRY      - resting limit order at the zone's proximal edge (closest
                  to the price that broke away from it). Stop beyond the
                  zone's distal edge (+ ATR buffer). Fixed R:R target.
  5. INVALIDATION - a close fully through the distal edge before being
                  triggered cancels the setup. Untouched zones also expire
                  after OB_EXPIRE_CANDLES so old, stale zones stop cluttering
                  the backtest.
  6. RISK       - flat per-trade risk, capped at MAX_CONCURRENT open trades
                  at once (order blocks can stack up during a trend).
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ict_common import load_data, is_fractal_high, is_fractal_low, resolve_sl_tp, summarize

SYMBOL = "BTCUSDT"
RESOLUTION = "5m"
LOOKBACK_DAYS = 30

FRACTAL_STRENGTH = 2
OB_LOOKBACK_CANDLES = 10     # how far back from the BOS bar to look for the opposite candle
OB_EXPIRE_CANDLES = 288      # ~1 day @5m -- untouched zones go stale

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

    obs = []           # full lifecycle log
    open_obs = []      # indices into obs still PENDING/ACTIVE
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

        # ---- break of structure -> new order block --------------------
        if last_fh_level is not None and not fh_broken and c[i] > last_fh_level:
            fh_broken = True
            lo_bound = max(last_fh_idx + 1, i - OB_LOOKBACK_CANDLES)
            for p2 in range(i - 1, lo_bound - 1, -1):
                if c[p2] < o[p2]:
                    obs.append(dict(is_bull=True, upper=h[p2], lower=l[p2], created_time=times[p2],
                                     created_idx=p2, bos_time=t, state="PENDING", entry=None, sl=None,
                                     tp=None, risk=None, trigger_time=None, exit_time=None,
                                     exit_price=None, outcome_r=None))
                    open_obs.append(len(obs) - 1)
                    break

        if last_fl_level is not None and not fl_broken and c[i] < last_fl_level:
            fl_broken = True
            lo_bound = max(last_fl_idx + 1, i - OB_LOOKBACK_CANDLES)
            for p2 in range(i - 1, lo_bound - 1, -1):
                if c[p2] > o[p2]:
                    obs.append(dict(is_bull=False, upper=h[p2], lower=l[p2], created_time=times[p2],
                                     created_idx=p2, bos_time=t, state="PENDING", entry=None, sl=None,
                                     tp=None, risk=None, trigger_time=None, exit_time=None,
                                     exit_price=None, outcome_r=None))
                    open_obs.append(len(obs) - 1)
                    break

        # ---- manage every tracked order block --------------------------
        still_open = []
        for oi in open_obs:
            ob = obs[oi]
            if ob["state"] == "PENDING":
                touched = (l[i] <= ob["upper"]) if ob["is_bull"] else (h[i] >= ob["lower"])
                if touched and i > ob["created_idx"]:
                    buf = atr[i] * SL_BUFFER_ATR_MULT if not np.isnan(atr[i]) else 0
                    if ob["is_bull"]:
                        ob["entry"] = ob["upper"]
                        ob["sl"] = ob["lower"] - buf
                    else:
                        ob["entry"] = ob["lower"]
                        ob["sl"] = ob["upper"] + buf
                    dist = abs(ob["entry"] - ob["sl"])
                    ob["tp"] = ob["entry"] + dist * RISK_REWARD if ob["is_bull"] else ob["entry"] - dist * RISK_REWARD
                    ob["state"] = "ACTIVE"
                elif (i - ob["created_idx"]) > OB_EXPIRE_CANDLES:
                    ob["state"] = "EXPIRED"
                    ob["exit_time"] = t

            if ob["state"] == "ACTIVE":
                broken = (c[i] < ob["lower"]) if ob["is_bull"] else (c[i] > ob["upper"])
                triggered = (h[i] >= ob["entry"]) if ob["is_bull"] else (l[i] <= ob["entry"])
                if triggered and trades_open < MAX_CONCURRENT:
                    ob["state"] = "TRIGGERED"
                    ob["trigger_time"] = t
                    ob["risk"] = balance * RISK_PCT / 100.0
                    trades_open += 1
                elif broken:
                    ob["state"] = "INVALIDATED"
                    ob["exit_time"] = t
                elif (i - ob["created_idx"]) > OB_EXPIRE_CANDLES:
                    ob["state"] = "EXPIRED"
                    ob["exit_time"] = t

            if ob["state"] == "TRIGGERED":
                hit_sl, hit_tp = resolve_sl_tp(h, l, i, ob["is_bull"], ob["sl"], ob["tp"])
                if hit_sl or hit_tp:
                    outcome_r = -1.0 if hit_sl else RISK_REWARD
                    ob["outcome_r"] = outcome_r
                    ob["exit_price"] = ob["sl"] if hit_sl else ob["tp"]
                    ob["exit_time"] = t
                    balance += ob["risk"] * outcome_r
                    ob["state"] = "CLOSED"
                    trades_open -= 1

            if ob["state"] not in ("CLOSED", "INVALIDATED", "EXPIRED"):
                still_open.append(oi)
        open_obs = still_open

        equity_curve.append((t, balance))

    return obs, equity_curve, balance


def build_chart(df, obs, equity_curve, final_balance):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color="#00e676", decreasing_line_color="#ff1744",
        increasing_fillcolor="#00e676", decreasing_fillcolor="#ff1744",
        name=f"{SYMBOL} {RESOLUTION}"))

    for ob in obs:
        end_t = ob["exit_time"] if ob["exit_time"] else df.index[-1]
        color = INVALID_COLOR if ob["state"] in ("INVALIDATED", "EXPIRED") else (BULL_COLOR if ob["is_bull"] else BEAR_COLOR)
        fig.add_shape(type="rect", x0=ob["created_time"], x1=end_t, y0=ob["lower"], y1=ob["upper"],
                      fillcolor=color, line=dict(width=0), layer="below")

    entry_x, entry_y, win_x, win_y, loss_x, loss_y = [], [], [], [], [], []
    for ob in obs:
        if ob["state"] == "CLOSED":
            entry_x.append(ob["trigger_time"]); entry_y.append(ob["entry"])
            if ob["outcome_r"] > 0:
                win_x.append(ob["exit_time"]); win_y.append(ob["exit_price"])
            else:
                loss_x.append(ob["exit_time"]); loss_y.append(ob["exit_price"])
    fig.add_trace(go.Scatter(x=entry_x, y=entry_y, mode="markers",
                              marker=dict(symbol="circle", size=8, color="white", line=dict(color="black", width=1)),
                              name="Entry"))
    fig.add_trace(go.Scatter(x=win_x, y=win_y, mode="markers",
                              marker=dict(symbol="star", size=11, color="#00e676"), name="Win"))
    fig.add_trace(go.Scatter(x=loss_x, y=loss_y, mode="markers",
                              marker=dict(symbol="x", size=10, color="#ff1744"), name="Loss"))

    closed = [ob for ob in obs if ob["state"] == "CLOSED"]
    summary = summarize(closed, STARTING_BALANCE, final_balance)
    fig.update_layout(
        title=f"ICT Order Block - {SYMBOL} {RESOLUTION} (Delta Exchange)<br><sub>{summary}</sub>",
        template="plotly_dark",
        xaxis_rangeslider_visible=True,
        height=850,
        legend=dict(orientation="h", y=1.05),
    )
    return fig, summary


def main():
    df = load_data(SYMBOL, RESOLUTION, LOOKBACK_DAYS, ATR_PERIOD)
    obs, equity_curve, final_balance = run_backtest(df)
    fig, summary = build_chart(df, obs, equity_curve, final_balance)

    out_html = "/home/user/tvs-motor-anallytics/backtest/ict_order_block_btcusdt.html"
    fig.write_html(out_html, include_plotlyjs="cdn")

    pd.DataFrame(obs).to_csv("/home/user/tvs-motor-anallytics/backtest/order_block_trades.csv", index=False)
    eq = pd.DataFrame(equity_curve, columns=["time", "balance"]).drop_duplicates("time")
    eq.to_csv("/home/user/tvs-motor-anallytics/backtest/order_block_equity_curve.csv", index=False)

    print(summary)
    print(f"Chart written to {out_html}")
    print(f"Candles analyzed: {len(df)} ({df.index.min()} -> {df.index.max()})")
    print(f"Total order blocks detected: {len(obs)}")


if __name__ == "__main__":
    main()

"""ICT Turtle Soup backtest against real BTCUSDT data from Delta Exchange.

Concept (adapted by ICT from Larry Williams): a "breakout" beyond a recent
well-known liquidity reference -- here, the previous day's high or low (PDH
/ PDL) -- that fails and snaps back inside the prior range is itself the
signal, not the breakout. Stops resting just beyond PDH/PDL get run, the
breakout traders who chased it get trapped, and price reverses.

This is deliberately simpler and faster-firing than the Silver Bullet/Judas
Swing scripts in this directory:
  - No kill-zone time restriction -- a failed breakout of PDH/PDL can occur
    any time of day.
  - No fractal-based market structure shift -- confirmation is just a close
    back on the other side of the swept level within a short window. Turtle
    Soup is meant to be a *fast* reversal; if it takes too long to reclaim
    the level, the "soup" thesis is wrong and the setup is abandoned.
  - Multiple sweep attempts are allowed per day (PDH/PDL can get poked more
    than once before a real failed-breakout reversal shows up); only after
    an actual trade is taken does the day stop looking for new setups.

Per UTC day:
  1. PDH/PDL = previous calendar day's high/low, locked at midnight UTC.
  2. SWEEP    - first candle (since the last reset) that trades beyond PDH
                or PDL.
  3. CONFIRM  - within CONFIRM_MAX_CANDLES, a close back on the inside of
                that level. If it doesn't happen in time, re-arm and keep
                watching for the next sweep attempt that day.
  4. ENTRY    - market entry at the confirmation candle's close, reversal
                direction. Stop beyond the sweep candle's extreme (+ ATR
                buffer). Target a fixed R:R, same as the other scripts here.
  5. EXIT     - SL/TP, or mark-to-market close at day's last candle if
                neither is hit.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ict_common import load_data, resolve_sl_tp, summarize

SYMBOL = "BTCUSDT"
RESOLUTION = "5m"
LOOKBACK_DAYS = 30

CONFIRM_MAX_CANDLES = 6     # 30min @5m -- a failed breakout reverses fast or it isn't one
ATR_PERIOD = 100
SL_BUFFER_ATR_MULT = 0.25
RISK_REWARD = 2.0
RISK_PCT = 1.0
MAX_TRADES_PER_DAY = 1

STARTING_BALANCE = 10_000.0


def run_backtest(df: pd.DataFrame):
    n = len(df)
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    atr = df["atr"].values
    times = df.index

    cur_day = None
    day_high, day_low = -np.inf, np.inf   # accumulates *this* day's range, becomes tomorrow's PDH/PDL
    pdh, pdl = None, None                  # locked at the start of each day from the prior day's range

    sweep_found = False
    sweep_is_sell = False
    sweep_idx = None
    trade = None
    trades_today = 0

    trades = []
    balance = STARTING_BALANCE
    equity_curve = []
    annotations = {"pd_lines": [], "sweeps": []}

    def reset_sweep_state():
        nonlocal sweep_found, sweep_is_sell, sweep_idx
        sweep_found, sweep_is_sell, sweep_idx = False, False, None

    for i in range(n):
        t = times[i]
        day_date = t.normalize()
        if day_date != cur_day:
            if pdh is not None:
                annotations["pd_lines"].append((cur_day, day_date, pdh, pdl))
            pdh, pdl = day_high, day_low
            day_high, day_low = -np.inf, np.inf
            cur_day = day_date
            reset_sweep_state()
            trade = None
            trades_today = 0

        if h[i] > day_high: day_high = h[i]
        if l[i] < day_low: day_low = l[i]

        if pdh is not None and trades_today < MAX_TRADES_PER_DAY:
            # ---- sweep detection (re-arms after a failed/expired attempt) --
            if not sweep_found:
                swept_high = h[i] > pdh
                swept_low = l[i] < pdl
                if swept_high and not swept_low:
                    sweep_found, sweep_is_sell, sweep_idx = True, True, i
                    annotations["sweeps"].append((t, h[i], True))
                elif swept_low and not swept_high:
                    sweep_found, sweep_is_sell, sweep_idx = True, False, i
                    annotations["sweeps"].append((t, l[i], False))

            # ---- confirmation: close back inside the prior range -----------
            elif trade is None and i > sweep_idx:
                closed_back = (c[i] < pdh) if sweep_is_sell else (c[i] > pdl)
                if closed_back:
                    is_bull = not sweep_is_sell
                    entry = c[i]
                    buf = atr[i] * SL_BUFFER_ATR_MULT if not np.isnan(atr[i]) else 0
                    sl = (l[sweep_idx] - buf) if is_bull else (h[sweep_idx] + buf)
                    dist = abs(entry - sl)
                    tp = entry + dist * RISK_REWARD if is_bull else entry - dist * RISK_REWARD
                    risk = balance * RISK_PCT / 100.0
                    trade = dict(is_bull=is_bull, sweep_time=times[sweep_idx], entry=entry, sl=sl, tp=tp,
                                 risk=risk, entry_time=t, exit_time=None, exit_price=None,
                                 outcome_r=None, state="OPEN")
                elif (i - sweep_idx) > CONFIRM_MAX_CANDLES:
                    reset_sweep_state()   # this attempt expired, watch for the next sweep

        # ---- manage the open trade --------------------------------------
        if trade is not None and trade["state"] == "OPEN" and t > trade["entry_time"]:
            hit_sl, hit_tp = resolve_sl_tp(h, l, i, trade["is_bull"], trade["sl"], trade["tp"])
            if hit_sl or hit_tp:
                outcome_r = -1.0 if hit_sl else RISK_REWARD
                trade["outcome_r"] = outcome_r
                trade["exit_price"] = trade["sl"] if hit_sl else trade["tp"]
                trade["exit_time"] = t
                balance += trade["risk"] * outcome_r
                trade["state"] = "CLOSED"
                trades.append(dict(trade))
                trades_today += 1
                trade = None
                reset_sweep_state()

        is_last_bar_of_day = (i == n - 1) or (times[i + 1].normalize() != day_date)
        if is_last_bar_of_day and trade is not None and trade["state"] == "OPEN":
            dist = abs(trade["entry"] - trade["sl"])
            outcome_r = ((c[i] - trade["entry"]) / dist) if trade["is_bull"] else ((trade["entry"] - c[i]) / dist)
            trade["outcome_r"] = outcome_r
            trade["exit_price"] = c[i]
            trade["exit_time"] = t
            balance += trade["risk"] * outcome_r
            trade["state"] = "CLOSED_EOD"
            trades.append(dict(trade))
            trade = None
            trades_today += 1

        equity_curve.append((t, balance))

    if pdh is not None:
        annotations["pd_lines"].append((cur_day, cur_day + pd.Timedelta(days=1), pdh, pdl))

    return trades, annotations, equity_curve, balance


def build_chart(df, trades, annotations, equity_curve, final_balance):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color="#00e676", decreasing_line_color="#ff1744",
        increasing_fillcolor="#00e676", decreasing_fillcolor="#ff1744",
        name=f"{SYMBOL} {RESOLUTION}"))

    for x0, x1, pdh, pdl in annotations["pd_lines"]:
        fig.add_shape(type="line", x0=x0, x1=x1, y0=pdh, y1=pdh,
                      line=dict(color="gold", dash="dot", width=1))
        fig.add_shape(type="line", x0=x0, x1=x1, y0=pdl, y1=pdl,
                      line=dict(color="gold", dash="dot", width=1))

    sweep_up_x, sweep_up_y, sweep_dn_x, sweep_dn_y = [], [], [], []
    for tt, price, is_high_sweep in annotations["sweeps"]:
        if is_high_sweep:
            sweep_dn_x.append(tt); sweep_dn_y.append(price)
        else:
            sweep_up_x.append(tt); sweep_up_y.append(price)
    fig.add_trace(go.Scatter(x=sweep_dn_x, y=sweep_dn_y, mode="markers",
                              marker=dict(symbol="triangle-down", size=10, color="orange"),
                              name="PDH sweep attempt"))
    fig.add_trace(go.Scatter(x=sweep_up_x, y=sweep_up_y, mode="markers",
                              marker=dict(symbol="triangle-up", size=10, color="cyan"),
                              name="PDL sweep attempt"))

    entry_x, entry_y, win_x, win_y, loss_x, loss_y = [], [], [], [], [], []
    for tr in trades:
        entry_x.append(tr["entry_time"]); entry_y.append(tr["entry"])
        if tr["outcome_r"] > 0:
            win_x.append(tr["exit_time"]); win_y.append(tr["exit_price"])
        else:
            loss_x.append(tr["exit_time"]); loss_y.append(tr["exit_price"])
    fig.add_trace(go.Scatter(x=entry_x, y=entry_y, mode="markers",
                              marker=dict(symbol="circle", size=8, color="white", line=dict(color="black", width=1)),
                              name="Entry"))
    fig.add_trace(go.Scatter(x=win_x, y=win_y, mode="markers",
                              marker=dict(symbol="star", size=11, color="#00e676"), name="Win"))
    fig.add_trace(go.Scatter(x=loss_x, y=loss_y, mode="markers",
                              marker=dict(symbol="x", size=10, color="#ff1744"), name="Loss"))

    summary = summarize(trades, STARTING_BALANCE, final_balance)
    fig.update_layout(
        title=f"ICT Turtle Soup - {SYMBOL} {RESOLUTION} (Delta Exchange)<br><sub>{summary}</sub>",
        template="plotly_dark",
        xaxis_rangeslider_visible=True,
        height=850,
        legend=dict(orientation="h", y=1.05),
    )
    return fig, summary


def main():
    df = load_data(SYMBOL, RESOLUTION, LOOKBACK_DAYS, ATR_PERIOD)
    trades, annotations, equity_curve, final_balance = run_backtest(df)
    fig, summary = build_chart(df, trades, annotations, equity_curve, final_balance)

    out_html = "/home/user/tvs-motor-anallytics/backtest/ict_turtle_soup_btcusdt.html"
    fig.write_html(out_html, include_plotlyjs="cdn")

    pd.DataFrame(trades).to_csv("/home/user/tvs-motor-anallytics/backtest/turtle_soup_trades.csv", index=False)
    eq = pd.DataFrame(equity_curve, columns=["time", "balance"]).drop_duplicates("time")
    eq.to_csv("/home/user/tvs-motor-anallytics/backtest/turtle_soup_equity_curve.csv", index=False)

    print(summary)
    print(f"Chart written to {out_html}")
    print(f"Candles analyzed: {len(df)} ({df.index.min()} -> {df.index.max()})")
    print(f"Sweep attempts: {len(annotations['sweeps'])}, trades taken: {len(trades)}")


if __name__ == "__main__":
    main()

"""ICT Power of Three (Accumulation-Manipulation-Distribution / AMD) backtest
against real BTCUSDT data from Delta Exchange.

Concept: ICT teaches that price action at every scale (a single candle, a
session, a day, a week) repeats the same three-phase cycle:
  - Accumulation: a tight, low-volatility range builds up while orders get
    positioned.
  - Manipulation: price is pushed beyond that range to run the liquidity
    resting just outside it -- a deliberate fakeout.
  - Distribution: the real move, opposite the manipulation, that actually
    gets distributed/delivered.

Judas Swing (run_judas_swing.py) is one *specific instance* of this same
pattern pinned to the Asian-range/London-open session. This script instead
detects the pattern wherever and whenever it shows up intraday, using
volatility compression (range vs. ATR) to recognize accumulation rather than
a fixed clock window -- closer to how ICT describes it as a fractal,
repeating structure rather than a once-a-day session event.

State machine (repeats continuously, one cycle at a time):
  1. ACCUM    - scan forward until a rolling ACCUM_WINDOW_CANDLES window's
                high-low range compresses to <= ACCUM_RANGE_ATR_MULT * ATR.
                Lock that window's high/low as the accumulation range.
  2. MANIP    - within MANIP_MAX_CANDLES after accumulation locks, the first
                candle to trade beyond the locked high/low is the
                manipulation leg (the liquidity sweep). No sweep in time ->
                abandon this cycle and resume scanning for a fresh
                accumulation range.
  3. DISTRIB  - within CONFIRM_MAX_CANDLES, price must close back inside the
                accumulation range (a fast reclaim, same idea as Turtle
                Soup) -- that confirms manipulation failed and distribution
                is starting. Market entry at that close, reversal direction.
  4. EXIT     - stop beyond the manipulation leg's extreme (+ ATR buffer).
                Target is a *measured move*: the accumulation range's size
                projected from entry (a common AMD heuristic -- the
                distribution leg tends to be at least as large as the
                accumulation range that preceded it), reported in R using
                the stop distance as 1R.
  Either way the cycle resolves, the next cycle starts scanning fresh from
  the following candle.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ict_common import load_data, resolve_sl_tp, summarize

SYMBOL = "BTCUSDT"
RESOLUTION = "5m"
LOOKBACK_DAYS = 30

ACCUM_WINDOW_CANDLES = 24       # 2h @5m
ACCUM_RANGE_ATR_MULT = 6.0      # how "tight" a window must be to count as accumulation
MANIP_MAX_CANDLES = 12          # 1h to find the sweep after accumulation locks
CONFIRM_MAX_CANDLES = 6         # 30min fast reclaim to confirm distribution

ATR_PERIOD = 100
SL_BUFFER_ATR_MULT = 0.25
TARGET_RANGE_MULT = 1.0         # distribution leg target = N x the accumulation range size
RISK_PCT = 1.0
MAX_CONCURRENT = 2

STARTING_BALANCE = 10_000.0

ACCUM_COLOR = "rgba(255,215,0,0.12)"


def run_backtest(df: pd.DataFrame):
    n = len(df)
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    atr = df["atr"].values
    times = df.index

    phase = "ACCUM"
    accum_high, accum_low, accum_end_idx = None, None, None
    sweep_found, sweep_is_sell, sweep_idx = False, False, None
    trade = None

    trades = []
    accum_boxes = []
    balance = STARTING_BALANCE
    equity_curve = []
    trades_open = 0

    for i in range(n):
        t = times[i]

        if phase == "ACCUM":
            if i + 1 >= ACCUM_WINDOW_CANDLES and not np.isnan(atr[i]) and atr[i] > 0:
                w0 = i - ACCUM_WINDOW_CANDLES + 1
                whigh, wlow = h[w0:i + 1].max(), l[w0:i + 1].min()
                if (whigh - wlow) <= ACCUM_RANGE_ATR_MULT * atr[i]:
                    accum_high, accum_low, accum_end_idx = whigh, wlow, i
                    accum_boxes.append((times[w0], t, whigh, wlow))
                    phase = "MANIP"
                    sweep_found, sweep_is_sell, sweep_idx = False, False, None

        elif phase == "MANIP":
            if (i - accum_end_idx) > MANIP_MAX_CANDLES:
                phase = "ACCUM"
                continue
            swept_high = h[i] > accum_high
            swept_low = l[i] < accum_low
            if swept_high and not swept_low:
                sweep_found, sweep_is_sell, sweep_idx = True, True, i
                phase = "DISTRIB"
            elif swept_low and not swept_high:
                sweep_found, sweep_is_sell, sweep_idx = True, False, i
                phase = "DISTRIB"

        elif phase == "DISTRIB":
            if trade is None:
                closed_back = (c[i] < accum_high) if sweep_is_sell else (c[i] > accum_low)
                if closed_back and i > sweep_idx:
                    is_bull = not sweep_is_sell
                    entry = c[i]
                    buf = atr[i] * SL_BUFFER_ATR_MULT if not np.isnan(atr[i]) else 0
                    sl = (l[sweep_idx] - buf) if is_bull else (h[sweep_idx] + buf)
                    accum_range = accum_high - accum_low
                    tp = entry + accum_range * TARGET_RANGE_MULT if is_bull else entry - accum_range * TARGET_RANGE_MULT
                    risk_dist = abs(entry - sl)
                    if trades_open < MAX_CONCURRENT and risk_dist > 0:
                        risk = balance * RISK_PCT / 100.0
                        trade = dict(is_bull=is_bull, accum_high=accum_high, accum_low=accum_low,
                                     sweep_time=times[sweep_idx], entry=entry, sl=sl, tp=tp,
                                     risk_dist=risk_dist, risk=risk, entry_time=t, exit_time=None,
                                     exit_price=None, outcome_r=None, state="OPEN")
                        trades_open += 1
                    else:
                        phase = "ACCUM"
                elif (i - sweep_idx) > CONFIRM_MAX_CANDLES:
                    phase = "ACCUM"
            elif trade["state"] == "OPEN" and t > trade["entry_time"]:
                hit_sl, hit_tp = resolve_sl_tp(h, l, i, trade["is_bull"], trade["sl"], trade["tp"])
                if hit_sl or hit_tp:
                    outcome_r = -1.0 if hit_sl else (trade["tp"] - trade["entry"]) / trade["risk_dist"] * (1 if trade["is_bull"] else -1)
                    trade["outcome_r"] = outcome_r
                    trade["exit_price"] = trade["sl"] if hit_sl else trade["tp"]
                    trade["exit_time"] = t
                    balance += trade["risk"] * outcome_r
                    trade["state"] = "CLOSED"
                    trades.append(dict(trade))
                    trades_open -= 1
                    trade = None
                    phase = "ACCUM"

        equity_curve.append((t, balance))

    return trades, accum_boxes, equity_curve, balance


def build_chart(df, trades, accum_boxes, equity_curve, final_balance):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color="#00e676", decreasing_line_color="#ff1744",
        increasing_fillcolor="#00e676", decreasing_fillcolor="#ff1744",
        name=f"{SYMBOL} {RESOLUTION}"))

    for x0, x1, ahigh, alow in accum_boxes:
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=alow, y1=ahigh,
                      fillcolor=ACCUM_COLOR, line=dict(color="gold", width=1), layer="below")

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
        title=f"ICT Power of Three (AMD) - {SYMBOL} {RESOLUTION} (Delta Exchange)<br><sub>{summary}</sub>",
        template="plotly_dark",
        xaxis_rangeslider_visible=True,
        height=850,
        legend=dict(orientation="h", y=1.05),
    )
    return fig, summary


def main():
    df = load_data(SYMBOL, RESOLUTION, LOOKBACK_DAYS, ATR_PERIOD)
    trades, accum_boxes, equity_curve, final_balance = run_backtest(df)
    fig, summary = build_chart(df, trades, accum_boxes, equity_curve, final_balance)

    out_html = "/home/user/tvs-motor-anallytics/backtest/ict_power_of_three_btcusdt.html"
    fig.write_html(out_html, include_plotlyjs="cdn")

    pd.DataFrame(trades).to_csv("/home/user/tvs-motor-anallytics/backtest/power_of_three_trades.csv", index=False)
    eq = pd.DataFrame(equity_curve, columns=["time", "balance"]).drop_duplicates("time")
    eq.to_csv("/home/user/tvs-motor-anallytics/backtest/power_of_three_equity_curve.csv", index=False)

    print(summary)
    print(f"Chart written to {out_html}")
    print(f"Candles analyzed: {len(df)} ({df.index.min()} -> {df.index.max()})")
    print(f"Accumulation ranges detected: {len(accum_boxes)}, trades taken: {len(trades)}")


if __name__ == "__main__":
    main()

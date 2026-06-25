"""ICT Judas Swing backtest against real BTCUSDT data from Delta Exchange.

Concept (ICT): the "Asian range" -- the quiet consolidation that builds up
overnight -- gets a deliberate false breakout right as the London Open kill
zone begins. That false move (the "Judas Swing") runs stops/liquidity resting
just beyond the Asian range, traps breakout traders, and then reverses hard
for the rest of the session. The trade is the reversal, not the breakout.

This implementation, per UTC day:
  1. ACCUMULATION  - track the high/low of the Asian range window
                     [ASIAN_START_HOUR_UTC, ASIAN_END_HOUR_UTC).
  2. MANIPULATION  - the first candle in the following London-open window
                     that trades beyond the locked Asian high or low is the
                     liquidity sweep (the Judas Swing itself).
  3. CONFIRMATION  - a fractal swing point formed since the Asian range must
                     get closed through in the *opposite* direction of the
                     sweep (a market structure shift) within a few candles,
                     or the setup is abandoned for the day.
  4. ENTRY         - market entry at the confirmation candle's close, in the
                     reversal direction. Stop beyond the sweep's extreme
                     wick (+ ATR buffer). Target a fixed R:R, same as the
                     Silver Bullet script for apples-to-apples comparison.
                     Unlike the FVG Silver Bullet's resting stop order into a
                     gap, this is a direct market-entry setup -- there's only
                     one Judas Swing per day, so there's no decayed sizing
                     across multiple signals.
  5. EXIT          - SL/TP, or mark-to-market close at day's last candle if
                     neither is hit (the move is meant to play out within the
                     session, not be held indefinitely).

UTC hours are a clean stand-in for ICT's EST-based session times (Asian range
~7pm-12am EST, London Open kill zone ~2am-5am EST); exact DST alignment isn't
the point of this backtest -- the setup mechanics are.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ict_common import load_data, is_fractal_high, is_fractal_low, resolve_sl_tp, summarize

SYMBOL = "BTCUSDT"
RESOLUTION = "5m"
LOOKBACK_DAYS = 30

ASIAN_START_HOUR_UTC = 0
ASIAN_END_HOUR_UTC = 6
JUDAS_END_HOUR_UTC = 9          # sweep + reversal must both happen by this hour

FRACTAL_STRENGTH = 2
MSS_LOOKBACK_CANDLES = 40
MSS_CONFIRM_MAX_CANDLES = 12    # candles after the sweep to get a confirmed close

ATR_PERIOD = 100
SL_BUFFER_ATR_MULT = 0.25
RISK_REWARD = 2.0
RISK_PCT = 1.0

STARTING_BALANCE = 10_000.0

BULL_COLOR = "rgba(0,230,118,0.18)"
BEAR_COLOR = "rgba(255,20,147,0.18)"


def run_backtest(df: pd.DataFrame):
    n = len(df)
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    atr = df["atr"].values
    times = df.index

    cur_day = None
    asian_start_idx = None
    asian_high, asian_low = -np.inf, np.inf
    asian_locked = False
    asian_end_idx = None

    sweep_found = False
    sweep_is_sell = False
    sweep_idx = None

    mss_found = False
    mss_level = None
    mss_fractal_idx = None
    mss_confirmed = False
    mss_invalidated = False

    trade = None          # at most one active/pending trade per day
    trades = []            # full lifecycle log, one row per day attempted
    balance = STARTING_BALANCE
    equity_curve = []

    annotations = {"asian_boxes": [], "sweeps": [], "mss_lines": []}

    def reset_day():
        nonlocal asian_start_idx, asian_high, asian_low, asian_locked, asian_end_idx
        nonlocal sweep_found, sweep_is_sell, sweep_idx
        nonlocal mss_found, mss_level, mss_fractal_idx, mss_confirmed, mss_invalidated, trade
        asian_start_idx = i
        asian_high, asian_low = -np.inf, np.inf
        asian_locked = False
        asian_end_idx = None
        sweep_found, sweep_is_sell, sweep_idx = False, False, None
        mss_found, mss_level, mss_fractal_idx = False, None, None
        mss_confirmed, mss_invalidated = False, False
        trade = None

    for i in range(n):
        t = times[i]
        day_date = t.normalize()
        if day_date != cur_day:
            if cur_day is not None and asian_locked:
                annotations["asian_boxes"].append((cur_day + pd.Timedelta(hours=ASIAN_START_HOUR_UTC),
                                                     cur_day + pd.Timedelta(hours=ASIAN_END_HOUR_UTC),
                                                     asian_high, asian_low))
            cur_day = day_date
            reset_day()

        in_asian_window = t.hour < ASIAN_END_HOUR_UTC
        in_judas_window = ASIAN_END_HOUR_UTC <= t.hour < JUDAS_END_HOUR_UTC

        if in_asian_window:
            if h[i] > asian_high: asian_high = h[i]
            if l[i] < asian_low: asian_low = l[i]
            equity_curve.append((t, balance))
            continue

        if not asian_locked:
            asian_locked = True
            asian_end_idx = i

        # ---- signal detection is scoped to the Judas (London-open) window;
        # trade management below is NOT, since a trade opened near the end
        # of the window must still get its SL/TP/EOD-close checked for the
        # rest of the day even after the window itself has passed.
        if in_judas_window and not sweep_found:
            swept_high = h[i] > asian_high
            swept_low = l[i] < asian_low
            if swept_high and not swept_low:
                sweep_found, sweep_is_sell, sweep_idx = True, True, i
                annotations["sweeps"].append((t, h[i], True))
            elif swept_low and not swept_high:
                sweep_found, sweep_is_sell, sweep_idx = True, False, i
                annotations["sweeps"].append((t, l[i], False))

        # ---- market structure shift: most recent fractal before the sweep
        if in_judas_window and sweep_found and not mss_found:
            k = FRACTAL_STRENGTH
            lo_bound = max(asian_start_idx, sweep_idx - MSS_LOOKBACK_CANDLES)
            for p in range(sweep_idx - 1, lo_bound - 1, -1):
                if p - k < asian_start_idx or p + k > i:
                    continue
                if sweep_is_sell:
                    if is_fractal_high(h, p, k):
                        mss_found, mss_level, mss_fractal_idx = True, h[p], p
                        break
                else:
                    if is_fractal_low(l, p, k):
                        mss_found, mss_level, mss_fractal_idx = True, l[p], p
                        break

        # ---- MSS confirmation: close back through the fractal level ------
        if in_judas_window and mss_found and not mss_confirmed and not mss_invalidated and i > sweep_idx and trade is None:
            closed_through = (c[i] < mss_level) if sweep_is_sell else (c[i] > mss_level)
            if closed_through:
                mss_confirmed = True
                annotations["mss_lines"].append((times[mss_fractal_idx], t, mss_level, sweep_is_sell, True))
                is_bull = not sweep_is_sell
                entry = c[i]
                buf = atr[i] * SL_BUFFER_ATR_MULT if not np.isnan(atr[i]) else 0
                sl = (l[sweep_idx] - buf) if is_bull else (h[sweep_idx] + buf)
                dist = abs(entry - sl)
                tp = entry + dist * RISK_REWARD if is_bull else entry - dist * RISK_REWARD
                risk = balance * RISK_PCT / 100.0
                trade = dict(is_bull=is_bull, sweep_time=t, entry=entry, sl=sl, tp=tp, risk=risk,
                             entry_time=t, exit_time=None, exit_price=None, outcome_r=None, state="OPEN")
            elif (i - sweep_idx) > MSS_CONFIRM_MAX_CANDLES:
                mss_invalidated = True

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

        equity_curve.append((t, balance))

    if cur_day is not None and asian_locked:
        annotations["asian_boxes"].append((cur_day + pd.Timedelta(hours=ASIAN_START_HOUR_UTC),
                                            cur_day + pd.Timedelta(hours=ASIAN_END_HOUR_UTC),
                                            asian_high, asian_low))

    return trades, annotations, equity_curve, balance


def build_chart(df, trades, annotations, equity_curve, final_balance):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color="#00e676", decreasing_line_color="#ff1744",
        increasing_fillcolor="#00e676", decreasing_fillcolor="#ff1744",
        name=f"{SYMBOL} {RESOLUTION}"))

    for x0, x1, ahigh, alow in annotations["asian_boxes"]:
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=alow, y1=ahigh,
                      fillcolor="rgba(100,149,237,0.12)", line=dict(color="cornflowerblue", width=1), layer="below")

    sweep_up_x, sweep_up_y, sweep_dn_x, sweep_dn_y = [], [], [], []
    for tt, price, is_high_sweep in annotations["sweeps"]:
        if is_high_sweep:
            sweep_dn_x.append(tt); sweep_dn_y.append(price)
        else:
            sweep_up_x.append(tt); sweep_up_y.append(price)
    fig.add_trace(go.Scatter(x=sweep_dn_x, y=sweep_dn_y, mode="markers",
                              marker=dict(symbol="triangle-down", size=12, color="red"),
                              name="Judas sweep (high)"))
    fig.add_trace(go.Scatter(x=sweep_up_x, y=sweep_up_y, mode="markers",
                              marker=dict(symbol="triangle-up", size=12, color="lime"),
                              name="Judas sweep (low)"))

    for t1, t2, level, is_sell, confirmed in annotations["mss_lines"]:
        fig.add_shape(type="line", x0=t1, x1=t2, y0=level, y1=level,
                      line=dict(color="dodgerblue", dash="dash", width=1))
        fig.add_annotation(x=t1, y=level, text=("MSS Sell" if is_sell else "MSS Buy"), showarrow=False,
                            font=dict(color="dodgerblue", size=9), yshift=10, xanchor="left")

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
        title=f"ICT Judas Swing - {SYMBOL} {RESOLUTION} (Delta Exchange)<br><sub>{summary}</sub>",
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

    out_html = "/home/user/tvs-motor-anallytics/backtest/ict_judas_swing_btcusdt.html"
    fig.write_html(out_html, include_plotlyjs="cdn")

    pd.DataFrame(trades).to_csv("/home/user/tvs-motor-anallytics/backtest/judas_swing_trades.csv", index=False)
    eq = pd.DataFrame(equity_curve, columns=["time", "balance"]).drop_duplicates("time")
    eq.to_csv("/home/user/tvs-motor-anallytics/backtest/judas_swing_equity_curve.csv", index=False)

    print(summary)
    print(f"Chart written to {out_html}")
    print(f"Candles analyzed: {len(df)} ({df.index.min()} -> {df.index.max()})")
    print(f"Days with a confirmed Judas Swing setup: {len(trades)}")


if __name__ == "__main__":
    main()

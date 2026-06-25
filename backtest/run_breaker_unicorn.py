"""ICT Breaker Block / Unicorn backtest against real BTCUSDT data from Delta
Exchange.

Concept: an order block that fails -- price closes all the way through it
before it ever gets traded -- doesn't just disappear. It flips polarity: a
bullish order block (a would-be support zone) that gets broken *down*
becomes resistance on a later retest from underneath; a bearish order block
broken *up* becomes support on a later retest from above. That flipped zone
is the "Breaker Block." When the same displacement that broke the order
block also leaves a Fair Value Gap overlapping that zone, ICT calls the
confluence a "Unicorn Model" -- considered a higher-probability version of
the same trade.

This script only trades the *breaker* zones, not the original order blocks
(see run_order_block.py for trading the OBs directly):

  1. Track order blocks exactly like run_order_block.py (BOS off a fractal
     swing high/low -> last opposite-colored candle before the break).
  2. The moment an order block is invalidated -- a close all the way through
     its far edge before it was ever touched/triggered -- spawn a Breaker
     Block on the *same* price zone with *flipped* direction.
  3. Right after the breaker forms, scan a short window for a 3-candle Fair
     Value Gap in the same direction overlapping the breaker's zone. If
     found, tag the breaker as a Unicorn (is_unicorn=True) -- purely a
     confluence tag for comparison, the trade mechanics are identical
     either way.
  4. Trade the breaker zone with the same resting-order mechanics as an
     order block: wait for a retest touch, enter at the proximal edge,
     stop beyond the distal edge (+ ATR buffer), fixed R:R target.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ict_common import load_data, is_fractal_high, is_fractal_low, resolve_sl_tp, summarize

SYMBOL = "BTCUSDT"
RESOLUTION = "5m"
LOOKBACK_DAYS = 30

FRACTAL_STRENGTH = 2
OB_LOOKBACK_CANDLES = 10
OB_EXPIRE_CANDLES = 288

UNICORN_FVG_SEARCH_CANDLES = 6   # how far past the break to look for a confluence FVG
FVG_MIN_ATR_MULT = 0.3

ATR_PERIOD = 100
SL_BUFFER_ATR_MULT = 0.25
RISK_REWARD = 2.0
RISK_PCT = 1.0
MAX_CONCURRENT = 3

STARTING_BALANCE = 10_000.0

BULL_COLOR = "rgba(0,230,118,0.30)"
BEAR_COLOR = "rgba(255,20,147,0.30)"
INVALID_COLOR = "rgba(128,128,128,0.25)"
UNICORN_BORDER = "rgba(255,215,0,0.9)"


def has_overlapping_fvg(h, l, atr, break_idx, n, is_bull, zone_lower, zone_upper):
    end = min(n, break_idx + UNICORN_FVG_SEARCH_CANDLES + 2)
    for i0 in range(break_idx + 2, end):
        i2 = i0 - 2
        a = atr[i0] if not np.isnan(atr[i0]) else 0
        min_size = a * FVG_MIN_ATR_MULT
        if is_bull and h[i2] < l[i0]:
            lower, upper = h[i2], l[i0]
        elif not is_bull and l[i2] > h[i0]:
            lower, upper = h[i0], l[i2]
        else:
            continue
        if (upper - lower) >= min_size and not (lower > zone_upper or upper < zone_lower):
            return True
    return False


def run_backtest(df: pd.DataFrame):
    n = len(df)
    o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    atr = df["atr"].values
    times = df.index
    k = FRACTAL_STRENGTH

    last_fh_level, last_fh_idx, fh_broken = None, None, True
    last_fl_level, last_fl_idx, fl_broken = None, None, True

    obs = []           # order-block tracking (internal only, not traded)
    open_obs = []
    breakers = []      # the actual tradeable setups
    open_breakers = []

    balance = STARTING_BALANCE
    equity_curve = []
    trades_open = 0

    for i in range(n):
        t = times[i]

        p = i - k
        if p >= k:
            if is_fractal_high(h, p, k):
                last_fh_level, last_fh_idx, fh_broken = h[p], p, False
            if is_fractal_low(l, p, k):
                last_fl_level, last_fl_idx, fl_broken = l[p], p, False

        if last_fh_level is not None and not fh_broken and c[i] > last_fh_level:
            fh_broken = True
            lo_bound = max(last_fh_idx + 1, i - OB_LOOKBACK_CANDLES)
            for p2 in range(i - 1, lo_bound - 1, -1):
                if c[p2] < o[p2]:
                    obs.append(dict(is_bull=True, upper=h[p2], lower=l[p2], created_idx=p2, state="PENDING"))
                    open_obs.append(len(obs) - 1)
                    break

        if last_fl_level is not None and not fl_broken and c[i] < last_fl_level:
            fl_broken = True
            lo_bound = max(last_fl_idx + 1, i - OB_LOOKBACK_CANDLES)
            for p2 in range(i - 1, lo_bound - 1, -1):
                if c[p2] > o[p2]:
                    obs.append(dict(is_bull=False, upper=h[p2], lower=l[p2], created_idx=p2, state="PENDING"))
                    open_obs.append(len(obs) - 1)
                    break

        # ---- order-block lifecycle: only care about the INVALIDATED event
        still_open_obs = []
        for oi in open_obs:
            ob = obs[oi]
            if ob["state"] == "PENDING":
                touched = (l[i] <= ob["upper"]) if ob["is_bull"] else (h[i] >= ob["lower"])
                broken = (c[i] < ob["lower"]) if ob["is_bull"] else (c[i] > ob["upper"])
                if broken and i > ob["created_idx"]:
                    ob["state"] = "INVALIDATED"
                    flip_is_bull = not ob["is_bull"]
                    is_unicorn = has_overlapping_fvg(h, l, atr, i, n, flip_is_bull, ob["lower"], ob["upper"])
                    breakers.append(dict(is_bull=flip_is_bull, upper=ob["upper"], lower=ob["lower"],
                                          created_time=t, created_idx=i, is_unicorn=is_unicorn,
                                          state="PENDING", entry=None, sl=None, tp=None, risk=None,
                                          trigger_time=None, exit_time=None, exit_price=None, outcome_r=None))
                    open_breakers.append(len(breakers) - 1)
                elif touched:
                    ob["state"] = "ACTIVE"  # successfully traded as a normal OB -- no longer breaker material
                elif (i - ob["created_idx"]) > OB_EXPIRE_CANDLES:
                    ob["state"] = "EXPIRED"

            if ob["state"] == "ACTIVE":
                broken = (c[i] < ob["lower"]) if ob["is_bull"] else (c[i] > ob["upper"])
                if broken:
                    ob["state"] = "INVALIDATED"
                    flip_is_bull = not ob["is_bull"]
                    is_unicorn = has_overlapping_fvg(h, l, atr, i, n, flip_is_bull, ob["lower"], ob["upper"])
                    breakers.append(dict(is_bull=flip_is_bull, upper=ob["upper"], lower=ob["lower"],
                                          created_time=t, created_idx=i, is_unicorn=is_unicorn,
                                          state="PENDING", entry=None, sl=None, tp=None, risk=None,
                                          trigger_time=None, exit_time=None, exit_price=None, outcome_r=None))
                    open_breakers.append(len(breakers) - 1)
                elif (i - ob["created_idx"]) > OB_EXPIRE_CANDLES:
                    ob["state"] = "EXPIRED"

            if ob["state"] not in ("INVALIDATED", "EXPIRED"):
                still_open_obs.append(oi)
        open_obs = still_open_obs

        # ---- manage tradeable breaker zones ------------------------------
        still_open_b = []
        for bi in open_breakers:
            b = breakers[bi]
            if b["state"] == "PENDING":
                touched = (l[i] <= b["upper"]) if b["is_bull"] else (h[i] >= b["lower"])
                if touched and i > b["created_idx"]:
                    buf = atr[i] * SL_BUFFER_ATR_MULT if not np.isnan(atr[i]) else 0
                    if b["is_bull"]:
                        b["entry"] = b["upper"]
                        b["sl"] = b["lower"] - buf
                    else:
                        b["entry"] = b["lower"]
                        b["sl"] = b["upper"] + buf
                    dist = abs(b["entry"] - b["sl"])
                    b["tp"] = b["entry"] + dist * RISK_REWARD if b["is_bull"] else b["entry"] - dist * RISK_REWARD
                    b["state"] = "ACTIVE"
                elif (i - b["created_idx"]) > OB_EXPIRE_CANDLES:
                    b["state"] = "EXPIRED"
                    b["exit_time"] = t

            if b["state"] == "ACTIVE":
                broken = (c[i] < b["lower"]) if b["is_bull"] else (c[i] > b["upper"])
                triggered = (h[i] >= b["entry"]) if b["is_bull"] else (l[i] <= b["entry"])
                if triggered and trades_open < MAX_CONCURRENT:
                    b["state"] = "TRIGGERED"
                    b["trigger_time"] = t
                    b["risk"] = balance * RISK_PCT / 100.0
                    trades_open += 1
                elif broken:
                    b["state"] = "INVALIDATED"
                    b["exit_time"] = t
                elif (i - b["created_idx"]) > OB_EXPIRE_CANDLES:
                    b["state"] = "EXPIRED"
                    b["exit_time"] = t

            if b["state"] == "TRIGGERED":
                hit_sl, hit_tp = resolve_sl_tp(h, l, i, b["is_bull"], b["sl"], b["tp"])
                if hit_sl or hit_tp:
                    outcome_r = -1.0 if hit_sl else RISK_REWARD
                    b["outcome_r"] = outcome_r
                    b["exit_price"] = b["sl"] if hit_sl else b["tp"]
                    b["exit_time"] = t
                    balance += b["risk"] * outcome_r
                    b["state"] = "CLOSED"
                    trades_open -= 1

            if b["state"] not in ("CLOSED", "INVALIDATED", "EXPIRED"):
                still_open_b.append(bi)
        open_breakers = still_open_b

        equity_curve.append((t, balance))

    return breakers, equity_curve, balance


def build_chart(df, breakers, equity_curve, final_balance):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color="#00e676", decreasing_line_color="#ff1744",
        increasing_fillcolor="#00e676", decreasing_fillcolor="#ff1744",
        name=f"{SYMBOL} {RESOLUTION}"))

    for b in breakers:
        end_t = b["exit_time"] if b["exit_time"] else df.index[-1]
        color = INVALID_COLOR if b["state"] in ("INVALIDATED", "EXPIRED") else (BULL_COLOR if b["is_bull"] else BEAR_COLOR)
        line = dict(color=UNICORN_BORDER, width=2) if b["is_unicorn"] else dict(width=0)
        fig.add_shape(type="rect", x0=b["created_time"], x1=end_t, y0=b["lower"], y1=b["upper"],
                      fillcolor=color, line=line, layer="below")

    entry_x, entry_y, win_x, win_y, loss_x, loss_y = [], [], [], [], [], []
    for b in breakers:
        if b["state"] == "CLOSED":
            entry_x.append(b["trigger_time"]); entry_y.append(b["entry"])
            if b["outcome_r"] > 0:
                win_x.append(b["exit_time"]); win_y.append(b["exit_price"])
            else:
                loss_x.append(b["exit_time"]); loss_y.append(b["exit_price"])
    fig.add_trace(go.Scatter(x=entry_x, y=entry_y, mode="markers",
                              marker=dict(symbol="circle", size=8, color="white", line=dict(color="black", width=1)),
                              name="Entry"))
    fig.add_trace(go.Scatter(x=win_x, y=win_y, mode="markers",
                              marker=dict(symbol="star", size=11, color="#00e676"), name="Win"))
    fig.add_trace(go.Scatter(x=loss_x, y=loss_y, mode="markers",
                              marker=dict(symbol="x", size=10, color="#ff1744"), name="Loss"))

    closed = [b for b in breakers if b["state"] == "CLOSED"]
    unicorn_closed = [b for b in closed if b["is_unicorn"]]
    plain_closed = [b for b in closed if not b["is_unicorn"]]
    summary = summarize(closed, STARTING_BALANCE, final_balance)
    uni_summary = summarize(unicorn_closed, STARTING_BALANCE, STARTING_BALANCE + sum(t["outcome_r"] * t["risk"] for t in unicorn_closed)) if unicorn_closed else "Unicorn: 0 trades"
    plain_summary = summarize(plain_closed, STARTING_BALANCE, STARTING_BALANCE + sum(t["outcome_r"] * t["risk"] for t in plain_closed)) if plain_closed else "Plain breaker: 0 trades"

    fig.update_layout(
        title=(f"ICT Breaker Block / Unicorn - {SYMBOL} {RESOLUTION} (Delta Exchange)<br>"
               f"<sub>All breakers: {summary}</sub>"),
        template="plotly_dark",
        xaxis_rangeslider_visible=True,
        height=850,
        legend=dict(orientation="h", y=1.05),
    )
    return fig, summary, uni_summary, plain_summary


def main():
    df = load_data(SYMBOL, RESOLUTION, LOOKBACK_DAYS, ATR_PERIOD)
    breakers, equity_curve, final_balance = run_backtest(df)
    fig, summary, uni_summary, plain_summary = build_chart(df, breakers, equity_curve, final_balance)

    out_html = "/home/user/tvs-motor-anallytics/backtest/ict_breaker_unicorn_btcusdt.html"
    fig.write_html(out_html, include_plotlyjs="cdn")

    pd.DataFrame(breakers).to_csv("/home/user/tvs-motor-anallytics/backtest/breaker_unicorn_trades.csv", index=False)
    eq = pd.DataFrame(equity_curve, columns=["time", "balance"]).drop_duplicates("time")
    eq.to_csv("/home/user/tvs-motor-anallytics/backtest/breaker_unicorn_equity_curve.csv", index=False)

    print(summary)
    print("  " + uni_summary)
    print("  " + plain_summary)
    print(f"Chart written to {out_html}")
    print(f"Candles analyzed: {len(df)} ({df.index.min()} -> {df.index.max()})")
    print(f"Total breakers detected: {len(breakers)} ({sum(1 for b in breakers if b['is_unicorn'])} unicorns)")


if __name__ == "__main__":
    main()

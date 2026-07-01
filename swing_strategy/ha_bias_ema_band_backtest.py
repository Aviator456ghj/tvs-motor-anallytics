"""
Daily Heikin-Ashi bias + 34-EMA High/Low channel breakout.

Mechanical retail system: establish a directional bias from the previous
day's Heikin-Ashi candle color on the daily chart, then on a lower
execution timeframe wait for price to cross and close outside a channel
formed by a 34-period EMA of High (upper band) and a 34-period EMA of Low
(lower band) - only in the direction the daily bias allows. No bias
flipping intraday, no trading inside the channel ("no trade zone").

This repo has no Indian equity/options data (no 9:15am sector scan, no
Calls/Puts) - it has 24/7 BTCUSD from Kraken, so the "intraday timeframe"
here is the 5-minute chart (data/btc_usd_5min_cvd.csv, ~30 days) and the
daily bias chart is data/btc_usd_daily.csv (2 years, so the HA color
itself is computed on a long, stable history rather than just the last
30 days - only the bias *lookup* is restricted to the last 30 days where
5-min execution data exists). There's no real overnight "gap" in a 24/7
market, so the "gap mismatch" invalidation in the original system has no
direct equivalent here; the cross-and-close entry condition already
achieves the same effect (it can't fire until price actually re-enters
the correct side of the channel).

Stop is structural and dynamic, not a fixed price: once long, an exit
triggers the first time a 5-min candle CLOSES back below the (then-current)
upper band - a failed breakout / reversal, exactly as described. Risk for
position sizing is measured as the distance from entry to the band value
at the entry bar. Take-profit is a fixed R-multiple of that risk (the
video itself says "1:2 or 1:3" - swept below). Entry and stop-out exits
both fill at the next bar's open (no lookahead); take-profit fills
intrabar at the touched price level, same convention as every other
variant in this repo. $5,000 / 1% account convention, as everywhere else.
"""
import csv

from measured_swing_backtest import ACCOUNT_SIZE, RISK_PCT

DAILY_PATH = "data/btc_usd_daily.csv"
EXEC_PATH = "data/btc_usd_5min_cvd.csv"

EMA_PERIOD = 34
TP_RR_MULT = 2.0


def load_daily(path):
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({"date": r["date"], "open": float(r["open"]), "high": float(r["high"]),
                         "low": float(r["low"]), "close": float(r["close"])})
    return rows


def heikin_ashi(daily_bars):
    ha = []
    prev_open = prev_close = None
    for b in daily_bars:
        ha_open = (b["open"] + b["close"]) / 2 if prev_open is None else (prev_open + prev_close) / 2
        ha_close = (b["open"] + b["high"] + b["low"] + b["close"]) / 4
        color = "GREEN" if ha_close > ha_open else "RED"
        ha.append({"date": b["date"], "color": color})
        prev_open, prev_close = ha_open, ha_close
    return ha


def bias_by_date(daily_bars):
    """date -> bias for THAT date, derived from the PREVIOUS day's HA color."""
    ha = heikin_ashi(daily_bars)
    bias = {}
    for i in range(1, len(ha)):
        bias[ha[i]["date"]] = "BULLISH" if ha[i - 1]["color"] == "GREEN" else "BEARISH"
    return bias


def load_5min(path):
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({"timestamp": int(r["timestamp"]), "datetime": r["datetime"],
                         "date": r["datetime"][:10],
                         "open": float(r["open"]), "high": float(r["high"]),
                         "low": float(r["low"]), "close": float(r["close"])})
    return rows


def ema_series(values, period):
    k = 2 / (period + 1)
    out = []
    ema = None
    for v in values:
        ema = v if ema is None else v * k + ema * (1 - k)
        out.append(ema)
    return out


def run_backtest(daily_bars, bars_5m, ema_period=EMA_PERIOD, tp_rr_mult=TP_RR_MULT):
    bias_map = bias_by_date(daily_bars)
    upper = ema_series([b["high"] for b in bars_5m], ema_period)
    lower = ema_series([b["low"] for b in bars_5m], ema_period)

    trades = []
    seen_days = set()
    funnel = {"days": 0, "bias_days": 0, "signals": 0, "traded": 0}

    n = len(bars_5m)
    i = ema_period
    while i < n:
        bar = bars_5m[i]
        date = bar["date"]
        if date not in seen_days:
            seen_days.add(date)
        bias = bias_map.get(date)
        if bias is None:
            i += 1
            continue
        funnel["bias_days"] = len({d for d in seen_days if d in bias_map})

        prev_close = bars_5m[i - 1]["close"]
        close = bar["close"]
        signal = None
        if bias == "BULLISH" and close > upper[i] and prev_close <= upper[i - 1]:
            signal = "LONG"
        elif bias == "BEARISH" and close < lower[i] and prev_close >= lower[i - 1]:
            signal = "SHORT"
        if signal is None:
            i += 1
            continue
        funnel["signals"] += 1

        entry_idx = i + 1
        if entry_idx >= n:
            break
        entry = bars_5m[entry_idx]["open"]
        band_at_entry = upper[i] if signal == "LONG" else lower[i]
        risk = (entry - band_at_entry) if signal == "LONG" else (band_at_entry - entry)

        trade = {"direction": signal, "date": date, "signal_idx": i, "entry_idx": entry_idx,
                  "entry": entry, "band_at_entry": band_at_entry, "risk": risk, "outcome": None}
        if risk <= 0:
            trade["outcome"] = "BAD_RISK_GEOMETRY"
            trades.append(trade)
            i = entry_idx + 1
            continue
        funnel["traded"] += 1
        tp = entry + risk * tp_rr_mult if signal == "LONG" else entry - risk * tp_rr_mult
        trade["tp"] = tp

        resolved = False
        next_i = entry_idx + 1
        for j in range(entry_idx, n):
            jbar = bars_5m[j]
            if signal == "LONG":
                hit_sl, hit_tp = jbar["close"] < upper[j], jbar["high"] >= tp
            else:
                hit_sl, hit_tp = jbar["close"] > lower[j], jbar["low"] <= tp

            if hit_sl:
                exit_idx = j + 1
                if exit_idx >= n:
                    break
                trade["outcome"], trade["exit_idx"] = "LOSS", exit_idx
                trade["exit_price"] = bars_5m[exit_idx]["open"]
                resolved, next_i = True, exit_idx + 1
                break
            if hit_tp:
                trade["outcome"], trade["exit_idx"] = "WIN", j
                trade["exit_price"] = tp
                resolved, next_i = True, j + 1
                break
        if not resolved:
            trade["outcome"] = "OPEN"
        else:
            move = (trade["exit_price"] - entry) if signal == "LONG" else (entry - trade["exit_price"])
            position_size = (ACCOUNT_SIZE * RISK_PCT) / risk
            trade["pnl_cash"] = position_size * move
            trade["r_multiple"] = move / risk
        trades.append(trade)
        i = next_i

    funnel["days"] = len(seen_days)
    return trades, funnel


def report(bars_5m, trades, funnel, label, ema_period, tp_rr_mult):
    lines = []
    lines.append("=" * 110)
    lines.append(f"DAILY HEIKIN-ASHI BIAS + {ema_period}-EMA HIGH/LOW BAND BREAKOUT - {label}")
    lines.append("=" * 110)
    lines.append(f"EMA period: {ema_period}   TP: {tp_rr_mult:.1f}R")
    lines.append("")

    closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
    header = (f"{'#':>3} {'Dir':<6} {'Date':<11} {'Entry Date':<19} {'Exit Date':<19} {'Entry':>10} "
              f"{'Risk':>8} {'TP':>10} {'Res':<5} {'PnL$':>9} {'R':>6} {'W-L':<8} {'Equity$':>10}")
    lines.append(header)
    seq = w = l = 0
    cum = 0.0
    equity = ACCOUNT_SIZE
    for t in closed:
        seq += 1
        if t["outcome"] == "WIN":
            w += 1
        else:
            l += 1
        cum += t["pnl_cash"]
        equity = ACCOUNT_SIZE + cum
        lines.append(f"{seq:>3} {t['direction']:<6} {t['date']:<11} "
                     f"{bars_5m[t['entry_idx']]['datetime']:<19} {bars_5m[t['exit_idx']]['datetime']:<19} "
                     f"{t['entry']:>10,.1f} {t['risk']:>8,.1f} {t['tp']:>10,.1f} {t['outcome']:<5} "
                     f"{t['pnl_cash']:>9,.2f} {t['r_multiple']:>6.2f} {f'{w}-{l}':<8} {equity:>10,.2f}")

    lines.append("")
    lines.append("-" * 110)
    lines.append("FUNNEL")
    lines.append(f"  Calendar days in execution window     : {funnel['days']}")
    lines.append(f"  + days with a usable daily bias        : {funnel['bias_days']}")
    lines.append(f"  + bias-aligned channel breakout signals: {funnel['signals']}")
    lines.append(f"  -> traded                              : {funnel['traded']}")
    lines.append("")
    lines.append("SUMMARY")
    lines.append(f"Closed trades  : {len(closed)}")
    lines.append(f"  Wins         : {w}")
    lines.append(f"  Losses       : {l}")
    if closed:
        lines.append(f"  Win rate     : {w/len(closed)*100:.1f}%")
        avg_r = sum(t["r_multiple"] for t in closed) / len(closed)
        lines.append(f"  Avg R-multiple : {avg_r:+.2f}R")
        lines.append(f"  Net P&L      : ${cum:+,.2f}  (${ACCOUNT_SIZE:,.0f} -> ${equity:,.2f})")
        mw = ml = cw = cl = 0
        for t in closed:
            if t["outcome"] == "WIN":
                cw += 1; cl = 0
            else:
                cl += 1; cw = 0
            mw, ml = max(mw, cw), max(ml, cl)
        lines.append(f"  Longest win/loss streak: {mw} / {ml}")
    return "\n".join(lines)


def parameter_sweep(daily_bars, bars_5m):
    lines = []
    lines.append("-" * 110)
    lines.append("PARAMETER SWEEP (EMA period x TP R-multiple)")
    lines.append("-" * 110)
    lines.append(f"{'EMA':>5} {'TP_RR':>6} {'Signals':>8} {'Traded':>7} {'Closed':>7} {'W':>3} {'L':>3} "
                 f"{'WinRate':>8} {'AvgR':>7} {'NetPnL':>10}")
    for ema_period in (13, 21, 34, 55):
        for tp_rr in (1.0, 1.5, 2.0, 3.0):
            trades, funnel = run_backtest(daily_bars, bars_5m, ema_period=ema_period, tp_rr_mult=tp_rr)
            closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
            w = sum(1 for t in closed if t["outcome"] == "WIN")
            l = len(closed) - w
            net = sum(t["pnl_cash"] for t in closed)
            avg_r = (sum(t["r_multiple"] for t in closed) / len(closed)) if closed else 0.0
            wr = (w / len(closed) * 100) if closed else 0.0
            lines.append(f"{ema_period:>5} {tp_rr:>6.1f} {funnel['signals']:>8} {funnel['traded']:>7} "
                         f"{len(closed):>7} {w:>3} {l:>3} {wr:>7.1f}% {avg_r:>+6.2f}R {net:>+10.2f}")
    return "\n".join(lines)


def main():
    daily_bars = load_daily(DAILY_PATH)
    bars_5m = load_5min(EXEC_PATH)
    trades, funnel = run_backtest(daily_bars, bars_5m)
    label = f"{bars_5m[0]['datetime']} -> {bars_5m[-1]['datetime']}"
    out = report(bars_5m, trades, funnel, label, EMA_PERIOD, TP_RR_MULT)
    out += "\n\n" + parameter_sweep(daily_bars, bars_5m)
    print(out)
    with open("results_ha_bias_ema_band.txt", "w") as f:
        f.write(out + "\n")


if __name__ == "__main__":
    main()

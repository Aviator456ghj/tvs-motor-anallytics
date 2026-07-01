"""
Order-flow confirmed order block + multi-timeframe structure backtest.

Same 4H bias -> 15m external/internal structure -> order block skeleton as
order_block_mtf_backtest.py (bias/structure/OB code is reused unchanged from
that module), but replaces that variant's mechanical 1-minute price-pivot
CHoCH with genuine order-flow evidence of institutional activity at the
order-block zone, using Kraken's real buyer/seller aggressor tag on every
trade (not a price-uptick proxy):

  - Absorption: a 1-min bar trading at/inside the OB zone with volume at
    least ABSORPTION_VOL_MULT x its trailing average, that still closes in
    the *reversal* direction (a huge-volume bearish close right at
    resistance, or bullish close right at support). Size came in and price
    didn't get away with it - someone large is taking the other side of
    the crowd's continuation attempt.
  - CVD divergence: a bar prints a fresh local extreme into the order-block
    zone (a new N-bar high for a SHORT setup testing resistance, a new
    N-bar low for a LONG testing support) but that bar's own delta
    (buy_vol - sell_vol) fails to confirm it - delta <= 0 on the fresh
    high, or >= 0 on the fresh low. The push lacks real aggressive volume
    behind it.

Either signal, firing while price is actually trading at/inside the OB
zone, replaces the old variant's CHoCH step. From there entry requires one
more close that rejects back out of the zone (the confirmation); entry
fills at the next bar's open. Unlike the CHoCH variant, there is no
separate modelled "pullback away and back" leg - the absorption/divergence
bar is itself evidence of a reversal happening *at* the zone, so the
sequence collapses to: touch -> order-flow signal -> confirmation close ->
entry. The same fake-out rule applies throughout: a close through the far
side of the OB zone before confirmation completes kills the setup.

No lookahead anywhere: every decision at bar j uses only opens/highs/lows/
closes/volume/delta through bar j; entries fill at the following bar's
open. Same $5,000 / 1% account convention as every other variant here.
"""
import csv
import bisect

from measured_swing_backtest import find_pivots, ACCOUNT_SIZE, RISK_PCT
from order_block_mtf_backtest import (
    load_bars, compute_bias_events, bias_lookup_table, bias_at,
    find_order_block, scan_for_ob_touch,
    BARS_4H, BARS_15M, BIAS_THRESHOLD_4H, EXT_THRESHOLD_15M, INT_THRESHOLD_15M,
)

BARS_1M = "data/btc_usd_1min.csv"

VOL_LOOKBACK = 20           # bars of trailing volume used as the local baseline
ABSORPTION_VOL_MULT = 2.0   # bar volume must be at least this many x baseline to count as absorption
EXTREME_LOOKBACK = 10       # bars used to decide whether a bar prints a "fresh local extreme" for divergence
OB_TOUCH_WINDOW_1M = 240    # bars (4h) to wait for order-flow signal -> confirmation before giving up
SL_BUFFER = 0.001           # stop placed this far beyond the OB zone boundary
TP_RR_MULT = 2.0            # reward sized as a multiple of risk


def load_1m_bars(path):
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "timestamp": int(r["timestamp"]), "datetime": r["datetime"],
                "open": float(r["open"]), "high": float(r["high"]),
                "low": float(r["low"]), "close": float(r["close"]),
                "volume": float(r["volume"]), "delta": float(r["delta"]),
            })
    return rows


def bar_in_zone(bar, ob, direction):
    return (bar["high"] >= ob["low"]) if direction == "SHORT" else (bar["low"] <= ob["high"])


def order_flow_kind(bars_1m, j, ob, direction, vol_lookback, absorption_mult, extreme_lookback):
    """Single-bar check: absorption or CVD divergence, only while the bar is
    actually trading at/inside the OB zone. Returns a label or None."""
    if j < vol_lookback:
        return None
    bar = bars_1m[j]
    if not bar_in_zone(bar, ob, direction):
        return None

    baseline = sum(bars_1m[k]["volume"] for k in range(j - vol_lookback, j)) / vol_lookback
    vol_ratio = bar["volume"] / baseline if baseline > 0 else 0.0
    is_bull = bar["close"] > bar["open"]
    if direction == "SHORT" and vol_ratio >= absorption_mult and not is_bull:
        return "ABSORPTION"
    if direction == "LONG" and vol_ratio >= absorption_mult and is_bull:
        return "ABSORPTION"

    lb_start = max(0, j - extreme_lookback)
    if direction == "SHORT":
        fresh_extreme = bar["high"] >= max(b["high"] for b in bars_1m[lb_start:j + 1])
        if fresh_extreme and bar["delta"] <= 0:
            return "DIVERGENCE"
    else:
        fresh_extreme = bar["low"] <= min(b["low"] for b in bars_1m[lb_start:j + 1])
        if fresh_extreme and bar["delta"] >= 0:
            return "DIVERGENCE"
    return None


def evaluate_1m_entry(bars_1m, ts_1m, touch_ts, ob, direction, window_bars=OB_TOUCH_WINDOW_1M,
                       vol_lookback=VOL_LOOKBACK, absorption_mult=ABSORPTION_VOL_MULT,
                       extreme_lookback=EXTREME_LOOKBACK):
    start_1m = bisect.bisect_left(ts_1m, touch_ts)
    if start_1m >= len(bars_1m):
        return {"outcome": "NO_1M_DATA"}
    end_1m = min(len(bars_1m) - 1, start_1m + window_bars)

    def broke_far_side(bar):
        return bar["close"] > ob["high"] if direction == "SHORT" else bar["close"] < ob["low"]

    signal_idx = signal_kind = None
    for j in range(start_1m, end_1m + 1):
        bar = bars_1m[j]
        if broke_far_side(bar):
            return {"outcome": "FAKEOUT", "fakeout_idx": j}
        kind = order_flow_kind(bars_1m, j, ob, direction, vol_lookback, absorption_mult, extreme_lookback)
        if kind:
            signal_idx, signal_kind = j, kind
            break
    if signal_idx is None:
        return {"outcome": "NO_SIGNAL_IN_WINDOW"}

    confirm_idx = None
    for j in range(signal_idx, end_1m + 1):
        bar = bars_1m[j]
        if broke_far_side(bar):
            return {"outcome": "FAKEOUT", "fakeout_idx": j, "signal_idx": signal_idx, "signal_kind": signal_kind}
        rejected = (bar["close"] < ob["low"]) if direction == "SHORT" else (bar["close"] > ob["high"])
        if rejected:
            confirm_idx = j
            break
    if confirm_idx is None or confirm_idx + 1 >= len(bars_1m) or confirm_idx + 1 > end_1m:
        return {"outcome": "NO_CONFIRMATION_IN_WINDOW", "signal_idx": signal_idx, "signal_kind": signal_kind}

    return {"outcome": "ENTRY", "signal_idx": signal_idx, "signal_kind": signal_kind,
            "confirm_idx": confirm_idx, "entry_idx": confirm_idx + 1}


def run_order_flow_backtest(bars_4h, bars_15m, bars_1m, ext_threshold=EXT_THRESHOLD_15M,
                             absorption_mult=ABSORPTION_VOL_MULT, tp_rr_mult=TP_RR_MULT):
    pivots_4h = find_pivots(bars_4h, BIAS_THRESHOLD_4H)
    bias_ts, bias_vals = bias_lookup_table(bars_4h, pivots_4h)
    pivots_15m = find_pivots(bars_15m, ext_threshold)
    ts_1m = [b["timestamp"] for b in bars_1m]

    trades = []
    funnel = {"legs": 0, "bias_aligned": 0, "ob_marked": 0, "ob_touched": 0,
              "signal_confirmed": 0, "fakeout": 0, "traded": 0,
              "signal_absorption": 0, "signal_divergence": 0}

    for i in range(1, len(pivots_15m) - 1):
        p0, p1 = pivots_15m[i - 1], pivots_15m[i]
        if p0.kind == "H" and p1.kind == "L":
            direction = "SHORT"
        elif p0.kind == "L" and p1.kind == "H":
            direction = "LONG"
        else:
            continue
        funnel["legs"] += 1

        leg_end_ts = bars_15m[p1.confirm_idx]["timestamp"]
        bias = bias_at(bias_ts, bias_vals, leg_end_ts)
        expected_bias = "BEARISH" if direction == "SHORT" else "BULLISH"
        trade = {"direction": direction, "leg_origin": p0.price, "leg_extreme": p1.price,
                  "bias": bias, "outcome": None}
        if bias != expected_bias:
            trade["outcome"] = "BIAS_NOT_ALIGNED"
            trades.append(trade)
            continue
        funnel["bias_aligned"] += 1

        ob = find_order_block(bars_15m, p0.idx, p1.idx, direction)
        if ob is None:
            trade["outcome"] = "NO_ORDER_BLOCK"
            trades.append(trade)
            continue
        funnel["ob_marked"] += 1
        trade["ob_high"], trade["ob_low"] = ob["high"], ob["low"]

        window_end = pivots_15m[i + 1].confirm_idx if i + 1 < len(pivots_15m) else len(bars_15m) - 1
        touch_idx = scan_for_ob_touch(bars_15m, p1.idx, window_end, ob, direction, INT_THRESHOLD_15M)
        if touch_idx is None:
            trade["outcome"] = "NO_OB_TOUCH"
            trades.append(trade)
            continue
        funnel["ob_touched"] += 1

        result = evaluate_1m_entry(bars_1m, ts_1m, bars_15m[touch_idx]["timestamp"], ob, direction,
                                    absorption_mult=absorption_mult)
        if result["outcome"] == "FAKEOUT":
            funnel["fakeout"] += 1
            trade["outcome"] = "FAKEOUT"
            trades.append(trade)
            continue
        if result["outcome"] != "ENTRY":
            trade["outcome"] = result["outcome"]
            trades.append(trade)
            continue
        funnel["signal_confirmed"] += 1
        if result["signal_kind"] == "ABSORPTION":
            funnel["signal_absorption"] += 1
        else:
            funnel["signal_divergence"] += 1
        trade["signal_kind"] = result["signal_kind"]

        entry_idx = result["entry_idx"]
        entry = bars_1m[entry_idx]["open"]
        if direction == "SHORT":
            sl = ob["high"] * (1 + SL_BUFFER)
            risk = sl - entry
            tp = entry - risk * tp_rr_mult
        else:
            sl = ob["low"] * (1 - SL_BUFFER)
            risk = entry - sl
            tp = entry + risk * tp_rr_mult

        if risk <= 0:
            trade["outcome"] = "BAD_RISK_GEOMETRY"
            trades.append(trade)
            continue
        funnel["traded"] += 1

        trade.update({"entry_idx": entry_idx, "entry": entry, "sl": sl, "tp": tp})
        resolved = False
        for j in range(entry_idx, len(bars_1m)):
            bar = bars_1m[j]
            if direction == "SHORT":
                hit_sl, hit_tp = bar["high"] >= sl, bar["low"] <= tp
            else:
                hit_sl, hit_tp = bar["low"] <= sl, bar["high"] >= tp
            if hit_sl:
                trade["outcome"], trade["exit_price"], trade["exit_idx"] = "LOSS", sl, j
                resolved = True
                break
            if hit_tp:
                trade["outcome"], trade["exit_price"], trade["exit_idx"] = "WIN", tp, j
                resolved = True
                break
        if not resolved:
            trade["outcome"] = "OPEN"

        position_size = (ACCOUNT_SIZE * RISK_PCT) / risk
        if trade["outcome"] in ("WIN", "LOSS"):
            move = (trade["exit_price"] - entry) if direction == "LONG" else (entry - trade["exit_price"])
            trade["pnl_cash"] = position_size * move
            trade["r_multiple"] = move / risk
        trades.append(trade)

    return trades, funnel


def report(bars_1m, trades, funnel, label):
    lines = []
    lines.append("=" * 112)
    lines.append(f"ORDER-FLOW CONFIRMED ORDER BLOCK STRATEGY - {label}")
    lines.append("=" * 112)
    lines.append(f"4H bias threshold: {BIAS_THRESHOLD_4H:.1%}   15m external: {EXT_THRESHOLD_15M:.1%}   "
                 f"15m internal: {INT_THRESHOLD_15M:.1%}   absorption mult: {ABSORPTION_VOL_MULT:.1f}x   "
                 f"TP: {TP_RR_MULT:.1f}R")
    lines.append("")

    closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
    header = (f"{'#':>3} {'Dir':<6} {'Sig':<10} {'Entry Date':<19} {'Exit Date':<19} {'Entry':>10} {'SL':>10} "
              f"{'TP':>10} {'Res':<5} {'PnL$':>9} {'R':>6} {'W-L':<8} {'Equity$':>10}")
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
        lines.append(f"{seq:>3} {t['direction']:<6} {t['signal_kind']:<10} {bars_1m[t['entry_idx']]['datetime']:<19} "
                     f"{bars_1m[t['exit_idx']]['datetime']:<19} {t['entry']:>10,.1f} {t['sl']:>10,.1f} "
                     f"{t['tp']:>10,.1f} {t['outcome']:<5} {t['pnl_cash']:>9,.2f} "
                     f"{t['r_multiple']:>6.2f} {f'{w}-{l}':<8} {equity:>10,.2f}")

    lines.append("")
    lines.append("-" * 112)
    lines.append("FUNNEL")
    lines.append(f"  15m legs (external swing-high<->swing-low)      : {funnel['legs']}")
    lines.append(f"  + 4H bias aligned with leg direction             : {funnel['bias_aligned']}")
    lines.append(f"  + order block marked                             : {funnel['ob_marked']}")
    lines.append(f"  + internal structure counter-trend + OB touched  : {funnel['ob_touched']}")
    lines.append(f"  + order-flow signal + confirmation close         : {funnel['signal_confirmed']}"
                 f"  (absorption: {funnel['signal_absorption']}, divergence: {funnel['signal_divergence']})")
    lines.append(f"  -> traded                                        : {funnel['traded']}")
    lines.append(f"  fake-outs (closed through far side of OB)        : {funnel['fakeout']}")
    lines.append("")
    lines.append("SUMMARY")
    lines.append(f"Legs evaluated   : {len(trades)}")
    lines.append(f"Closed trades    : {len(closed)}")
    lines.append(f"  Wins           : {w}")
    lines.append(f"  Losses         : {l}")
    if closed:
        lines.append(f"  Win rate       : {w/len(closed)*100:.1f}%")
        avg_r = sum(t["r_multiple"] for t in closed) / len(closed)
        lines.append(f"  Avg R-multiple : {avg_r:+.2f}R")
        lines.append(f"  Net P&L        : ${cum:+,.2f}  (${ACCOUNT_SIZE:,.0f} -> ${equity:,.2f})")
        mw = ml = cw = cl = 0
        for t in closed:
            if t["outcome"] == "WIN":
                cw += 1; cl = 0
            else:
                cl += 1; cw = 0
            mw, ml = max(mw, cw), max(ml, cl)
        lines.append(f"  Longest win/loss streak: {mw} / {ml}")
    return "\n".join(lines)


def parameter_sweep(bars_4h, bars_15m, bars_1m):
    lines = []
    lines.append("-" * 112)
    lines.append("PARAMETER SWEEP (15m external threshold x absorption volume multiplier)")
    lines.append("-" * 112)
    lines.append(f"{'ExtThr':>7} {'AbsMult':>7} {'Legs':>5} {'BiasOK':>7} {'OBMark':>7} {'Touched':>8} "
                 f"{'Closed':>7} {'W':>3} {'L':>3} {'Fake':>5} {'WinRate':>8} {'NetPnL':>10}")
    for ext_thr in (0.010, 0.015, 0.020, 0.030):
        for abs_mult in (1.5, 2.0, 3.0, 4.0):
            trades, funnel = run_order_flow_backtest(bars_4h, bars_15m, bars_1m,
                                                      ext_threshold=ext_thr, absorption_mult=abs_mult)
            closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
            w = sum(1 for t in closed if t["outcome"] == "WIN")
            l = len(closed) - w
            net = sum(t["pnl_cash"] for t in closed)
            wr = (w / len(closed) * 100) if closed else 0.0
            lines.append(f"{ext_thr:>6.1%} {abs_mult:>6.1f}x {funnel['legs']:>5} {funnel['bias_aligned']:>7} "
                         f"{funnel['ob_marked']:>7} {funnel['ob_touched']:>8} {len(closed):>7} {w:>3} {l:>3} "
                         f"{funnel['fakeout']:>5} {wr:>7.1f}% {net:>+10.2f}")
    return "\n".join(lines)


def main():
    bars_4h = load_bars(BARS_4H)
    bars_15m = load_bars(BARS_15M)
    bars_1m = load_1m_bars(BARS_1M)
    trades, funnel = run_order_flow_backtest(bars_4h, bars_15m, bars_1m)
    out = report(bars_1m, trades, funnel,
                 f"{bars_1m[0]['datetime']} -> {bars_1m[-1]['datetime']}")
    out += "\n\n" + parameter_sweep(bars_4h, bars_15m, bars_1m)
    print(out)
    with open("results_order_flow_mtf.txt", "w") as f:
        f.write(out + "\n")


if __name__ == "__main__":
    main()

"""
Block-trade confirmed order block + multi-timeframe structure backtest.

Same 4H bias -> 15m external/internal structure -> order block skeleton as
order_block_mtf_backtest.py (reused unchanged from that module), but the
entry trigger is now a real, individual large trade hitting the order
block - the closest thing to a genuine institutional footprint available
in this historical dataset.

Real order-book depth (resting bids/asks, walls appearing/disappearing)
would be the more direct way to see a big player's hand, but Kraken's
public Depth endpoint only ever returns the *current* live book - its
`since` parameter is silently ignored and there is no historical depth
data anywhere in the public API (confirmed by direct testing). That data
was never captured 30 days ago and can't be reconstructed retroactively,
so it can only support a live monitor, not a backtest.

What Kraken's trade feed does carry historically is the real aggressor
side of every individual trade. extract_block_trades.py pulls out every
single trade >= 1.0 BTC from the raw 30-day dump into data/block_trades.csv
(9,401 of them). The entry trigger here is: while price is trading at/
inside the order-block zone, a single trade >= BLOCK_SIZE_THRESHOLD BTC
prints on the side that would defend the zone (a large sell hitting a
resistance OB for a SHORT, a large buy hitting a support OB for a LONG).
That single print stands in for the old CHoCH/order-flow steps; entry then
requires one more 1-minute close that rejects back out of the zone
(confirmation), filling at the next bar's open. The same fake-out rule
applies throughout: a close through the *far* side of the zone before
confirmation completes kills the setup.

No lookahead anywhere; same $5,000 / 1% account convention as every other
variant here.
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
BLOCK_TRADES_PATH = "data/block_trades.csv"

BLOCK_SIZE_THRESHOLD = 2.0  # BTC - minimum single-trade size to count as a "block"
OB_TOUCH_WINDOW_1M = 240    # bars (4h) to wait for block signal -> confirmation before giving up
SL_BUFFER = 0.001
TP_RR_MULT = 2.0


def load_1m_bars(path):
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "timestamp": int(r["timestamp"]), "datetime": r["datetime"],
                "open": float(r["open"]), "high": float(r["high"]),
                "low": float(r["low"]), "close": float(r["close"]),
            })
    return rows


def load_block_trades(path):
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append((float(r["timestamp"]), float(r["price"]), float(r["volume"]), r["side"]))
    rows.sort()
    return rows


def find_block_signal(block_trades, block_ts, start_ts, end_ts, ob, direction, size_threshold):
    """First trade in [start_ts, end_ts] that is >= size_threshold BTC, trades
    at a price inside the OB zone, and is on the side that would defend it
    (sell into resistance for a SHORT, buy into support for a LONG)."""
    wanted_side = "s" if direction == "SHORT" else "b"
    i = bisect.bisect_left(block_ts, start_ts)
    while i < len(block_trades) and block_trades[i][0] <= end_ts:
        ts, price, vol, side = block_trades[i]
        if vol >= size_threshold and side == wanted_side and ob["low"] <= price <= ob["high"]:
            return block_trades[i]
        i += 1
    return None


def evaluate_1m_entry(bars_1m, ts_1m, block_trades, block_ts, touch_ts, ob, direction,
                       size_threshold=BLOCK_SIZE_THRESHOLD, window_bars=OB_TOUCH_WINDOW_1M):
    start_1m = bisect.bisect_left(ts_1m, touch_ts)
    if start_1m >= len(bars_1m):
        return {"outcome": "NO_1M_DATA"}
    end_1m = min(len(bars_1m) - 1, start_1m + window_bars)
    end_ts = bars_1m[end_1m]["timestamp"] + 60

    def broke_far_side(bar):
        return bar["close"] > ob["high"] if direction == "SHORT" else bar["close"] < ob["low"]

    signal = find_block_signal(block_trades, block_ts, touch_ts, end_ts, ob, direction, size_threshold)
    if signal is None:
        return {"outcome": "NO_SIGNAL_IN_WINDOW"}
    signal_ts, signal_price, signal_vol, signal_side = signal

    signal_bar_idx = bisect.bisect_right(ts_1m, signal_ts) - 1
    signal_bar_idx = max(signal_bar_idx, start_1m)

    for j in range(start_1m, min(signal_bar_idx, end_1m) + 1):
        if broke_far_side(bars_1m[j]):
            return {"outcome": "FAKEOUT", "fakeout_idx": j}

    confirm_idx = None
    for j in range(signal_bar_idx, end_1m + 1):
        bar = bars_1m[j]
        if broke_far_side(bar):
            return {"outcome": "FAKEOUT", "fakeout_idx": j, "signal_ts": signal_ts}
        rejected = (bar["close"] < ob["low"]) if direction == "SHORT" else (bar["close"] > ob["high"])
        if rejected:
            confirm_idx = j
            break
    if confirm_idx is None or confirm_idx + 1 >= len(bars_1m) or confirm_idx + 1 > end_1m:
        return {"outcome": "NO_CONFIRMATION_IN_WINDOW", "signal_ts": signal_ts}

    return {"outcome": "ENTRY", "signal_ts": signal_ts, "signal_price": signal_price,
            "signal_vol": signal_vol, "confirm_idx": confirm_idx, "entry_idx": confirm_idx + 1}


def run_block_trade_backtest(bars_4h, bars_15m, bars_1m, block_trades, ext_threshold=EXT_THRESHOLD_15M,
                              size_threshold=BLOCK_SIZE_THRESHOLD, tp_rr_mult=TP_RR_MULT):
    pivots_4h = find_pivots(bars_4h, BIAS_THRESHOLD_4H)
    bias_ts, bias_vals = bias_lookup_table(bars_4h, pivots_4h)
    pivots_15m = find_pivots(bars_15m, ext_threshold)
    ts_1m = [b["timestamp"] for b in bars_1m]
    block_ts = [bt[0] for bt in block_trades]

    trades = []
    funnel = {"legs": 0, "bias_aligned": 0, "ob_marked": 0, "ob_touched": 0,
              "block_signal_confirmed": 0, "fakeout": 0, "traded": 0}

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

        result = evaluate_1m_entry(bars_1m, ts_1m, block_trades, block_ts,
                                    bars_15m[touch_idx]["timestamp"], ob, direction,
                                    size_threshold=size_threshold)
        if result["outcome"] == "FAKEOUT":
            funnel["fakeout"] += 1
            trade["outcome"] = "FAKEOUT"
            trades.append(trade)
            continue
        if result["outcome"] != "ENTRY":
            trade["outcome"] = result["outcome"]
            trades.append(trade)
            continue
        funnel["block_signal_confirmed"] += 1
        trade["signal_vol"] = result["signal_vol"]

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
    lines.append(f"BLOCK-TRADE CONFIRMED ORDER BLOCK STRATEGY - {label}")
    lines.append("=" * 112)
    lines.append(f"4H bias threshold: {BIAS_THRESHOLD_4H:.1%}   15m external: {EXT_THRESHOLD_15M:.1%}   "
                 f"15m internal: {INT_THRESHOLD_15M:.1%}   block size: {BLOCK_SIZE_THRESHOLD:.1f} BTC   "
                 f"TP: {TP_RR_MULT:.1f}R")
    lines.append("")

    closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
    header = (f"{'#':>3} {'Dir':<6} {'BlockBTC':>9} {'Entry Date':<19} {'Exit Date':<19} {'Entry':>10} "
              f"{'SL':>10} {'TP':>10} {'Res':<5} {'PnL$':>9} {'R':>6} {'W-L':<8} {'Equity$':>10}")
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
        lines.append(f"{seq:>3} {t['direction']:<6} {t['signal_vol']:>9.2f} "
                     f"{bars_1m[t['entry_idx']]['datetime']:<19} {bars_1m[t['exit_idx']]['datetime']:<19} "
                     f"{t['entry']:>10,.1f} {t['sl']:>10,.1f} {t['tp']:>10,.1f} {t['outcome']:<5} "
                     f"{t['pnl_cash']:>9,.2f} {t['r_multiple']:>6.2f} {f'{w}-{l}':<8} {equity:>10,.2f}")

    lines.append("")
    lines.append("-" * 112)
    lines.append("FUNNEL")
    lines.append(f"  15m legs (external swing-high<->swing-low)      : {funnel['legs']}")
    lines.append(f"  + 4H bias aligned with leg direction             : {funnel['bias_aligned']}")
    lines.append(f"  + order block marked                             : {funnel['ob_marked']}")
    lines.append(f"  + internal structure counter-trend + OB touched  : {funnel['ob_touched']}")
    lines.append(f"  + defending block trade + confirmation close     : {funnel['block_signal_confirmed']}")
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


def parameter_sweep(bars_4h, bars_15m, bars_1m, block_trades):
    lines = []
    lines.append("-" * 112)
    lines.append("PARAMETER SWEEP (15m external threshold x block-size threshold)")
    lines.append("-" * 112)
    lines.append(f"{'ExtThr':>7} {'BlockBTC':>8} {'Legs':>5} {'BiasOK':>7} {'OBMark':>7} {'Touched':>8} "
                 f"{'Closed':>7} {'W':>3} {'L':>3} {'Fake':>5} {'WinRate':>8} {'NetPnL':>10}")
    for ext_thr in (0.010, 0.015, 0.020, 0.030):
        for size_thr in (1.0, 2.0, 3.0, 5.0, 8.0):
            trades, funnel = run_block_trade_backtest(bars_4h, bars_15m, bars_1m, block_trades,
                                                       ext_threshold=ext_thr, size_threshold=size_thr)
            closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
            w = sum(1 for t in closed if t["outcome"] == "WIN")
            l = len(closed) - w
            net = sum(t["pnl_cash"] for t in closed)
            wr = (w / len(closed) * 100) if closed else 0.0
            lines.append(f"{ext_thr:>6.1%} {size_thr:>7.1f} {funnel['legs']:>5} {funnel['bias_aligned']:>7} "
                         f"{funnel['ob_marked']:>7} {funnel['ob_touched']:>8} {len(closed):>7} {w:>3} {l:>3} "
                         f"{funnel['fakeout']:>5} {wr:>7.1f}% {net:>+10.2f}")
    return "\n".join(lines)


def main():
    bars_4h = load_bars(BARS_4H)
    bars_15m = load_bars(BARS_15M)
    bars_1m = load_1m_bars(BARS_1M)
    block_trades = load_block_trades(BLOCK_TRADES_PATH)
    trades, funnel = run_block_trade_backtest(bars_4h, bars_15m, bars_1m, block_trades)
    out = report(bars_1m, trades, funnel,
                 f"{bars_1m[0]['datetime']} -> {bars_1m[-1]['datetime']}")
    out += "\n\n" + parameter_sweep(bars_4h, bars_15m, bars_1m, block_trades)
    print(out)
    with open("results_block_trade_mtf.txt", "w") as f:
        f.write(out + "\n")


if __name__ == "__main__":
    main()

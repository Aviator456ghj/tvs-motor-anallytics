"""
Order Block + Multi-Timeframe Market Structure backtest on BTCUSD.

Implements the ICT-style "smart money" entry sequence requested:
  1. 4-hour bias - bullish only once structure prints a confirmed Higher
     High AND Higher Low back to back (HH+HL); bearish only once it prints
     a Lower High AND Lower Low (LH+LL). A single new extreme alone
     doesn't flip it - both legs of the pair have to agree.
  2. 15-minute external structure - the latest two confirmed swing points
     (zig-zag pivots) define the "current leg." For a SHORT, that leg must
     run swing-high -> swing-low (a down-leg) and the 4H bias looked up at
     that leg's confirmation time must be BEARISH (mirror image for LONG).
  3. Order block - scanning backward from the leg's swing-extreme to its
     origin, the last opposite-colour 15-min candle (the last up-close
     candle before a down-impulse, or vice versa) is marked as the
     order-block zone (its full high/low range).
  4. Internal structure - from the swing-extreme forward, 15-minute price
     action is re-zig-zagged with a smaller threshold. The setup only
     stays alive once that *internal* structure is currently pushing
     counter to the leg's direction (an internal rally inside an external
     down-leg, or an internal dip inside an external up-leg) AND price
     actually trades back into the order-block zone.
  5. 1-minute change of character (CHoCH) - once the OB zone is touched,
     drop to 1-minute bars. The CHoCH reference level is the most recent
     confirmed 1-minute swing low (for a SHORT) or high (for a LONG)
     formed since the leg's swing-extreme; a 1-minute close back through
     that level is the change of character signalling the internal rally
     just reversed.
  6. Pullback + confirmation - after CHoCH, wait for price to trade back
     into the OB zone one more time (the pullback), then enter on the
     first 1-minute close that rejects back out of the zone. Entry fills
     at the next 1-minute bar's open (no lookahead).
  7. Fake-out detection - at any point before a valid CHoCH+pullback+
     confirmation completes, if price instead closes all the way through
     the far side of the OB zone, the setup is marked FAKEOUT and never
     traded - this is the liquidity-grab/stop-hunt case the order block
     was supposed to defend against.

Data: Kraken's public OHLC endpoint only ever serves the most recent 720
candles per interval (12h at 1-minute resolution - nowhere near enough),
so all three timeframes here are built by build_mtf_bars.py from the same
30-day raw trade dump already fetched for the CVD variant, guaranteeing
the 1m/15m/4h bars are mutually consistent (same underlying ticks).

No lookahead anywhere: every decision at bar j uses only opens/highs/lows/
closes through bar j; entries fill at the following bar's open.
Same $5,000 / 1% account convention as every other variant in this repo.
"""
import csv
import bisect

from measured_swing_backtest import find_pivots, ACCOUNT_SIZE, RISK_PCT

BARS_4H = "data/btc_usd_4h.csv"
BARS_15M = "data/btc_usd_15min.csv"
BARS_1M = "data/btc_usd_1min.csv"

BIAS_THRESHOLD_4H = 0.03        # 4H zig-zag threshold for the HH/HL vs LH/LL bias classifier
EXT_THRESHOLD_15M = 0.015       # 15-min external swing threshold (defines the tradeable "leg")
INT_THRESHOLD_15M = 0.005       # 15-min internal swing threshold (the corrective move inside the leg)
CHOCH_THRESHOLD_1M = 0.0015     # 1-min internal swing threshold (CHoCH reference level)
OB_TOUCH_WINDOW_1M = 240        # bars (4h) to wait for CHoCH -> pullback -> confirmation before giving up
SL_BUFFER = 0.001               # stop placed this far beyond the OB zone boundary
TP_RR_MULT = 2.0                # reward sized as a multiple of risk


def load_bars(path):
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


def compute_bias_events(pivots):
    """Replay confirmed pivots (drop the final provisional one) and emit a
    (confirm_idx, bias) timeline. Bias only changes once the latest two
    highs AND the latest two lows agree on direction (HH+HL or LH+LL);
    a lone new extreme holds the previous bias rather than flipping it."""
    events = []
    highs, lows = [], []
    bias = None
    for p in pivots[:-1]:
        if p.kind == "H":
            highs.append(p.price)
        else:
            lows.append(p.price)
        if len(highs) >= 2 and len(lows) >= 2:
            if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
                bias = "BULLISH"
            elif highs[-1] < highs[-2] and lows[-1] < lows[-2]:
                bias = "BEARISH"
        events.append((p.confirm_idx, bias))
    return events


def bias_lookup_table(bars_4h, pivots_4h):
    events = compute_bias_events(pivots_4h)
    table_ts = [bars_4h[idx]["timestamp"] for idx, _ in events]
    table_bias = [b for _, b in events]
    return table_ts, table_bias


def bias_at(table_ts, table_bias, ts):
    i = bisect.bisect_right(table_ts, ts) - 1
    if i < 0:
        return None
    return table_bias[i]


def find_order_block(bars, start_idx, end_idx, direction):
    """Scanning backward from the swing extreme to the leg's origin, the
    last opposite-colour candle before the impulse - bearish OB = last
    up-close candle before a down-impulse; bullish OB = last down-close
    candle before an up-impulse."""
    for k in range(end_idx, start_idx - 1, -1):
        bar = bars[k]
        is_bullish = bar["close"] > bar["open"]
        if direction == "SHORT" and is_bullish:
            return {"idx": k, "high": bar["high"], "low": bar["low"]}
        if direction == "LONG" and not is_bullish:
            return {"idx": k, "high": bar["high"], "low": bar["low"]}
    return None


def scan_for_ob_touch(bars_15m, p1_idx, window_end, ob, direction, int_threshold):
    """From the swing extreme forward, re-zig-zag the growing slice each
    bar to read the *current* internal trend (the function's final,
    still-provisional pivot direction). Once that internal trend is
    counter to the leg AND price has actually traded into the OB zone,
    return that bar index."""
    for j in range(p1_idx, window_end + 1):
        sub = bars_15m[p1_idx:j + 1]
        if len(sub) < 2:
            continue
        sub_pivots = find_pivots(sub, int_threshold)
        internal_trend_up = sub_pivots[-1].kind == "H"
        bar = bars_15m[j]
        if direction == "SHORT":
            counter_trend = internal_trend_up
            touched = bar["high"] >= ob["low"]
        else:
            counter_trend = not internal_trend_up
            touched = bar["low"] <= ob["high"]
        if counter_trend and touched:
            return j
    return None


def choch_reference_level(bars_1m, lookback_start_idx, touch_idx, threshold, direction):
    """Most recent confirmed 1-min swing low (SHORT) / high (LONG) since
    the 15-min swing extreme; falls back to that extreme's own level if
    the rally was too sharp for even one internal 1-min pivot to confirm."""
    sub = bars_1m[lookback_start_idx:touch_idx + 1]
    fallback = bars_1m[lookback_start_idx]["low" if direction == "SHORT" else "high"]
    if len(sub) < 2:
        return fallback
    pivots = find_pivots(sub, threshold)
    kind_wanted = "L" if direction == "SHORT" else "H"
    candidates = [p for p in pivots[:-1] if p.kind == kind_wanted]
    return candidates[-1].price if candidates else fallback


def evaluate_1m_entry(bars_1m, ts_1m, p1_ts, touch_ts, ob, direction,
                       choch_threshold=CHOCH_THRESHOLD_1M, window_bars=OB_TOUCH_WINDOW_1M):
    start_1m = bisect.bisect_left(ts_1m, touch_ts)
    if start_1m >= len(bars_1m):
        return {"outcome": "NO_1M_DATA"}
    lookback_1m = min(bisect.bisect_left(ts_1m, p1_ts), start_1m)
    end_1m = min(len(bars_1m) - 1, start_1m + window_bars)
    ref_level = choch_reference_level(bars_1m, lookback_1m, start_1m, choch_threshold, direction)

    def broke_far_side(bar):
        return bar["close"] > ob["high"] if direction == "SHORT" else bar["close"] < ob["low"]

    choch_idx = None
    for j in range(start_1m, end_1m + 1):
        bar = bars_1m[j]
        if broke_far_side(bar):
            return {"outcome": "FAKEOUT", "fakeout_idx": j}
        choch_hit = bar["close"] < ref_level if direction == "SHORT" else bar["close"] > ref_level
        if choch_hit:
            choch_idx = j
            break
    if choch_idx is None:
        return {"outcome": "NO_CHOCH_IN_WINDOW"}

    pullback_idx = None
    for j in range(choch_idx + 1, end_1m + 1):
        bar = bars_1m[j]
        if broke_far_side(bar):
            return {"outcome": "FAKEOUT", "fakeout_idx": j, "choch_idx": choch_idx}
        touched_again = (bar["high"] >= ob["low"]) if direction == "SHORT" else (bar["low"] <= ob["high"])
        if touched_again:
            pullback_idx = j
            break
    if pullback_idx is None:
        return {"outcome": "NO_PULLBACK_IN_WINDOW", "choch_idx": choch_idx}

    confirm_idx = None
    for j in range(pullback_idx, end_1m + 1):
        bar = bars_1m[j]
        if broke_far_side(bar):
            return {"outcome": "FAKEOUT", "fakeout_idx": j, "choch_idx": choch_idx, "pullback_idx": pullback_idx}
        rejected = (bar["close"] < ob["low"]) if direction == "SHORT" else (bar["close"] > ob["high"])
        if rejected:
            confirm_idx = j
            break
    if confirm_idx is None or confirm_idx + 1 >= len(bars_1m) or confirm_idx + 1 > end_1m:
        return {"outcome": "NO_CONFIRMATION_IN_WINDOW", "choch_idx": choch_idx, "pullback_idx": pullback_idx}

    return {"outcome": "ENTRY", "choch_idx": choch_idx, "pullback_idx": pullback_idx,
            "confirm_idx": confirm_idx, "entry_idx": confirm_idx + 1}


def run_order_block_backtest(bars_4h, bars_15m, bars_1m, ext_threshold=EXT_THRESHOLD_15M,
                              tp_rr_mult=TP_RR_MULT):
    pivots_4h = find_pivots(bars_4h, BIAS_THRESHOLD_4H)
    bias_ts, bias_vals = bias_lookup_table(bars_4h, pivots_4h)
    pivots_15m = find_pivots(bars_15m, ext_threshold)
    ts_1m = [b["timestamp"] for b in bars_1m]

    trades = []
    funnel = {"legs": 0, "bias_aligned": 0, "ob_marked": 0, "ob_touched": 0,
              "choch_confirmed": 0, "pullback_confirmed": 0, "fakeout": 0, "traded": 0}

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

        result = evaluate_1m_entry(bars_1m, ts_1m, bars_15m[p1.idx]["timestamp"],
                                    bars_15m[touch_idx]["timestamp"], ob, direction)
        if result["outcome"] == "FAKEOUT":
            funnel["fakeout"] += 1
            trade["outcome"] = "FAKEOUT"
            trades.append(trade)
            continue
        if result["outcome"] != "ENTRY":
            trade["outcome"] = result["outcome"]
            trades.append(trade)
            continue
        funnel["choch_confirmed"] += 1
        funnel["pullback_confirmed"] += 1

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
    lines.append(f"ORDER BLOCK + MULTI-TIMEFRAME STRUCTURE STRATEGY - {label}")
    lines.append("=" * 112)
    lines.append(f"4H bias threshold: {BIAS_THRESHOLD_4H:.1%}   15m external: {EXT_THRESHOLD_15M:.1%}   "
                 f"15m internal: {INT_THRESHOLD_15M:.1%}   1m CHoCH: {CHOCH_THRESHOLD_1M:.2%}   "
                 f"TP: {TP_RR_MULT:.1f}R")
    lines.append("")

    closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
    header = (f"{'#':>3} {'Dir':<6} {'Entry Date':<19} {'Exit Date':<19} {'Entry':>10} {'SL':>10} {'TP':>10} "
              f"{'Res':<5} {'PnL$':>9} {'R':>6} {'W-L':<8} {'Equity$':>10}")
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
        lines.append(f"{seq:>3} {t['direction']:<6} {bars_1m[t['entry_idx']]['datetime']:<19} "
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
    lines.append(f"  + 1m CHoCH confirmed                             : {funnel['choch_confirmed']}")
    lines.append(f"  + pullback into OB confirmed                     : {funnel['pullback_confirmed']}")
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
    lines.append("PARAMETER SWEEP (15m external threshold x TP R-multiple)")
    lines.append("-" * 112)
    lines.append(f"{'ExtThr':>7} {'TP_R':>5} {'Legs':>5} {'BiasOK':>7} {'OBMark':>7} {'Touched':>8} "
                 f"{'Closed':>7} {'W':>3} {'L':>3} {'Fake':>5} {'WinRate':>8} {'NetPnL':>10}")
    for ext_thr in (0.010, 0.015, 0.020, 0.030):
        for tp_r in (1.0, 1.5, 2.0, 3.0):
            trades, funnel = run_order_block_backtest(bars_4h, bars_15m, bars_1m,
                                                        ext_threshold=ext_thr, tp_rr_mult=tp_r)
            closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
            w = sum(1 for t in closed if t["outcome"] == "WIN")
            l = len(closed) - w
            net = sum(t["pnl_cash"] for t in closed)
            wr = (w / len(closed) * 100) if closed else 0.0
            lines.append(f"{ext_thr:>6.1%} {tp_r:>5.1f} {funnel['legs']:>5} {funnel['bias_aligned']:>7} "
                         f"{funnel['ob_marked']:>7} {funnel['ob_touched']:>8} {len(closed):>7} {w:>3} {l:>3} "
                         f"{funnel['fakeout']:>5} {wr:>7.1f}% {net:>+10.2f}")
    return "\n".join(lines)


def main():
    bars_4h = load_bars(BARS_4H)
    bars_15m = load_bars(BARS_15M)
    bars_1m = load_bars(BARS_1M)
    trades, funnel = run_order_block_backtest(bars_4h, bars_15m, bars_1m)
    out = report(bars_1m, trades, funnel,
                 f"{bars_1m[0]['datetime']} -> {bars_1m[-1]['datetime']}")
    out += "\n\n" + parameter_sweep(bars_4h, bars_15m, bars_1m)
    print(out)
    with open("results_order_block_mtf.txt", "w") as f:
        f.write(out + "\n")


if __name__ == "__main__":
    main()

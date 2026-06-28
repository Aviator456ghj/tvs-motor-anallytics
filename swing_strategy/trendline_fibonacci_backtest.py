"""
Trendline + Fibonacci confluence backtest on BTCUSD daily candles.

Distinct from the two Fib variants already in this repo:
  - measured_swing_backtest.py: pure Fib retracement (61.8% entry / 78.6%
    stop / origin TP), no trend confirmation at all. 24.5% WR, -$837,
    robustly net-negative across the threshold sweep.
  - trend_filtered_backtest.py: same Fib math, gated by a 50/200 SMA
    *macro* trend filter. Also failed - "macro SMA trend direction does
    not predict whether a 61.8% retracement entry resolves to TP or SL".

This variant replaces the macro SMA gate with an actual drawn TRENDLINE -
the classic technical-analysis combo of connecting the last two same-kind
swing pivots (two rising lows in an uptrend, two falling highs in a
downtrend) and projecting that line forward as dynamic support/resistance.
The idea: a retracement into the 50-61.8% Fib zone is only a continuation
entry if it also respects the structural trendline; a retracement that
closes through both the trendline AND the 78.6% invalidation line is
treated as a trend break, not a buyable dip.

Entry sequence for an up-trend continuation (mirror image for down-trends):
  1. Confirmed legs p_prev(L) -> p0(L) -> p1(H): p_prev/p0 are two rising
     lows defining the trendline; p1 is the impulse high being retraced.
  2. Walk forward from p1's confirmation bar. Price must dip into the
     50-61.8% Fib zone (golden zone) without a CLOSE breaking the 78.6%
     invalidation line or closing meaningfully below the trendline
     extrapolated to that bar - either breach invalidates the setup.
  3. Once the zone has been touched and the setup survives, the first bar
     that closes back above the zone's shallow (50%) edge is the bounce
     confirmation. Entry fills at the NEXT bar's open (no lookahead).
  4. SL sits just beyond the 78.6% invalidation line; TP is a 127.2% Fib
     extension beyond the original impulse leg.

No lookahead: every decision uses only closes/highs/lows through the bar
being evaluated; entries fill at the following bar's open. Same $5,000/1%
account sizing as the other variants here.
"""
from measured_swing_backtest import load_data, find_pivots, ACCOUNT_SIZE, RISK_PCT

DAILY_SRC = "data/btc_usd_daily.csv"

ZIGZAG_THRESHOLD = 0.08
FIB_GOLDEN_LOW = 0.5        # shallow edge of the golden zone (50% retrace)
FIB_GOLDEN_HIGH = 0.618     # deep edge of the golden zone (61.8% retrace)
FIB_INVALIDATION = 0.786    # beyond this retrace, the setup is invalidated
TRENDLINE_BUFFER = 0.01     # 1% slack below/above the extrapolated trendline before calling it broken
SL_BUFFER = 0.02            # stop placed this far beyond the invalidation line
TP_EXTENSION = 1.272        # Fib extension target beyond the impulse leg
MIN_RR = 1.0


def trendline_price(p_from, p_to, idx):
    """Linear trendline through two same-kind pivots, extrapolated to idx."""
    if p_to.idx == p_from.idx:
        return p_to.price
    slope = (p_to.price - p_from.price) / (p_to.idx - p_from.idx)
    return p_to.price + slope * (idx - p_to.idx)


def run_trendline_fib_backtest(bars, pivots, golden_low=FIB_GOLDEN_LOW, golden_high=FIB_GOLDEN_HIGH,
                                invalidation=FIB_INVALIDATION, tp_extension=TP_EXTENSION):
    trades = []
    funnel = {"legs_evaluated": 0, "zone_touched": 0, "survived_to_bounce": 0,
              "bounce_confirmed": 0, "rr_ok": 0, "traded": 0}

    for i in range(2, len(pivots) - 1):
        p_prev, p0, p1 = pivots[i - 2], pivots[i], pivots[i + 1]
        if p_prev.kind != p0.kind:
            continue  # strictly alternating zig-zag guarantees same kind 2 apart, but guard anyway
        funnel["legs_evaluated"] += 1

        direction = "LONG" if p1.kind == "H" else "SHORT"
        rng = abs(p1.price - p0.price)

        if direction == "LONG":
            golden_hi_price = p1.price - golden_low * rng
            golden_lo_price = p1.price - golden_high * rng
            invalidation_price = p1.price - invalidation * rng
        else:
            golden_lo_price = p1.price + golden_low * rng
            golden_hi_price = p1.price + golden_high * rng
            invalidation_price = p1.price + invalidation * rng

        window_end = pivots[i + 2].confirm_idx if i + 2 < len(pivots) else len(bars) - 1
        start = p1.confirm_idx + 1

        trade = {"direction": direction, "swing_origin": p0.price, "swing_point": p1.price,
                  "golden_lo": golden_lo_price, "golden_hi": golden_hi_price,
                  "invalidation": invalidation_price, "outcome": None}

        touched_zone = False
        entry_idx = None
        for j in range(start, window_end + 1):
            bar = bars[j]
            tl_price = trendline_price(p_prev, p0, j)

            if direction == "LONG":
                broke_invalidation = bar["close"] < invalidation_price
                broke_trendline = bar["close"] < tl_price * (1 - TRENDLINE_BUFFER)
            else:
                broke_invalidation = bar["close"] > invalidation_price
                broke_trendline = bar["close"] > tl_price * (1 + TRENDLINE_BUFFER)

            if broke_invalidation or broke_trendline:
                trade["outcome"] = "INVALIDATED_BEFORE_BOUNCE" if touched_zone else "INVALIDATED_NO_TOUCH"
                break

            in_zone = (bar["low"] <= golden_hi_price) if direction == "LONG" else (bar["high"] >= golden_lo_price)
            if in_zone and not touched_zone:
                touched_zone = True
                funnel["zone_touched"] += 1

            if touched_zone:
                bounced = (bar["close"] > golden_hi_price) if direction == "LONG" else (bar["close"] < golden_lo_price)
                if bounced and j + 1 <= window_end:
                    entry_idx = j + 1
                    break

        if entry_idx is not None:
            funnel["survived_to_bounce"] += 1
            funnel["bounce_confirmed"] += 1
        elif trade["outcome"] is None:
            trade["outcome"] = "NO_BOUNCE_IN_WINDOW" if touched_zone else "NO_ZONE_TOUCH"

        if entry_idx is None:
            trades.append(trade)
            continue

        trade["entry_idx"] = entry_idx
        entry = bars[entry_idx]["open"]
        trade["entry"] = entry

        if direction == "LONG":
            sl = invalidation_price * (1 - SL_BUFFER)
            tp = p1.price + rng * tp_extension
        else:
            sl = invalidation_price * (1 + SL_BUFFER)
            tp = p1.price - rng * tp_extension
        trade["sl"], trade["tp"] = sl, tp

        risk_per_unit = abs(entry - sl)
        if risk_per_unit <= 0 or (direction == "LONG" and (sl >= entry or tp <= entry)) or \
                (direction == "SHORT" and (sl <= entry or tp >= entry)):
            trade["outcome"] = "BAD_RISK_GEOMETRY"
            trades.append(trade)
            continue

        reward_per_unit = abs(tp - entry)
        if reward_per_unit / risk_per_unit < MIN_RR:
            trade["outcome"] = "RR_TOO_LOW"
            trades.append(trade)
            continue
        funnel["rr_ok"] += 1
        funnel["traded"] += 1

        resolved = False
        for j in range(entry_idx, len(bars)):
            bar = bars[j]
            if direction == "LONG":
                hit_sl, hit_tp = bar["low"] <= sl, bar["high"] >= tp
            else:
                hit_sl, hit_tp = bar["high"] >= sl, bar["low"] <= tp
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

        position_size = (ACCOUNT_SIZE * RISK_PCT) / risk_per_unit
        if trade["outcome"] in ("WIN", "LOSS"):
            move = (trade["exit_price"] - entry) if direction == "LONG" else (entry - trade["exit_price"])
            trade["pnl_cash"] = position_size * move
            trade["r_multiple"] = move / risk_per_unit
        trades.append(trade)

    return trades, funnel


def report(bars, trades, funnel, label):
    lines = []
    lines.append("=" * 108)
    lines.append(f"TRENDLINE + FIBONACCI CONFLUENCE STRATEGY - {label}")
    lines.append("=" * 108)
    lines.append(f"Golden zone: {FIB_GOLDEN_LOW:.1%}-{FIB_GOLDEN_HIGH:.1%} retrace   "
                 f"Invalidation: {FIB_INVALIDATION:.1%} retrace OR trendline break ({TRENDLINE_BUFFER:.1%} slack)   "
                 f"TP extension: {TP_EXTENSION:.1%}")
    lines.append("")

    closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
    no_touch = sum(1 for t in trades if t["outcome"] in ("NO_ZONE_TOUCH", "INVALIDATED_NO_TOUCH"))
    no_bounce = sum(1 for t in trades if t["outcome"] in ("NO_BOUNCE_IN_WINDOW", "INVALIDATED_BEFORE_BOUNCE"))
    bad_geometry = sum(1 for t in trades if t["outcome"] in ("BAD_RISK_GEOMETRY", "RR_TOO_LOW"))

    header = (f"{'#':>3} {'Dir':<6} {'Entry Date':<11} {'Exit Date':<11} {'Entry':>10} {'SL':>10} {'TP':>10} "
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
        lines.append(f"{seq:>3} {t['direction']:<6} {bars[t['entry_idx']]['date']:<11} "
                     f"{bars[t['exit_idx']]['date']:<11} {t['entry']:>10,.1f} {t['sl']:>10,.1f} "
                     f"{t['tp']:>10,.1f} {t['outcome']:<5} {t['pnl_cash']:>9,.2f} "
                     f"{t['r_multiple']:>6.2f} {f'{w}-{l}':<8} {equity:>10,.2f}")

    lines.append("")
    lines.append("-" * 108)
    lines.append("FUNNEL")
    lines.append(f"  Legs evaluated (3 consecutive same-trend pivots) : {funnel['legs_evaluated']}")
    lines.append(f"  + retraced into the 50-61.8% golden zone         : {funnel['zone_touched']}")
    lines.append(f"  + survived (no invalidation/trendline break)     : {funnel['survived_to_bounce']}")
    lines.append(f"  + bounce confirmed (closed back out of zone)     : {funnel['bounce_confirmed']}")
    lines.append(f"  + risk/reward >= {MIN_RR}                              : {funnel['rr_ok']}")
    lines.append(f"  -> traded                                        : {funnel['traded']}")
    lines.append("")
    lines.append(f"Never reached/survived the golden zone : {no_touch}")
    lines.append(f"Touched zone but never bounced in time : {no_bounce}")
    lines.append(f"Bounced but failed risk/reward geometry : {bad_geometry}")
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


def parameter_sweep(bars):
    lines = []
    lines.append("-" * 108)
    lines.append("PARAMETER SWEEP (zig-zag threshold x TP extension)")
    lines.append("-" * 108)
    lines.append(f"{'Thresh':>6} {'TPExt':>6} {'Legs':>5} {'NoZone':>7} {'NoBounce':>8} {'Closed':>7} "
                 f"{'W':>3} {'L':>3} {'WinRate':>8} {'NetPnL':>10}")
    for pct in (0.05, 0.06, 0.08, 0.10, 0.12, 0.15):
        pivots = find_pivots(bars, pct)
        for tp_ext in (1.0, 1.272, 1.618):
            trades, funnel = run_trendline_fib_backtest(bars, pivots, tp_extension=tp_ext)
            closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
            no_touch = sum(1 for t in trades if t["outcome"] in ("NO_ZONE_TOUCH", "INVALIDATED_NO_TOUCH"))
            no_bounce = sum(1 for t in trades if t["outcome"] in ("NO_BOUNCE_IN_WINDOW", "INVALIDATED_BEFORE_BOUNCE"))
            w = sum(1 for t in closed if t["outcome"] == "WIN")
            l = len(closed) - w
            net = sum(t["pnl_cash"] for t in closed)
            wr = (w / len(closed) * 100) if closed else 0.0
            lines.append(f"{pct:>5.0%} {tp_ext:>6.3f} {len(trades):>5} {no_touch:>7} {no_bounce:>8} "
                         f"{len(closed):>7} {w:>3} {l:>3} {wr:>7.1f}% {net:>+10.2f}")
    return "\n".join(lines)


def main():
    bars = load_data(DAILY_SRC)
    pivots = find_pivots(bars, ZIGZAG_THRESHOLD)
    trades, funnel = run_trendline_fib_backtest(bars, pivots)
    out = report(bars, trades, funnel, f"{ZIGZAG_THRESHOLD:.0%} zig-zag, {bars[0]['date']} -> {bars[-1]['date']}")
    out += "\n\n" + parameter_sweep(bars)
    print(out)
    with open("results_trendline_fibonacci.txt", "w") as f:
        f.write(out + "\n")


if __name__ == "__main__":
    main()

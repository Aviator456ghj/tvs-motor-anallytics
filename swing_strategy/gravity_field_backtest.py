"""
Gravity-field ("price magnet") backtest on BTCUSD daily candles.

Reframes the chart as a 1-D mass-distribution problem instead of a cycle:
every historical close is one unit of "mass" sitting at its price level;
levels visited often (support/resistance, value areas, congestion zones)
accumulate more mass than levels price blew straight through. The chart's
own physics textbook answer for why price gets pulled back to - and pushed
away from - certain zones is the same answer 1-D gravity gives for why a
point mass feels a force from a line of other masses:

  In ONE dimension the gravitational potential of a point mass is
  logarithmic (not the familiar 1/r of 3-D space):  U(x) = -G*m*ln|x|
  Force is its negative gradient:                   F(x) = -dU/dx = G*m/x

Treating the historical close-price histogram as a density of masses along
the (log-)price axis and summing this 1/distance force from every
historical level to today's price gives a single number: net gravitational
pull. Positive = more/closer historical mass sits above current price than
below -> price is being pulled UP toward zones it occupied before. The
take-profit projects WHERE in the future price is headed by walking that
same force's direction outward from today's price until it hits the next
prominent local peak in the smoothed density curve - the next "magnet"
zone, i.e. literally the next area-occurred-before that the model expects
price to revisit.

No lookahead: the density histogram for day i is built only from closes
strictly before i; the force/peak-target/entry decision uses information
available through day i's own close; the order fills at day i+1's open.
Same $5,000 / 1% account sizing as the other daily variants here.
"""
import statistics
from math import exp, log

from measured_swing_backtest import load_data, ACCOUNT_SIZE, RISK_PCT

DAILY_SRC = "data/btc_usd_daily.csv"

LOOKBACK_DAYS = 180        # how much price history builds "the" mass distribution
BIN_PCT = 0.02             # log-price bin width, ~2% of price per bin (scale-invariant)
SMOOTH_BINS = 2            # +/- bins averaged when smoothing the density curve
FORCE_Z_WINDOW = 90        # window for z-scoring the raw gravity force
FORCE_Z_THRESHOLD = 1.0    # how many sigma of "unusual pull" required to trade
MIN_PEAK_SCAN_BINS = 2     # a target peak must be at least this many bins away (not next-door noise)
MAX_PEAK_SCAN_BINS = 60    # give up looking for a target this far out
PEAK_PROMINENCE_MULT = 1.0 # candidate peak's density must beat this x the mean nonzero density
SL_LOOKBACK_DAYS = 14
SL_STDEV_MULT = 1.5
MIN_RR = 1.0               # minimal risk/reward sanity floor


def build_density(closes, i, lookback, bin_width):
    bins = {}
    for j in range(max(0, i - lookback), i):
        k = round(log(closes[j]) / bin_width)
        bins[k] = bins.get(k, 0) + 1
    return bins


def smooth_density(bins, smooth):
    if not bins:
        return bins
    keys = sorted(bins)
    out = {}
    for k in range(keys[0] - smooth, keys[-1] + smooth + 1):
        vals = [bins.get(kk, 0) for kk in range(k - smooth, k + smooth + 1)]
        out[k] = sum(vals) / len(vals)
    return out


def gravity_force(bins, x_now_bin, eps=0.5):
    force = 0.0
    for k, mass in bins.items():
        dist = k - x_now_bin
        if abs(dist) < eps:
            dist = eps if dist >= 0 else -eps
        force += mass / dist
    return force


def find_peak_target(smoothed, x_now_bin, direction, bin_width):
    """Walk outward from today's price, in the direction the force points,
    looking for the next local-maximum density bin (a historical magnet
    zone) that's actually prominent, not just noise. Returns a price or
    None if no qualifying peak is found within the scan range."""
    if not smoothed:
        return None
    nonzero = [v for v in smoothed.values() if v > 0]
    if not nonzero:
        return None
    prominence_floor = (sum(nonzero) / len(nonzero)) * PEAK_PROMINENCE_MULT
    step = 1 if direction > 0 else -1
    start_bin = round(x_now_bin)
    for n in range(MIN_PEAK_SCAN_BINS, MAX_PEAK_SCAN_BINS + 1):
        k = start_bin + step * n
        d_here = smoothed.get(k, 0.0)
        d_prev = smoothed.get(k - step, 0.0)
        d_next = smoothed.get(k + step, 0.0)
        if d_here >= d_prev and d_here >= d_next and d_here >= prominence_floor:
            return exp(k * bin_width)
    return None


def run_gravity_backtest(bars, force_z_threshold=FORCE_Z_THRESHOLD, bin_pct=BIN_PCT,
                          lookback_days=LOOKBACK_DAYS, sl_stdev_mult=SL_STDEV_MULT):
    closes = [bar["close"] for bar in bars]
    bin_width = log(1 + bin_pct)
    start = lookback_days + SL_LOOKBACK_DAYS + FORCE_Z_WINDOW + 5

    trades = []
    open_trade = None
    force_history = []
    funnel = {"force_computed": 0, "z_threshold_passed": 0, "peak_target_found": 0, "rr_ok": 0, "traded": 0}

    i = start
    while i < len(bars) - 1:
        bins = build_density(closes, i, lookback_days, bin_width)
        smoothed = smooth_density(bins, SMOOTH_BINS)
        x_now_bin = log(closes[i]) / bin_width
        force = gravity_force(bins, x_now_bin)
        force_history.append(force)
        if len(force_history) > FORCE_Z_WINDOW:
            force_history.pop(0)
        funnel["force_computed"] += 1

        if open_trade is not None:
            bar = bars[i]
            t = open_trade
            if t["direction"] == "LONG":
                hit_sl, hit_tp = bar["low"] <= t["sl"], bar["high"] >= t["tp"]
            else:
                hit_sl, hit_tp = bar["high"] >= t["sl"], bar["low"] <= t["tp"]
            if hit_sl:
                t["outcome"], t["exit_price"], t["exit_idx"] = "LOSS", t["sl"], i
            elif hit_tp:
                t["outcome"], t["exit_price"], t["exit_idx"] = "WIN", t["tp"], i
            if t["outcome"]:
                move = (t["exit_price"] - t["entry"]) if t["direction"] == "LONG" else (t["entry"] - t["exit_price"])
                t["pnl_cash"] = t["position_size"] * move
                t["r_multiple"] = move / t["risk_per_unit"]
                trades.append(t)
                open_trade = None
            i += 1
            continue

        if len(force_history) < FORCE_Z_WINDOW:
            i += 1
            continue
        mean_f = statistics.mean(force_history)
        stdev_f = statistics.pstdev(force_history)
        if stdev_f == 0:
            i += 1
            continue
        z = (force - mean_f) / stdev_f
        if abs(z) < force_z_threshold:
            i += 1
            continue
        funnel["z_threshold_passed"] += 1

        direction = "LONG" if z > 0 else "SHORT"
        target_price = find_peak_target(smoothed, x_now_bin, 1 if direction == "LONG" else -1, bin_width)
        if target_price is None:
            i += 1
            continue
        funnel["peak_target_found"] += 1

        sl_window = closes[i - SL_LOOKBACK_DAYS + 1:i + 1]
        sigma = statistics.pstdev(sl_window)
        entry_idx = i + 1
        entry = bars[entry_idx]["open"]
        if direction == "LONG":
            sl = entry - sl_stdev_mult * sigma
            tp = target_price
        else:
            sl = entry + sl_stdev_mult * sigma
            tp = target_price
        risk_per_unit = abs(entry - sl)
        reward_per_unit = abs(tp - entry)
        if risk_per_unit <= 0 or (direction == "LONG" and tp <= entry) or (direction == "SHORT" and tp >= entry):
            i += 1
            continue
        if reward_per_unit / risk_per_unit < MIN_RR:
            i += 1
            continue
        funnel["rr_ok"] += 1
        funnel["traded"] += 1

        open_trade = {
            "direction": direction, "entry_idx": entry_idx, "entry": entry, "sl": sl, "tp": tp,
            "risk_per_unit": risk_per_unit, "force_z": z,
            "position_size": (ACCOUNT_SIZE * RISK_PCT) / risk_per_unit, "outcome": None,
        }
        i += 1

    if open_trade is not None:
        open_trade["outcome"] = "OPEN"
        trades.append(open_trade)

    return trades, funnel


def force_distribution_diagnostic(bars):
    closes = [bar["close"] for bar in bars]
    bin_width = log(1 + BIN_PCT)
    start = LOOKBACK_DAYS + 5
    forces = []
    for i in range(start, len(bars) - 1):
        bins = build_density(closes, i, LOOKBACK_DAYS, bin_width)
        x_now_bin = log(closes[i]) / bin_width
        forces.append(gravity_force(bins, x_now_bin))
    lines = []
    lines.append("-" * 108)
    lines.append("FORCE DISTRIBUTION DIAGNOSTIC (raw gravity force, before z-scoring)")
    lines.append("-" * 108)
    abs_forces = sorted(abs(f) for f in forces)
    lines.append(f"Samples: {len(forces)}   mean(|F|): {statistics.mean(abs_forces):.2f}   "
                 f"median(|F|): {statistics.median(abs_forces):.2f}   max(|F|): {max(abs_forces):.2f}")
    return "\n".join(lines)


def report(bars, trades, funnel):
    lines = []
    lines.append("=" * 108)
    lines.append("GRAVITY-FIELD (PRICE MAGNET) STRATEGY - BTCUSD DAILY BACKTEST")
    lines.append("=" * 108)
    lines.append(f"Lookback: {LOOKBACK_DAYS}d   Bin width: {BIN_PCT:.1%} (log-price)   "
                 f"Force Z window: {FORCE_Z_WINDOW}d   Z threshold: {FORCE_Z_THRESHOLD}")
    lines.append(f"SL: {SL_LOOKBACK_DAYS}d stdev x {SL_STDEV_MULT}   TP: next prominent density peak in force "
                 f"direction   Min RR: {MIN_RR}")
    lines.append("")

    closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
    still_open = [t for t in trades if t["outcome"] == "OPEN"]

    header = (f"{'#':>3} {'Dir':<6} {'Entry Date':<11} {'Exit Date':<11} {'Entry':>10} {'SL':>10} "
              f"{'TP':>10} {'ForceZ':>7} {'Res':<5} {'PnL$':>9} {'R':>6} {'W-L':<8} {'Equity$':>10}")
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
                     f"{t['tp']:>10,.1f} {t['force_z']:>7.2f} {t['outcome']:<5} {t['pnl_cash']:>9,.2f} "
                     f"{t['r_multiple']:>6.2f} {f'{w}-{l}':<8} {equity:>10,.2f}")

    lines.append("")
    lines.append("-" * 108)
    lines.append("FUNNEL")
    lines.append(f"  Force computed                           : {funnel['force_computed']}")
    lines.append(f"  + |z(force)| >= threshold                 : {funnel['z_threshold_passed']}")
    lines.append(f"  + a prominent peak target found           : {funnel['peak_target_found']}")
    lines.append(f"  + risk/reward >= {MIN_RR}                       : {funnel['rr_ok']}")
    lines.append(f"  -> traded                                  : {funnel['traded']}")
    lines.append("")
    lines.append("SUMMARY")
    lines.append(f"Trades still open at data end   : {len(still_open)}")
    lines.append(f"Closed trades                   : {len(closed)}")
    lines.append(f"  Wins                          : {w}")
    lines.append(f"  Losses                        : {l}")
    if closed:
        lines.append(f"  Win rate                      : {w/len(closed)*100:.1f}%")
        avg_r = sum(t["r_multiple"] for t in closed) / len(closed)
        lines.append(f"  Avg R-multiple                : {avg_r:+.2f}R")
        lines.append(f"  Net P&L                       : ${cum:+,.2f}  (${ACCOUNT_SIZE:,.0f} -> ${equity:,.2f})")
        mw = ml = cw = cl = 0
        for t in closed:
            if t["outcome"] == "WIN":
                cw += 1; cl = 0
            else:
                cl += 1; cw = 0
            mw, ml = max(mw, cw), max(ml, cl)
        lines.append(f"  Longest win/loss streak       : {mw} / {ml}")
    return "\n".join(lines)


def parameter_sweep(bars):
    lines = []
    lines.append("-" * 108)
    lines.append("PARAMETER SWEEP (force Z threshold x lookback days x bin %)")
    lines.append("-" * 108)
    lines.append(f"{'ZThresh':>7} {'Lookback':>8} {'BinPct':>7} {'Traded':>6} {'Closed':>6} {'W':>3} {'L':>3} "
                 f"{'WinRate':>8} {'NetPnL':>10}")
    for z_thr in (0.5, 1.0, 1.5, 2.0):
        for lookback in (90, 180, 270):
            for bin_pct in (0.01, 0.02, 0.04):
                trades, funnel = run_gravity_backtest(bars, force_z_threshold=z_thr, bin_pct=bin_pct,
                                                        lookback_days=lookback)
                closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
                w = sum(1 for t in closed if t["outcome"] == "WIN")
                l = len(closed) - w
                net = sum(t["pnl_cash"] for t in closed)
                wr = (w / len(closed) * 100) if closed else 0.0
                lines.append(f"{z_thr:>7.1f} {lookback:>8} {bin_pct:>7.2f} {funnel['traded']:>6} {len(closed):>6} "
                             f"{w:>3} {l:>3} {wr:>7.1f}% {net:>+10.2f}")
    return "\n".join(lines)


def main():
    bars = load_data(DAILY_SRC)
    trades, funnel = run_gravity_backtest(bars)
    out = report(bars, trades, funnel)
    out += "\n\n" + force_distribution_diagnostic(bars)
    out += "\n\n" + parameter_sweep(bars)
    print(out)
    with open("results_gravity_field.txt", "w") as f:
        f.write(out + "\n")


if __name__ == "__main__":
    main()

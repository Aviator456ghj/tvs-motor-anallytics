"""
Phase-rotation cycle backtest on BTCUSD daily candles.

Where `cycle_sine_backtest.py` fits a sinusoid and reads its derivative for
turning points, this variant uses a different chain of the same trig tools
end to end - forward fit, inverse extraction, integration, forward
projection - rather than the derivative alone:

  1. FORWARD FIT (sin/cos): same periodogram fit as cycle_sine_backtest
     - detrended price ~= a*cos(wt) + b*sin(wt) - to get the dominant cycle
     length T* and amplitude R = sqrt(a^2+b^2).

  2. TIME-DELAY PHASE PORTRAIT: build a 2-D vector V(t) = (z(t), z(t-L))
     from the z-scored detrended price and its own value one quarter-cycle
     (L = T*/4) earlier. For a true sinusoid this traces a circle in the
     (z(t), z(t-L)) plane, rotating at a constant angular rate - a standard
     time-delay (Takens) embedding trick for exposing cyclical structure
     directly in the data, not just in the fitted curve.

  3. INVERSE TRIG (the "reverse"): the signed rotation angle from V(t-1) to
     V(t) is theta = atan2(cross, dot), where
       dot   = V(t-1).V(t)   = |V(t-1)||V(t)| * cos(theta)
       cross = V(t-1) x V(t) = |V(t-1)||V(t)| * sin(theta)
     atan2 is exactly the inverse of (cos, sin) taken together - it recovers
     the angle a forward sin/cos pair was built from, the literal "reverse"
     of step 1's trig.

  4. INTEGRATION: cumulative phase Theta(t) = Theta(t-1) + theta(t) is the
     discrete integral of this instantaneous angular velocity - literally
     "how far around the circle has price rotated", tracked continuously
     start to end regardless of whether a trade is open.

  5. FORWARD PROJECTION (sin/cos again): cos(Theta(t)) re-expresses the
     accumulated rotation as a point on the unit circle. When it is pinned
     near -1 the price is sitting at a phase-portrait trough (LONG); near
     +1, a crest (SHORT). The take-profit projects the *next* extreme half
     a cycle ahead by reapplying the cosine: cos(Theta + pi) = -cos(Theta).

A coherence filter (the last few rotation steps must share a sign) gates
every entry - a single trough/crest touch from numerical noise is not
trusted, same "don't trust the curve fit alone" discipline as
cycle_sine_backtest's momentum check.

No lookahead: rotation state updates every bar regardless of trade status
(true continuous integration), entries fill at the next bar's open, exits
resolve against high/low of bars actually reached. $5,000/1% account
sizing, identical to the other variants here for direct comparability.
"""
import statistics
from math import atan2, cos, pi, sqrt

from measured_swing_backtest import load_data, ACCOUNT_SIZE, RISK_PCT
from cycle_sine_backtest import compute_detrended, fit_dominant_cycle, DETREND_WINDOW, FIT_WINDOW

DAILY_SRC = "data/btc_usd_daily.csv"

STDEV_WINDOW = 20          # window for z-scoring the phase-portrait axes (and the SL distance)
LAG_FRACTION = 0.25        # L = T* * this fraction (quarter-cycle delay embedding)
MIN_VECTOR_MAG = 0.05      # phase vectors shorter than this (near the origin) give unstable angles - skipped
TROUGH_COS, CREST_COS = -0.95, 0.95
COHERENCE_BARS = 5         # last N rotation steps must agree in sign before an entry is trusted
SL_STDEV_MULT = 1.5


def compute_rolling_stdev(detrended, window):
    out = [None] * len(detrended)
    for i in range(len(detrended)):
        lo = i - window + 1
        if lo < 0 or detrended[i] is None or any(v is None for v in detrended[lo:i + 1]):
            continue
        out[i] = statistics.pstdev(detrended[lo:i + 1])
    return out


def run_phase_rotation_backtest(bars, lag_fraction=LAG_FRACTION, band_threshold=TROUGH_COS,
                                 coherence_bars=COHERENCE_BARS, sl_stdev_mult=SL_STDEV_MULT):
    closes = [bar["close"] for bar in bars]
    detrended = compute_detrended(closes, DETREND_WINDOW)
    stdevs = compute_rolling_stdev(detrended, STDEV_WINDOW)
    start = DETREND_WINDOW - 1 + FIT_WINDOW - 1 + STDEV_WINDOW + 20

    trades = []
    open_trade = None
    theta_cum = 0.0
    recent_steps = []
    in_trough = in_crest = False
    funnel = {"valid_vector": 0, "coherent": 0, "band_touch": 0, "traded": 0}
    periods_seen = []

    def zscore(idx):
        if idx < 0 or idx >= len(bars) or detrended[idx] is None or stdevs[idx] in (None, 0.0):
            return None
        return detrended[idx] / stdevs[idx]

    i = start
    while i < len(bars) - 1:
        window = detrended[i - FIT_WINDOW + 1:i + 1]
        T, a, b, amplitude = fit_dominant_cycle(window)
        periods_seen.append(T)
        L = max(1, round(T * lag_fraction))

        x_t, y_t = zscore(i), zscore(i - L)
        x_p, y_p = zscore(i - 1), zscore(i - 1 - L)

        signal_ready = False
        if None not in (x_t, y_t, x_p, y_p):
            mag_t = sqrt(x_t * x_t + y_t * y_t)
            mag_p = sqrt(x_p * x_p + y_p * y_p)
            if mag_t >= MIN_VECTOR_MAG and mag_p >= MIN_VECTOR_MAG:
                funnel["valid_vector"] += 1
                dot = x_t * x_p + y_t * y_p
                cross = x_p * y_t - x_t * y_p
                step = atan2(cross, dot)
                theta_cum += step
                recent_steps.append(step)
                if len(recent_steps) > coherence_bars:
                    recent_steps.pop(0)
                signal_ready = True

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

        if not signal_ready:
            i += 1
            continue

        cos_phase = cos(theta_cum)
        was_trough, was_crest = in_trough, in_crest
        in_trough = cos_phase <= band_threshold
        in_crest = cos_phase >= -band_threshold

        direction = None
        if in_trough and not was_trough:
            direction = "LONG"
        elif in_crest and not was_crest:
            direction = "SHORT"

        if direction is None:
            i += 1
            continue
        funnel["band_touch"] += 1

        coherent = (len(recent_steps) == coherence_bars and
                    (all(s > 0 for s in recent_steps) or all(s < 0 for s in recent_steps)))
        if not coherent:
            i += 1
            continue
        funnel["coherent"] += 1

        entry_idx = i + 1
        entry = bars[entry_idx]["open"]
        sma_now = closes[i] - detrended[i]
        tp = sma_now - amplitude * cos(theta_cum)
        sl = entry - sl_stdev_mult * stdevs[i] if direction == "LONG" else entry + sl_stdev_mult * stdevs[i]
        risk_per_unit = abs(entry - sl)
        if risk_per_unit <= 0 or (direction == "LONG" and tp <= entry) or (direction == "SHORT" and tp >= entry):
            i += 1
            continue
        funnel["traded"] += 1

        open_trade = {
            "direction": direction, "entry_idx": entry_idx, "entry": entry, "sl": sl, "tp": tp,
            "risk_per_unit": risk_per_unit,
            "position_size": (ACCOUNT_SIZE * RISK_PCT) / risk_per_unit,
            "period": T, "lag": L, "outcome": None,
        }
        i += 1

    if open_trade is not None:
        open_trade["outcome"] = "OPEN"
        trades.append(open_trade)

    return trades, funnel, periods_seen


def report(bars, trades, funnel, periods_seen):
    lines = []
    lines.append("=" * 108)
    lines.append("PHASE-ROTATION CYCLE STRATEGY - BTCUSD DAILY BACKTEST")
    lines.append("=" * 108)
    lines.append(f"Detrend SMA: {DETREND_WINDOW}d   Fit window: {FIT_WINDOW}d   Stdev window: {STDEV_WINDOW}d   "
                 f"Lag fraction: {LAG_FRACTION} of T*")
    lines.append(f"Trough/crest band: cos(Theta) <= {TROUGH_COS} / >= {CREST_COS}   "
                 f"Coherence bars: {COHERENCE_BARS}   SL: {SL_STDEV_MULT}x stdev")
    lines.append("")

    closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
    still_open = [t for t in trades if t["outcome"] == "OPEN"]

    header = (f"{'#':>3} {'Dir':<6} {'Entry Date':<11} {'Exit Date':<11} {'Entry':>10} {'SL':>10} "
              f"{'TP':>10} {'Period':>7} {'Lag':>4} {'Res':<5} {'PnL$':>9} {'R':>6} {'W-L':<8} {'Equity$':>10}")
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
                     f"{t['tp']:>10,.1f} {t['period']:>7} {t['lag']:>4} {t['outcome']:<5} {t['pnl_cash']:>9,.2f} "
                     f"{t['r_multiple']:>6.2f} {f'{w}-{l}':<8} {equity:>10,.2f}")

    lines.append("")
    lines.append("-" * 108)
    lines.append("FUNNEL")
    lines.append(f"  Valid phase-portrait vector (mag ok)     : {funnel['valid_vector']}")
    lines.append(f"  + trough/crest band touch                : {funnel['band_touch']}")
    lines.append(f"  + rotation coherent over last {COHERENCE_BARS} steps    : {funnel['coherent']}")
    lines.append(f"  + valid risk/TP -> traded                : {funnel['traded']}")
    lines.append("")
    lines.append("SUMMARY")
    lines.append(f"Trades still open at data end   : {len(still_open)}")
    lines.append(f"Closed trades                   : {len(closed)}")
    lines.append(f"  Wins                          : {w}")
    lines.append(f"  Losses                        : {l}")
    if periods_seen:
        lines.append(f"Dominant period detected (median): {statistics.median(periods_seen):.0f}d "
                     f"(min {min(periods_seen)}d, max {max(periods_seen)}d)")
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
    lines.append("PARAMETER SWEEP (lag fraction x band threshold x coherence bars)")
    lines.append("-" * 108)
    lines.append(f"{'LagFrac':>7} {'Band':>6} {'CohBars':>7} {'Traded':>6} {'Closed':>6} {'W':>3} {'L':>3} "
                 f"{'WinRate':>8} {'NetPnL':>10}")
    for lag_fraction in (1/6, 0.25, 1/3):
        for band in (-0.90, -0.95, -0.98):
            for coh in (3, 5, 8):
                trades, funnel, _ = run_phase_rotation_backtest(
                    bars, lag_fraction=lag_fraction, band_threshold=band, coherence_bars=coh)
                closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
                w = sum(1 for t in closed if t["outcome"] == "WIN")
                l = len(closed) - w
                net = sum(t["pnl_cash"] for t in closed)
                wr = (w / len(closed) * 100) if closed else 0.0
                lines.append(f"{lag_fraction:>7.3f} {band:>6.2f} {coh:>7} {funnel['traded']:>6} {len(closed):>6} "
                             f"{w:>3} {l:>3} {wr:>7.1f}% {net:>+10.2f}")
    return "\n".join(lines)


def main():
    bars = load_data(DAILY_SRC)
    trades, funnel, periods = run_phase_rotation_backtest(bars)
    out = report(bars, trades, funnel, periods)
    out += "\n\n" + parameter_sweep(bars)
    print(out)
    with open("results_phase_rotation.txt", "w") as f:
        f.write(out + "\n")


if __name__ == "__main__":
    main()

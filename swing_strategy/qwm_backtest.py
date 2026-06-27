"""
Quantum Wave Matrix (QWM) backtest - BTCUSD 5-minute scalps.

This implements the QWM playbook's entry/risk logic, but with three pieces
of its math made dimensionally sound (the playbook as literally written
left them undefined or scale-dependent - see swing_strategy/README.md for
the full critique):

1. Vector angle Theta. The playbook's arctan(DeltaPrice/DeltaTime) is not
   scale-invariant - it changes if you redraw the chart at a different
   zoom, because price ($) and time (bars) aren't the same unit. Here the
   slope is normalized by ATR per bar first, so Theta means "how many ATRs
   of slope, expressed as an angle" - the same 70 degrees means the same
   relative violence on any asset/timeframe:

       Theta = arctan( (close[i]-close[i-n])/n / ATR[i] )

2. Phase oscillator Phi(t) = sin(w*t+phi). The playbook never says how to
   get w (cycle frequency) or phi (phase) from data. Reuses the discrete
   Fourier periodogram fit from cycle_sine_backtest.py, run on a 4-hour
   anchor series derived from the same 5-minute data, to fit them for real:

       a(T) = (2/W) sum x_t cos(2*pi*t/T),  b(T) likewise with sin
       T* = argmax_T a(T)^2 + b(T)^2
       Phi(t) = (a*cos(w*t) + b*sin(w*t)) / sqrt(a^2+b^2)   in [-1, 1]

3. "Structural Mass" integral check. The playbook's Structural Mass =
   integral f(x) dx has units of $*bars, so a fixed "1.0" threshold is
   meaningless (it isn't 1.0 of anything). Here the integral (trapezoidal
   area between price and its level n bars ago) is z-scored against its
   own trailing distribution, and >= 1.0 standard deviation is required -
   a dimensionless, comparable version of the same "is this move unusually
   forceful" question.

Liquidity-gate session filter, stdev-based stop loss, breakeven-at-1.5R,
and the position-sizing formula are implemented exactly as specified - that
part of the playbook was already well-defined.
"""
import csv
from datetime import datetime, time as dtime, timezone
from math import atan, cos, degrees, pi, sin, sqrt
from zoneinfo import ZoneInfo

from cycle_sine_backtest import compute_detrended

DATA_SRC = "data/btc_usd_5min_cvd.csv"
NY_TZ = ZoneInfo("America/New_York")

# --- Phase 2: liquidity gates (New York local time) ---
LONDON_GATE = (dtime(3, 0), dtime(6, 30))
NY_GATE = (dtime(8, 30), dtime(11, 30))

# --- Phase 1/3: angle + phase + mass thresholds ---
ANGLE_LOOKBACK_BARS = 6        # 30 minutes on M5 - the "expansion leg" window
ATR_WINDOW = 14
ANGLE_THRESHOLD_DEG = 70.0
CONSOLIDATION_BAND_DEG = 45.0  # |Theta| <= this -> explicitly silent, per Phase 6

DETREND_WINDOW_H4 = 20         # H4 bars (~3.3 days) SMA subtracted before fitting
FIT_WINDOW_H4 = 60             # H4 bars (~10 days) trailing window for the periodogram
PERIOD_MIN_H4, PERIOD_MAX_H4, PERIOD_STEP_H4 = 4, 30, 1   # candidate cycle lengths, in H4 bars
PHASE_THRESHOLD = 0.995
H4_ZIGZAG_THRESHOLD = 0.03     # 3% reversal confirms an H4 swing point

MASS_HISTORY_LEN = 200         # trailing samples the z-score is computed against
MASS_Z_THRESHOLD = 1.0

# --- Phase 4: risk architecture ---
STDEV_WINDOW = 20              # trailing 5m closes
SL_STDEV_MULT = 0.50
BREAKEVEN_R_MULT = 1.5

# --- Phase 5: position sizing ---
ACCOUNT_SIZE = 100_000.0
RISK_PCT = 0.01
TICK_VALUE_CONSTANT = 1.0      # BTC: price already in $ per unit


def load_data(path):
    bars = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            bars.append({
                "ts": int(r["timestamp"]),
                "date": r["datetime"],
                "open": float(r["open"]), "high": float(r["high"]),
                "low": float(r["low"]), "close": float(r["close"]),
            })
    return bars


def in_liquidity_gate(ts):
    ny = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(NY_TZ).time()
    return (LONDON_GATE[0] <= ny < LONDON_GATE[1]) or (NY_GATE[0] <= ny < NY_GATE[1])


def build_h4_bars(bars5m):
    """Aggregate 5-minute bars into 4-hour bars aligned to real UTC H4
    boundaries (00:00, 04:00, ...), dropping any boundary bucket that isn't
    (almost) fully populated so the anchor series has no partial bars."""
    H4_SECONDS = 4 * 3600
    buckets, counts, order = {}, {}, []
    for bar in bars5m:
        key = bar["ts"] - (bar["ts"] % H4_SECONDS)
        if key not in buckets:
            buckets[key] = {"date": bar["date"], "high": bar["high"], "low": bar["low"],
                             "close": bar["close"], "ts_end": key + H4_SECONDS}
            counts[key] = 1
            order.append(key)
        else:
            b = buckets[key]
            b["high"] = max(b["high"], bar["high"])
            b["low"] = min(b["low"], bar["low"])
            b["close"] = bar["close"]
            counts[key] += 1
    return [buckets[k] for k in order if counts[k] >= 44]  # 44/48 5m bars present


def find_h4_pivots(h4_bars, threshold):
    """Same zig-zag rule as the daily backtests, applied to the H4 anchor
    series - confirmed pivots only, no lookahead."""
    pivots = []
    trend = None
    extreme_price, extreme_idx = h4_bars[0]["close"], 0
    for i in range(1, len(h4_bars)):
        h, l = h4_bars[i]["high"], h4_bars[i]["low"]
        if trend is None:
            if h >= extreme_price * (1 + threshold):
                trend, extreme_price, extreme_idx = "up", h, i
            elif l <= extreme_price * (1 - threshold):
                trend, extreme_price, extreme_idx = "down", l, i
            continue
        if trend == "up":
            if h > extreme_price:
                extreme_price, extreme_idx = h, i
            elif l <= extreme_price * (1 - threshold):
                pivots.append({"price": extreme_price, "confirm_idx": i})
                trend, extreme_price, extreme_idx = "down", l, i
        else:
            if l < extreme_price:
                extreme_price, extreme_idx = l, i
            elif h >= extreme_price * (1 + threshold):
                pivots.append({"price": extreme_price, "confirm_idx": i})
                trend, extreme_price, extreme_idx = "up", h, i
    return pivots


def fit_phase(window_vals):
    """Discrete Fourier periodogram fit, identical method to
    cycle_sine_backtest.fit_dominant_cycle but with H4-bar period
    constants - kept local so the two backtests don't silently share
    mutable globals tuned for different bar spacings."""
    W = len(window_vals)
    best = None
    for T in range(PERIOD_MIN_H4, PERIOD_MAX_H4 + 1, PERIOD_STEP_H4):
        omega = 2 * pi / T
        a = b = 0.0
        for t, x in enumerate(window_vals):
            a += x * cos(omega * t)
            b += x * sin(omega * t)
        a *= 2.0 / W
        b *= 2.0 / W
        power = a * a + b * b
        if best is None or power > best[0]:
            best = (power, T, a, b)
    _, T, a, b = best
    return T, a, b, sqrt(a * a + b * b)


def compute_atr(bars):
    atr = [None] * len(bars)
    trs = []
    for i in range(1, len(bars)):
        h, l, prev_close = bars[i]["high"], bars[i]["low"], bars[i - 1]["close"]
        trs.append(max(h - l, abs(h - prev_close), abs(l - prev_close)))
        if len(trs) > ATR_WINDOW:
            trs.pop(0)
        if len(trs) == ATR_WINDOW:
            atr[i] = sum(trs) / ATR_WINDOW
    return atr


def compute_sigma(closes, i, window):
    vals = closes[i - window + 1:i + 1]
    mu = sum(vals) / window
    var = sum((c - mu) ** 2 for c in vals) / window
    return sqrt(var)


def run_qwm_backtest(bars, angle_threshold=ANGLE_THRESHOLD_DEG, phase_threshold=PHASE_THRESHOLD,
                      mass_z_threshold=MASS_Z_THRESHOLD):
    closes = [b["close"] for b in bars]
    atr = compute_atr(bars)

    h4_bars = build_h4_bars(bars)
    h4_closes = [b["close"] for b in h4_bars]
    h4_detrended = compute_detrended(h4_closes, DETREND_WINDOW_H4)
    h4_pivots = find_h4_pivots(h4_bars, H4_ZIGZAG_THRESHOLD)

    fit_start = DETREND_WINDOW_H4 - 1 + FIT_WINDOW_H4 - 1
    phase_fits = {}
    for h in range(fit_start, len(h4_bars)):
        window = h4_detrended[h - FIT_WINDOW_H4 + 1:h + 1]
        phase_fits[h] = fit_phase(window)

    start = ANGLE_LOOKBACK_BARS + ATR_WINDOW + STDEV_WINDOW + 5
    trades = []
    open_trade = None
    mass_history = []
    funnel = {"angle_extreme": 0, "phase_confirm": 0, "mass_confirm": 0, "traded": 0}

    h4_ptr = -1
    pivot_ptr = 0

    i = start
    while i < len(bars) - 1:
        while h4_ptr + 1 < len(h4_bars) and h4_bars[h4_ptr + 1]["ts_end"] <= bars[i]["ts"]:
            h4_ptr += 1
        while pivot_ptr < len(h4_pivots) and h4_pivots[pivot_ptr]["confirm_idx"] <= h4_ptr:
            pivot_ptr += 1

        if open_trade is not None:
            bar = bars[i]
            t = open_trade
            if t["direction"] == "LONG":
                fav = bar["high"] - t["entry"]
                hit_sl, hit_tp = bar["low"] <= t["sl"], bar["high"] >= t["tp"]
            else:
                fav = t["entry"] - bar["low"]
                hit_sl, hit_tp = bar["high"] >= t["sl"], bar["low"] <= t["tp"]
            if hit_sl:
                t["outcome"], t["exit_price"], t["exit_idx"] = "LOSS", t["sl"], i
            elif hit_tp:
                t["outcome"], t["exit_price"], t["exit_idx"] = "WIN", t["tp"], i
            elif not t["breakeven_armed"] and fav >= BREAKEVEN_R_MULT * t["risk_per_unit"]:
                t["sl"] = t["entry"]
                t["breakeven_armed"] = True
            if t["outcome"]:
                move = (t["exit_price"] - t["entry"]) if t["direction"] == "LONG" else (t["entry"] - t["exit_price"])
                t["pnl_cash"] = t["position_size"] * move
                t["r_multiple"] = move / t["risk_per_unit"]
                trades.append(t)
                open_trade = None
            i += 1
            continue

        if not in_liquidity_gate(bars[i]["ts"]):
            i += 1
            continue

        if atr[i] is None:
            i += 1
            continue

        delta_price = closes[i] - closes[i - ANGLE_LOOKBACK_BARS]
        slope_atr = (delta_price / ANGLE_LOOKBACK_BARS) / atr[i] if atr[i] else 0.0
        theta_deg = degrees(atan(slope_atr))

        devs = [closes[k] - closes[i - ANGLE_LOOKBACK_BARS] for k in range(i - ANGLE_LOOKBACK_BARS, i + 1)]
        mass = sum((devs[k] + devs[k + 1]) / 2.0 for k in range(len(devs) - 1))

        mass_z = None
        if len(mass_history) >= 20:
            mu = sum(mass_history) / len(mass_history)
            var = sum((m - mu) ** 2 for m in mass_history) / len(mass_history)
            sd = sqrt(var)
            if sd > 0:
                mass_z = (abs(mass) - mu) / sd
        mass_history.append(abs(mass))
        if len(mass_history) > MASS_HISTORY_LEN:
            mass_history.pop(0)

        if abs(theta_deg) <= CONSOLIDATION_BAND_DEG:
            i += 1
            continue

        direction = None
        if theta_deg >= angle_threshold:
            direction = "SHORT"
        elif theta_deg <= -angle_threshold:
            direction = "LONG"
        if direction is None:
            i += 1
            continue
        funnel["angle_extreme"] += 1

        if h4_ptr not in phase_fits:
            i += 1
            continue
        T, a, b, R = phase_fits[h4_ptr]
        if R == 0:
            i += 1
            continue
        omega = 2 * pi / T
        t_eval = FIT_WINDOW_H4 - 1
        phi_now = (a * cos(omega * t_eval) + b * sin(omega * t_eval)) / R

        phase_ok = (direction == "SHORT" and phi_now >= phase_threshold) or \
                   (direction == "LONG" and phi_now <= -phase_threshold)
        if not phase_ok:
            i += 1
            continue
        funnel["phase_confirm"] += 1

        if mass_z is None or mass_z < mass_z_threshold:
            i += 1
            continue
        funnel["mass_confirm"] += 1

        if pivot_ptr < 2:
            i += 1
            continue
        p0, p1 = h4_pivots[pivot_ptr - 2], h4_pivots[pivot_ptr - 1]
        macro_mid = (p0["price"] + p1["price"]) / 2.0

        entry_idx = i + 1
        entry = bars[entry_idx]["open"]
        sigma = compute_sigma(closes, i, STDEV_WINDOW)

        if direction == "SHORT":
            sl = bars[i]["high"] + SL_STDEV_MULT * sigma
            tp = macro_mid
            valid_target = tp < entry
        else:
            sl = bars[i]["low"] - SL_STDEV_MULT * sigma
            tp = macro_mid
            valid_target = tp > entry

        risk_per_unit = abs(entry - sl)
        if not valid_target or risk_per_unit <= 0:
            i += 1
            continue
        funnel["traded"] += 1

        open_trade = {
            "direction": direction, "entry_idx": entry_idx, "entry": entry,
            "sl": sl, "tp": tp, "risk_per_unit": risk_per_unit,
            "position_size": (ACCOUNT_SIZE * RISK_PCT) / (risk_per_unit * TICK_VALUE_CONSTANT),
            "theta_deg": round(theta_deg, 1), "phi": round(phi_now, 3), "mass_z": round(mass_z, 2),
            "breakeven_armed": False, "outcome": None,
        }
        i += 1

    if open_trade is not None:
        open_trade["outcome"] = "OPEN"
        trades.append(open_trade)

    return trades, funnel


def report(bars, trades, funnel):
    lines = []
    lines.append("=" * 110)
    lines.append("QUANTUM WAVE MATRIX (QWM) - BTCUSD 5-MINUTE BACKTEST")
    lines.append("=" * 110)
    lines.append(f"Data range: {bars[0]['date']} -> {bars[-1]['date']}  ({len(bars)} 5m candles)")
    lines.append(f"Angle threshold: +/-{ANGLE_THRESHOLD_DEG}deg (ATR-normalized)   "
                 f"Phase threshold: +/-{PHASE_THRESHOLD}   Mass z-threshold: {MASS_Z_THRESHOLD}")
    lines.append(f"Liquidity gates (NY time): London {LONDON_GATE[0]}-{LONDON_GATE[1]}, "
                 f"NY {NY_GATE[0]}-{NY_GATE[1]}")
    lines.append("")

    closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
    still_open = [t for t in trades if t["outcome"] == "OPEN"]

    header = (f"{'#':>3} {'Dir':<6} {'Entry':<17} {'Exit':<17} {'EntryPx':>10} {'SL':>10} {'TP':>10} "
              f"{'Th':>6} {'Phi':>6} {'MassZ':>6} {'Res':<5} {'PnL$':>9} {'R':>6} {'W-L':<8}")
    lines.append(header)
    seq = w = l = 0
    cum = 0.0
    for t in closed:
        seq += 1
        if t["outcome"] == "WIN":
            w += 1
        else:
            l += 1
        cum += t["pnl_cash"]
        lines.append(f"{seq:>3} {t['direction']:<6} {bars[t['entry_idx']]['date']:<17} "
                     f"{bars[t['exit_idx']]['date']:<17} {t['entry']:>10,.1f} {t['sl']:>10,.1f} "
                     f"{t['tp']:>10,.1f} {t['theta_deg']:>6.1f} {t['phi']:>6.3f} {t['mass_z']:>6.2f} "
                     f"{t['outcome']:<5} {t['pnl_cash']:>9,.2f} {t['r_multiple']:>6.2f} {f'{w}-{l}':<8}")

    lines.append("")
    lines.append("-" * 110)
    lines.append("FUNNEL (how many candidates survive each gate)")
    lines.append(f"  Angle >= {ANGLE_THRESHOLD_DEG}deg (and outside chop band) : {funnel['angle_extreme']}")
    lines.append(f"  + phase confirms                          : {funnel['phase_confirm']}")
    lines.append(f"  + mass z-score confirms                   : {funnel['mass_confirm']}")
    lines.append(f"  + valid macro target -> traded             : {funnel['traded']}")
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
        lines.append(f"  Net P&L                       : ${cum:+,.2f}  (on ${ACCOUNT_SIZE:,.0f} account)")
    return "\n".join(lines)


def angle_distribution_diagnostic(bars):
    """Explains *why* the funnel is empty: shows the actual distribution of
    the ATR-normalized angle Theta inside the liquidity gates, so a zero
    trade count is verifiable from the data rather than asserted."""
    closes = [b["close"] for b in bars]
    atr = compute_atr(bars)
    start = ANGLE_LOOKBACK_BARS + ATR_WINDOW + STDEV_WINDOW + 5
    thetas = []
    for i in range(start, len(bars) - 1):
        if atr[i] is None or not in_liquidity_gate(bars[i]["ts"]):
            continue
        delta_price = closes[i] - closes[i - ANGLE_LOOKBACK_BARS]
        slope_atr = (delta_price / ANGLE_LOOKBACK_BARS) / atr[i]
        thetas.append(degrees(atan(slope_atr)))

    lines = []
    lines.append("-" * 110)
    lines.append("ANGLE DISTRIBUTION DIAGNOSTIC (inside liquidity gates only)")
    lines.append("-" * 110)
    if not thetas:
        lines.append("No in-gate bars found.")
        return "\n".join(lines)
    abs_thetas = sorted(abs(t) for t in thetas)
    lines.append(f"In-gate bars sampled        : {len(thetas)}")
    lines.append(f"Max |Theta| ever reached    : {abs_thetas[-1]:.1f}deg  "
                 f"(playbook's literal trigger is {ANGLE_THRESHOLD_DEG:.0f}deg)")
    lines.append(f"99th percentile |Theta|     : {abs_thetas[int(len(abs_thetas)*0.99)]:.1f}deg")
    lines.append(f"Mean |Theta|                : {sum(abs_thetas)/len(abs_thetas):.1f}deg")
    for thr in (45, 60, 70):
        n = sum(1 for t in abs_thetas if t > thr)
        lines.append(f"Bars with |Theta| > {thr}deg     : {n}")
    return "\n".join(lines)


def parameter_sweep(bars):
    lines = []
    lines.append("-" * 110)
    lines.append("PARAMETER SWEEP (angle threshold x phase threshold)")
    lines.append("-" * 110)
    lines.append(f"{'AngleDeg':>8} {'PhaseThr':>8} {'Funnel(traded)':>14} {'Closed':>6} {'W':>3} {'L':>3} "
                 f"{'WinRate':>8} {'NetPnL':>10}")
    for angle_thr in (30.0, 40.0, 50.0, 60.0, 70.0, 80.0):
        for phase_thr in (0.90, 0.95, 0.995):
            trades, funnel = run_qwm_backtest(bars, angle_threshold=angle_thr, phase_threshold=phase_thr)
            closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
            w = sum(1 for t in closed if t["outcome"] == "WIN")
            l = len(closed) - w
            net = sum(t["pnl_cash"] for t in closed)
            wr = (w / len(closed) * 100) if closed else 0.0
            lines.append(f"{angle_thr:>8.1f} {phase_thr:>8.3f} {funnel['traded']:>14} {len(closed):>6} "
                         f"{w:>3} {l:>3} {wr:>7.1f}% {net:>+10.2f}")
    return "\n".join(lines)


def main():
    bars = load_data(DATA_SRC)
    trades, funnel = run_qwm_backtest(bars)
    out = report(bars, trades, funnel)
    out += "\n\n" + angle_distribution_diagnostic(bars)
    out += "\n\n" + parameter_sweep(bars)
    print(out)
    with open("results_qwm.txt", "w") as f:
        f.write(out + "\n")


if __name__ == "__main__":
    main()

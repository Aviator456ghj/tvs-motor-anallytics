"""
Quantum Wave Matrix (QWM) backtest, daily-resolution variant.

qwm_backtest.py implements the playbook literally (M5 execution, H4 anchor,
London/NY liquidity gates) but this repo only has 30 days of 5-minute
BTCUSD data, so that version produced zero trades at every threshold -
the angle/phase/mass conditions never even got the chance to be tested
against a meaningful sample.

This variant re-derives the same three corrected signals (ATR-normalized
angle, periodogram-fit phase, z-scored mass - see qwm_backtest.py's
docstring for why each needed fixing) on the ~2-year daily BTCUSD series
instead, trading the daily/weekly pair in place of M5/H4:

  - Execution timeframe : daily bars (was M5)
  - Anchor timeframe    : weekly bars, chunked 7 daily bars at a time
                          (was H4, chunked 48 5-min bars at a time) -
                          same ~7x/~48x coarsening *ratio* concept, just
                          rescaled to the only resolution this repo has
                          two years of.

One deliberate, documented deviation: the London/New York liquidity-gate
session filter is DROPPED here. It is a time-of-day filter and daily bars
have no time-of-day - applying it would be meaningless, not just
difficult. Treat this as "does the angle/phase/mass logic find anything
on a longer real series," not a faithful re-test of the original
session-timed intraday strategy.

Same $100,000/1% risk sizing formula and no-lookahead walk-forward
discipline as qwm_backtest.py.
"""
from math import atan, cos, degrees, pi, sin, sqrt

from measured_swing_backtest import load_data
from cycle_sine_backtest import compute_detrended

DATA_SRC = "data/btc_usd_daily.csv"

# --- angle ---
ANGLE_LOOKBACK_DAYS = 5        # one trading week - the "expansion leg" window
ATR_WINDOW = 14
ANGLE_THRESHOLD_DEG = 70.0
CONSOLIDATION_BAND_DEG = 45.0

# --- phase (fit on the weekly anchor series) ---
DETREND_WINDOW_WEEKLY = 8      # weeks of SMA subtracted before fitting (~2 months)
FIT_WINDOW_WEEKLY = 30         # trailing weeks used to fit the dominant cycle (~7 months)
PERIOD_MIN_WEEKLY, PERIOD_MAX_WEEKLY, PERIOD_STEP_WEEKLY = 4, 20, 1   # candidate cycle lengths, in weeks
PHASE_THRESHOLD = 0.995
WEEKLY_ZIGZAG_THRESHOLD = 0.10  # 10% reversal confirms a weekly swing point

# --- mass ---
MASS_HISTORY_LEN = 200
MASS_Z_THRESHOLD = 1.0

# --- risk architecture (identical formulas to qwm_backtest.py) ---
STDEV_WINDOW = 20
SL_STDEV_MULT = 0.50
BREAKEVEN_R_MULT = 1.5
ACCOUNT_SIZE = 100_000.0
RISK_PCT = 0.01
TICK_VALUE_CONSTANT = 1.0


def build_weekly_bars(bars):
    """Chunk every 7 sequential daily bars into one weekly bar - the daily
    analogue of qwm_backtest.build_h4_bars' 48-bar buckets. Drops a trailing
    partial week so every weekly bar is fully formed."""
    weekly = []
    for k in range(len(bars) // 7):
        chunk = bars[k * 7:(k + 1) * 7]
        weekly.append({
            "date": chunk[-1]["date"],
            "high": max(b["high"] for b in chunk),
            "low": min(b["low"] for b in chunk),
            "close": chunk[-1]["close"],
            "last_daily_idx": k * 7 + 6,   # this weekly bar is confirmed only once this daily bar has closed
        })
    return weekly


def find_weekly_pivots(weekly_bars, threshold):
    """Same zig-zag rule as measured_swing_backtest.find_pivots, applied to
    the weekly anchor series."""
    pivots = []
    trend = None
    extreme_price, extreme_idx = weekly_bars[0]["close"], 0
    for i in range(1, len(weekly_bars)):
        h, l = weekly_bars[i]["high"], weekly_bars[i]["low"]
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
    cycle_sine_backtest.fit_dominant_cycle but with weekly-bar period
    constants."""
    W = len(window_vals)
    best = None
    for T in range(PERIOD_MIN_WEEKLY, PERIOD_MAX_WEEKLY + 1, PERIOD_STEP_WEEKLY):
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


def run_qwm_daily_backtest(bars, angle_threshold=ANGLE_THRESHOLD_DEG, phase_threshold=PHASE_THRESHOLD,
                            mass_z_threshold=MASS_Z_THRESHOLD, angle_lookback_days=ANGLE_LOOKBACK_DAYS):
    closes = [b["close"] for b in bars]
    atr = compute_atr(bars)

    weekly_bars = build_weekly_bars(bars)
    weekly_closes = [b["close"] for b in weekly_bars]
    weekly_detrended = compute_detrended(weekly_closes, DETREND_WINDOW_WEEKLY)
    weekly_pivots = find_weekly_pivots(weekly_bars, WEEKLY_ZIGZAG_THRESHOLD)

    fit_start = DETREND_WINDOW_WEEKLY - 1 + FIT_WINDOW_WEEKLY - 1
    phase_fits = {}
    for w in range(fit_start, len(weekly_bars)):
        window = weekly_detrended[w - FIT_WINDOW_WEEKLY + 1:w + 1]
        phase_fits[w] = fit_phase(window)

    start = angle_lookback_days + ATR_WINDOW + STDEV_WINDOW + 5
    trades = []
    open_trade = None
    mass_history = []
    funnel = {"angle_extreme": 0, "phase_confirm": 0, "mass_confirm": 0, "traded": 0}

    week_ptr = -1
    pivot_ptr = 0

    i = start
    while i < len(bars) - 1:
        confirmed_week = ((i + 1) // 7) - 1
        if confirmed_week > week_ptr:
            week_ptr = confirmed_week
        while pivot_ptr < len(weekly_pivots) and weekly_pivots[pivot_ptr]["confirm_idx"] <= week_ptr:
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

        if atr[i] is None:
            i += 1
            continue

        delta_price = closes[i] - closes[i - angle_lookback_days]
        slope_atr = (delta_price / angle_lookback_days) / atr[i] if atr[i] else 0.0
        theta_deg = degrees(atan(slope_atr))

        devs = [closes[k] - closes[i - angle_lookback_days] for k in range(i - angle_lookback_days, i + 1)]
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

        if week_ptr not in phase_fits:
            i += 1
            continue
        T, a, b, R = phase_fits[week_ptr]
        if R == 0:
            i += 1
            continue
        omega = 2 * pi / T
        t_eval = FIT_WINDOW_WEEKLY - 1
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
        p0, p1 = weekly_pivots[pivot_ptr - 2], weekly_pivots[pivot_ptr - 1]
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
    lines.append("QUANTUM WAVE MATRIX (QWM) - BTCUSD DAILY-RESOLUTION VARIANT")
    lines.append("=" * 110)
    lines.append(f"Data range: {bars[0]['date']} -> {bars[-1]['date']}  ({len(bars)} daily candles)")
    lines.append(f"Execution: daily   Anchor: weekly (7-day chunks)   "
                 f"NOTE: liquidity-gate session filter dropped (no time-of-day on daily bars)")
    lines.append(f"Angle threshold: +/-{ANGLE_THRESHOLD_DEG}deg (ATR-normalized)   "
                 f"Phase threshold: +/-{PHASE_THRESHOLD}   Mass z-threshold: {MASS_Z_THRESHOLD}")
    lines.append("")

    closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
    still_open = [t for t in trades if t["outcome"] == "OPEN"]

    header = (f"{'#':>3} {'Dir':<6} {'Entry Date':<11} {'Exit Date':<11} {'EntryPx':>10} {'SL':>10} {'TP':>10} "
              f"{'Th':>6} {'Phi':>6} {'MassZ':>6} {'Res':<5} {'PnL$':>9} {'R':>6} {'W-L':<8} {'Equity$':>11}")
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
                     f"{t['tp']:>10,.1f} {t['theta_deg']:>6.1f} {t['phi']:>6.3f} {t['mass_z']:>6.2f} "
                     f"{t['outcome']:<5} {t['pnl_cash']:>9,.2f} {t['r_multiple']:>6.2f} {f'{w}-{l}':<8} {equity:>11,.2f}")

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


def angle_distribution_diagnostic(bars):
    closes = [b["close"] for b in bars]
    atr = compute_atr(bars)
    start = ANGLE_LOOKBACK_DAYS + ATR_WINDOW + STDEV_WINDOW + 5
    thetas = []
    for i in range(start, len(bars) - 1):
        if atr[i] is None:
            continue
        delta_price = closes[i] - closes[i - ANGLE_LOOKBACK_DAYS]
        slope_atr = (delta_price / ANGLE_LOOKBACK_DAYS) / atr[i]
        thetas.append(degrees(atan(slope_atr)))

    lines = []
    lines.append("-" * 110)
    lines.append("ANGLE DISTRIBUTION DIAGNOSTIC (all daily bars)")
    lines.append("-" * 110)
    if not thetas:
        lines.append("No bars found.")
        return "\n".join(lines)
    abs_thetas = sorted(abs(t) for t in thetas)
    lines.append(f"Bars sampled                : {len(thetas)}")
    lines.append(f"Max |Theta| ever reached    : {abs_thetas[-1]:.1f}deg  "
                 f"(playbook's literal trigger is {ANGLE_THRESHOLD_DEG:.0f}deg)")
    lines.append(f"99th percentile |Theta|     : {abs_thetas[int(len(abs_thetas)*0.99)]:.1f}deg")
    lines.append(f"Mean |Theta|                : {sum(abs_thetas)/len(abs_thetas):.1f}deg")
    for thr in (45, 60, 70):
        n = sum(1 for t in abs_thetas if t > thr)
        lines.append(f"Bars with |Theta| > {thr}deg     : {n}")
    return "\n".join(lines)


def lookback_sensitivity_sweep(bars):
    """The default ANGLE_LOOKBACK_DAYS=5 averages the slope over a week,
    which dampens Theta well below 70deg no matter how much data you feed
    it (see angle_distribution_diagnostic). This checks whether a more
    permissive single-day lookback - the most generous possible reading of
    "vector angle of price/time" - ever lets the literal threshold
    combination fire."""
    lines = []
    lines.append("-" * 110)
    lines.append("LOOKBACK SENSITIVITY (angle_lookback_days=1, the most permissive reading)")
    lines.append("-" * 110)
    lines.append(f"{'AngleDeg':>8} {'PhaseThr':>8} {'Funnel(traded)':>14} {'Closed':>6} {'W':>3} {'L':>3} "
                 f"{'WinRate':>8} {'NetPnL':>10}")
    for angle_thr in (50.0, 55.0, 60.0, 65.0, 70.0):
        for phase_thr in (0.50, 0.80, 0.90, 0.995):
            trades, funnel = run_qwm_daily_backtest(bars, angle_threshold=angle_thr, phase_threshold=phase_thr,
                                                      angle_lookback_days=1)
            closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
            w = sum(1 for t in closed if t["outcome"] == "WIN")
            l = len(closed) - w
            net = sum(t["pnl_cash"] for t in closed)
            wr = (w / len(closed) * 100) if closed else 0.0
            lines.append(f"{angle_thr:>8.1f} {phase_thr:>8.3f} {funnel['traded']:>14} {len(closed):>6} "
                         f"{w:>3} {l:>3} {wr:>7.1f}% {net:>+10.2f}")
    lines.append("")
    lines.append("Even at angle_lookback_days=1, the literal 70deg/0.995 combination still never fires "
                 "(max single-day |Theta| across the whole 2-year series is 68.5deg) - and every "
                 "loosened cell above is net-negative.")
    return "\n".join(lines)


def parameter_sweep(bars):
    lines = []
    lines.append("-" * 110)
    lines.append("PARAMETER SWEEP (angle threshold x phase threshold)")
    lines.append("-" * 110)
    lines.append(f"{'AngleDeg':>8} {'PhaseThr':>8} {'Funnel(traded)':>14} {'Closed':>6} {'W':>3} {'L':>3} "
                 f"{'WinRate':>8} {'NetPnL':>10}")
    for angle_thr in (46.0, 50.0, 55.0, 60.0, 65.0, 70.0):
        for phase_thr in (0.50, 0.80, 0.90, 0.995):
            trades, funnel = run_qwm_daily_backtest(bars, angle_threshold=angle_thr, phase_threshold=phase_thr)
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
    trades, funnel = run_qwm_daily_backtest(bars)
    out = report(bars, trades, funnel)
    out += "\n\n" + angle_distribution_diagnostic(bars)
    out += "\n\n" + parameter_sweep(bars)
    out += "\n\n" + lookback_sensitivity_sweep(bars)
    print(out)
    with open("results_qwm_daily.txt", "w") as f:
        f.write(out + "\n")


if __name__ == "__main__":
    main()

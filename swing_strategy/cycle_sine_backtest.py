"""
Cycle (sine-wave) backtest on BTCUSD daily candles.

Detrends price (close - SMA) to isolate the oscillating component, fits a
single dominant sinusoid to a trailing window via a discrete Fourier
coefficient scan (the periodogram - literally integrating x(t)*cos(wt) and
x(t)*sin(wt) over the window, in discrete-sum form), then trades the
turning points of that fitted wave:

  a(T) = (2/W) * sum_t  x_t * cos(2*pi*t/T)
  b(T) = (2/W) * sum_t  x_t * sin(2*pi*t/T)

T* = argmax_T [a(T)^2 + b(T)^2]   (dominant cycle length, in days)

Fitted model: x_t ~= a*cos(w*t) + b*sin(w*t),  w = 2*pi/T*
Its derivative (cos's derivative is -sin, sin's derivative is cos - the
"reverse" relationship the trig identities give for free):

  dx/dt ~= -a*w*sin(w*t) + b*w*cos(w*t)

A trough (derivative crosses negative -> positive) is a LONG signal; a peak
(positive -> negative) is a SHORT signal. amplitude = sqrt(a^2+b^2) sizes
the take-profit (the cycle's own swing size), and a real-price momentum
check over the last few bars gates every signal - the curve fit alone is
not trusted, same "no pure lookahead/no pure curve-fit" discipline as the
other backtests in this directory.

Same $5,000 / 1% risk sizing and walk-forward, no-lookahead simulation as
the other backtests for direct comparison.
"""
import statistics
from math import atan2, cos, pi, sin, sqrt

from measured_swing_backtest import load_data, ACCOUNT_SIZE, RISK_PCT

DAILY_SRC = "data/btc_usd_daily.csv"

DETREND_WINDOW = 50        # SMA window subtracted from price to isolate the cycle
FIT_WINDOW = 180           # trailing bars used to fit the dominant sinusoid each bar
PERIOD_MIN, PERIOD_MAX, PERIOD_STEP = 10, 60, 2   # candidate cycle lengths scanned (days)
MOMENTUM_CONFIRM_BARS = 3  # real price must also be moving with the signal, not just the fit
SWING_LOOKBACK = 20        # bars back for the structural stop-loss
SL_BUFFER = 0.02
TP_AMPLITUDE_MULT = 1.0    # take-profit = entry +/- this many cycle amplitudes


def compute_detrended(closes, window):
    """close - trailing SMA, aligned to the same index as `closes`; None
    where the SMA isn't yet defined."""
    out = [None] * len(closes)
    for i in range(window - 1, len(closes)):
        sma = sum(closes[i - window + 1:i + 1]) / window
        out[i] = closes[i] - sma
    return out


def fit_dominant_cycle(window_vals):
    """window_vals: W detrended values, oldest first (t=0..W-1). Scans
    candidate periods and returns the one with the largest periodogram
    power, i.e. the cycle length the data correlates with most strongly."""
    W = len(window_vals)
    best = None
    for T in range(PERIOD_MIN, PERIOD_MAX + 1, PERIOD_STEP):
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
    amplitude = sqrt(a * a + b * b)
    return T, a, b, amplitude


def cycle_derivative(a, b, omega, t):
    """d/dt [a*cos(wt) + b*sin(wt)] = -a*w*sin(wt) + b*w*cos(wt)."""
    return -a * omega * sin(omega * t) + b * omega * cos(omega * t)


def run_cycle_backtest(bars, tp_amplitude_mult=TP_AMPLITUDE_MULT, fit_window=FIT_WINDOW):
    closes = [bar["close"] for bar in bars]
    detrended = compute_detrended(closes, DETREND_WINDOW)
    start = DETREND_WINDOW - 1 + fit_window - 1

    trades = []
    open_trade = None
    dominant_periods = []
    signals_seen = signals_confirmed = 0

    i = start
    while i < len(bars) - 1:
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

        window = detrended[i - fit_window + 1:i + 1]
        T, a, b, amplitude = fit_dominant_cycle(window)
        dominant_periods.append(T)
        omega = 2 * pi / T
        W = len(window)
        d_now = cycle_derivative(a, b, omega, W - 1)
        d_prev = cycle_derivative(a, b, omega, W - 2)

        direction = None
        if d_prev <= 0 and d_now > 0:
            direction = "LONG"
        elif d_prev >= 0 and d_now < 0:
            direction = "SHORT"

        if direction:
            signals_seen += 1
            momentum_ok = (
                closes[i] > closes[i - MOMENTUM_CONFIRM_BARS] if direction == "LONG"
                else closes[i] < closes[i - MOMENTUM_CONFIRM_BARS]
            )
            if momentum_ok:
                signals_confirmed += 1
                entry_idx = i + 1
                entry = bars[entry_idx]["open"]
                lo = min(bar["low"] for bar in bars[i - SWING_LOOKBACK + 1:i + 1])
                hi = max(bar["high"] for bar in bars[i - SWING_LOOKBACK + 1:i + 1])
                if direction == "LONG":
                    sl = lo * (1 - SL_BUFFER)
                    tp = entry + amplitude * tp_amplitude_mult
                else:
                    sl = hi * (1 + SL_BUFFER)
                    tp = entry - amplitude * tp_amplitude_mult
                risk_per_unit = abs(entry - sl)
                if risk_per_unit > 0:
                    open_trade = {
                        "direction": direction, "entry_idx": entry_idx, "entry": entry,
                        "sl": sl, "tp": tp, "risk_per_unit": risk_per_unit,
                        "position_size": (ACCOUNT_SIZE * RISK_PCT) / risk_per_unit,
                        "period": T, "amplitude": amplitude, "outcome": None,
                    }
        i += 1

    if open_trade is not None:
        open_trade["outcome"] = "OPEN"
        trades.append(open_trade)

    return trades, dominant_periods, signals_seen, signals_confirmed


def report(bars, trades, dominant_periods, signals_seen, signals_confirmed):
    lines = []
    lines.append("=" * 100)
    lines.append("CYCLE (SINE-WAVE) STRATEGY - BTCUSD DAILY BACKTEST")
    lines.append("=" * 100)
    lines.append(f"Detrend SMA: {DETREND_WINDOW}d   Fit window: {FIT_WINDOW}d   "
                 f"Candidate periods: {PERIOD_MIN}-{PERIOD_MAX}d step {PERIOD_STEP}")
    lines.append(f"Momentum confirm: {MOMENTUM_CONFIRM_BARS}d   SL: swing {SWING_LOOKBACK}d lookback "
                 f"+{SL_BUFFER:.0%} buffer   TP: {TP_AMPLITUDE_MULT}x fitted cycle amplitude")
    lines.append("")

    closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
    still_open = [t for t in trades if t["outcome"] == "OPEN"]

    header = (f"{'#':>3} {'Dir':<6} {'Entry Date':<11} {'Exit Date':<11} {'Entry':>10} {'SL':>10} "
              f"{'TP':>10} {'Period':>7} {'Res':<5} {'PnL$':>9} {'R':>6} {'W-L':<8} {'Equity$':>10}")
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
                     f"{t['tp']:>10,.1f} {t['period']:>7} {t['outcome']:<5} {t['pnl_cash']:>9,.2f} "
                     f"{t['r_multiple']:>6.2f} {f'{w}-{l}':<8} {equity:>10,.2f}")

    lines.append("")
    lines.append("-" * 100)
    lines.append("SUMMARY")
    lines.append(f"Cycle-turn signals detected     : {signals_seen}")
    lines.append(f"  Passed momentum confirmation  : {signals_confirmed} "
                 f"({signals_confirmed/signals_seen*100:.1f}%)" if signals_seen else "  Passed momentum confirmation  : 0")
    lines.append(f"Trades still open at data end   : {len(still_open)}")
    lines.append(f"Closed trades                   : {len(closed)}")
    lines.append(f"  Wins                          : {w}")
    lines.append(f"  Losses                        : {l}")
    if dominant_periods:
        lines.append(f"Dominant period detected (median): {statistics.median(dominant_periods):.0f}d "
                     f"(min {min(dominant_periods)}d, max {max(dominant_periods)}d across {len(dominant_periods)} fits)")
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
    """Same discipline as the other backtests here: a single config that
    looks good is worthless until it survives varying the free parameters.
    Sweeps the fit window (how much history defines "the" cycle) and the
    TP amplitude multiple (how big a slice of that cycle is targeted)."""
    lines = []
    lines.append("-" * 100)
    lines.append("PARAMETER SWEEP (fit window x TP amplitude multiple)")
    lines.append("-" * 100)
    lines.append(f"{'FitWin':>6} {'TPxAmp':>6} {'Signals':>7} {'Confirmed':>9} {'Closed':>6} "
                 f"{'W':>3} {'L':>3} {'WinRate':>8} {'NetPnL':>10}")
    for fit_window in (120, 150, 180, 240):
        for tp_mult in (0.5, 0.75, 1.0, 1.5, 2.0):
            trades, _, seen, confirmed = run_cycle_backtest(bars, tp_amplitude_mult=tp_mult, fit_window=fit_window)
            closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
            w = sum(1 for t in closed if t["outcome"] == "WIN")
            l = len(closed) - w
            net = sum(t["pnl_cash"] for t in closed)
            wr = (w / len(closed) * 100) if closed else 0.0
            lines.append(f"{fit_window:>6} {tp_mult:>6.2f} {seen:>7} {confirmed:>9} {len(closed):>6} "
                         f"{w:>3} {l:>3} {wr:>7.1f}% {net:>+10.2f}")
    return "\n".join(lines)


def main():
    bars = load_data(DAILY_SRC)
    trades, periods, seen, confirmed = run_cycle_backtest(bars)
    out = report(bars, trades, periods, seen, confirmed)
    out += "\n\n" + parameter_sweep(bars)
    print(out)
    with open("results_cycle_sine.txt", "w") as f:
        f.write(out + "\n")


if __name__ == "__main__":
    main()

"""
Cycle (sine-wave) signal, ported for live monitoring from
swing_strategy/cycle_sine_backtest.py's periodogram fit / derivative
turning-point logic - duplicated here (not imported), same reasoning as
strategy.py duplicating find_pivots: no cross-package relative-path
dependency between this bot and the backtest package.

Unlike the breakout setups, a cycle signal isn't pivot-anchored, so the
live evaluator only checks the latest fully-confirmed bar each pass and
keys idempotency off that bar's date + direction instead of a leg key.
"""
from math import cos, pi, sin, sqrt

from config import (
    CYCLE_DETREND_WINDOW, CYCLE_FIT_WINDOW, CYCLE_PERIOD_MIN, CYCLE_PERIOD_MAX,
    CYCLE_PERIOD_STEP, CYCLE_MOMENTUM_CONFIRM_BARS, CYCLE_SWING_LOOKBACK,
    CYCLE_SL_BUFFER, CYCLE_TP_AMPLITUDE_MULT,
)


def compute_detrended(closes, window):
    out = [None] * len(closes)
    for i in range(window - 1, len(closes)):
        sma = sum(closes[i - window + 1:i + 1]) / window
        out[i] = closes[i] - sma
    return out


def fit_dominant_cycle(window_vals):
    W = len(window_vals)
    best = None
    for T in range(CYCLE_PERIOD_MIN, CYCLE_PERIOD_MAX + 1, CYCLE_PERIOD_STEP):
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
    return -a * omega * sin(omega * t) + b * omega * cos(omega * t)


def current_watch_cycle(bars):
    """Most recent fit/derivative state, for status/dashboard display only -
    never used for trade decisions (those require an actual fresh
    trough/peak crossing, checked in evaluate_latest_cycle_signal)."""
    closes = [bar["close"] for bar in bars]
    detrended = compute_detrended(closes, CYCLE_DETREND_WINDOW)
    start = CYCLE_DETREND_WINDOW - 1 + CYCLE_FIT_WINDOW - 1
    i = len(bars) - 2  # latest fully-confirmed bar (bars[-1] may still be forming)
    if i < start:
        return None
    window = detrended[i - CYCLE_FIT_WINDOW + 1:i + 1]
    T, a, b, amplitude = fit_dominant_cycle(window)
    omega = 2 * pi / T
    W = len(window)
    d_now = cycle_derivative(a, b, omega, W - 1)
    return {"period": T, "amplitude": round(amplitude, 2), "derivative": round(d_now, 4),
            "date": bars[i]["date"]}


def evaluate_latest_cycle_signal(bars, already_handled_cycle_key):
    """Checks the most recently CONFIRMED bar (bars[-2]) for a trough/peak
    crossing in the fitted cycle's derivative, gated by real-price momentum
    - same rule chain as cycle_sine_backtest.run_cycle_backtest. Returns a
    setup dict (entry at the NEXT bar's open) or None."""
    closes = [bar["close"] for bar in bars]
    detrended = compute_detrended(closes, CYCLE_DETREND_WINDOW)
    start = CYCLE_DETREND_WINDOW - 1 + CYCLE_FIT_WINDOW - 1 + CYCLE_MOMENTUM_CONFIRM_BARS

    i = len(bars) - 2  # last fully confirmed bar; entry would fill at bars[i+1]'s open
    if i < start or i + 1 >= len(bars):
        return None

    window = detrended[i - CYCLE_FIT_WINDOW + 1:i + 1]
    T, a, b, amplitude = fit_dominant_cycle(window)
    omega = 2 * pi / T
    W = len(window)
    d_now = cycle_derivative(a, b, omega, W - 1)
    d_prev = cycle_derivative(a, b, omega, W - 2)

    direction = None
    if d_prev <= 0 and d_now > 0:
        direction = "LONG"
    elif d_prev >= 0 and d_now < 0:
        direction = "SHORT"
    if direction is None:
        return None

    cycle_key = f"{bars[i]['date']}:{direction}"
    if cycle_key == already_handled_cycle_key:
        return None

    momentum_ok = (
        closes[i] > closes[i - CYCLE_MOMENTUM_CONFIRM_BARS] if direction == "LONG"
        else closes[i] < closes[i - CYCLE_MOMENTUM_CONFIRM_BARS]
    )
    if not momentum_ok:
        return None

    entry_idx = i + 1
    entry = bars[entry_idx]["open"]
    lo = min(bar["low"] for bar in bars[i - CYCLE_SWING_LOOKBACK + 1:i + 1])
    hi = max(bar["high"] for bar in bars[i - CYCLE_SWING_LOOKBACK + 1:i + 1])
    if direction == "LONG":
        sl = lo * (1 - CYCLE_SL_BUFFER)
        tp = entry + amplitude * CYCLE_TP_AMPLITUDE_MULT
    else:
        sl = hi * (1 + CYCLE_SL_BUFFER)
        tp = entry - amplitude * CYCLE_TP_AMPLITUDE_MULT

    risk_per_unit = abs(entry - sl)
    if risk_per_unit <= 0:
        return None

    return {
        "direction": direction, "entry_price": entry, "sl": sl, "tp": tp,
        "period": T, "amplitude": amplitude, "cycle_key": cycle_key,
        "triggered_date": bars[entry_idx].get("date"), "triggered_bar_idx": entry_idx,
    }

"""
v2 breakout-continuation rules, ported for live monitoring from
swing_strategy/breakout_continuation_v2_backtest.py. Reuses the same
zig-zag pivot detector as strategy.py (find_pivots/Pivot) since the pivot
structure is identical to v1 - only the entry confirmation and SL/TP math
differ: entry requires a CLOSE beyond the breakout level (not a wick touch)
and fills at the NEXT bar's open, SL is anchored to the breakout level
itself retraced by SL_GIVEBACK_FRAC of the leg's range (not the leg's far
origin like v1), and TP is a 161.8% extension instead of v1's 100%.
"""
from config import BREAKOUT_BUFFER, SL_GIVEBACK_FRAC, TP_EXTENSION_V2
from strategy import find_pivots


def build_breakout_setup_v2(p0, p1):
    rng = abs(p1.price - p0.price)
    direction = "LONG" if p1.kind == "H" else "SHORT"

    if direction == "LONG":
        breakout_level = p1.price * (1 + BREAKOUT_BUFFER)
        sl = breakout_level - SL_GIVEBACK_FRAC * rng
        tp = breakout_level + rng * TP_EXTENSION_V2
    else:
        breakout_level = p1.price * (1 - BREAKOUT_BUFFER)
        sl = breakout_level + SL_GIVEBACK_FRAC * rng
        tp = breakout_level - rng * TP_EXTENSION_V2

    return {
        "direction": direction, "swing_origin": p0.price, "swing_point": p1.price,
        "breakout_level": breakout_level, "sl": sl, "tp": tp, "rng": rng,
        "leg_key": f"{p1.idx}:{p1.kind}:{p1.price:.2f}",
        "confirm_idx": p1.confirm_idx,
    }


def current_watch_v2(bars):
    """Same anchor as evaluate_latest_leg_v2 (pivots[-3]/[-2]) but returns
    the setup unconditionally, purely for status/dashboard display."""
    pivots = find_pivots(bars)
    if len(pivots) < 3:
        return None
    p0, p1 = pivots[-3], pivots[-2]
    return build_breakout_setup_v2(p0, p1)


def evaluate_latest_leg_v2(bars, already_handled_leg_key):
    """Returns a trigger dict if the most recently CONFIRMED leg has closed
    beyond its breakout level and hasn't already been acted on, else None.
    Entry fills at the NEXT bar's open - matches
    breakout_continuation_v2_backtest.run_breakout_v2_backtest's entry rule
    exactly, just anchored on the latest leg only instead of walking all
    historical legs."""
    pivots = find_pivots(bars)
    if len(pivots) < 3:
        return None

    p0, p1 = pivots[-3], pivots[-2]
    setup = build_breakout_setup_v2(p0, p1)

    if setup["leg_key"] == already_handled_leg_key:
        return None

    start = setup["confirm_idx"] + 1
    for j in range(start, len(bars) - 1):
        bar = bars[j]
        confirmed = (bar["close"] >= setup["breakout_level"] if setup["direction"] == "LONG"
                     else bar["close"] <= setup["breakout_level"])
        if confirmed:
            entry_idx = j + 1
            setup["triggered_bar_idx"] = entry_idx
            setup["triggered_date"] = bars[entry_idx].get("date")
            setup["entry_price"] = bars[entry_idx]["open"]
            return setup

    return None  # still watching, no close-confirmed breakout yet

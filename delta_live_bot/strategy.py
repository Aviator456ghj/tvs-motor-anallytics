"""
v1 breakout-continuation rules, ported for live monitoring instead of an
offline backtest. Pivot detection is the same zig-zag algorithm as
swing_strategy/measured_swing_backtest.py::find_pivots - duplicated here
(rather than imported) so this bot has no dependency on the backtest
package's relative paths.

Pivot list semantics: every entry except the LAST one is a fully
CONFIRMED swing point (price reversed past ZIGZAG_THRESHOLD away from it).
The last entry is a provisional "current running extreme" that updates
every bar while the trend continues - it is NOT a confirmed pivot, so live
trade logic anchors off pivots[-2] (last confirmed point) and
pivots[-3] (the point before it), never pivots[-1].
"""
from dataclasses import dataclass

from config import ZIGZAG_THRESHOLD, BREAKOUT_BUFFER, SL_BUFFER, TP_EXTENSION


@dataclass
class Pivot:
    idx: int
    price: float
    kind: str  # 'H' or 'L'
    confirm_idx: int


def find_pivots(bars, threshold=ZIGZAG_THRESHOLD):
    pivots = []
    trend = None
    extreme_price = bars[0]["close"]
    extreme_idx = 0

    for i in range(1, len(bars)):
        h, l = bars[i]["high"], bars[i]["low"]

        if trend is None:
            if h >= extreme_price * (1 + threshold):
                trend = "up"
                extreme_price, extreme_idx = h, i
            elif l <= extreme_price * (1 - threshold):
                trend = "down"
                extreme_price, extreme_idx = l, i
            continue

        if trend == "up":
            if h > extreme_price:
                extreme_price, extreme_idx = h, i
            elif l <= extreme_price * (1 - threshold):
                pivots.append(Pivot(extreme_idx, extreme_price, "H", i))
                trend = "down"
                extreme_price, extreme_idx = l, i
        else:
            if l < extreme_price:
                extreme_price, extreme_idx = l, i
            elif h >= extreme_price * (1 + threshold):
                pivots.append(Pivot(extreme_idx, extreme_price, "L", i))
                trend = "up"
                extreme_price, extreme_idx = h, i

    pivots.append(Pivot(extreme_idx, extreme_price, "H" if trend == "up" else "L", len(bars) - 1))
    return pivots


def build_breakout_setup(p0: Pivot, p1: Pivot):
    """Same math as breakout_continuation_backtest.run_breakout_backtest:
    SL at the leg's origin +/- 2%, TP at a 100% measured move from the
    breakout level. This is v1 as the user explicitly chose to deploy,
    not the more robust v2 redesign."""
    rng = abs(p1.price - p0.price)
    direction = "LONG" if p1.kind == "H" else "SHORT"

    if direction == "LONG":
        breakout_level = p1.price * (1 + BREAKOUT_BUFFER)
        sl = p0.price * (1 - SL_BUFFER)
        tp = breakout_level + rng * TP_EXTENSION
    else:
        breakout_level = p1.price * (1 - BREAKOUT_BUFFER)
        sl = p0.price * (1 + SL_BUFFER)
        tp = breakout_level - rng * TP_EXTENSION

    return {
        "direction": direction, "swing_origin": p0.price, "swing_point": p1.price,
        "breakout_level": breakout_level, "sl": sl, "tp": tp, "rng": rng,
        "leg_key": f"{p1.idx}:{p1.kind}:{p1.price:.2f}",
        "confirm_idx": p1.confirm_idx,
    }


def evaluate_latest_leg(bars, already_handled_leg_key):
    """Returns a trigger dict if the most recently CONFIRMED leg has
    broken out and hasn't already been acted on, else None."""
    pivots = find_pivots(bars)
    if len(pivots) < 3:
        return None  # not enough confirmed history yet

    p0, p1 = pivots[-3], pivots[-2]  # last fully confirmed leg
    setup = build_breakout_setup(p0, p1)

    if setup["leg_key"] == already_handled_leg_key:
        return None  # already acted on this leg

    start = setup["confirm_idx"] + 1
    for j in range(start, len(bars)):
        bar = bars[j]
        if setup["direction"] == "LONG" and bar["high"] >= setup["breakout_level"]:
            setup["triggered_bar_idx"] = j
            setup["triggered_date"] = bar.get("date")
            return setup
        if setup["direction"] == "SHORT" and bar["low"] <= setup["breakout_level"]:
            setup["triggered_bar_idx"] = j
            setup["triggered_date"] = bar.get("date")
            return setup

    return None  # still watching, no breakout yet

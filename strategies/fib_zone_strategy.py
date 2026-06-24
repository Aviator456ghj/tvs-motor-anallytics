"""
Trend-Based Fibonacci Zone strategy — FINALIZED, chosen version.

Structure timeframe: 30m (HH/HL and LL/LH swing detection, Point3 retest, zone projection)
Entry timeframe: 5m (candle confirmation inside the zone)
Cascade: OFF — only the first zone touched+confirmed per setup is traded.

Selection rationale (see STRATEGY_NOTES.md for the full analysis trail):
this configuration was chosen over a 30m/5m cascading-zone variant and a
1h/5m cascading variant because it is the only one where BTCUSD, ETHUSD,
and SOLUSD were ALL individually profitable, on the largest trade sample
of the three candidates compared.

Usage:
    from fib_zone_strategy import build_zigzag, find_setups, run_backtest

Data format expected: list of dicts with keys open/high/low/close/time/volume,
ascending by time (matches Delta Exchange India /v2/history/candles response).
"""

import bisect

# Paired Fibonacci zone boxes (per the corroborated screenshot reference):
# 0 and 2.618 are plain anchor lines, NOT independently tradable.
ZONES = [
    ("ZoneA_red", 0.5, 0.618),
    ("ZoneB_teal", 1.414, 1.618),
    ("ZoneC_yellow", 2.0, 2.272),
]

PIVOT_W = 3                       # swing pivot confirmation width, in structure-TF bars
RETEST_TOL_PCT = 0.0015           # how close price must come back to Point1 to count as Point3
RETEST_MAX_BARS_STRUCT = 300      # how many structure-TF bars to wait for the Point3 retest
ZONE_TOUCH_BUFFER_PCT = 0.0005    # extra wick tolerance on zone edges
STOP_BUFFER_PCT = 0.0015          # stop placed this far beyond the zone edge
ENTRY_VALID_BARS_STRUCT = 300     # how many structure-TF bars the zone stays "live" for entries
MAX_HOLD_BARS_STRUCT = 288        # max trade duration, expressed in structure-TF bars

STRUCT_BAR_SECONDS = 1800         # 30m
ENTRY_BAR_SECONDS = 300           # 5m


def build_zigzag(highs, lows, n):
    def is_pivot_high(i):
        if i - PIVOT_W < 0 or i + PIVOT_W >= n:
            return False
        return highs[i] == max(highs[i - PIVOT_W:i + PIVOT_W + 1])

    def is_pivot_low(i):
        if i - PIVOT_W < 0 or i + PIVOT_W >= n:
            return False
        return lows[i] == min(lows[i - PIVOT_W:i + PIVOT_W + 1])

    raw = []
    for i in range(n):
        if is_pivot_high(i):
            raw.append((i, "H", highs[i], i + PIVOT_W))
        if is_pivot_low(i):
            raw.append((i, "L", lows[i], i + PIVOT_W))
    raw.sort(key=lambda p: p[0])

    zigzag = []
    for p in raw:
        if not zigzag:
            zigzag.append(p)
            continue
        last = zigzag[-1]
        if p[1] == last[1]:
            if p[1] == "H" and p[2] > last[2]:
                zigzag[-1] = p
            elif p[1] == "L" and p[2] < last[2]:
                zigzag[-1] = p
        else:
            zigzag.append(p)
    return zigzag


def find_setups(zigzag):
    """LONG = HH followed by a genuine HL. SHORT = LL followed by a genuine LH."""
    setups = []
    for k in range(1, len(zigzag) - 1):
        cur, nxt = zigzag[k], zigzag[k + 1]
        if cur[1] == "H" and nxt[1] == "L":
            prior_highs = [z for z in zigzag[:k] if z[1] == "H"]
            prior_lows = [z for z in zigzag[:k] if z[1] == "L"]
            if prior_highs and prior_lows and cur[2] > prior_highs[-1][2] and nxt[2] > prior_lows[-1][2]:
                setups.append(("LONG", cur[2], cur[3], nxt[2], nxt[3]))
        if cur[1] == "L" and nxt[1] == "H":
            prior_lows = [z for z in zigzag[:k] if z[1] == "L"]
            prior_highs = [z for z in zigzag[:k] if z[1] == "H"]
            if prior_lows and prior_highs and cur[2] < prior_lows[-1][2] and nxt[2] < prior_highs[-1][2]:
                setups.append(("SHORT", cur[2], cur[3], nxt[2], nxt[3]))
    return setups


def compute_zone_boxes(direction, p3, leg):
    """Returns [(name, lo, hi), ...] price ranges for the 3 zones, given Point3 and the leg size."""
    zone_boxes = []
    for name, r_near, r_far in ZONES:
        if direction == "LONG":
            near_edge = p3 - r_near * leg
            far_edge = p3 - r_far * leg
            zone_boxes.append((name, far_edge, near_edge))
        else:
            near_edge = p3 + r_near * leg
            far_edge = p3 + r_far * leg
            zone_boxes.append((name, near_edge, far_edge))
    return zone_boxes


def run_backtest(struct_candles, entry_candles):
    """
    struct_candles: 30m candles (or whatever structure TF) used to build the zigzag,
                     detect HH/HL & LL/LH setups, and locate the Point3 retest.
    entry_candles:  5m candles (or whatever lower TF) used purely to confirm/trigger
                     the actual entry once price reaches a zone.
    Returns a list of trade dicts.
    """
    s_highs = [float(c["high"]) for c in struct_candles]
    s_lows = [float(c["low"]) for c in struct_candles]
    s_times = [c["time"] for c in struct_candles]
    n_s = len(struct_candles)

    e_opens = [float(c["open"]) for c in entry_candles]
    e_highs = [float(c["high"]) for c in entry_candles]
    e_lows = [float(c["low"]) for c in entry_candles]
    e_closes = [float(c["close"]) for c in entry_candles]
    e_times = [c["time"] for c in entry_candles]
    n_e = len(entry_candles)

    zigzag = build_zigzag(s_highs, s_lows, n_s)
    setups = find_setups(zigzag)

    retest_max_seconds = RETEST_MAX_BARS_STRUCT * STRUCT_BAR_SECONDS
    entry_valid_seconds = ENTRY_VALID_BARS_STRUCT * STRUCT_BAR_SECONDS
    max_hold_seconds = MAX_HOLD_BARS_STRUCT * STRUCT_BAR_SECONDS

    trades = []
    in_trade_until_time = -1

    for direction, p1, p1_at, p2, p2_at in setups:
        leg = abs(p1 - p2)
        if leg <= 0:
            continue

        retest_deadline = s_times[p2_at] + retest_max_seconds
        p3_idx = None
        for j in range(p2_at, n_s):
            if s_times[j] > retest_deadline:
                break
            if s_times[j] <= in_trade_until_time:
                continue
            if direction == "LONG" and s_highs[j] >= p1 * (1 - RETEST_TOL_PCT):
                p3_idx = j; break
            if direction == "SHORT" and s_lows[j] <= p1 * (1 + RETEST_TOL_PCT):
                p3_idx = j; break
        if p3_idx is None:
            continue
        p3 = p1
        p3_time = s_times[p3_idx]

        zone_boxes = compute_zone_boxes(direction, p3, leg)

        e_start_idx = bisect.bisect_right(e_times, p3_time)
        e_scan_end_time = p3_time + entry_valid_seconds
        entered = False
        for j in range(e_start_idx, n_e):
            if e_times[j] > e_scan_end_time:
                break
            if e_times[j] <= in_trade_until_time:
                continue
            c, o, h, l = e_closes[j], e_opens[j], e_highs[j], e_lows[j]
            for name, zlo, zhi in zone_boxes:
                buf = zlo * ZONE_TOUCH_BUFFER_PCT
                if direction == "LONG":
                    touched = l <= zhi and l >= zlo - buf
                    rejection = c > o and c >= zlo
                else:
                    touched = h >= zlo and h <= zhi + buf
                    rejection = c < o and c <= zhi
                if not (touched and rejection):
                    continue
                entry = c
                if direction == "LONG":
                    stop = zlo * (1 - STOP_BUFFER_PCT)
                    risk = entry - stop
                else:
                    stop = zhi * (1 + STOP_BUFFER_PCT)
                    risk = stop - entry
                if risk <= 0:
                    continue
                target = p3
                exit_price = exit_reason = exit_idx = None
                hold_end_time = e_times[j] + max_hold_seconds
                for m in range(j + 1, n_e):
                    if e_times[m] > hold_end_time:
                        break
                    if direction == "LONG":
                        if e_lows[m] <= stop:
                            exit_price, exit_reason, exit_idx = stop, "STOP", m; break
                        if e_highs[m] >= target:
                            exit_price, exit_reason, exit_idx = target, "TARGET", m; break
                    else:
                        if e_highs[m] >= stop:
                            exit_price, exit_reason, exit_idx = stop, "STOP", m; break
                        if e_lows[m] <= target:
                            exit_price, exit_reason, exit_idx = target, "TARGET", m; break
                if exit_price is None:
                    bar_step = e_times[1] - e_times[0]
                    exit_idx = min(j + 1 + int(max_hold_seconds / bar_step), n_e - 1)
                    exit_price, exit_reason = e_closes[exit_idx], "TIME"
                pnl = (exit_price - entry) if direction == "LONG" else (entry - exit_price)
                r = pnl / risk
                trades.append({
                    "direction": direction, "zone": name, "entry_time": e_times[j],
                    "entry": entry, "stop": stop, "target": target,
                    "exit_price": exit_price, "exit_reason": exit_reason, "r_multiple": r,
                })
                in_trade_until_time = e_times[exit_idx]
                entered = True
                break
            if entered:
                break
    return trades


def find_live_setup(struct_candles, entry_candles):
    """
    Causal, no-lookahead check for whether a zone is ACTIVE right now (last entry candle),
    i.e. price is currently sitting inside one of the 3 zones for the most recent unresolved
    setup, waiting for (or just printing) a confirmation candle. Used for live monitoring,
    not backtesting. Returns a dict describing the live zone state, or None.
    """
    s_highs = [float(c["high"]) for c in struct_candles]
    s_lows = [float(c["low"]) for c in struct_candles]
    s_times = [c["time"] for c in struct_candles]
    n_s = len(struct_candles)

    zigzag = build_zigzag(s_highs, s_lows, n_s)
    setups = find_setups(zigzag)
    if not setups:
        return None

    retest_max_seconds = RETEST_MAX_BARS_STRUCT * STRUCT_BAR_SECONDS
    entry_valid_seconds = ENTRY_VALID_BARS_STRUCT * STRUCT_BAR_SECONDS

    last_close_time = entry_candles[-1]["time"]
    last_close = float(entry_candles[-1]["close"])
    last_low = float(entry_candles[-1]["low"])
    last_high = float(entry_candles[-1]["high"])
    last_open = float(entry_candles[-1]["open"])

    for direction, p1, p1_at, p2, p2_at in reversed(setups):
        leg = abs(p1 - p2)
        if leg <= 0:
            continue
        retest_deadline = s_times[p2_at] + retest_max_seconds
        p3_idx = None
        for j in range(p2_at, n_s):
            if s_times[j] > retest_deadline:
                break
            if direction == "LONG" and s_highs[j] >= p1 * (1 - RETEST_TOL_PCT):
                p3_idx = j; break
            if direction == "SHORT" and s_lows[j] <= p1 * (1 + RETEST_TOL_PCT):
                p3_idx = j; break
        if p3_idx is None:
            continue
        p3 = p1
        p3_time = s_times[p3_idx]
        if last_close_time > p3_time + entry_valid_seconds:
            continue  # zone has expired

        zone_boxes = compute_zone_boxes(direction, p3, leg)
        for name, zlo, zhi in zone_boxes:
            buf = zlo * ZONE_TOUCH_BUFFER_PCT
            if direction == "LONG":
                touched = last_low <= zhi and last_low >= zlo - buf
                confirmed = last_close > last_open and last_close >= zlo
            else:
                touched = last_high >= zlo and last_high <= zhi + buf
                confirmed = last_close < last_open and last_close <= zhi
            if touched:
                return {
                    "direction": direction, "zone": name, "zone_lo": zlo, "zone_hi": zhi,
                    "p1": p1, "p3": p3, "leg": leg, "confirmed": confirmed,
                    "current_close": last_close,
                }
        break  # only the most recent setup matters for "live" status
    return None

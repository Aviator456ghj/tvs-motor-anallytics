"""
Leg/2.6 confluence strategy — FINALIZED, chosen subset.

Origin: Saide's "leg/2.6" video method (demoed on XAUUSD): measure a price leg
(swing high to swing low, or the mirror swing low to swing high), divide the
leg size by 2.6, and project that value further in the leg's direction from
its endpoint. Stack the last few legs; where 2+ projected levels cluster
("confluence"), that's a tradable zone.

Corrected per user's reference screenshot: a DOWN leg (H->L) projects its
zone further DOWN from the low -> a SHORT continuation zone. The mirror UP
leg (L->H) projects further UP from the high -> a LONG continuation zone.

See LEG26_STRATEGY_NOTES.md for the full analysis trail (this is a secondary/
weaker strategy than fib_zone_strategy.py -- saved for reference, not as the
primary signal generator).

Two independently-run, single-timeframe configs were the only ones that held
up in isolation (no MTF, no lower-TF confirmation, no trend filter):
    1h  : trade BOTH long-leg and short-leg confluence zones (PF 1.18, all 3 assets positive)
    30m : trade SHORT-leg confluence zones ONLY (PF 1.20; LONG side was negative in isolation)

15m and 5m were also tested and REJECTED (15m PF 0.96 losing, 5m PF 1.00 breakeven,
both in isolation) -- not included here.

Each TF config is run as its own standalone causal backtest per asset; this module
does not share a trade-lock between the 1h and 30m configs.

Usage:
    from leg26_confluence_strategy import run_backtest, find_live_setup
    trades = run_backtest(candles, "1h")
    trades = run_backtest(candles, "30m")
"""

PIVOT_W = 3
DIVISOR = 2.6
MAX_LEGS_STACKED = 4
CONFLUENCE_TOL_PCT = 0.0025
ZONE_BUFFER_PCT = 0.0015
TARGET_R = 2.0
HOLD_DAYS = 6

TF_CONFIG = {
    "1h": {"bar_seconds": 3600, "directions": ("LONG", "SHORT")},
    "30m": {"bar_seconds": 1800, "directions": ("SHORT",)},
}


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


def build_legs(zigzag):
    """down_legs -> SHORT continuation zones (level = low - leg/2.6).
    up_legs -> LONG continuation zones (level = high + leg/2.6)."""
    down_legs, up_legs = [], []
    for k in range(len(zigzag) - 1):
        a, b = zigzag[k], zigzag[k + 1]
        if a[1] == "H" and b[1] == "L":
            leg_size = a[2] - b[2]
            if leg_size <= 0:
                continue
            level = b[2] - leg_size / DIVISOR
            confirmed_at = max(a[3], b[3])
            down_legs.append({"level": level, "confirmed_at": confirmed_at})
        if a[1] == "L" and b[1] == "H":
            leg_size = b[2] - a[2]
            if leg_size <= 0:
                continue
            level = b[2] + leg_size / DIVISOR
            confirmed_at = max(a[3], b[3])
            up_legs.append({"level": level, "confirmed_at": confirmed_at})
    return down_legs, up_legs


def confluence_zones(levels):
    if len(levels) < 2:
        return []
    levels_sorted = sorted(levels)
    clusters, cur = [], [levels_sorted[0]]
    for lv in levels_sorted[1:]:
        if (lv - cur[-1]) / cur[-1] <= CONFLUENCE_TOL_PCT:
            cur.append(lv)
        else:
            clusters.append(cur)
            cur = [lv]
    clusters.append(cur)
    return [(min(c), max(c)) for c in clusters if len(c) >= 2]


def run_backtest(candles, timeframe):
    """candles: list of OHLCV dicts for the given timeframe, ascending by time."""
    directions = TF_CONFIG[timeframe]["directions"]
    bar_seconds = TF_CONFIG[timeframe]["bar_seconds"]
    max_hold_bars = max(1, int(HOLD_DAYS * 86400 / bar_seconds))

    opens = [float(c["open"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    closes = [float(c["close"]) for c in candles]
    times = [c["time"] for c in candles]
    n = len(candles)

    zigzag = build_zigzag(highs, lows, n)
    down_legs, up_legs = build_legs(zigzag)

    trades = []
    in_trade_until = -1

    for i in range(n):
        if i <= in_trade_until:
            continue
        c, o, h, l = closes[i], opens[i], highs[i], lows[i]
        avail_down = [lg["level"] for lg in down_legs if lg["confirmed_at"] < i]
        avail_up = [lg["level"] for lg in up_legs if lg["confirmed_at"] < i]
        short_zones = confluence_zones(avail_down[-MAX_LEGS_STACKED:]) if len(avail_down) >= 2 else []
        long_zones = confluence_zones(avail_up[-MAX_LEGS_STACKED:]) if len(avail_up) >= 2 else []

        fired = False
        if "SHORT" in directions:
            for zlo, zhi in short_zones:
                buf = zlo * ZONE_BUFFER_PCT
                touched = h >= zlo - buf and h <= zhi + buf * 3
                rejected = c < o and c <= zhi
                if touched and rejected:
                    entry = c
                    stop = zhi * (1 + ZONE_BUFFER_PCT)
                    risk = stop - entry
                    if risk <= 0:
                        continue
                    target = entry - risk * TARGET_R
                    exit_price = exit_reason = exit_idx = None
                    for m in range(i + 1, min(i + 1 + max_hold_bars, n)):
                        if highs[m] >= stop:
                            exit_price, exit_reason, exit_idx = stop, "STOP", m; break
                        if lows[m] <= target:
                            exit_price, exit_reason, exit_idx = target, "TARGET", m; break
                    if exit_price is None:
                        exit_idx = min(i + max_hold_bars, n - 1)
                        exit_price, exit_reason = closes[exit_idx], "TIME"
                    r = (entry - exit_price) / risk
                    trades.append({"entry_time": times[i], "direction": "SHORT", "entry": entry,
                                   "stop": stop, "target": target, "exit_price": exit_price,
                                   "exit_reason": exit_reason, "r_multiple": r})
                    in_trade_until = exit_idx
                    fired = True
                    break
        if fired:
            continue

        if "LONG" in directions:
            for zlo, zhi in long_zones:
                buf = zlo * ZONE_BUFFER_PCT
                touched = l <= zhi + buf and l >= zlo - buf * 3
                rejected = c > o and c >= zlo
                if touched and rejected:
                    entry = c
                    stop = zlo * (1 - ZONE_BUFFER_PCT)
                    risk = entry - stop
                    if risk <= 0:
                        continue
                    target = entry + risk * TARGET_R
                    exit_price = exit_reason = exit_idx = None
                    for m in range(i + 1, min(i + 1 + max_hold_bars, n)):
                        if lows[m] <= stop:
                            exit_price, exit_reason, exit_idx = stop, "STOP", m; break
                        if highs[m] >= target:
                            exit_price, exit_reason, exit_idx = target, "TARGET", m; break
                    if exit_price is None:
                        exit_idx = min(i + max_hold_bars, n - 1)
                        exit_price, exit_reason = closes[exit_idx], "TIME"
                    r = (exit_price - entry) / risk
                    trades.append({"entry_time": times[i], "direction": "LONG", "entry": entry,
                                   "stop": stop, "target": target, "exit_price": exit_price,
                                   "exit_reason": exit_reason, "r_multiple": r})
                    in_trade_until = exit_idx
                    break
    return trades


def find_live_setup(candles, timeframe):
    """
    Causal, no-lookahead check for whether a confluence zone is ACTIVE right now
    (on the last closed candle) for the given timeframe's configured direction(s).
    Returns a dict describing the live zone state, or None.
    """
    directions = TF_CONFIG[timeframe]["directions"]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    n = len(candles)

    zigzag = build_zigzag(highs, lows, n)
    down_legs, up_legs = build_legs(zigzag)

    last = candles[-1]
    last_close, last_open = float(last["close"]), float(last["open"])
    last_low, last_high = float(last["low"]), float(last["high"])

    if "SHORT" in directions:
        levels = [lg["level"] for lg in down_legs[-MAX_LEGS_STACKED:]]
        for zlo, zhi in confluence_zones(levels):
            buf = zlo * ZONE_BUFFER_PCT
            touched = last_high >= zlo - buf and last_high <= zhi + buf * 3
            if touched:
                confirmed = last_close < last_open and last_close <= zhi
                return {"direction": "SHORT", "zone_lo": zlo, "zone_hi": zhi,
                        "confirmed": confirmed, "current_close": last_close}

    if "LONG" in directions:
        levels = [lg["level"] for lg in up_legs[-MAX_LEGS_STACKED:]]
        for zlo, zhi in confluence_zones(levels):
            buf = zlo * ZONE_BUFFER_PCT
            touched = last_low <= zhi + buf and last_low >= zlo - buf * 3
            if touched:
                confirmed = last_close > last_open and last_close >= zlo
                return {"direction": "LONG", "zone_lo": zlo, "zone_hi": zhi,
                        "confirmed": confirmed, "current_close": last_close}

    return None

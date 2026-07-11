#!/usr/bin/env python3
"""Pattern agent — chart-pattern breakout (+ optional candlestick confirmation).

Presets from the July 2026 backtest study:
  eth-pattern-1h   ETHUSD 1h  chart-pattern breakouts        (943 tr, 52% WR, +337% / 1y)
  btc-combo-45m    BTCUSD 45m breakout + candle confirmation (220 tr, 59% WR, +106% / 2mo)
  btc-combo-1h     BTCUSD 1h  breakout + candle confirmation (1791 tr, 50% WR, +208% / 2y)
  btc-combo-4h     BTCUSD 4h  breakout + candle confirmation (349 tr, 48% WR, +123% / 2y)

Rules (identical to the backtests):
  setup   = double/triple tops+bottoms, H&S / inverse, wedges, triangles,
            pennants, broadening (pivot + trendline-fit detection)
  entry   = close beyond the pattern line; combo presets also require a
            confirming candle (strong close, engulfing, tweezer, marubozu,
            morning/evening star, hammer family, piercing, dark cloud,
            harami) in the breakout direction within 5 bars
  stop    = pattern extreme (capped 5% from entry)
  target  = measured move (pattern height);  timeout = 48 bars

PAPER ONLY. Writes the same state/journal files the dashboard reads.
Candles come from Delta Exchange India's public API (no login). 45m is
resampled from 15m (Delta has no native 45m).

Usage:
    python agents/pattern_agent.py --list
    python agents/pattern_agent.py btc-combo-1h
"""
import argparse, csv, json, os, statistics, time, urllib.request
from collections import defaultdict

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(AGENTS_DIR)
API = "https://api.india.delta.exchange/v2/history/candles"

PRESETS = {
    "eth-pattern-1h": dict(
        _desc="Chart-pattern breakouts, ETHUSD 1h, no confirmation. Backtest "
              "(1y): 943 trades, 52% WR, +337% sum of per-trade %.",
        symbols=("ETHUSD",), strategy="pattern", timeframe_minutes=60,
        resolution="1h", resample=1, confirm=False),
    "btc-combo-45m": dict(
        _desc="Breakout + candle confirmation, BTCUSD 45m (resampled 15m). "
              "Backtest (2mo): 220 trades, 59% WR, +106%.",
        symbols=("BTCUSD",), strategy="pattern-combo", timeframe_minutes=45,
        resolution="15m", resample=3, confirm=True),
    "btc-combo-1h": dict(
        _desc="Breakout + candle confirmation, BTCUSD 1h. Backtest (2y): "
              "1791 trades, 50% WR, +208%.",
        symbols=("BTCUSD",), strategy="pattern-combo", timeframe_minutes=60,
        resolution="1h", resample=1, confirm=True),
    "btc-combo-4h": dict(
        _desc="Breakout + candle confirmation, BTCUSD 4h. Backtest (2y): "
              "349 trades, 48% WR, +123%.",
        symbols=("BTCUSD",), strategy="pattern-combo", timeframe_minutes=240,
        resolution="4h", resample=1, confirm=True),
}

LOOKBACK_BARS, HOLD_BARS, CONFIRM_WINDOW, RISK_FRACTION = 400, 48, 5, 1.0


def fetch_candles(symbol, resolution, count=1300):
    step = {"15m": 900, "1h": 3600, "4h": 14400}[resolution]
    end = int(time.time()); start = end - step * (count + 5)
    url = f"{API}?resolution={resolution}&symbol={symbol}&start={start}&end={end}"
    req = urllib.request.Request(url, headers={"User-Agent": "pattern-agent/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)["result"]
    bars = sorted(data, key=lambda b: b["time"])
    out = [[b["time"], float(b["open"]), float(b["high"]),
            float(b["low"]), float(b["close"])] for b in bars]
    return out[:-1]  # drop still-forming candle


def resample(c, n):
    if n == 1: return c
    out = []
    for i in range(0, len(c) - n + 1, n):
        w = c[i:i + n]
        out.append([w[0][0], w[0][1], max(x[2] for x in w),
                    min(x[3] for x in w), w[-1][4]])
    return out


def _pivots(arr, n, k, kind):
    out = []
    for i in range(k, n - k):
        w = arr[i - k:i + k + 1]
        if (kind == "low" and arr[i] == min(w)) or (kind == "high" and arr[i] == max(w)):
            if not out or i - out[-1] > k: out.append(i)
    return out


def _slope(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0: return 0, my
    m = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    return m, my - m * mx


def chart_patterns(o, h, l, cl):
    n = len(cl)
    PL = _pivots(l, n, 3, "low"); PH = _pivots(h, n, 3, "high")
    P = []; add = lambda *a: P.append(a)
    for ws in range(0, n - 40, 10):
        we = ws + 40
        hs = [(i, h[i]) for i in PH if ws <= i < we]
        ls = [(i, l[i]) for i in PL if ws <= i < we]
        if len(hs) < 2 or len(ls) < 2: continue
        mh, bh = _slope(hs); ml, bl = _slope(ls)
        rng = statistics.mean(h[ws:we]); sh, sl_ = mh / rng * 1000, ml / rng * 1000
        top = lambda k, mh=mh, bh=bh: mh * k + bh
        bot = lambda k, ml=ml, bl=bl: ml * k + bl
        flat = 0.05; prior = (cl[ws] - cl[max(0, ws - 20)]) / cl[ws]
        if sh < -flat and sl_ > flat:
            name = ("bullish_pennant" if prior > 0.01 else
                    "bearish_pennant" if prior < -0.01 else "symmetrical_triangle")
            add(name, ws, we, "both", (top, bot))
        elif abs(sh) < flat and sl_ > flat: add("ascending_triangle", ws, we, "long", (top, bot))
        elif sh < -flat and abs(sl_) < flat: add("descending_triangle", ws, we, "short", (top, bot))
        elif sh < -flat and sl_ < -flat and sh < sl_: add("falling_wedge", ws, we, "long", (top, bot))
        elif sh > flat and sl_ > flat and sh > sl_: add("rising_wedge", ws, we, "short", (top, bot))
        elif sh > flat and sl_ < -flat: add("broadening", ws, we, "both", (top, bot))
    hline = lambda v: (lambda k, v=v: v, lambda k, v=v: v)
    for a in range(len(PL) - 1):
        i, j = PL[a], PL[a + 1]
        if 8 <= j - i <= 60 and abs(l[i] - l[j]) / l[i] < 0.015:
            neck = max(h[i:j + 1])
            if (neck - min(l[i], l[j])) / l[i] >= 0.015:
                add("double_bottom", i, j, "long", hline(neck))
    for a in range(len(PH) - 1):
        i, j = PH[a], PH[a + 1]
        if 8 <= j - i <= 60 and abs(h[i] - h[j]) / h[i] < 0.015:
            neck = min(l[i:j + 1])
            if (max(h[i], h[j]) - neck) / h[i] >= 0.015:
                add("double_top", i, j, "short", hline(neck))
    for a in range(len(PH) - 2):
        i, m, j = PH[a], PH[a + 1], PH[a + 2]
        if j - i <= 80 and abs(h[i] - h[j]) / h[i] < 0.015:
            if h[m] > h[i] and h[m] > h[j] and (h[m] - h[i]) / h[i] > 0.008:
                add("head_shoulders", i, j, "short", hline(min(l[i:j + 1])))
            elif abs(h[m] - h[i]) / h[i] < 0.008:
                add("triple_top", i, j, "short", hline(min(l[i:j + 1])))
    for a in range(len(PL) - 2):
        i, m, j = PL[a], PL[a + 1], PL[a + 2]
        if j - i <= 80 and abs(l[i] - l[j]) / l[i] < 0.015:
            if l[m] < l[i] and l[m] < l[j] and (l[i] - l[m]) / l[i] > 0.008:
                add("inv_head_shoulders", i, j, "long", hline(max(h[i:j + 1])))
            elif abs(l[m] - l[i]) / l[i] < 0.008:
                add("triple_bottom", i, j, "long", hline(max(h[i:j + 1])))
    return P


def candle_signals(o, h, l, cl):
    n = len(cl)
    body = lambda i: abs(cl[i] - o[i]); rng = lambda i: h[i] - l[i]
    green = lambda i: cl[i] > o[i]; red = lambda i: cl[i] < o[i]
    up = lambda i: h[i] - max(o[i], cl[i]); lo = lambda i: min(o[i], cl[i]) - l[i]
    W = 14
    def avgbody(i):
        s = max(0, i - W)
        return sum(body(j) for j in range(s, i)) / max(i - s, 1)
    long_ = lambda i: body(i) > 1.2 * avgbody(i)
    small = lambda i: body(i) < 0.5 * avgbody(i)
    sig = defaultdict(set)
    for i in range(16, n):
        if body(i) > 0:
            if lo(i) > 2 * body(i) and up(i) <= 0.3 * body(i):
                sig[i].add(("long", "hammer")); sig[i].add(("short", "hanging_man"))
            if up(i) > 2 * body(i) and lo(i) <= 0.3 * body(i):
                sig[i].add(("long", "inverted_hammer")); sig[i].add(("short", "shooting_star"))
        if long_(i) and rng(i) > 0 and up(i) <= 0.05 * rng(i) and lo(i) <= 0.05 * rng(i):
            sig[i].add(("long", "marubozu") if green(i) else ("short", "marubozu"))
        j = i - 1
        if red(j) and green(i) and o[i] <= cl[j] and cl[i] >= o[j] and body(i) > body(j):
            sig[i].add(("long", "bullish_engulfing"))
        if green(j) and red(i) and o[i] >= cl[j] and cl[i] <= o[j] and body(i) > body(j):
            sig[i].add(("short", "bearish_engulfing"))
        if red(j) and green(i) and o[i] < cl[j] and cl[i] > (o[j] + cl[j]) / 2 and cl[i] < o[j]:
            sig[i].add(("long", "piercing"))
        if green(j) and red(i) and o[i] > cl[j] and cl[i] < (o[j] + cl[j]) / 2 and cl[i] > o[j]:
            sig[i].add(("short", "dark_cloud"))
        if red(j) and long_(j) and green(i) and small(i) and \
           max(o[i], cl[i]) < o[j] and min(o[i], cl[i]) > cl[j]:
            sig[i].add(("long", "bullish_harami"))
        if green(j) and long_(j) and red(i) and small(i) and \
           max(o[i], cl[i]) < cl[j] and min(o[i], cl[i]) > o[j]:
            sig[i].add(("short", "bearish_harami"))
        if red(j) and green(i) and abs(l[i] - l[j]) / l[j] < 0.002:
            sig[i].add(("long", "tweezer_bottom"))
        if green(j) and red(i) and abs(h[i] - h[j]) / h[j] < 0.002:
            sig[i].add(("short", "tweezer_top"))
        k = i - 2
        if k >= 16:
            if red(k) and long_(k) and small(i - 1) and green(i) and long_(i) and cl[i] > (o[k] + cl[k]) / 2:
                sig[i].add(("long", "morning_star"))
            if green(k) and long_(k) and small(i - 1) and red(i) and long_(i) and cl[i] < (o[k] + cl[k]) / 2:
                sig[i].add(("short", "evening_star"))
        if long_(i):
            sig[i].add(("long", "strong_close") if green(i) else ("short", "strong_close"))
    return sig


def latest_signal(candles, confirm):
    o = [x[1] for x in candles]; h = [x[2] for x in candles]
    l = [x[3] for x in candles]; cl = [x[4] for x in candles]
    n = len(cl); last = n - 1
    sig = candle_signals(o, h, l, cl) if confirm else None
    for name, i, j, side, (top, bot) in chart_patterns(o, h, l, cl):
        brk = dr = None
        for k in range(j + 1, min(j + 24, n)):
            if side in ("long", "both") and cl[k] > top(k): brk, dr = k, "long"; break
            if side in ("short", "both") and cl[k] < bot(k): brk, dr = k, "short"; break
        if brk is None: continue
        if confirm:
            entry = cname = None
            for s in range(brk, min(brk + CONFIRM_WINDOW, n)):
                names = [nm for d, nm in sig.get(s, ()) if d == dr]
                if names: entry, cname = s, names[0]; break
            if entry is None: continue
        else:
            entry, cname = brk, ""
        if entry != last: continue
        ep = cl[entry]
        height = max(h[i:j + 1]) - min(l[i:j + 1])
        stop = min(l[i:j + 1]) if dr == "long" else max(h[i:j + 1])
        if abs(ep - stop) / ep > 0.05: stop = ep * (0.97 if dr == "long" else 1.03)
        target = ep + height if dr == "long" else ep - height
        return dict(pattern=name, confirm=cname, side=dr, entry=ep,
                    stop=stop, target=target, bar_time=candles[entry][0])
    return None


class Paper:
    def __init__(self, preset):
        self.preset = preset
        self.path = os.path.join(REPO, f"scalper_state_{preset}_paper.json")
        self.state = {"equity": 1000.0, "position": None, "pending": None, "trades": []}
        if os.path.exists(self.path):
            try:
                with open(self.path) as f: self.state = json.load(f)
            except (json.JSONDecodeError, OSError): pass

    def save(self):
        with open(self.path, "w") as f: json.dump(self.state, f, indent=1)

    def open(self, sig, symbol):
        notional = self.state["equity"] * RISK_FRACTION
        self.state["position"] = {
            "side": "buy" if sig["side"] == "long" else "sell",
            "entry_price": sig["entry"], "stop": sig["stop"],
            "target": sig["target"], "notional": notional,
            "opened_at": sig["bar_time"], "bars": 0,
            "pattern": sig["pattern"], "confirm": sig["confirm"], "symbol": symbol}
        self.save()

    def manage(self, bar):
        p = self.state["position"]
        if not p: return None
        p["bars"] += 1
        t, _, hi, lo, c = bar
        long = p["side"] == "buy"
        exit_price = reason = None
        if long and lo <= p["stop"]: exit_price, reason = p["stop"], "stop"
        elif long and hi >= p["target"]: exit_price, reason = p["target"], "target"
        elif not long and hi >= p["stop"]: exit_price, reason = p["stop"], "stop"
        elif not long and lo <= p["target"]: exit_price, reason = p["target"], "target"
        elif p["bars"] >= HOLD_BARS: exit_price, reason = c, "timeout"
        if exit_price is None:
            self.save(); return None
        ret = (exit_price - p["entry_price"]) / p["entry_price"] * (1 if long else -1)
        pnl = p["notional"] * ret
        self.state["equity"] = round(self.state["equity"] + pnl, 2)
        trade = dict(closed_at=t, symbol=p["symbol"], side=p["side"],
                     entry=p["entry_price"], exit=exit_price,
                     notional=round(p["notional"], 2), pnl=round(pnl, 2),
                     r_outcome=("+1R" if pnl > 0 else "-1R"), exit_reason=reason,
                     pattern=p["pattern"], confirm=p["confirm"])
        self.state["trades"].append(trade)
        self.state["position"] = None
        self.save()
        return trade


def journal(trade, strategy):
    path = os.path.join(REPO, "trade_journal.csv")
    fields = ["closed_at", "strategy", "symbol", "side", "entry", "exit",
              "notional", "pnl", "r_outcome", "exit_reason", "pattern", "confirm"]
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if new: w.writeheader()
        row = dict(trade); row["strategy"] = strategy
        w.writerow(row)


def run(preset_name):
    p = PRESETS[preset_name]
    symbol = p["symbols"][0]
    paper = Paper(preset_name)
    print(f"pattern agent [{preset_name}] {p['_desc']}", flush=True)
    print(f"paper equity: ${paper.state['equity']}", flush=True)
    last_bar = None
    while True:
        try:
            raw = fetch_candles(symbol, p["resolution"],
                                count=LOOKBACK_BARS * p["resample"] + 10)
            candles = resample(raw, p["resample"])[-LOOKBACK_BARS:]
            newest = candles[-1][0]
            if newest != last_bar:
                last_bar = newest
                closed = paper.manage(candles[-1])
                if closed:
                    journal(closed, p["strategy"])
                    print(f"CLOSED {closed['side']} {closed['exit_reason']} "
                          f"pnl {closed['pnl']} eq {paper.state['equity']}", flush=True)
                if not paper.state["position"]:
                    sig = latest_signal(candles, p["confirm"])
                    if sig:
                        paper.open(sig, symbol)
                        print(f"OPEN {sig['side']} {sig['pattern']}"
                              f"{'+' + sig['confirm'] if sig['confirm'] else ''} "
                              f"@ {sig['entry']} stop {round(sig['stop'], 2)} "
                              f"target {round(sig['target'], 2)}", flush=True)
        except Exception as e:
            print(f"loop error: {e}", flush=True)
        time.sleep(60)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("preset", nargs="?", choices=sorted(PRESETS), metavar="PRESET")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list or not args.preset:
        for name, p in PRESETS.items():
            print(f"  {name}\n      {p['_desc']}\n")
        return
    run(args.preset)


if __name__ == "__main__":
    main()

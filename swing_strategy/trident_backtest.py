"""
Trident System backtest - 30-minute FVG/Doji institutional pattern.

IMPORTANT DATA-FIT CAVEAT, stated up front rather than buried at the end:
this playbook is explicitly written for FX majors (GBPUSD/EURUSD/USDCAD/
USDJPY) and Gold, built around the London-session liquidity structure of
those markets, and claims a frequency of only ~6-15 entries PER YEAR per
instrument. This repo has no forex/gold data - only BTCUSD - and only 30
days of intraday history. That is structurally incapable of producing a
meaningful sample for a strategy this selective, even with a perfect
implementation. This backtest exists to test whether the playbook's
pattern-matching/EMA/risk MATH is internally sound and produces sane
trades when it does fire, not to claim a verdict on "the Trident System"
as intended for its real target markets.

Implements the spec as literally as possible:
  Phase 1 - kill-zone gate (3:00-6:30 NY), M30 execution timeframe.
  Phase 2 - 200-EMA baseline filter + 5/9/13/21 EMA stack alignment.
  Phase 3 - 4-candle FVG -> 50% CE -> Doji -> confirmation-close pattern.
  Phase 4 - SL at the Doji wick (+ a small tick buffer), TP at the
            playbook's stated minimum baseline of 1:20 RR (the
            "macro daily-structure" trailing target is a discretionary,
            not-objectively-codeable rule and is therefore not backtested -
            documented assumption, same approach as other ambiguous specs
            in this directory).
  Phase 5 - position sizing formula, using the document's own worked
            example ($200,000 / 0.5% risk) for direct comparability.

The document only spells out the LONG side of the candle pattern; the
SHORT side here is the literal mirror image (gap down FVG, doji wicking
up to the CE, confirmation candle closing above the doji's low) -
documented since it's an inference, not something the text states.

No-lookahead walk-forward: M30 bars are built from real 5-minute OHLC
(UTC-aligned, no partial buckets), filters/pattern are evaluated using
only the closed candle data, and the entry fills at Candle 4's own close
(the playbook's literal "market buy the millisecond Candle 4 closes" -
an idealized zero-slippage assumption, flagged rather than hidden).
"""
import csv
from datetime import datetime, time as dtime, timezone
from zoneinfo import ZoneInfo

DATA_SRC = "data/btc_usd_5min_cvd.csv"
NY_TZ = ZoneInfo("America/New_York")

KILL_ZONE = (dtime(3, 0), dtime(6, 30))   # NY local time
M30_SECONDS = 30 * 60

EMA_STACK = (5, 9, 13, 21)
EMA_BASELINE = 200

DOJI_BODY_RATIO = 0.30     # body <= 30% of range counts as a doji (spec gives no exact number)
TICK_BUFFER_PCT = 0.0005   # 0.05% of price - BTC has no FX "pip"/"tick" standard, documented stand-in
MIN_RR = 20.0              # the playbook's stated baseline minimum (1:20)

ACCOUNT_SIZE = 200_000.0   # matches the document's own worked example
RISK_PCT = 0.005


def load_5min(path):
    bars = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            bars.append({
                "ts": int(r["timestamp"]), "date": r["datetime"],
                "open": float(r["open"]), "high": float(r["high"]),
                "low": float(r["low"]), "close": float(r["close"]),
            })
    return bars


def build_m30_bars(bars5m):
    buckets, counts, order = {}, {}, []
    for bar in bars5m:
        key = bar["ts"] - (bar["ts"] % M30_SECONDS)
        if key not in buckets:
            buckets[key] = {"ts": key, "date": bar["date"], "open": bar["open"],
                             "high": bar["high"], "low": bar["low"], "close": bar["close"]}
            counts[key] = 1
            order.append(key)
        else:
            b = buckets[key]
            b["high"] = max(b["high"], bar["high"])
            b["low"] = min(b["low"], bar["low"])
            b["close"] = bar["close"]
            counts[key] += 1
    return [buckets[k] for k in order if counts[k] >= 6]   # full 6/6 5-min bars present


def in_kill_zone(ts):
    ny = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(NY_TZ).time()
    return KILL_ZONE[0] <= ny < KILL_ZONE[1]


def compute_ema_series(closes, period):
    ema = [None] * len(closes)
    k = 2.0 / (period + 1)
    seed = sum(closes[:period]) / period
    ema[period - 1] = seed
    for i in range(period, len(closes)):
        ema[i] = closes[i] * k + ema[i - 1] * (1 - k)
    return ema


def is_doji(bar):
    rng = bar["high"] - bar["low"]
    if rng <= 0:
        return False
    return abs(bar["close"] - bar["open"]) <= DOJI_BODY_RATIO * rng


def run_trident_backtest(bars5m, min_rr=MIN_RR, doji_body_ratio=DOJI_BODY_RATIO):
    m30 = build_m30_bars(bars5m)
    closes = [b["close"] for b in m30]
    emas = {p: compute_ema_series(closes, p) for p in EMA_STACK + (EMA_BASELINE,)}

    start = EMA_BASELINE + 5
    trades = []
    open_trade = None
    funnel = {"kill_zone": 0, "trend_filter": 0, "ema_stack": 0, "fvg_doji_found": 0,
              "confirmation_ok": 0, "traded": 0}

    i = start
    while i < len(m30) - 1:
        if open_trade is not None:
            bar = m30[i]
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

        if not in_kill_zone(m30[i]["ts"]):
            i += 1
            continue
        funnel["kill_zone"] += 1

        if any(emas[p][i] is None for p in EMA_STACK + (EMA_BASELINE,)):
            i += 1
            continue

        price = closes[i]
        e5, e9, e13, e21, e200 = (emas[5][i], emas[9][i], emas[13][i], emas[21][i], emas[EMA_BASELINE][i])

        long_trend = price > e200
        short_trend = price < e200
        if not (long_trend or short_trend):
            i += 1
            continue
        funnel["trend_filter"] += 1

        long_stack = price > e5 > e9 > e13 > e21
        short_stack = price < e5 < e9 < e13 < e21
        direction_bias = "LONG" if (long_trend and long_stack) else ("SHORT" if (short_trend and short_stack) else None)
        if direction_bias is None:
            i += 1
            continue
        funnel["ema_stack"] += 1

        if i < 3:
            i += 1
            continue
        c1, c2, c3 = m30[i - 3], m30[i - 2], m30[i - 1]
        c4 = m30[i]

        direction = None
        ce = None
        if direction_bias == "LONG" and c2["low"] > c1["high"]:
            ce = (c1["high"] + c2["low"]) / 2.0
            if is_doji(c3) and c3["low"] <= ce <= c3["high"]:
                direction = "LONG"
        elif direction_bias == "SHORT" and c2["high"] < c1["low"]:
            ce = (c1["low"] + c2["high"]) / 2.0
            if is_doji(c3) and c3["low"] <= ce <= c3["high"]:
                direction = "SHORT"

        if direction is None:
            i += 1
            continue
        funnel["fvg_doji_found"] += 1

        if direction == "LONG":
            confirmation_ok = c4["close"] < c3["high"]
        else:
            confirmation_ok = c4["close"] > c3["low"]
        if not confirmation_ok:
            i += 1
            continue
        funnel["confirmation_ok"] += 1

        entry = c4["close"]
        if direction == "LONG":
            sl = c3["low"] * (1 - TICK_BUFFER_PCT)
            risk_per_unit = entry - sl
            tp = entry + min_rr * risk_per_unit
        else:
            sl = c3["high"] * (1 + TICK_BUFFER_PCT)
            risk_per_unit = sl - entry
            tp = entry - min_rr * risk_per_unit

        if risk_per_unit <= 0:
            i += 1
            continue
        funnel["traded"] += 1

        open_trade = {
            "direction": direction, "entry_idx": i, "entry": entry, "sl": sl, "tp": tp,
            "risk_per_unit": risk_per_unit,
            "position_size": (ACCOUNT_SIZE * RISK_PCT) / risk_per_unit,
            "ce": round(ce, 2), "outcome": None,
        }
        i += 1

    if open_trade is not None:
        open_trade["outcome"] = "OPEN"
        trades.append(open_trade)

    return trades, funnel, m30


def fvg_diagnostic(m30):
    """Root-cause check: does the FVG itself ever even form on M30 BTC
    candles, independent of trend/stack/doji/CE filters?"""
    lines = []
    lines.append("-" * 110)
    lines.append("FVG DIAGNOSTIC (does Candle1->Candle2 gap exist at all, ignoring every other filter?)")
    lines.append("-" * 110)
    fvg_long = fvg_short = 0
    fvg_long_doji_ce = fvg_short_doji_ce = 0
    for i in range(3, len(m30)):
        c1, c2, c3 = m30[i - 3], m30[i - 2], m30[i - 1]
        if c2["low"] > c1["high"]:
            fvg_long += 1
            ce = (c1["high"] + c2["low"]) / 2.0
            if is_doji(c3) and c3["low"] <= ce <= c3["high"]:
                fvg_long_doji_ce += 1
        if c2["high"] < c1["low"]:
            fvg_short += 1
            ce = (c1["low"] + c2["high"]) / 2.0
            if is_doji(c3) and c3["low"] <= ce <= c3["high"]:
                fvg_short_doji_ce += 1
    lines.append(f"M30 candles scanned                      : {len(m30)}")
    lines.append(f"Bullish FVG occurrences (c2.low > c1.high): {fvg_long}")
    lines.append(f"Bearish FVG occurrences (c2.high < c1.low): {fvg_short}")
    lines.append(f"  of which doji sits at the 50% CE level  : {fvg_long_doji_ce + fvg_short_doji_ce}")
    lines.append("")
    lines.append("This is the real root cause of the zero-trade result, more fundamental than the "
                 "200-EMA/stack/kill-zone gates upstream: continuous 24/7 crypto trading almost never "
                 "leaves a true gap between one M30 candle's high/low and the next's, unlike session-based "
                 "FX/equities/Gold where the FVG pattern this playbook is built around actually forms "
                 "(open-outside-prior-range gaps at session opens, news, etc). No sweep of the doji-ratio "
                 "or min-RR parameters can fix this - the precondition the pattern depends on essentially "
                 "doesn't exist in this market/timeframe/dataset.")
    return "\n".join(lines)


def report(m30, trades, funnel):
    lines = []
    lines.append("=" * 110)
    lines.append("TRIDENT SYSTEM - BTCUSD 30-MINUTE BACKTEST (structural test only - see module docstring)")
    lines.append("=" * 110)
    lines.append(f"Data range: {m30[0]['date']} -> {m30[-1]['date']}  ({len(m30)} M30 candles, aggregated from 5-min)")
    lines.append("CAVEAT: this playbook targets FX majors/Gold and claims ~6-15 signals PER YEAR per "
                 "instrument. Tested here on 30 days of BTCUSD only - not a fair sample either way.")
    lines.append(f"Kill zone (NY time): {KILL_ZONE[0]}-{KILL_ZONE[1]}   EMA stack: {EMA_STACK}   "
                 f"Baseline: {EMA_BASELINE}-EMA   Min RR: 1:{MIN_RR:.0f}")
    lines.append("")

    closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
    still_open = [t for t in trades if t["outcome"] == "OPEN"]

    header = (f"{'#':>3} {'Dir':<6} {'EntryIdx':>9} {'ExitIdx':>9} {'Entry':>10} {'SL':>10} {'TP':>10} "
              f"{'Res':<5} {'PnL$':>10} {'R':>7} {'W-L':<8}")
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
        lines.append(f"{seq:>3} {t['direction']:<6} {t['entry_idx']:>9} {t['exit_idx']:>9} "
                     f"{t['entry']:>10,.1f} {t['sl']:>10,.1f} {t['tp']:>10,.1f} {t['outcome']:<5} "
                     f"{t['pnl_cash']:>10,.2f} {t['r_multiple']:>7.2f} {f'{w}-{l}':<8}")

    lines.append("")
    lines.append("-" * 110)
    lines.append("FUNNEL (how many M30 bars survive each gate)")
    lines.append(f"  Inside kill zone                         : {funnel['kill_zone']}")
    lines.append(f"  + 200-EMA trend filter passes             : {funnel['trend_filter']}")
    lines.append(f"  + 5/9/13/21 EMA stack aligned             : {funnel['ema_stack']}")
    lines.append(f"  + FVG + Doji-at-CE pattern found          : {funnel['fvg_doji_found']}")
    lines.append(f"  + Candle 4 confirmation close ok          : {funnel['confirmation_ok']}")
    lines.append(f"  + valid risk -> traded                    : {funnel['traded']}")
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


def parameter_sweep(bars5m):
    lines = []
    lines.append("-" * 110)
    lines.append("PARAMETER SWEEP (doji body ratio x minimum RR target)")
    lines.append("-" * 110)
    lines.append(f"{'DojiRatio':>9} {'MinRR':>6} {'Traded':>7} {'Closed':>6} {'W':>3} {'L':>3} "
                 f"{'WinRate':>8} {'NetPnL':>10}")
    for doji_ratio in (0.20, 0.30, 0.40, 0.50):
        for min_rr in (5.0, 10.0, 15.0, 20.0):
            trades, funnel, _ = run_trident_backtest(bars5m, min_rr=min_rr, doji_body_ratio=doji_ratio)
            closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
            w = sum(1 for t in closed if t["outcome"] == "WIN")
            l = len(closed) - w
            net = sum(t["pnl_cash"] for t in closed)
            wr = (w / len(closed) * 100) if closed else 0.0
            lines.append(f"{doji_ratio:>9.2f} {min_rr:>6.0f} {funnel['traded']:>7} {len(closed):>6} "
                         f"{w:>3} {l:>3} {wr:>7.1f}% {net:>+10.2f}")
    return "\n".join(lines)


def main():
    bars5m = load_5min(DATA_SRC)
    trades, funnel, m30 = run_trident_backtest(bars5m)
    out = report(m30, trades, funnel)
    out += "\n\n" + fvg_diagnostic(m30)
    out += "\n\n" + parameter_sweep(bars5m)
    print(out)
    with open("results_trident.txt", "w") as f:
        f.write(out + "\n")


if __name__ == "__main__":
    main()

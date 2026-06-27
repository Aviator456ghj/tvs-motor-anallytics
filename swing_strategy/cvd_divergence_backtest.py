"""
CVD Delta Divergence backtest engine.

Upgrades the original passive-limit Fibonacci entries (measured_swing_backtest.py)
to a gated, reactive trigger, exactly per the requested rule change:

  OLD: Price touches 61.8% line -> automatically place limit order.
  NEW: Price enters the 61.8%-100% retracement zone of the SAME daily swing
       -> gate opens -> monitor price/CVD pivots inside the zone ->
       only execute a MARKET order if price prints a new extreme (Higher
       High for shorts / Lower Low for longs) that is NOT confirmed by CVD
       (CVD prints a Lower High / Higher Low - absorption) -> otherwise
       skip the leg entirely.

Stop loss changes from "78.6% line + 2-3% buffer" to a tight structural
stop: 1 tick beyond the wick of the divergence-trigger bar.
Take profit is unchanged (origin swing point) so the comparison isolates
the effect of the entry/stop change.

This engine is data-granularity agnostic: it is fed daily bars with a
volume-delta *proxy* for the long 2-year comparison, and real 5-minute
bars with true buy/sell-tagged CVD for the short, accurate window.
"""
import csv
from dataclasses import dataclass

from measured_swing_backtest import find_pivots, ZIGZAG_THRESHOLD, TP_BUFFER, ACCOUNT_SIZE, RISK_PCT

TICK_SIZE = 0.1  # Kraken XBTUSD tick


@dataclass
class CvdTrade:
    direction: str
    swing_high: float
    swing_low: float
    zone_low: float
    zone_high: float
    trigger_idx: int = None
    entry_idx: int = None
    entry: float = None
    sl: float = None
    tp: float = None
    exit_idx: int = None
    exit_price: float = None
    outcome: str = None  # WIN / LOSS / NO_DIVERGENCE / NO_DATA / OPEN
    risk_per_unit: float = None
    position_size: float = None
    pnl_cash: float = None
    r_multiple: float = None


def load_bars_with_delta(path):
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "date": r.get("datetime", r.get("date")),
                "open": float(r["open"]), "high": float(r["high"]),
                "low": float(r["low"]), "close": float(r["close"]),
                "cvd": float(r["cvd"]),
            })
    return rows


def local_extrema(bars, k):
    """Return (highs, lows): sets of bar indices that are local price extrema
    over a +/-k bar window."""
    n = len(bars)
    highs, lows = set(), set()
    for i in range(k, n - k):
        window = bars[i - k:i + k + 1]
        if bars[i]["high"] == max(b["high"] for b in window):
            highs.add(i)
        if bars[i]["low"] == min(b["low"] for b in window):
            lows.add(i)
    return highs, lows


def find_zone_window(fine_bars, fine_dates, start_date, end_date):
    """Indices of fine_bars whose date falls within [start_date, end_date)."""
    idxs = [i for i, d in enumerate(fine_dates) if start_date <= d < end_date]
    return idxs


def detect_divergence_and_trigger(fine_bars, idxs, zone_low, zone_high, direction, k):
    """Scan zone-restricted indices in chronological order for a price
    extreme NOT confirmed by CVD. Returns trigger bar index or None."""
    highs, lows = local_extrema(fine_bars, k)

    if direction == "SHORT":
        candidates = [i for i in idxs if i in highs and zone_low <= fine_bars[i]["high"] <= zone_high]
        last_price, last_cvd = None, None
        for i in candidates:
            price, cvd = fine_bars[i]["high"], fine_bars[i]["cvd"]
            if last_price is not None and price > last_price and cvd < last_cvd:
                return i
            last_price, last_cvd = price, cvd
        return None
    else:
        candidates = [i for i in idxs if i in lows and zone_low <= fine_bars[i]["low"] <= zone_high]
        last_price, last_cvd = None, None
        for i in candidates:
            price, cvd = fine_bars[i]["low"], fine_bars[i]["cvd"]
            if last_price is not None and price < last_price and cvd > last_cvd:
                return i
            last_price, last_cvd = price, cvd
        return None


def run_cvd_backtest(daily_bars, fine_bars, k=3, label=""):
    """daily_bars: used only to detect the swing legs / zones (same zig-zag
    as the original strategy). fine_bars: where signals & fills happen -
    may be the same series (daily proxy) or a separate, finer real-data
    series whose date range may only cover part of daily_bars."""
    pivots = find_pivots(daily_bars, ZIGZAG_THRESHOLD)
    fine_dates = [b["date"] for b in fine_bars]
    trades = []

    for i in range(len(pivots) - 1):
        p_from, p_to = pivots[i], pivots[i + 1]
        swing_range = abs(p_from.price - p_to.price)

        if p_from.kind == "H" and p_to.kind == "L":
            swing_high, swing_low = p_from.price, p_to.price
            zone_low = swing_low + swing_range * 0.618
            zone_high = swing_high
            direction = "SHORT"
        else:
            swing_high, swing_low = p_to.price, p_from.price
            zone_low = swing_low
            zone_high = swing_high - swing_range * 0.618
            direction = "LONG"

        trade = CvdTrade(direction, swing_high, swing_low, zone_low, zone_high)

        start_date = daily_bars[p_to.confirm_idx]["date"]
        window_end_idx = pivots[i + 2].confirm_idx if i + 2 < len(pivots) else len(daily_bars) - 1
        end_date = daily_bars[window_end_idx]["date"]

        idxs = find_zone_window(fine_bars, fine_dates, start_date, end_date)
        if not idxs:
            trade.outcome = "NO_DATA"
            trades.append(trade)
            continue

        trigger_idx = detect_divergence_and_trigger(fine_bars, idxs, zone_low, zone_high, direction, k)
        if trigger_idx is None:
            trade.outcome = "NO_DIVERGENCE"
            trades.append(trade)
            continue

        if trigger_idx + 1 >= len(fine_bars):
            trade.outcome = "NO_DATA"
            trades.append(trade)
            continue

        entry_idx = trigger_idx + 1
        entry = fine_bars[entry_idx]["open"]
        trigger_bar = fine_bars[trigger_idx]

        if direction == "SHORT":
            sl = trigger_bar["high"] + TICK_SIZE
            tp = swing_low * (1 + TP_BUFFER)
        else:
            sl = trigger_bar["low"] - TICK_SIZE
            tp = swing_high * (1 - TP_BUFFER)

        trade.trigger_idx, trade.entry_idx, trade.entry, trade.sl, trade.tp = trigger_idx, entry_idx, entry, sl, tp

        resolved = False
        for j in range(entry_idx, len(fine_bars)):
            bar = fine_bars[j]
            if direction == "SHORT":
                hit_sl, hit_tp = bar["high"] >= sl, bar["low"] <= tp
            else:
                hit_sl, hit_tp = bar["low"] <= sl, bar["high"] >= tp
            if hit_sl:
                trade.outcome, trade.exit_price, trade.exit_idx = "LOSS", sl, j
                resolved = True
                break
            if hit_tp:
                trade.outcome, trade.exit_price, trade.exit_idx = "WIN", tp, j
                resolved = True
                break
        if not resolved:
            trade.outcome = "OPEN"

        trade.risk_per_unit = abs(trade.entry - trade.sl)
        cash_risk = ACCOUNT_SIZE * RISK_PCT
        trade.position_size = cash_risk / trade.risk_per_unit if trade.risk_per_unit else 0
        if trade.outcome in ("WIN", "LOSS"):
            move = (trade.exit_price - trade.entry) if direction == "LONG" else (trade.entry - trade.exit_price)
            trade.pnl_cash = trade.position_size * move
            trade.r_multiple = move / trade.risk_per_unit

        trades.append(trade)

    return trades, fine_dates


def summarize(trades, fine_dates, fine_bars, label):
    closed = [t for t in trades if t.outcome in ("WIN", "LOSS")]
    no_div = sum(1 for t in trades if t.outcome == "NO_DIVERGENCE")
    no_data = sum(1 for t in trades if t.outcome == "NO_DATA")
    open_ = sum(1 for t in trades if t.outcome == "OPEN")
    wins = sum(1 for t in closed if t.outcome == "WIN")
    losses = len(closed) - wins
    pnl = sum(t.pnl_cash for t in closed)

    lines = []
    lines.append("=" * 100)
    lines.append(f"CVD DELTA DIVERGENCE BACKTEST - {label}")
    lines.append("=" * 100)
    lines.append(f"Legs evaluated: {len(trades)}  |  Gated out (no divergence): {no_div}  |  "
                 f"No fine data in window: {no_data}  |  Still open: {open_}")
    lines.append("")
    lines.append(f"{'#':>3} {'Dir':<5} {'Entry':<19} {'Exit':<19} {'Entry$':>10} {'SL':>10} {'TP':>10} "
                 f"{'Res':<5} {'PnL$':>8} {'R':>6} {'W-L':<8} {'Equity$':>10}")
    seq = w = l = 0
    cum = 0.0
    equity = ACCOUNT_SIZE
    for t in closed:
        seq += 1
        if t.outcome == "WIN":
            w += 1
        else:
            l += 1
        cum += t.pnl_cash
        equity = ACCOUNT_SIZE + cum
        lines.append(f"{seq:>3} {t.direction:<5} {fine_bars[t.entry_idx]['date']:<19} "
                     f"{fine_bars[t.exit_idx]['date']:<19} {t.entry:>10,.1f} {t.sl:>10,.1f} {t.tp:>10,.1f} "
                     f"{t.outcome:<5} {t.pnl_cash:>8,.2f} {t.r_multiple:>6.2f} {f'{w}-{l}':<8} {equity:>10,.2f}")

    lines.append("")
    lines.append("-" * 100)
    lines.append("SUMMARY")
    lines.append(f"Closed trades : {len(closed)}   Wins: {wins}   Losses: {losses}")
    if closed:
        lines.append(f"Win rate      : {wins/len(closed)*100:.1f}%")
        lines.append(f"Avg R-multiple: {sum(t.r_multiple for t in closed)/len(closed):+.2f}R")
        lines.append(f"Net P&L       : ${cum:+,.2f}  (${ACCOUNT_SIZE:,.0f} -> ${equity:,.2f})")
        mw = ml = cw = cl = 0
        for t in closed:
            if t.outcome == "WIN":
                cw += 1; cl = 0
            else:
                cl += 1; cw = 0
            mw, ml = max(mw, cw), max(ml, cl)
        lines.append(f"Longest win/loss streak: {mw} / {ml}")
    return "\n".join(lines)

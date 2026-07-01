"""
Measured Swing Strategy backtest on BTCUSD daily candles.

Implements the document's rules end to end:
  Phase 1 - swing point detection (zig-zag on completed impulsive legs)
  Phase 2 - Fibonacci retracement / extension math (Swing Range based)
  Phase 4 - Entry (61.8% retrace), Stop Loss (78.6% retrace + 2-3% buffer),
            Take Profit (back at the origin swing point)
  Phase 5 - Fixed cash-risk position sizing ($5,000 account / 1% = $50 risk)

Trades are walked forward bar-by-bar in chronological order (no lookahead:
a pivot only becomes tradeable once price has reversed past the confirmation
threshold) and reported strictly in the sequence they occurred.
"""
import csv
import datetime
from dataclasses import dataclass, field

DATA_FILE = "data/btc_usd_daily.csv"

# --- Strategy parameters, taken directly from the document ---
ZIGZAG_THRESHOLD = 0.08          # 8% reversal confirms a swing point (filters consolidation noise)
ENTRY_RATIO = 0.618              # Golden Ratio entry
SL_RATIO = 0.786                 # 78.6% retracement line for the stop
SL_BUFFER = 0.025                # 2-3% buffer beyond the 78.6% line -> use 2.5% midpoint
TP_BUFFER = 0.003                # "just above/below" the origin swing point -> 0.3% buffer
ACCOUNT_SIZE = 5000.0
RISK_PCT = 0.01                  # 1% of account risked per trade ($50 on a $5,000 account)


@dataclass
class Pivot:
    idx: int            # bar index of the actual extreme
    price: float
    kind: str           # 'H' or 'L'
    confirm_idx: int     # bar index where the reversal threshold confirmed this pivot


@dataclass
class Trade:
    direction: str
    swing_high: float
    swing_low: float
    entry: float
    sl: float
    tp: float
    setup_confirm_idx: int
    entry_idx: int = None
    exit_idx: int = None
    outcome: str = None   # 'WIN', 'LOSS', 'OPEN', 'NO_FILL'
    exit_price: float = None
    risk_per_unit: float = None
    position_size: float = None
    pnl_cash: float = None
    r_multiple: float = None


def load_data(path):
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "date": r["date"],
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
            })
    return rows


def find_pivots(bars, threshold):
    """Zig-zag swing detector: an extreme is confirmed only after price
    reverses by `threshold` percent away from it (no lookahead bias -
    the pivot is usable for trading only from confirm_idx onward)."""
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
        else:  # trend == "down"
            if l < extreme_price:
                extreme_price, extreme_idx = l, i
            elif h >= extreme_price * (1 + threshold):
                pivots.append(Pivot(extreme_idx, extreme_price, "L", i))
                trend = "up"
                extreme_price, extreme_idx = h, i

    pivots.append(Pivot(extreme_idx, extreme_price, "H" if trend == "up" else "L", len(bars) - 1))
    return pivots


def build_setup(p_from: Pivot, p_to: Pivot):
    """Phase 2 & 4: turn one completed impulsive leg into an order ticket."""
    swing_range = abs(p_from.price - p_to.price)

    if p_from.kind == "H" and p_to.kind == "L":
        # Down leg -> short the 61.8% bounce, continuation short
        swing_high, swing_low = p_from.price, p_to.price
        entry = swing_low + swing_range * ENTRY_RATIO
        sl_line = swing_low + swing_range * SL_RATIO
        sl = sl_line * (1 + SL_BUFFER)
        tp = swing_low * (1 + TP_BUFFER)
        direction = "SHORT"
    else:
        # Up leg -> buy the 61.8% dip, continuation long
        swing_high, swing_low = p_to.price, p_from.price
        entry = swing_high - swing_range * ENTRY_RATIO
        sl_line = swing_high - swing_range * SL_RATIO
        sl = sl_line * (1 - SL_BUFFER)
        tp = swing_high * (1 - TP_BUFFER)
        direction = "LONG"

    return Trade(direction, swing_high, swing_low, entry, sl, tp, p_to.confirm_idx)


def run_backtest(bars, pivots):
    trades = []

    for i in range(len(pivots) - 1):
        p_from, p_to = pivots[i], pivots[i + 1]
        trade = build_setup(p_from, p_to)

        window_end = pivots[i + 2].confirm_idx if i + 2 < len(pivots) else len(bars) - 1
        start = trade.setup_confirm_idx + 1

        # 1) Wait for the limit order to fill at the 61.8% line
        filled_idx = None
        for j in range(start, window_end + 1):
            bar = bars[j]
            if trade.direction == "SHORT" and bar["high"] >= trade.entry:
                filled_idx = j
                break
            if trade.direction == "LONG" and bar["low"] <= trade.entry:
                filled_idx = j
                break

        if filled_idx is None:
            trade.outcome = "NO_FILL"
            trades.append(trade)
            continue

        trade.entry_idx = filled_idx

        # 2) Walk forward from the fill bar looking for SL or TP.
        #    If both levels are touched on the same bar, conservatively assume SL hit first.
        resolved = False
        for j in range(filled_idx, len(bars)):
            bar = bars[j]
            if trade.direction == "SHORT":
                hit_sl = bar["high"] >= trade.sl
                hit_tp = bar["low"] <= trade.tp
                if hit_sl:
                    trade.outcome, trade.exit_price, trade.exit_idx = "LOSS", trade.sl, j
                    resolved = True
                    break
                if hit_tp:
                    trade.outcome, trade.exit_price, trade.exit_idx = "WIN", trade.tp, j
                    resolved = True
                    break
            else:
                hit_sl = bar["low"] <= trade.sl
                hit_tp = bar["high"] >= trade.tp
                if hit_sl:
                    trade.outcome, trade.exit_price, trade.exit_idx = "LOSS", trade.sl, j
                    resolved = True
                    break
                if hit_tp:
                    trade.outcome, trade.exit_price, trade.exit_idx = "WIN", trade.tp, j
                    resolved = True
                    break

        if not resolved:
            trade.outcome = "OPEN"

        # Phase 5: position sizing on fixed cash risk
        trade.risk_per_unit = abs(trade.entry - trade.sl)
        cash_risk = ACCOUNT_SIZE * RISK_PCT
        trade.position_size = cash_risk / trade.risk_per_unit
        if trade.outcome in ("WIN", "LOSS"):
            move = (trade.exit_price - trade.entry) if trade.direction == "LONG" else (trade.entry - trade.exit_price)
            trade.pnl_cash = trade.position_size * move
            trade.r_multiple = move / trade.risk_per_unit

        trades.append(trade)

    return trades


def format_report(bars, trades):
    lines = []
    lines.append("=" * 100)
    lines.append("MEASURED SWING STRATEGY - BTCUSD DAILY BACKTEST")
    lines.append("=" * 100)
    lines.append(f"Data range : {bars[0]['date']} -> {bars[-1]['date']}  ({len(bars)} daily candles, Kraken XBTUSD)")
    lines.append(f"Zig-zag threshold: {ZIGZAG_THRESHOLD:.0%}   Entry: 61.8%   SL: 78.6% +{SL_BUFFER:.1%} buffer   TP: origin swing point")
    lines.append(f"Account: ${ACCOUNT_SIZE:,.0f}   Risk per trade: {RISK_PCT:.0%} (${ACCOUNT_SIZE*RISK_PCT:,.0f})")
    lines.append("")

    closed = [t for t in trades if t.outcome in ("WIN", "LOSS")]
    no_fill = [t for t in trades if t.outcome == "NO_FILL"]
    still_open = [t for t in trades if t.outcome == "OPEN"]

    lines.append("-" * 100)
    lines.append("SEQUENTIAL TRADE LOG (chronological order - series, not grouped by outcome)")
    lines.append("-" * 100)
    header = f"{'#':>3} {'Dir':<5} {'Entry Date':<11} {'Exit Date':<11} {'Entry':>10} {'SL':>10} {'TP':>10} {'Result':<6} {'PnL $':>9} {'R':>6} {'Run W-L':<8} {'Equity $':>10}"
    lines.append(header)

    seq_no = 0
    wins = losses = 0
    cum_pnl = 0.0
    equity = ACCOUNT_SIZE

    for t in trades:
        if t.outcome not in ("WIN", "LOSS"):
            continue
        seq_no += 1
        entry_date = bars[t.entry_idx]["date"]
        exit_date = bars[t.exit_idx]["date"]
        if t.outcome == "WIN":
            wins += 1
        else:
            losses += 1
        cum_pnl += t.pnl_cash
        equity = ACCOUNT_SIZE + cum_pnl
        lines.append(
            f"{seq_no:>3} {t.direction:<5} {entry_date:<11} {exit_date:<11} "
            f"{t.entry:>10,.1f} {t.sl:>10,.1f} {t.tp:>10,.1f} {t.outcome:<6} "
            f"{t.pnl_cash:>9,.2f} {t.r_multiple:>6.2f} {f'{wins}-{losses}':<8} {equity:>10,.2f}"
        )

    lines.append("")
    lines.append("-" * 100)
    lines.append("SUMMARY")
    lines.append("-" * 100)
    total_setups = len(trades)
    lines.append(f"Swing legs detected            : {total_setups}")
    lines.append(f"Setups never filled (no touch) : {len(no_fill)}")
    lines.append(f"Trades still open at data end  : {len(still_open)}")
    lines.append(f"Closed trades (in sequence)    : {len(closed)}")
    lines.append(f"  Wins                         : {wins}")
    lines.append(f"  Losses                       : {losses}")
    if closed:
        win_rate = wins / len(closed) * 100
        lines.append(f"  Win rate                     : {win_rate:.1f}%")
        avg_r = sum(t.r_multiple for t in closed) / len(closed)
        lines.append(f"  Average R-multiple per trade : {avg_r:+.2f}R")
        lines.append(f"  Total P&L                    : ${cum_pnl:+,.2f}  (starting ${ACCOUNT_SIZE:,.0f} -> ${equity:,.2f})")
        max_consec_w = max_consec_l = cur_w = cur_l = 0
        for t in closed:
            if t.outcome == "WIN":
                cur_w += 1; cur_l = 0
            else:
                cur_l += 1; cur_w = 0
            max_consec_w = max(max_consec_w, cur_w)
            max_consec_l = max(max_consec_l, cur_l)
        lines.append(f"  Longest winning streak       : {max_consec_w}")
        lines.append(f"  Longest losing streak        : {max_consec_l}")

    return "\n".join(lines)


def write_trade_csv(bars, trades, path="results_trade_log.csv"):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seq", "direction", "entry_date", "exit_date", "swing_high", "swing_low",
                    "entry", "sl", "tp", "outcome", "exit_price", "pnl_cash", "r_multiple"])
        seq = 0
        for t in trades:
            if t.outcome not in ("WIN", "LOSS"):
                continue
            seq += 1
            w.writerow([seq, t.direction, bars[t.entry_idx]["date"], bars[t.exit_idx]["date"],
                        f"{t.swing_high:.2f}", f"{t.swing_low:.2f}", f"{t.entry:.2f}", f"{t.sl:.2f}",
                        f"{t.tp:.2f}", t.outcome, f"{t.exit_price:.2f}", f"{t.pnl_cash:.2f}", f"{t.r_multiple:.2f}"])


def main():
    bars = load_data(DATA_FILE)
    pivots = find_pivots(bars, ZIGZAG_THRESHOLD)
    trades = run_backtest(bars, pivots)
    report = format_report(bars, trades)
    print(report)
    with open("results.txt", "w") as f:
        f.write(report + "\n")
    write_trade_csv(bars, trades)


if __name__ == "__main__":
    main()

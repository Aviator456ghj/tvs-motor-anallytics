"""
Trend-Filtered Measured Swing Strategy.

Same Fibonacci entries/stops/targets as the original strategy (61.8% entry,
78.6%+2.5% buffer stop, origin-swing take profit) - the ONLY change is a
macro trend gate:

  - LONG (buy-the-dip) setups are only taken when the higher-timeframe
    trend is UP (50-day SMA > 200-day SMA).
  - SHORT (sell-the-bounce) setups are only taken when the higher-timeframe
    trend is DOWN (50-day SMA < 200-day SMA).
  - Setups that fight the macro trend are skipped entirely.

This isolates the trend filter as the single variable under test, against
the same 69 swing legs the original backtest used, so the comparison is
apples-to-apples.
"""
from measured_swing_backtest import (
    load_data, find_pivots, build_setup, ZIGZAG_THRESHOLD, ACCOUNT_SIZE, RISK_PCT
)

DAILY_SRC = "data/btc_usd_daily.csv"
SMA_FAST = 50
SMA_SLOW = 200


def compute_sma(bars, period):
    closes = [b["close"] for b in bars]
    sma = [None] * len(bars)
    window_sum = 0.0
    for i, c in enumerate(closes):
        window_sum += c
        if i >= period:
            window_sum -= closes[i - period]
        if i >= period - 1:
            sma[i] = window_sum / period
    return sma


def trend_at(sma_fast, sma_slow, idx):
    if sma_fast[idx] is None or sma_slow[idx] is None:
        return None
    return "UP" if sma_fast[idx] > sma_slow[idx] else "DOWN"


def run_trend_filtered_backtest(bars, pivots, sma_fast, sma_slow):
    trades = []
    for i in range(len(pivots) - 1):
        p_from, p_to = pivots[i], pivots[i + 1]
        trade = build_setup(p_from, p_to)

        trend = trend_at(sma_fast, sma_slow, trade.setup_confirm_idx)
        wants = "UP" if trade.direction == "LONG" else "DOWN"

        if trend is None:
            trade.outcome = "NO_TREND_DATA"
            trades.append(trade)
            continue
        if trend != wants:
            trade.outcome = "FILTERED_OUT"
            trades.append(trade)
            continue

        window_end = pivots[i + 2].confirm_idx if i + 2 < len(pivots) else len(bars) - 1
        start = trade.setup_confirm_idx + 1

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
        resolved = False
        for j in range(filled_idx, len(bars)):
            bar = bars[j]
            if trade.direction == "SHORT":
                hit_sl, hit_tp = bar["high"] >= trade.sl, bar["low"] <= trade.tp
            else:
                hit_sl, hit_tp = bar["low"] <= trade.sl, bar["high"] >= trade.tp
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

        trade.risk_per_unit = abs(trade.entry - trade.sl)
        cash_risk = ACCOUNT_SIZE * RISK_PCT
        trade.position_size = cash_risk / trade.risk_per_unit
        if trade.outcome in ("WIN", "LOSS"):
            move = (trade.exit_price - trade.entry) if trade.direction == "LONG" else (trade.entry - trade.exit_price)
            trade.pnl_cash = trade.position_size * move
            trade.r_multiple = move / trade.risk_per_unit

        trades.append(trade)

    return trades


def report(bars, trades, label):
    lines = []
    lines.append("=" * 100)
    lines.append(f"TREND-FILTERED MEASURED SWING STRATEGY - {label}")
    lines.append("=" * 100)
    lines.append(f"Trend gate: {SMA_FAST}-day SMA vs {SMA_SLOW}-day SMA. "
                 f"Only LONG-the-dip when trend=UP, only SHORT-the-bounce when trend=DOWN.")
    lines.append("")

    filtered_out = sum(1 for t in trades if t.outcome == "FILTERED_OUT")
    no_trend = sum(1 for t in trades if t.outcome == "NO_TREND_DATA")
    no_fill = sum(1 for t in trades if t.outcome == "NO_FILL")
    closed = [t for t in trades if t.outcome in ("WIN", "LOSS")]

    lines.append(f"{'#':>3} {'Dir':<5} {'Entry Date':<11} {'Exit Date':<11} {'Entry':>10} {'SL':>10} {'TP':>10} "
                 f"{'Res':<5} {'PnL$':>8} {'R':>6} {'W-L':<8} {'Equity$':>10}")
    seq = w = l = 0
    cum = 0.0
    equity = ACCOUNT_SIZE
    for t in trades:
        if t.outcome not in ("WIN", "LOSS"):
            continue
        seq += 1
        if t.outcome == "WIN":
            w += 1
        else:
            l += 1
        cum += t.pnl_cash
        equity = ACCOUNT_SIZE + cum
        lines.append(f"{seq:>3} {t.direction:<5} {bars[t.entry_idx]['date']:<11} {bars[t.exit_idx]['date']:<11} "
                     f"{t.entry:>10,.1f} {t.sl:>10,.1f} {t.tp:>10,.1f} {t.outcome:<5} "
                     f"{t.pnl_cash:>8,.2f} {t.r_multiple:>6.2f} {f'{w}-{l}':<8} {equity:>10,.2f}")

    lines.append("")
    lines.append("-" * 100)
    lines.append("SUMMARY")
    lines.append(f"Legs evaluated          : {len(trades)}")
    lines.append(f"Filtered out (countertrend): {filtered_out}")
    lines.append(f"No trend data (warm-up) : {no_trend}")
    lines.append(f"Setups, never filled    : {no_fill}")
    lines.append(f"Closed trades           : {len(closed)}")
    lines.append(f"  Wins                  : {w}")
    lines.append(f"  Losses                : {l}")
    if closed:
        lines.append(f"  Win rate              : {w/len(closed)*100:.1f}%")
        avg_r = sum(t.r_multiple for t in closed) / len(closed)
        lines.append(f"  Avg R-multiple        : {avg_r:+.2f}R")
        lines.append(f"  Net P&L               : ${cum:+,.2f}  (${ACCOUNT_SIZE:,.0f} -> ${equity:,.2f})")
        mw = ml = cw = cl = 0
        for t in closed:
            if t.outcome == "WIN":
                cw += 1; cl = 0
            else:
                cl += 1; cw = 0
            mw, ml = max(mw, cw), max(ml, cl)
        lines.append(f"  Longest win/loss streak: {mw} / {ml}")
    return "\n".join(lines)


def main():
    bars = load_data(DAILY_SRC)
    sma_fast = compute_sma(bars, SMA_FAST)
    sma_slow = compute_sma(bars, SMA_SLOW)
    pivots = find_pivots(bars, ZIGZAG_THRESHOLD)
    trades = run_trend_filtered_backtest(bars, pivots, sma_fast, sma_slow)
    out = report(bars, trades, f"{ZIGZAG_THRESHOLD:.0%} zig-zag, {bars[0]['date']} -> {bars[-1]['date']}")
    print(out)
    with open("results_trend_filtered.txt", "w") as f:
        f.write(out + "\n")


if __name__ == "__main__":
    main()

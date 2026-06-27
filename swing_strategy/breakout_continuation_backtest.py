"""
Breakout-Continuation backtest - the strategy implied by the swing anatomy
finding: 54.4% of swings EXTEND past the prior swing point rather than
retracing into the 38.2-61.8% golden zone. Instead of fading the bounce
(original Fibonacci strategy), this trades WITH the break:

  - Leg completes UP (low -> swing high) -> place a buy-stop just above
    that swing high. If price breaks out, go LONG (continuation).
  - Leg completes DOWN (high -> swing low) -> sell-stop just below that
    swing low. Breakout -> SHORT (continuation).
  - Stop loss: structural - back at the origin of the leg that's
    breaking out (the point that, if revisited, invalidates the breakout).
  - Take profit: 100% measured move (Phase 2.3 extension formula) -
    breakout level +/- the same range that just formed.

Same $5,000 / 1% risk sizing, same no-lookahead confirmation, same
walk-forward simulation as the other backtests, for direct comparison.
"""
import csv

from measured_swing_backtest import load_data, find_pivots, ZIGZAG_THRESHOLD, ACCOUNT_SIZE, RISK_PCT

DAILY_SRC = "data/btc_usd_daily.csv"
BREAKOUT_BUFFER = 0.002   # 0.2% above/below the swing point to confirm a real break, not noise
SL_BUFFER = 0.02          # 2% beyond the leg's origin, same convention as the other backtests
TP_EXTENSION = 1.0        # 100% measured move


def run_breakout_backtest(bars, pivots):
    trades = []
    for i in range(len(pivots) - 1):
        p0, p1 = pivots[i], pivots[i + 1]
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

        window_end = pivots[i + 2].confirm_idx if i + 2 < len(pivots) else len(bars) - 1
        start = p1.confirm_idx + 1

        trade = {"direction": direction, "swing_origin": p0.price, "swing_point": p1.price,
                 "breakout_level": breakout_level, "sl": sl, "tp": tp, "outcome": None}

        filled_idx = None
        for j in range(start, window_end + 1):
            bar = bars[j]
            if direction == "LONG" and bar["high"] >= breakout_level:
                filled_idx = j
                break
            if direction == "SHORT" and bar["low"] <= breakout_level:
                filled_idx = j
                break

        if filled_idx is None:
            trade["outcome"] = "NO_BREAKOUT"
            trades.append(trade)
            continue

        trade["entry_idx"] = filled_idx
        trade["entry"] = breakout_level

        resolved = False
        for j in range(filled_idx, len(bars)):
            bar = bars[j]
            if direction == "LONG":
                hit_sl, hit_tp = bar["low"] <= sl, bar["high"] >= tp
            else:
                hit_sl, hit_tp = bar["high"] >= sl, bar["low"] <= tp
            if hit_sl:
                trade["outcome"], trade["exit_price"], trade["exit_idx"] = "LOSS", sl, j
                resolved = True
                break
            if hit_tp:
                trade["outcome"], trade["exit_price"], trade["exit_idx"] = "WIN", tp, j
                resolved = True
                break
        if not resolved:
            trade["outcome"] = "OPEN"

        risk_per_unit = abs(trade["entry"] - sl)
        position_size = (ACCOUNT_SIZE * RISK_PCT) / risk_per_unit
        if trade["outcome"] in ("WIN", "LOSS"):
            move = (trade["exit_price"] - trade["entry"]) if direction == "LONG" else (trade["entry"] - trade["exit_price"])
            trade["pnl_cash"] = position_size * move
            trade["r_multiple"] = move / risk_per_unit
        trades.append(trade)

    return trades


def report(bars, trades):
    lines = []
    lines.append("=" * 100)
    lines.append("BREAKOUT-CONTINUATION STRATEGY - BTCUSD DAILY BACKTEST")
    lines.append("=" * 100)
    lines.append("Trades WITH the 54.4% extension bias found in the swing anatomy decode, "
                  "instead of fading the bounce back into the Fibonacci zone.")
    lines.append(f"Breakout buffer: {BREAKOUT_BUFFER:.1%}   SL: 2% beyond leg origin   TP: 100% measured move")
    lines.append("")

    closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
    no_breakout = sum(1 for t in trades if t["outcome"] == "NO_BREAKOUT")

    header = f"{'#':>3} {'Dir':<6} {'Entry Date':<11} {'Exit Date':<11} {'Entry':>10} {'SL':>10} {'TP':>10} {'Res':<5} {'PnL$':>8} {'R':>6} {'W-L':<8} {'Equity$':>10}"
    lines.append(header)
    seq = w = l = 0
    cum = 0.0
    equity = ACCOUNT_SIZE
    for t in closed:
        seq += 1
        if t["outcome"] == "WIN":
            w += 1
        else:
            l += 1
        cum += t["pnl_cash"]
        equity = ACCOUNT_SIZE + cum
        lines.append(f"{seq:>3} {t['direction']:<6} {bars[t['entry_idx']]['date']:<11} {bars[t['exit_idx']]['date']:<11} "
                     f"{t['entry']:>10,.1f} {t['sl']:>10,.1f} {t['tp']:>10,.1f} {t['outcome']:<5} "
                     f"{t['pnl_cash']:>8,.2f} {t['r_multiple']:>6.2f} {f'{w}-{l}':<8} {equity:>10,.2f}")

    lines.append("")
    lines.append("-" * 100)
    lines.append("SUMMARY")
    lines.append(f"Legs evaluated      : {len(trades)}")
    lines.append(f"Never broke out     : {no_breakout}")
    lines.append(f"Closed trades       : {len(closed)}")
    lines.append(f"  Wins              : {w}")
    lines.append(f"  Losses            : {l}")
    if closed:
        lines.append(f"  Win rate          : {w/len(closed)*100:.1f}%")
        avg_r = sum(t["r_multiple"] for t in closed) / len(closed)
        lines.append(f"  Avg R-multiple    : {avg_r:+.2f}R")
        lines.append(f"  Net P&L           : ${cum:+,.2f}  (${ACCOUNT_SIZE:,.0f} -> ${equity:,.2f})")
        mw = ml = cw = cl = 0
        for t in closed:
            if t["outcome"] == "WIN":
                cw += 1; cl = 0
            else:
                cl += 1; cw = 0
            mw, ml = max(mw, cw), max(ml, cl)
        lines.append(f"  Longest win/loss streak: {mw} / {ml}")
    return "\n".join(lines)


def main():
    bars = load_data(DAILY_SRC)
    pivots = find_pivots(bars, ZIGZAG_THRESHOLD)
    trades = run_breakout_backtest(bars, pivots)
    out = report(bars, trades)
    print(out)
    with open("results_breakout_continuation.txt", "w") as f:
        f.write(out + "\n")


if __name__ == "__main__":
    main()

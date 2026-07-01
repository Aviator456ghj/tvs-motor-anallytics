"""
Breakout-Continuation v2 - redesigned exit/filter to fix the threshold
fragility found in breakout_continuation_backtest.py (v1).

v1 diagnosis: SL was placed all the way back at the ORIGIN of the leg that
broke out, while TP was a 100% measured move from the breakout level. On
this dataset that meant risk was consistently 110-145% the size of the
move being targeted - the strategy was risking more than it could win on
every single trade, structurally, regardless of win rate. It only looked
good at the 8% zig-zag threshold because that was the one sample (n=7)
where win rate happened to be high enough to paper over the bad risk:reward.

v2 changes, both grounded in a parameter sweep (see results file) rather
than picked to fit one threshold:

  1. Entry confirmation requires a CLOSE beyond the breakout level, not
     just a wick touch - filters out single-candle fakeouts that v1 let
     trigger trades on. Entry fills at the NEXT bar's open (no lookahead).
  2. Stop loss is anchored to the breakout level itself (not the far leg
     origin): SL = breakout level retraced by SL_GIVEBACK_FRAC (61.8%) of
     the leg's own range. This scales with volatility and is structurally
     tighter than v1's stop.
  3. Take profit is extended past the 100% measured move to 161.8% (an
     extension target rather than a 1:1 measured move), so reward is
     larger relative to the now-tighter risk.

Same $5,000 / 1% risk sizing, same no-lookahead pivot confirmation, same
walk-forward simulation as the other backtests.
"""
from measured_swing_backtest import load_data, find_pivots, ZIGZAG_THRESHOLD, ACCOUNT_SIZE, RISK_PCT

DAILY_SRC = "data/btc_usd_daily.csv"
BREAKOUT_BUFFER = 0.002    # 0.2% above/below the swing point to confirm a real break, not noise
SL_GIVEBACK_FRAC = 0.618   # stop = breakout level retraced 61.8% of the leg's range
TP_EXTENSION = 1.618       # target = breakout level + 161.8% of the leg's range


def run_breakout_v2_backtest(bars, pivots):
    trades = []
    for i in range(len(pivots) - 1):
        p0, p1 = pivots[i], pivots[i + 1]
        rng = abs(p1.price - p0.price)
        direction = "LONG" if p1.kind == "H" else "SHORT"

        if direction == "LONG":
            breakout_level = p1.price * (1 + BREAKOUT_BUFFER)
            sl = breakout_level - SL_GIVEBACK_FRAC * rng
            tp = breakout_level + rng * TP_EXTENSION
        else:
            breakout_level = p1.price * (1 - BREAKOUT_BUFFER)
            sl = breakout_level + SL_GIVEBACK_FRAC * rng
            tp = breakout_level - rng * TP_EXTENSION

        window_end = pivots[i + 2].confirm_idx if i + 2 < len(pivots) else len(bars) - 1
        start = p1.confirm_idx + 1

        trade = {"direction": direction, "swing_origin": p0.price, "swing_point": p1.price,
                 "breakout_level": breakout_level, "sl": sl, "tp": tp, "outcome": None}

        entry_idx = None
        for j in range(start, window_end + 1):
            bar = bars[j]
            confirmed = bar["close"] >= breakout_level if direction == "LONG" else bar["close"] <= breakout_level
            if confirmed and j + 1 < len(bars):
                entry_idx = j + 1
                break

        if entry_idx is None:
            trade["outcome"] = "NO_BREAKOUT"
            trades.append(trade)
            continue

        trade["entry_idx"] = entry_idx
        trade["entry"] = bars[entry_idx]["open"]
        entry = trade["entry"]

        resolved = False
        for j in range(entry_idx, len(bars)):
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

        risk_per_unit = abs(entry - sl)
        position_size = (ACCOUNT_SIZE * RISK_PCT) / risk_per_unit
        if trade["outcome"] in ("WIN", "LOSS"):
            move = (trade["exit_price"] - entry) if direction == "LONG" else (entry - trade["exit_price"])
            trade["pnl_cash"] = position_size * move
            trade["r_multiple"] = move / risk_per_unit
        trades.append(trade)

    return trades


def report(bars, trades, label):
    lines = []
    lines.append("=" * 100)
    lines.append(f"BREAKOUT-CONTINUATION v2 STRATEGY - {label}")
    lines.append("=" * 100)
    lines.append("Close-confirmed breakout entry (next bar's open), stop = 61.8% giveback of the leg's "
                  "range from the breakout level, target = 161.8% extension.")
    lines.append(f"Breakout buffer: {BREAKOUT_BUFFER:.1%}   SL giveback: {SL_GIVEBACK_FRAC:.1%}   "
                 f"TP extension: {TP_EXTENSION:.1%}")
    lines.append("")

    closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
    no_breakout = sum(1 for t in trades if t["outcome"] == "NO_BREAKOUT")

    header = (f"{'#':>3} {'Dir':<6} {'Entry Date':<11} {'Exit Date':<11} {'Entry':>10} {'SL':>10} {'TP':>10} "
              f"{'Res':<5} {'PnL$':>8} {'R':>6} {'W-L':<8} {'Equity$':>10}")
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


def threshold_sweep(bars):
    lines = []
    lines.append("-" * 100)
    lines.append("THRESHOLD SENSITIVITY SWEEP (same SL/TP design, varying zig-zag %)")
    lines.append("-" * 100)
    lines.append(f"{'Thresh':>6} {'Legs':>5} {'NoBreak':>7} {'Closed':>7} {'W':>3} {'L':>3} {'WinRate':>8} {'NetPnL':>10}")
    for pct in [0.05, 0.06, 0.08, 0.10, 0.12, 0.15]:
        pivots = find_pivots(bars, pct)
        trades = run_breakout_v2_backtest(bars, pivots)
        closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
        no_breakout = sum(1 for t in trades if t["outcome"] == "NO_BREAKOUT")
        w = sum(1 for t in closed if t["outcome"] == "WIN")
        l = len(closed) - w
        net = sum(t["pnl_cash"] for t in closed)
        wr = (w / len(closed) * 100) if closed else 0.0
        lines.append(f"{pct:>5.0%} {len(trades):>5} {no_breakout:>7} {len(closed):>7} {w:>3} {l:>3} {wr:>7.1f}% {net:>+10.2f}")
    return "\n".join(lines)


def main():
    bars = load_data(DAILY_SRC)
    pivots = find_pivots(bars, ZIGZAG_THRESHOLD)
    trades = run_breakout_v2_backtest(bars, pivots)
    out = report(bars, trades, f"{ZIGZAG_THRESHOLD:.0%} zig-zag, {bars[0]['date']} -> {bars[-1]['date']}")
    out += "\n\n" + threshold_sweep(bars)
    print(out)
    with open("results_breakout_continuation_v2.txt", "w") as f:
        f.write(out + "\n")


if __name__ == "__main__":
    main()

"""
Two honesty checks on breakout_continuation_v2 - the one variant in this
README that's both net-positive and survives a parameter/threshold sweep.
"Robust across a sweep" and "will work every time" are not the same claim;
this script tries to close that gap as far as 2 years of daily BTCUSD data
honestly allows, rather than adding a 17th mean-reversion variant chasing
the same dead end every other variant in this README already hit (this
market extends through structure far more often than it reverses off it -
v2 is the only design here that trades WITH that fact instead of against
it, so the right move is to stress-test and sharpen it, not replace it).

1. WALK-FORWARD SPLIT: the 61.8% SL-giveback / 161.8% TP-extension
   parameters were chosen from a 30-cell grid swept over the FULL 2-year
   sample. That doesn't prove they'd have looked good if you only had the
   first half of the data and had to commit before seeing the second half.
   This splits the daily series at a fixed calendar cutoff, finds pivots
   independently in each half (legs are local, so this is safe - only the
   one leg straddling the cutoff is dropped), and reports the production
   parameters plus the full threshold sweep on EACH half separately.

2. DAILY-HA-BIAS FILTER: the order-block work in this README established
   that a market's bias from the *previous* day's Heikin-Ashi color is, on
   its own, an informative directional signal (46.3% win rate using it
   directly as a trade trigger - it lost money there only because of a
   stop-sizing flaw, not because the bias itself was wrong). This checks
   whether layering that bias as a FILTER on top of v2's existing entries
   (only take the breakout if it agrees with yesterday's HA color) trims
   the loser trades without giving up much sample size.

Same $5,000/1% account convention as every other script in this repo.
"""
from measured_swing_backtest import load_data, find_pivots, ACCOUNT_SIZE, RISK_PCT
from breakout_continuation_v2_backtest import run_breakout_v2_backtest
from ha_bias_ema_band_backtest import load_daily, heikin_ashi, bias_by_date, DAILY_PATH

DAILY_SRC = "data/btc_usd_daily.csv"
SPLIT_DATE = "2025-08-15"  # roughly the midpoint of the 2-year window


def summarize(trades):
    closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
    w = sum(1 for t in closed if t["outcome"] == "WIN")
    l = len(closed) - w
    net = sum(t["pnl_cash"] for t in closed)
    wr = (w / len(closed) * 100) if closed else 0.0
    avg_r = (sum(t["r_multiple"] for t in closed) / len(closed)) if closed else 0.0
    return len(trades), len(closed), w, l, wr, avg_r, net


def walk_forward_split(bars):
    lines = []
    lines.append("=" * 104)
    lines.append("CHECK 1: WALK-FORWARD SPLIT (pivots and trades computed independently in each half)")
    lines.append("=" * 104)
    split_idx = next(i for i, b in enumerate(bars) if b["date"] >= SPLIT_DATE)
    first_half, second_half = bars[:split_idx], bars[split_idx:]
    lines.append(f"Split date: {SPLIT_DATE}  (first half: {first_half[0]['date']} -> {first_half[-1]['date']}, "
                 f"{len(first_half)} days; second half: {second_half[0]['date']} -> {second_half[-1]['date']}, "
                 f"{len(second_half)} days)")
    lines.append("")
    lines.append(f"{'Half':<13} {'Thresh':>6} {'Legs':>5} {'Closed':>7} {'W':>3} {'L':>3} {'WinRate':>8} "
                 f"{'AvgR':>7} {'NetPnL':>10}")
    for label, half in (("FIRST HALF", first_half), ("SECOND HALF", second_half)):
        for pct in (0.05, 0.06, 0.08, 0.10, 0.12, 0.15):
            pivots = find_pivots(half, pct)
            trades = run_breakout_v2_backtest(half, pivots)
            legs, closed, w, l, wr, avg_r, net = summarize(trades)
            lines.append(f"{label:<13} {pct:>5.0%} {legs:>5} {closed:>7} {w:>3} {l:>3} {wr:>7.1f}% "
                         f"{avg_r:>+6.2f}R {net:>+10.2f}")
    lines.append("")
    lines.append("A genuinely robust edge should show up (net-positive, similar win rate) in BOTH halves at "
                 "the thresholds with a usable sample, not just one.")
    return "\n".join(lines)


def bias_filter_check(daily_bars):
    lines = []
    lines.append("")
    lines.append("=" * 104)
    lines.append("CHECK 2: DAILY HA-BIAS FILTER (only take a v2 breakout if it agrees with yesterday's HA color)")
    lines.append("=" * 104)
    bias_map = bias_by_date(daily_bars)
    lines.append(f"{'Thresh':>6} {'Filter':<10} {'Legs':>5} {'Closed':>7} {'W':>3} {'L':>3} {'WinRate':>8} "
                 f"{'AvgR':>7} {'NetPnL':>10}")
    for pct in (0.05, 0.06, 0.08, 0.10, 0.12, 0.15):
        pivots = find_pivots(daily_bars, pct)
        trades = run_breakout_v2_backtest(daily_bars, pivots)
        legs, closed, w, l, wr, avg_r, net = summarize(trades)
        lines.append(f"{pct:>5.0%} {'unfiltered':<10} {legs:>5} {closed:>7} {w:>3} {l:>3} {wr:>7.1f}% "
                     f"{avg_r:>+6.2f}R {net:>+10.2f}")

        filtered = []
        for t in trades:
            if t["outcome"] not in ("WIN", "LOSS"):
                continue
            entry_date = daily_bars[t["entry_idx"]]["date"]
            bias = bias_map.get(entry_date)
            wanted = "BULLISH" if t["direction"] == "LONG" else "BEARISH"
            if bias == wanted:
                filtered.append(t)
        closed_f = filtered
        w_f = sum(1 for t in closed_f if t["outcome"] == "WIN")
        l_f = len(closed_f) - w_f
        net_f = sum(t["pnl_cash"] for t in closed_f)
        wr_f = (w_f / len(closed_f) * 100) if closed_f else 0.0
        avg_r_f = (sum(t["r_multiple"] for t in closed_f) / len(closed_f)) if closed_f else 0.0
        lines.append(f"{pct:>5.0%} {'bias-OK':<10} {legs:>5} {len(closed_f):>7} {w_f:>3} {l_f:>3} {wr_f:>7.1f}% "
                     f"{avg_r_f:>+6.2f}R {net_f:>+10.2f}")
    lines.append("")
    lines.append("If the filter trims the loser trades, 'bias-OK' rows should show a higher win rate / net P&L "
                 "than 'unfiltered' on a meaningfully smaller sample; if it just throws away trades at the same "
                 "ratio, the bias filter is adding no information on top of the breakout signal itself.")
    return "\n".join(lines)


def main():
    bars = load_data(DAILY_SRC)
    out = walk_forward_split(bars)
    out += "\n" + bias_filter_check(bars)
    print(out)
    with open("results_breakout_v2_robustness.txt", "w") as f:
        f.write(out + "\n")


if __name__ == "__main__":
    main()

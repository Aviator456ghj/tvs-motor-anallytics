# Measured Swing Strategy — BTCUSD Backtest

Implements the Fibonacci "Measured Swing" rules (swing-high/low detection →
61.8% retracement entry → 78.6%+buffer stop → origin-swing take profit →
fixed-cash position sizing) and backtests them on real BTCUSD daily data.

## Data

`data/btc_usd_daily.csv` — 721 daily OHLCV candles for XBTUSD from Kraken's
public API, 2024-07-07 to 2026-06-27.

## Method

1. **Swing detection (Phase 1)** — a zig-zag pivot detector marks a swing
   high/low only after price reverses `ZIGZAG_THRESHOLD` (8%) away from the
   extreme, which is when a real trader could actually recognize the pivot.
   No lookahead: a leg only becomes tradeable from its confirmation bar
   onward.
2. **Fib math (Phase 2)** — for every confirmed leg, `Swing Range = High - Low`,
   then 61.8% / 78.6% / 100% levels per the document's formulas.
3. **Orders (Phase 4)** — down-leg → SHORT the 61.8% bounce; up-leg → LONG
   the 61.8% dip (continuation trades). Stop placed 2.5% beyond the 78.6%
   line; take-profit placed just past the leg's origin swing point.
4. **Position sizing (Phase 5)** — $5,000 account, 1% ($50) risked per
   trade, `position size = $50 / |entry - stop|`, non-compounding, exactly
   like the document's worked example.
5. **Walk-forward simulation** — bars are scanned in chronological order;
   a pending limit order is cancelled if the next opposing pivot forms
   before price ever reaches the 61.8% line. Once filled, exits resolve on
   whichever of SL/TP is touched first; if both are touched on the same
   candle the stop is assumed to hit first (conservative).
6. **Sequential reporting** — trades are logged and counted strictly in
   the order they occurred (entry-1, entry-2, …), not grouped into a
   winners bucket and a losers bucket.

## Running it

```
python3 measured_swing_backtest.py
```

Outputs `results.txt` (full report) and `results_trade_log.csv`
(per-trade ledger).

## Headline result (8% zig-zag threshold)

| Metric | Value |
|---|---|
| Swing legs detected | 69 |
| Setups never reached entry | 20 |
| Closed trades | 49 |
| Wins | 12 |
| Losses | 37 |
| Win rate | 24.5% |
| Avg R-multiple | -0.34R |
| Net P&L on $5,000 account | -$836.95 |
| Longest win streak / loss streak | 2 / 10 |

### Threshold sensitivity

The zig-zag threshold is the one free parameter (how big a move counts as
an "impulsive leg"). Re-running across thresholds:

| Threshold | Trades | Win rate | Net P&L |
|---|---|---|---|
| 5% | 95 | 30.5% | -$1,360 |
| 6% | 73 | 28.8% | -$1,055 |
| 8% | 49 | 24.5% | -$837 |
| 10% | 36 | 25.0% | -$480 |
| 12% | 25 | 36.0% | +$105 |
| 15% | 13 | 23.1% | -$168 |

Across nearly every parameterization the strategy is a net loser over this
~2-year BTCUSD window: winners run bigger than losers (avg R on wins is
well above 1), but the win rate (~25-30%) isn't high enough to overcome
that in a market that trended rather than mean-reverting back through
full swing ranges as often as the rulebook assumes.

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

## Variant: Trend-filtered (50/200 SMA gate)

`trend_filtered_backtest.py` keeps the identical Fib entry/SL/TP math and
only adds a macro trend gate: LONG-the-dip setups require 50-day SMA >
200-day SMA, SHORT-the-bounce setups require 50-day SMA < 200-day SMA;
counter-trend setups are skipped. Swept across the same threshold range
(see `results_trend_filtered.txt`):

| Threshold | Closed trades | Win rate | Net P&L |
|---|---|---|---|
| 5% | 32 | 25.0% | -$636 |
| 6% | 26 | 23.1% | -$551 |
| 8% | 18 | 11.1% | -$633 |
| 10% | 14 | 7.1% | -$537 |
| 12% | 9 | 11.1% | -$287 |
| 15% | 4 | 0.0% | -$200 |

**The trend filter is not a fix.** It is worse than the unfiltered baseline
at every threshold except 5%/6% (roughly a tie), and net P&L stays negative
everywhere. Macro SMA trend direction does not predict whether a 61.8%
retracement entry resolves to TP or SL on this series — the failure mode
isn't "fighting the trend," it's that price extends past the swing point
(see swing-anatomy finding below) more often than it retraces back to a
tradeable Fib zone, regardless of macro trend.

## Variant: Breakout-continuation (trade with the extension, not the retrace)

`swing_anatomy.py` decodes all 69 legs mathematically and finds 54.4% of
legs *extend* past the prior swing point rather than retracing into the
38.2-61.8% zone the strategy is built around — and a Monte Carlo test shows
the apparent Fibonacci-ratio clustering in leg-to-leg ranges is **not
statistically significant** (p=0.879 on price ratios, p=0.979 on time
ratios vs. a fitted lognormal null). `breakout_continuation_backtest.py`
tests trading with that extension bias (buy/sell-stop breakout of the prior
swing point, structural SL at the leg origin, 100% measured-move TP).
At 8% threshold this looked attractive (5W/2L, 71.4%, +$118) but the same
threshold sweep shows it isn't robust — most other thresholds are
net-negative with 38-50% win rates on tiny samples (2-21 trades).

## Bottom line across all variants

| Strategy | Best single result | Robust across thresholds? |
|---|---|---|
| Original Fibonacci retracement | 24.5% WR, -$837 | Yes (consistently net-negative) |
| Trend-filtered (50/200 SMA) | 11-25% WR, -$200 to -$636 | Yes (consistently worse or flat) |
| Breakout-continuation | 71.4% WR, +$118 (n=7) | **No** — cherry-picked single threshold |
| CVD divergence (real + proxy) | 0% WR, -$100 (n=2 each) | Sample too small to judge |

None of the tested variants produces a robust, statistically meaningful
high-win-rate edge on this BTCUSD daily dataset. See
`CVD_STRATEGY_COMPARISON.md` for the CVD-specific writeup.

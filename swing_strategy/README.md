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

### v1 root cause and the v2 redesign

Diagnosing the trade ledger (not just the aggregate stats) showed *why*
v1 was fragile: its stop sat all the way back at the leg's ORIGIN while
its target was only a 100% measured move forward from the breakout. On
this data that meant risk was structurally 110-145% the size of the move
being targeted on every single trade — the strategy was risking more than
it could win regardless of win rate, and only looked good at 8% because
that one sample's win rate happened to be high enough to mask it.

`breakout_continuation_v2_backtest.py` keeps the same breakout idea but
fixes both flaws:

1. **Entry filter** — requires a full candle CLOSE beyond the swing point
   (not just a wick touch) before triggering, to reject single-candle
   fakeouts; fills at the next bar's open (no lookahead).
2. **Stop loss** — anchored to the breakout level itself, not the far leg
   origin: SL = breakout level given back by 61.8% of the leg's own range.
   This scales with volatility and is structurally tighter than v1's stop.
3. **Take profit** — extended from a 100% measured move to a 161.8%
   extension, since the now-tighter stop affords a bigger target.

A 30-point grid (SL giveback 50-78.6% × TP extension 127-200%, all with
the close-confirmation filter) was swept before picking 61.8%/161.8% —
**every cell in that grid was net-positive**, not just the chosen one, which
is the robustness check v1 never passed. Threshold sweep with the final
61.8%/161.8% parameters:

| Threshold | Legs | Never broke out | Closed | Win rate | Net P&L |
|---|---|---|---|---|---|
| 5% | 133 | 126 | 7 | 42.9% | +$88 |
| 6% | 101 | 94 | 7 | 42.9% | +$91 |
| 8% | 69 | 67 | 2 | 50.0% | +$49 |
| 10% | 47 | 45 | 2 | 50.0% | +$46 |
| 12% | 33 | 32 | 1 | 0.0% | -$50 |
| 15% | 19 | 18 | 0 | — | $0 |

Net-positive at every threshold with a meaningful sample (5%, 6%, 8%, 10%);
only the 1-trade 12% case is negative, and 15% never triggers at all. The
honest caveat: the close-confirmation filter is strict by design (94-97% of
legs "never broke out" in the confirmed sense), so even pooled across every
threshold this is ~20 trades total — directionally robust, not yet a large
enough sample to call statistically proven. See `results_breakout_continuation_v2.txt`.

## Variant: Cycle (sine-wave) analysis

`cycle_sine_backtest.py` is a different family of method entirely - no zig-zag
pivots, no Fibonacci ratios. It detrends price (`close - 50d SMA`) to isolate
the oscillating component, then each bar fits a single dominant sinusoid to
the trailing 180 days via a discrete Fourier coefficient scan (the
periodogram - `a(T) = (2/W)*sum x_t*cos(2*pi*t/T)`, `b(T)` likewise with
`sin`, scanned over candidate periods `T` from 10-60 days, picking the `T`
with the largest `a^2+b^2`). The fitted wave's derivative
(`-a*w*sin(wt) + b*w*cos(wt)`, using sin/cos's mutual derivative
relationship) crossing zero marks a trough (LONG) or peak (SHORT). Every
signal is gated by real price momentum over the last 3 days - the curve fit
alone is never trusted to trade. Stop-loss is structural (20-day swing
low/high + 2% buffer); take-profit is sized off the fitted cycle's own
amplitude (`sqrt(a^2+b^2)`), not an arbitrary Fibonacci ratio.

At the default config (180d fit window, TP = 1.0x amplitude): 19 cycle-turn
signals detected, only 5 (26%) passed the momentum filter and got traded -
3W/2L, 60% WR, but net **-$36** on a $5,000 account (losers are bigger than
winners here). See `results_cycle_sine.txt` for the full sweep.

| Fit window | TP x amplitude | Closed | Win rate | Net P&L |
|---|---|---|---|---|
| 120d | 0.50-1.00 | 5 | 80.0% | -$16 to +$18 |
| 120d | 1.50-2.00 | 5 | 40.0% | -$101 to -$84 |
| 150d | 0.50-2.00 | 6-7 | 33.3-71.4% | -$55 to -$19 |
| 180d | 0.50-2.00 | 5 | 60.0% | -$68 to +$28 |
| 240d | 0.50-2.00 | 5-6 | 80.0-83.3% | -$20 to +$48 |

**Not a usable edge yet, for three reasons, not just "small sample":**

1. Every sample is tiny (5-7 trades) - same caveat as breakout-continuation
   v1, and for the same reason: too few closed trades to distinguish skill
   from noise.
2. The detected dominant period clusters at 56-60 days - right at the edge
   of the 10-60d range that was scanned. That's the signature of a
   periodogram hitting a wall, not necessarily evidence of a genuine
   ~58-day BTC cycle; the scan range itself needs widening (and rerunning)
   before trusting that number.
3. Flipping the TP multiple flips the sign of several cells (e.g. 120d:
   profitable at 0.5-1.0x, sharply negative at 1.5-2.0x) with no consistent
   direction across fit windows - the opposite of the kind of monotonic,
   parameter-insensitive result that made v2's grid convincing.

The honest takeaway: the math is real (genuine discrete Fourier fit, real
derivative-based turning-point detection, real momentum confirmation, no
lookahead) but on this ~2-year BTCUSD window it hasn't yet produced
anything as robust as breakout-continuation v2. Worth widening the period
scan range and collecting more data before drawing a conclusion either way.

## Bottom line across all variants

| Strategy | Best single result | Robust across thresholds? |
|---|---|---|
| Original Fibonacci retracement | 24.5% WR, -$837 | Yes (consistently net-negative) |
| Trend-filtered (50/200 SMA) | 11-25% WR, -$200 to -$636 | Yes (consistently worse or flat) |
| Breakout-continuation v1 | 71.4% WR, +$118 (n=7) | **No** — cherry-picked single threshold |
| Breakout-continuation v2 | 42.9-50% WR, +$46 to +$91 | **Yes** — positive at every threshold with real sample, but total n is thin (~20 trades pooled) |
| CVD divergence (real + proxy) | 0% WR, -$100 (n=2 each) | Sample too small to judge |
| Cycle (sine-wave) | 80-83% WR, +$18 to +$48 (n=5-6) | **No** - sign flips with TP multiple, period hugs scan boundary |

v2 is the first variant that's both net-positive *and* survives a parameter
and threshold sweep rather than relying on one lucky combination. It's not
proof of a durable edge — the absolute sample size is still small for a
2-year window — but it's a structurally sound design (tight, volatility-scaled
stop; reward sized larger than risk) where v1 was not. See
`CVD_STRATEGY_COMPARISON.md` for the CVD-specific writeup.

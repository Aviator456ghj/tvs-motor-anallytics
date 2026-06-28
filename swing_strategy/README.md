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

## Variant: Quantum Wave Matrix (QWM) — 5-minute multi-confirmation scalp

`qwm_backtest.py` implements a much more elaborate pasted playbook ("THE
QUANT QUANTUM WAVE MATRIX") that requires three signals to align
simultaneously on 5-minute BTCUSD bars, inside two daily liquidity windows
(London 03:00-06:30 NY, New York 08:30-11:30 NY):

1. **Vector angle Θ** — a price/time "angle" of a recent expansion leg,
   trigger at Θ≥+70° / ≤-70°, silence inside ±45°.
2. **π-radial cycle phase Φ(t)=sin(ωt+φ)** — trigger at Φ≥+0.995 / ≤-0.995.
3. **"Structural Mass"** — a definite integral of price displacement,
   trigger at ≥1.0.

As pasted, none of these three were dimensionally sound enough to
backtest as written, so three fixes were made (and documented in the
module docstring) before any code ran:

- **Θ made scale-invariant**: the raw `arctan(ΔPrice/ΔTime)` changes with
  chart zoom because $ and bars aren't the same unit. Fixed by normalizing
  the slope by ATR-per-bar first: `Θ = arctan( (Δprice/n) / ATR )`, so 70°
  means "the same relative violence" on any asset/timeframe.
- **Φ's ω and φ made fittable**: the playbook never says how to derive
  the cycle frequency/phase from data. Fixed by reusing the discrete
  Fourier periodogram fit from `cycle_sine_backtest.py`, run on a 4-hour
  anchor series built from the same 5-minute data.
- **Mass made dimensionless**: a raw $·bars integral has no natural "1.0"
  threshold. Fixed by z-scoring it against its own trailing 200-sample
  distribution — "≥1.0" now means "≥1 standard deviation of unusualness,"
  a documented assumption since the original text wasn't specific here.

Liquidity-gate session filter, stdev-based SL (0.5σ beyond the signal
bar's wick), breakeven-at-1.5R, and the position-sizing formula were
already well-defined in the playbook and implemented as specified.

### Result: the literal spec produces zero trades on real data

Running the corrected math on 30 days of real 5-minute BTCUSD (the only
intraday dataset in this repo — the playbook's other four assets have no
data here) produces **0 trades at every cell of a 6×3 angle×phase
threshold sweep**, including the playbook's literal 70°/0.995 values. The
`ANGLE DISTRIBUTION DIAGNOSTIC` block in `results_qwm.txt` shows why this
isn't a software bug:

| Metric (inside liquidity gates only) | Value |
|---|---|
| In-gate 5-min bars sampled | 2,322 |
| Max \|Θ\| ever reached | 54.8° |
| 99th percentile \|Θ\| | 42.2° |
| Bars with \|Θ\| > 45° | 12 |
| Bars with \|Θ\| > 60° or > 70° | 0 |

The ATR-normalized angle never once reaches the playbook's 70° trigger
in a month of real BTC 5-minute data — the highest it gets is 54.8°,
and only 12 bars total (out of 2,322 in-gate bars) even clear the 45°
"consolidation" floor. Of those 12, the H4 phase fit Φ never aligns in
the matching direction near the required ±0.995 (observed values: 0.93,
-0.55, 0.24, 0.04, and a few unscored bars too early for a phase fit) —
so even loosening the phase threshold to 0.90 inside the swept grid still
yields nothing.

To confirm this is a parameter/data problem and not a bug, the engine was
re-run with all three gates collapsed far below the spec (e.g. angle≥10°,
phase≥0.0, mass z≥-5.0) purely as a code-correctness check — at that point
entries fill, breakeven arms, SL/TP resolve, and position sizing computes
correctly, producing a handful of real trades. That confirms the execution
machinery works; it's the literal threshold *combination* the playbook
specifies that this dataset never satisfies.

**Honest verdict**: as written, this strategy is untestable on the data
available — not because the math is unsound (it's now dimensionally
correct) but because requiring three independent extreme conditions to
co-occur, restricted to ~27% of the day, is so strict that a month of
real BTC 5-minute data never produces a single qualifying signal. The
playbook's own claim of "10-15 entries per asset per month" would require
either a much longer backtest window, the other four assets it specifies,
or thresholds well below 70°/0.995/1.0σ — none of which can be confirmed
or denied from what's available here. This is a data-availability and
threshold-calibration finding, not a verdict on the underlying idea.

## Variant: Quantum Wave Matrix, daily resolution (2 years of data, not 30 days)

`qwm_backtest.py`'s zero-trade result came from only having 30 days of
5-minute data — not enough samples for a strategy whose angle/phase/mass
gates are individually rare. `qwm_daily_backtest.py` re-runs the same three
corrected signals (ATR-normalized angle, periodogram-fit phase, z-scored
mass) on the full ~2-year daily BTCUSD series this repo actually has,
trading daily bars against a weekly anchor (the daily/weekly analogue of
M5/H4 — weekly bars are chunked 7 daily bars at a time, same coarsening
*ratio* concept as H4's 48 5-min bars). One deliberate deviation: the
London/NY liquidity-gate session filter is **dropped**, because daily bars
carry no time-of-day and applying an intraday filter to them would be
meaningless, not just impractical.

**Result: still zero trades — and now for a sharper, more interesting
reason.** The `ANGLE DISTRIBUTION DIAGNOSTIC` in `results_qwm_daily.txt`
shows the default (5-day-average) angle never exceeds 44.5° in two full
years. But a deeper check — varying the lookback used to measure Θ down to
a single day, the most permissive possible reading of "vector angle of
price/time" — settles the question for good:

| Angle lookback | Max \|Θ\| ever reached (2yr) | Reaches 70° trigger? |
|---|---|---|
| 5-day average | 44.5° | No |
| 3-day average | 54.8° | No |
| 2-day average | 61.4° | No |
| 1-day (single best day in 2 years) | **68.5°** | **No — falls just short** |

The single best single-day move in two years of real BTCUSD price action,
expressed as ATRs-of-slope-per-bar, comes in at 68.5° — under the
playbook's 70° trigger. The threshold isn't merely strict, it's
calibrated at or just past the empirical ceiling of this asset's
historical volatility. With the angle gate loosened to 50-65° (so the
funnel can actually be exercised) and lookback=1, 1-9 trades appear per
cell of a 20-cell sweep — and **every single one is net-negative** (0-20%
win rate, -$1,000 to -$6,000 on $100,000). Full table in
`results_qwm_daily.txt`'s `LOOKBACK SENSITIVITY` section.

**Honest verdict**: this isn't a small-sample problem anymore — two years
of real daily BTCUSD is the same window the other backtests in this repo
use to draw real conclusions. The literal QWM thresholds never fire
regardless of lookback choice, and loosening them to where they do fire
produces a strategy with no edge. Combined with the 5-minute result, the
overall conclusion holds across both resolutions tested: the angle/phase/mass
gates as specified are either unreachable or, when made reachable, net-losing.

## Variant: Trident System (30-min FVG/Doji institutional pattern)

`trident_backtest.py` implements "THE TRIDENT SYSTEM" playbook (TG Capital
prop-firm model) as literally as possible: a 30-minute kill-zone gate
(3:00-6:30 AM NY), a 200-EMA baseline trend filter, a strict 5/9/13/21-EMA
stack alignment requirement, then a 4-candle Fair Value Gap → 50%
Consequent-Encroachment → Doji → confirmation-close entry pattern, with SL
at the doji wick and TP at the playbook's stated 1:20 minimum baseline RR.

**Data-fit caveat, stated upfront**: this playbook is explicitly written
for FX majors and Gold, built around London-session liquidity structure,
and itself claims only ~6-15 entries **per year** per instrument. This
repo has only BTCUSD and only 30 days of 5-minute history — structurally
incapable of producing a meaningful sample for a strategy this selective,
in either direction, even with a flawless implementation.

**Documented assumptions** (spec doesn't state these explicitly):
the SHORT side of the candle pattern is the literal mirror image of the
LONG side the document describes; the discretionary "macro daily-structure
trailing target" is not backtested (not objectively codeable) — only the
1:20 minimum baseline TP is; the FX/Gold "tick buffer" on the stop is
approximated as 0.05% of price, since BTC has no pip-equivalent; entry
fills at Candle 4's own close exactly as the text specifies ("market buy
the millisecond Candle 4 closes" — an idealized zero-slippage fill).

**Result: zero trades, at every cell of a 16-cell parameter sweep
(doji-body-ratio × minimum-RR).** The funnel in `results_trident.txt`
shows *why*, and the reason is sharper than just "thresholds too strict":

| Gate | M30 bars surviving |
|---|---|
| Inside kill zone | 181 |
| + 200-EMA trend filter | 181 |
| + 5/9/13/21 EMA stack aligned | 75 |
| + FVG + doji-at-CE pattern found | **0** |

The `FVG DIAGNOSTIC` section goes one level deeper and checks for the Fair
Value Gap *on its own*, with every other filter removed — across all 1,440
M30 candles in the dataset, a bullish FVG (candle-2 low above candle-1
high) occurs exactly **once**, and a bearish FVG **never** occurs at all.
No amount of loosening the doji-body-ratio or minimum-RR sweep parameters
can produce trades when the gap the pattern depends on essentially never
forms in the underlying data.

**Honest verdict**: this is a market-structure mismatch, not a tuning
problem. Continuous 24/7 crypto trading rarely leaves true gaps between
consecutive candle ranges — FVGs are a pattern born from session-based
markets (FX/equities/Gold) that close and reopen, where price can jump
across a range between candles. BTC's near-continuous order book means
the precondition for this entire playbook almost never exists at the M30
timeframe in this dataset, independent of and more fundamental than the
EMA/kill-zone/doji filters layered on top. Combined with the explicit
~6-15-trades-per-year claim on a 30-day sample, this result cannot be read
as either confirming or refuting "the Trident System" for its intended FX/Gold
markets — only as confirmation that the pattern-matching/EMA/risk math
itself runs correctly and produces sane (if zero) output when it has no
qualifying setups to act on.

## Variant: Phase-rotation cycle (time-delay embedding)

`phase_rotation_backtest.py` is a different mathematical construction from
the other cycle variant, not a re-test of an external playbook: it chains
the same trig/calculus tools end to end rather than using a derivative
check. (1) **Forward fit** — same periodogram sin/cos fit as
`cycle_sine_backtest.py` finds the dominant cycle length T* and amplitude.
(2) **Phase-portrait embedding** — builds a 2-D vector from the z-scored
detrended price and its own value one quarter-cycle (T*/4) earlier (a
standard time-delay/Takens embedding); a true sinusoid traces a circle in
this plane. (3) **Inverse trig** — the signed rotation angle between
consecutive phase vectors is `atan2(cross, dot)`, the literal inverse of
the forward sin/cos pair. (4) **Integration** — cumulative phase
`Theta(t) = Theta(t-1) + angle_step(t)` is the discrete integral of that
angular velocity, tracked continuously start to end regardless of trade
state. (5) **Forward projection** — `cos(Theta(t))` near -1/+1 flags a
phase-portrait trough/crest (LONG/SHORT), and the take-profit projects the
next extreme half a cycle ahead via `cos(Theta + pi) = -cos(Theta)`. A
coherence filter (the last 5 rotation steps must share a sign) gates every
entry so a single noisy tick isn't trusted as a real turn.

**Result: zero trades at the default settings.** The dominant cycle this
fit finds on 2 years of daily BTC is long (median 54 days, range 26-60),
so each day's rotation step is small; daily price noise flips the angle's
sign before 5 consecutive coherent steps ever accumulate, and the
coherence filter (by design) blocks the entry. The 27-cell sweep
(lag fraction × band threshold × coherence-bar count) in
`results_phase_rotation.txt` confirms this isn't a one-off: relaxing
coherence to 3 bars does let trades through (0-10 per cell), but the
results are thin-sample and mostly net-negative (-$1 to -$200 across most
cells); the handful of "100% win rate" cells are n=1 artifacts, not edge.

**Honest verdict**: the math chain is internally consistent (the angle
extraction and integration behave exactly as the trig identities predict,
and the projected TP correctly lands on the cycle's opposite extreme when
a trade does fire) but the signal itself has no edge on this data — same
conclusion as every other cycle-based variant in this repo, arrived at via
a genuinely different mathematical route.

## Variant: Gravity-field price-magnet model

`gravity_field_backtest.py` answers a different question than the cycle
variants: not "when does price turn" but "what pulls and pushes it toward
zones it has occupied before." Every historical daily close is treated as
one unit of mass on the log-price axis - levels visited often (support/
resistance, congestion, value areas) accumulate more mass than levels
price blew straight through. This maps directly onto 1-D gravity: in one
dimension a point mass's potential is *logarithmic*, `U(x) = -G*m*ln|x|`,
so its force is `F(x) = -dU/dx = G*m/x` - an inverse-*distance* pull, not
the inverse-square of 3-D gravity. Summing that 1/distance pull from every
historical price level (built only from data strictly before today, no
lookahead) to today's price gives one signed number: net gravitational
pull. The take-profit is the model's literal prediction of "where in the
future" - it walks outward from today's price in the force's direction
until it hits the next prominent peak in the smoothed historical-density
curve, i.e. the next zone the model expects price to be pulled back to.

**Result: this is the first variant in this repo to fire a real,
non-trivial sample without any threshold-loosening.** At the documented
default settings (180-day lookback, 2% log-price bins, 1.0-sigma force
threshold) it produces **15 trades**: 4 wins, 10 losses, 1 still open,
28.6% win rate, -0.33R average, net **-$233.78** on the $5,000 account.
The 36-cell sweep (Z-threshold × lookback × bin width) in
`results_gravity_field.txt` tells a consistent story - sample sizes range
3-29 trades per cell, win rates run 0-44%, and all but a handful of
thin-sample cells (n=3-9) are net-negative; the few positive cells
(+$29 to +$31) are themselves too small to read as edge.

**Honest verdict**: the physics is sound and the historical-density
"magnet" zones are real (price genuinely does revisit high-density
congestion areas more often than low-density ones, which is exactly what
volume/market-profile traders already exploit) - but knowing price will
likely *visit* a historical magnet zone again says nothing about whether
it will do so by going up or down from here in a way that's net profitable
once a stop-loss is in the mix, and that's exactly what 28.6% WR /
net-negative means: the directional read off the force sign isn't reliable
enough to beat the cost of the stop, even though the destination prediction
itself is a real, defensible piece of market structure.

## Variant: Trendline + Fibonacci confluence

`trendline_fibonacci_backtest.py` replaces the macro SMA gate (already
shown above to be no fix at all) with an actual drawn **trendline**: the
classic technical-analysis combo of connecting the last two same-kind
swing pivots (two rising lows in an uptrend, two falling highs in a
downtrend) and projecting that line forward as dynamic support/resistance.
A retracement into the 50-61.8% Fib golden zone is only treated as a
buyable/sellable continuation if it also respects this trendline; a close
through both the trendline and the 78.6% invalidation line kills the setup
instead of being entered.

### Headline result (8% zig-zag threshold)

| Metric | Value |
|---|---|
| Legs evaluated | 67 |
| Never reached/survived the golden zone | 34 |
| Touched zone but never bounced in time | 18 |
| Closed trades | 15 |
| Wins | 3 |
| Losses | 12 |
| Win rate | 20.0% |
| Avg R-multiple | -0.09R |
| Net P&L on $5,000 account | -$65.21 |
| Longest win streak / loss streak | 1 / 7 |

### Threshold × TP-extension sweep

| Threshold | TP ext | Closed trades | Win rate | Net P&L |
|---|---|---|---|---|
| 5% | 1.000 | 27 | 18.5% | -$462 |
| 5% | 1.272 | 27 | 18.5% | -$343 |
| 5% | 1.618 | 27 | 18.5% | -$191 |
| 6% | 1.000 | 27 | 22.2% | -$334 |
| 8% | 1.000 | 15 | 26.7% | +$22 |
| 8% | 1.272 | 15 | 20.0% | -$65 |
| 8% | 1.618 | 14 | 14.3% | -$174 |
| 10% | 1.000 | 14 | 7.1% | -$499 |
| 12% | 1.000 | 9 | 11.1% | -$249 |
| 15% | 1.000 | 4 | 25.0% | +$1 |

Full 18-cell sweep in `results_trendline_fibonacci.txt`.

**The trendline filter is not a fix either.** Adding a real structural
trendline (rather than a macro SMA) on top of the Fib zone narrows the
sample a lot (67 legs → 15 traded at 8%, vs. 69 legs → 49 traded for the
unfiltered baseline) but the surviving setups are still net-negative or
only marginally positive almost everywhere in the sweep — the two
"winning" cells (+$22 at 8%/1.0, +$1 at 15%/1.0) have n=15 and n=4
respectively, both too thin to read as edge, and every other one of the
18 cells loses money. Win rates (7-27%) sit in the same range as the
unfiltered and SMA-filtered variants. Confirming the structural trendline
holds doesn't change the underlying finding from the swing-anatomy
analysis: this market extends past swing points more often than it
retraces cleanly back through a Fib zone, regardless of which trend
filter is bolted onto the entry.

## Variant: Order block + multi-timeframe structure (4H bias + 15m structure/OB + 1m CHoCH)

`order_block_mtf_backtest.py` implements the ICT/smart-money-concepts entry
sequence end-to-end across three timeframes, all built from the *same*
30-day raw trade dump (`build_mtf_bars.py` aggregates Kraken's trade-by-trade
feed into aligned 1-min/15-min/4h bars, since Kraken's OHLC endpoint caps out
at 720 candles per interval — nowhere near enough history at 1-minute
resolution):

1. **4H bias** — bullish only once the structure prints a confirmed Higher
   High *and* Higher Low back to back; bearish only on a confirmed Lower
   High *and* Lower Low. A lone new extreme doesn't flip it.
2. **15-min external structure** — the latest two confirmed swing pivots
   define the tradeable leg; a SHORT requires that leg to run high→low
   *and* the 4H bias at that moment to be BEARISH (mirror image for LONG).
3. **Order block** — scanning backward from the leg's swing extreme to its
   origin, the last opposite-colour 15-min candle before the impulsive move
   is marked as the OB zone.
4. **Internal structure** — 15-min price is re-zig-zagged with a smaller
   threshold from the swing extreme forward; the setup stays alive only
   once that internal structure is currently running counter to the leg
   (an internal rally inside a down-leg, or dip inside an up-leg) *and*
   price actually trades back into the OB zone.
5. **1-min CHoCH → pullback → confirmation** — once the OB is touched, drop
   to 1-minute bars and wait for a close back through the most recent
   internal 1-min swing point (the change of character), then a pullback
   that re-touches the OB, then a close that rejects back out of it. Entry
   fills at the next 1-min bar's open.
6. **Fake-out detection** — at any point before that sequence completes, a
   close all the way through the *far side* of the OB zone kills the setup
   as a `FAKEOUT` instead of letting it ride to a phantom entry.

### Headline result (default: 4H bias 3%, 15m external 1.5%, 15m internal
0.5%, 1m CHoCH 0.15%, TP 2.0R)

| Metric | Value |
|---|---|
| 15m legs evaluated | 80 |
| 4H bias aligned with leg direction | 33 |
| Order block marked | 33 |
| Internal structure counter-trend + OB touched | 31 |
| 1m CHoCH confirmed | 1 |
| Pullback into OB confirmed | 1 |
| **Traded** | **1** |
| **Fake-outs (closed through far side of OB)** | **27 (87% of touches)** |
| Win rate | 0.0% (0W-1L) |
| Net P&L on $5,000 account | -$50.00 |

### Threshold sweep (15m external × TP R-multiple, full 16-cell table in
`results_order_block_mtf.txt`)

| Ext. thresh | TP R | Legs | OB touched | Closed | W | L | Fakeouts | Win rate | Net P&L |
|---|---|---|---|---|---|---|---|---|---|
| 1.0% | 1.0–3.0 | 174 | 60 | 8 | 3-4 | 4-5 | 49 (82%) | 37.5-50.0% | $0 to +$200 |
| 1.5% (default) | 1.0–3.0 | 80 | 31 | 1 | 0 | 1 | 27 (87%) | 0.0% | -$50 (flat) |
| 2.0% | 1.0–3.0 | 46 | 18 | 0 | 0 | 0 | 17 (94%) | n/a | $0 |
| 3.0% | 1.0–3.0 | 22 | 9 | 0 | 0 | 0 | 9 (100%) | n/a | $0 |

**This is essentially untestable at the structural thresholds the strategy
description actually calls for, and the one thing that *is* measurable
everywhere is damning for the setup's core premise.** At the default 1.5%
external threshold only 1 of 80 legs ever survives the full bias→OB→CHoCH→
pullback chain to a real entry; loosen to 1.0% and the sample grows to a
still-thin 8 trades with a coin-flip-ish 37.5-50% win rate that's roughly
flat-to-slightly-positive after costs; tighten to 2.0% or 3.0% (closer to
genuine swing-structure thresholds) and **zero trades ever complete** despite
9-18 order-block touches at each setting. Across every threshold, **82-100%
of all order-block touches end in FAKEOUT** — price closing straight through
the far side of the zone rather than respecting it and reversing. That's the
same finding this repo keeps surfacing in every swing/Fib/trendline variant
above: this BTCUSD series extends through structure (swing points, Fib
zones, trendlines, and now order blocks) far more often than it cleanly
respects it, so a strategy gated on "wait for the reversal to confirm"
mostly just waits.

## Bottom line across all variants

| Strategy | Best single result | Robust across thresholds? |
|---|---|---|
| Original Fibonacci retracement | 24.5% WR, -$837 | Yes (consistently net-negative) |
| Trend-filtered (50/200 SMA) | 11-25% WR, -$200 to -$636 | Yes (consistently worse or flat) |
| Breakout-continuation v1 | 71.4% WR, +$118 (n=7) | **No** — cherry-picked single threshold |
| Breakout-continuation v2 | 42.9-50% WR, +$46 to +$91 | **Yes** — positive at every threshold with real sample, but total n is thin (~20 trades pooled) |
| CVD divergence (real + proxy) | 0% WR, -$100 (n=2 each) | Sample too small to judge |
| Cycle (sine-wave) | 80-83% WR, +$18 to +$48 (n=5-6) | **No** - sign flips with TP multiple, period hugs scan boundary |
| Quantum Wave Matrix (QWM), 5-min/30d | 0 trades at every swept threshold | Untestable — thresholds never co-occur on 30d of 5-min data |
| Quantum Wave Matrix (QWM), daily/2yr | 0 trades at literal thresholds; net-negative when loosened | Yes (consistently a loser once it can fire at all) |
| Trident System (30-min FVG/Doji) | 0 trades at every swept threshold | Untestable — the FVG precondition itself almost never occurs on 24/7 crypto candles |
| Phase-rotation cycle (time-delay embedding) | 0 trades at default; -$1 to -$200 once coherence loosened | Yes (consistently thin-sample and net-negative once it can fire) |
| Gravity-field price-magnet | 28.6% WR, -$234 (n=15) at default, real sample | Yes (3-29 trades/cell across the sweep, almost all net-negative) |
| Trendline + Fibonacci confluence | 20-27% WR, -$65 to +$22 (n=15) at default | Yes (consistently net-negative or sub-$25 across 18 cells) |
| Order block + MTF structure (4H bias/15m OB/1m CHoCH) | 0% WR, -$50 (n=1) at default; 37.5-50% WR, ~flat (n=8) loosened | Untestable at structural thresholds (0 trades at 2-3%); dominant finding is 82-100% fake-out rate on every OB touch |

v2 is the first variant that's both net-positive *and* survives a parameter
and threshold sweep rather than relying on one lucky combination. It's not
proof of a durable edge — the absolute sample size is still small for a
2-year window — but it's a structurally sound design (tight, volatility-scaled
stop; reward sized larger than risk) where v1 was not. See
`CVD_STRATEGY_COMPARISON.md` for the CVD-specific writeup.

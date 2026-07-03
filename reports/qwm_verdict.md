# "Quantum Wave Matrix (QWM)" playbook — tested verdict

Tested on 180 days of real Delta Exchange 5m data (BTCUSD, ETHUSD),
walk-forward split (120d in-sample / 60d out-of-sample), taker fees and
slippage included. Full implementation: `backtests/run_qwm_backtest.py`.

## What the playbook actually says, de-jargoned

Strip the vocabulary ("vector calculus", "quantum", "π-radial cycle") and
QWM is one old idea: **fade a vertical price spike at a range extreme,
with a stop just past the wick, targeting the range midpoint**, during
London/NY sessions. Counter-trend knife-catching with a tight stop.

Three technical observations before any backtest:

1. **The "vector angle" is not a well-defined quantity.** The angle of
   price over time depends entirely on the chart's axis scaling — 70° on
   one zoom level is 20° on another. We normalized it the only defensible
   way (price change per bar in ATR units; tan 70° ≈ 2.75 ATR/bar).
2. **Φ(t) = sin(ωt + φ) contains no price term.** It is a sine wave of
   *clock time*. Any signal derived from it is astrology. Tested
   faithfully anyway: combined with the other conditions it produced
   **zero trades in 180 days**.
3. **The advertised trade frequency is self-contradictory.** As written
   (70° spike + 99.5% range extreme + volume climax + session gate), the
   conditions co-occur 0–2 times in 120 days, not the claimed "10–15
   entries per asset per month."

## Results

Faithful implementation: ~no trades. So we loosened every threshold
(angle 30–45°, wider windows, 90–98% range extreme, volume z ≥ 0.5,
gates on/off) until it traded at the claimed frequency, and evaluated
every combination:

| Best cells from the grid | Trades | Win rate | Profit factor | Return |
|---|---|---|---|---|
| BTC, 30°/6-bar, 90% extreme, gated (in-sample) | 88 | 10.2% | 0.40 | −44.4% |
| BTC, same (out-of-sample) | 44 | 9.1% | 0.16 | −37.7% |
| ETH, best in-sample cell | 26 | 26.9% | 0.99 | −0.3% |
| ETH, same (out-of-sample) | 10 | 10.0% | 0.50 | −4.6% |

**Every one of 24 tested configurations lost money in every phase on both
symbols.** The claimed 1:5–1:12 reward:risk is real on paper — but it is
paid for with a ~10% win rate (breakeven at 1:9 *before* costs), because
the 0.5σ stop sits directly in the path of the momentum being faded.

## Why it fails (the mechanics)

A vertical spike is momentum. Momentum statistically *continues* over the
next bars more often than it reverses (this is the same fact that makes
56% of pullbacks fail in the fib research). QWM's design shorts directly
into that force with a stop placed inside its noise band. The math
symbols in the document do not change what the trade *is*.

## The general lesson

Complexity of language is not evidence of edge. Every claim that can be
made mechanical can be tested in an afternoon — and the strategies that
survive testing in this repo (confirmed sweep + order block; fib 0.618
with slow-pullback filter) are described in plain words, not calculus
costumes.

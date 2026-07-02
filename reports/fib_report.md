# Fibonacci ratios (0.618 / 1.618 / 2.618) — research & backtest

Generated: 2026-07-02 17:47 UTC

## Does 2.618 predict price? (path research)

Claim under test: price moves A->B, retraces to a fib level, then
extends to 1.272/1.618/2.618 of the move — an exact road-map.
Measured on 180 days of 5m data, 24-bar fractal swings:

**BTCUSD** — 1209 impulse legs: 56% of pullbacks failed (broke the leg origin); median pullback depth 0.59 of the leg. After continuation, the next run reached 1.272x: 53%, 1.618x: 42%, 2.618x: 23%.

**ETHUSD** — 1208 impulse legs: 56% of pullbacks failed (broke the leg origin); median pullback depth 0.60 of the leg. After continuation, the next run reached 1.272x: 51%, 1.618x: 43%, 2.618x: 26%.

Conclusions:

1. The 0.618 retracement is a decent *central estimate* — median
   pullback depth is ~0.60 — and pullback depths cluster mildly
   near fib levels (~19% within 0.04 of one vs ~14% by chance).
2. **2.618 is not a prediction.** Even after a successful
   continuation, price reaches 2.618x the leg only ~25% of the
   time (1.272x ~50%, 1.618x ~40%). It is the ~75th-percentile
   outcome, not a destination.
3. 56% of pullbacks never continue at all — which is why the raw
   pattern loses money and a trend filter is mandatory.

## Strategy (what survived auto-refinement)

Grid-searched entries (0.5/0.618), stops (0.886/1.0), targets
(1.272/1.618/2.618), swing sizes and filters, walk-forward
validated. Winner: limit entry at the **0.618 retracement**, stop
just beyond the leg origin, target the **1.618 extension** from the
fill, EMA200 trend filter. Note: **1.618 beat 2.618 as a target** —
the bigger extension simply doesn't happen often enough.

| symbol   | phase             |   trades |   trades_per_day |   win_rate_% |   profit_factor |   avg_win_$ |   avg_loss_$ |   total_return_% |   max_drawdown_% |
|:---------|:------------------|---------:|-----------------:|-------------:|----------------:|------------:|-------------:|-----------------:|-----------------:|
| BTCUSD   | full 180d         |      156 |             0.87 |         32.1 |            1.27 |       17.9  |        -6.63 |            19.21 |           -11.52 |
| BTCUSD   | in-sample 120d    |      105 |             0.88 |         32.4 |            1.35 |       18.24 |        -6.47 |            16.1  |           -11.25 |
| BTCUSD   | out-of-sample 60d |       51 |             0.85 |         31.4 |            1.13 |       17.19 |        -6.97 |             2.68 |            -4.89 |
| ETHUSD   | full 180d         |      153 |             0.85 |         28.8 |            1.05 |       15.3  |        -5.89 |             3.15 |           -10.81 |
| ETHUSD   | in-sample 120d    |      102 |             0.85 |         29.4 |            1.09 |       15.39 |        -5.86 |             3.97 |            -9.83 |
| ETHUSD   | out-of-sample 60d |       51 |             0.85 |         27.5 |            0.96 |       15.09 |        -5.93 |            -0.79 |            -6.6  |

![fib equity](fib_equity.png)

## Verdict

Validated positive on BTCUSD in both walk-forward phases with a
meaningful sample (~150 trades); ETHUSD is breakeven. This is a
probability edge from asymmetric risk:reward (risk 0.382 of a leg
to make 1.618), NOT an exact price-prediction system. Run it:

```bash
DELTA_STRATEGY=fib DELTA_SYMBOLS=BTCUSD python run_bot.py
```

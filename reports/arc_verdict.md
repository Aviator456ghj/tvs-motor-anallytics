# "ARC method" (Area–Range–Candle) — tested verdict

Source: video transcript, "The Stupid Simple A+ Trading Strategy I Use To
Make 1k/Day". Tested on 540 days of BTCUSD 15m Delta Exchange data,
walk-forward (360d in / 180d out), taker fees + slippage.
Implementation: `backtests/run_arc_backtest.py`.

## The method, faithfully summarized

To its credit, ARC is coherent and fully mechanical (unlike the "QWM"
document) :

- **Area**: previous day's high/low ("box") + the nearest older daily
  high above / low below ("swing high/low"). Sell only at the top pair,
  buy only at the bottom pair, never trade the middle.
- **Range**: R = box height. Precondition: an "unabated move" ≥ 20% of R.
  Target: 50–100% of R.
- **Candle**: hammer-style rejection at the level, entry when the next
  candle takes out its extreme, stop under the rejection wick.

## Results — every configuration loses

| Variant (15m) | PF in / out | Return in / out |
|---|---|---|
| 50% target | 0.65 / 0.64 | −27% / −16% |
| 75% target | 0.68 / 0.74 | −25% / −11% |
| 100% target | 0.74 / 0.88 | −21% / −5% |
| box levels only | 0.68 / 0.65 | −19% / −11% |
| strict / loose wick | 0.69 / 0.58 · 0.66 / 0.71 | all negative |
| + 20–30% impulse precondition | 0.50–0.69 | all negative (worse) |

Ten configurations, twenty walk-forward cells, **zero positive**. Win
rates 26–35% — nowhere near the video's implication — with sub-1 payoff.

## Why it fails on crypto

1. **"Previous day" is an equity concept.** Stocks have session opens,
   auction gaps, and day-trader anchoring that give yesterday's high/low
   real order-flow meaning. Bitcoin trades 24/7 — a UTC midnight
   boundary is arbitrary, so the "box" is a weak liquidity anchor.
2. **It fades levels without trend context** — the same counter-trend
   trap we measured in QWM and the raw sweep tests. Every level "holds"
   until the day it doesn't, and that day pays for the demo wins.
3. **The video's evidence is chart reads plus one live trade.** Nine
   bounces circled in hindsight on a ranging NVDA chart is selection,
   not a sample.

## What ARC gets right (and where we already use it, stronger)

The healthy parts of ARC are already in this repo in validated form:
rejection-candle confirmation at a liquidity level (our golden-zone
red→green trigger), "as long as the level holds the trade is valid"
(our structural stop below A), and range-derived targets (our fib
extensions). The difference: our anchors come from **market structure**
(CHoCH swings, where a trend actually changed) rather than the calendar
— and those versions passed walk-forward while ARC did not.

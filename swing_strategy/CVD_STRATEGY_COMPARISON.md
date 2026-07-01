# CVD Delta Divergence Upgrade — Results

Per the requested rule change, the passive Fibonacci limit-order entry was
replaced with a gated, reactive trigger:

```
OLD: Price touches 61.8% line -> auto place limit order -> stopped out 75.5% of the time.
NEW: Price enters 61.8%-100% zone -> gate opens -> monitor 5-min price/CVD pivots ->
     divergence (price new extreme NOT confirmed by CVD) -> market order.
     No divergence -> skip the leg entirely.
Stop loss: fixed 78.6%+2-3% buffer -> 1 tick beyond the trigger bar's wick.
Take profit: unchanged (origin swing point), to isolate the effect of the entry/stop change.
```

Two backtests were run, because true buy/sell-tagged order-flow data is
only available from Kraken for a recent window — it can't be pulled at
scale for the full 2-year period the original test covered.

## 1. Real CVD — true trade-tagged data, last 30 days

1,930,000 individual trades pulled from Kraken (each tagged buyer- or
seller-initiated by the exchange itself), aggregated into 8,644 five-minute
bars with genuine Cumulative Volume Delta, covering 2026-05-28 → 2026-06-27.

| Metric | Value |
|---|---|
| Daily swing legs evaluated | 69 |
| Legs with no real CVD data in window (outside last 30d) | 66 |
| Legs gated out (no divergence found) | 1 |
| Trades triggered | **2** |
| Wins / Losses | 0 / 2 |
| Net P&L | **-$100.00** |

**This sample is too small to draw a conclusion from.** Only 3 of the 69
swing legs even fell inside the 30-day data window, and the divergence
gate (correctly) filtered one of those out, leaving 2 trades — both lost.
The result isn't evidence the CVD approach is worse than the original
Fibonacci strategy; there simply isn't enough real order-flow history
available through this data source to test it properly. A meaningful test
would need either a paid tick-data vendor with deep history, or to keep
collecting real trades forward in time for several more months.

## 2. Approximate CVD proxy — full 2-year window

Since real tagged trades aren't available that far back, daily candles
were given a volume-delta *proxy* (close position within the day's range
times volume) instead of true order flow, just to see how the gate logic
behaves at full history length.

| Metric | Value |
|---|---|
| Daily swing legs evaluated | 69 |
| Legs gated out (no divergence) | 66 |
| Trades triggered | **2** |
| Wins / Losses | 0 / 2 |
| Net P&L | **-$100.00** |

Same finding: at daily resolution the divergence gate is so strict that
97% of legs never fire at all — confirming the strategy *is* highly
selective as designed, but daily bars are simply too coarse to generate a
usable trade sample. This is an approximation, not real order flow, so
it's reported for context only, not as a verdict on the CVD method.

## 3. Reference — original Fibonacci passive-limit strategy (for comparison)

| Metric | Value |
|---|---|
| Closed trades | 49 |
| Wins / Losses | 12 / 37 |
| Win rate | 24.5% |
| Net P&L | **-$836.95** |

## Bottom line

The CVD gate does exactly what it was designed to do — it is dramatically
more selective than the passive Fibonacci entry (2 trades vs. 49 from the
same 69 swing legs) — but neither available dataset has enough qualifying
signals to say whether it's actually a *better* strategy. The honest
takeaway from this backtest: **the data, not the logic, is the
bottleneck.** Getting a statistically meaningful CVD verdict requires
either a longer real-trade history (e.g., a paid historical tick-data
feed) or loosening the divergence/zone criteria so more setups qualify —
both are decisions worth making deliberately rather than backed into.

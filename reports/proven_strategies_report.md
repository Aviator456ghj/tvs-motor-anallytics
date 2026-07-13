# Proven day-trading strategies vs real BTCUSD data

15m candles, last 180 days from Delta Exchange India (1768410000 -> 1783961100, 17280 bars).

Walk-forward: first 60% in-sample, last 40% out-of-sample. Fixed 2% risk/trade, 1.5x ATR stop, 2.0R target, cost 0.110%/round-trip (same cost model as the rest of this repo). **Judge every strategy by its out-of-sample (OOS) column — in-sample numbers are shown only to reveal overfitting gaps.**

| Strategy | IS trades | IS WR | IS PF | IS ret | IS maxDD | OOS trades | OOS WR | OOS PF | OOS ret | OOS maxDD |
|---|---|---|---|---|---|---|---|---|---|---|
| VWAP Reversion (daily) | 440 | 30% | 0.70 | -92.0% | -92.7% | 258 | 33% | 0.69 | -70.5% | -72.8% |
| RSI(14) 30/70 Reversion | 240 | 30% | 0.66 | -78.8% | -79.6% | 149 | 32% | 0.59 | -61.8% | -61.8% |
| Bollinger(20,2) Reversion | 440 | 30% | 0.60 | -96.3% | -96.7% | 284 | 31% | 0.55 | -88.5% | -89.1% |
| EMA 9/21 Crossover | 427 | 31% | 0.47 | -94.1% | -94.1% | 299 | 28% | 0.48 | -94.7% | -94.7% |
| MACD(12,26,9) Crossover | 484 | 33% | 0.62 | -92.1% | -92.3% | 360 | 27% | 0.46 | -97.2% | -97.2% |
| Donchian(20) Breakout | 399 | 34% | 0.70 | -86.1% | -87.1% | 282 | 28% | 0.43 | -92.7% | -93.0% |
| Opening Range Breakout 30m | 42 | 19% | 0.35 | -42.2% | -42.2% | 23 | 22% | 0.39 | -25.6% | -31.1% |

**PF (profit factor) = gross win / gross loss. PF < 1.0 means the strategy lost money after real costs. A strategy needs OOS PF meaningfully above 1 AND a reasonable trade count to mean anything — a handful of OOS trades is not a validated edge either way.**

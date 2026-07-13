# Daily MACD bias -> 1H 50EMA pullback -> 15m MSS — literal recipe, cross-asset

Daily MACD(12,26,9) bias, 1H 50 EMA pullback zone, 15m MSS confirmation, 1% risk/trade, dead-zone filter (no entries 00:00-07:00 UTC), fixed 2R target, last 365 days, tested on BTCUSD, ETHUSD, SOLUSD, XRPUSD.

**Disclosed conventions:** entry fills at the next 15m bar's open after the structure-shift candle closes (this repo's standard no-lookahead rule — you can't pre-place a limit at a candle's open before its close is what makes it 'the' structural candle). Stop tested both literally ($15) and at a realistic 0.15% buffer, same reasoning as the other two literal tests. Daily bias uses the most recently CLOSED daily candle, never the forming one.

Walk-forward: 60% in-sample / 40% out-of-sample by time, cost 0.110%/round-trip, 1% risk/trade (as literally specified, not this repo's usual 2%).

| Symbol | Stop buffer | IS trades | IS WR | IS PF | IS ret | OOS trades | OOS WR | OOS PF | OOS ret | OOS maxDD |
|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSD | literal $15 | 97 | 31% | 0.71 | -19.5% | 60 | 37% | 0.97 | -1.1% | -7.1% |
| BTCUSD | realistic 0.15% | 88 | 31% | 0.68 | -18.8% | 59 | 37% | 1.00 | +0.2% | -5.4% |
| ETHUSD | literal $15 | 73 | 38% | 1.03 | +1.5% | 45 | 47% | 1.34 | +8.1% | -3.5% |
| ETHUSD | realistic 0.15% | 79 | 37% | 0.93 | -3.6% | 53 | 47% | 1.24 | +8.1% | -7.6% |
| SOLUSD | literal $15 | 58 | 41% | 0.63 | -4.9% | 38 | 50% | 0.76 | -0.7% | -1.3% |
| SOLUSD | realistic 0.15% | 85 | 27% | 0.60 | -22.1% | 52 | 35% | 0.76 | -8.6% | -15.3% |
| XRPUSD | literal $15 | 57 | 51% | 0.63 | -0.1% | 40 | 30% | 0.41 | -0.0% | -0.0% |
| XRPUSD | realistic 0.15% | 83 | 35% | 0.80 | -10.7% | 63 | 22% | 0.50 | -23.4% | -25.6% |

**Pooled: 620 in-sample trades, 410 out-of-sample trades across all 4 assets x 2 stop variants (pooled OOS win rate 37%).**

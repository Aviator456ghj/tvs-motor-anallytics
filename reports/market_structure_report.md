# Market-structure scalping — backtest report

Generated: 2026-07-02 16:50 UTC

Mechanical 'smart money' entry models tested on 180 days of 5m
Delta Exchange data (in-sample = first 120 days, out-of-sample = last
60), with maker/taker fees and slippage:

- **sweep + CHoCH (market)** — 1h swing low/high swept by a wick that
  closes back inside, confirmed by a close beyond the sweep bar's local
  extreme; taker entry at the next bar open.
- **sweep confirmed + order block** — adds (a) a fakeout-quality filter:
  the wick beyond the level must be >= 50% of the sweep bar's range, and
  (b) a LIMIT entry at the sweep bar's body edge (the order block),
  filled only on a retest. Better price, maker fee, tighter stop.
  This is what `DELTA_STRATEGY=structure` trades.
- **BOS retest** — close through a confirmed swing level, limit entry on
  the retest of the broken level; stop beyond the last opposite swing.

Stops always sit at the sweep extreme — the exact price where the trade
idea is invalidated. Targets at 2R. The baseline trend-pullback runs its
usual 15m rules on the same 180 days.

| symbol   | strategy                      | phase             |   trades |   trades_per_day |   win_rate_% |   profit_factor |   avg_win_$ |   avg_loss_$ |   total_return_% |   max_drawdown_% |
|:---------|:------------------------------|:------------------|---------:|-----------------:|-------------:|----------------:|------------:|-------------:|-----------------:|-----------------:|
| BTCUSD   | trend-pullback (baseline)     | full 180d         |      218 |             1.21 |         34.9 |            0.83 |        7.91 |        -5.13 |           -12.72 |           -18.23 |
| BTCUSD   | trend-pullback (baseline)     | in-sample 120d    |      150 |             1.25 |         31.3 |            0.71 |        8.14 |        -5.26 |           -15.88 |           -18.03 |
| BTCUSD   | trend-pullback (baseline)     | out-of-sample 60d |       68 |             1.13 |         42.6 |            1.17 |        7.53 |        -4.79 |             3.75 |            -3.14 |
| BTCUSD   | sweep + CHoCH (market)        | full 180d         |      149 |             0.83 |         38.9 |            0.67 |        5.37 |        -5.1  |           -15.26 |           -16.93 |
| BTCUSD   | sweep + CHoCH (market)        | in-sample 120d    |      115 |             0.96 |         37.4 |            0.73 |        6.26 |        -5.1  |            -9.81 |           -14    |
| BTCUSD   | sweep + CHoCH (market)        | out-of-sample 60d |       34 |             0.57 |         44.1 |            0.44 |        2.84 |        -5.11 |            -6.04 |            -6.87 |
| BTCUSD   | sweep confirmed + order block | full 180d         |       31 |             0.17 |         35.5 |            0.69 |        7.69 |        -6.13 |            -3.8  |            -3.93 |
| BTCUSD   | sweep confirmed + order block | in-sample 120d    |       26 |             0.22 |         34.6 |            0.68 |        7.86 |        -6.16 |            -3.4  |            -3.75 |
| BTCUSD   | sweep confirmed + order block | out-of-sample 60d |        5 |             0.08 |         40   |            0.77 |        6.91 |        -5.95 |            -0.42 |            -1.82 |
| BTCUSD   | BOS retest                    | full 180d         |      908 |             5.04 |         34.7 |            0.58 |        2.86 |        -2.6  |           -64.08 |           -64.58 |
| BTCUSD   | BOS retest                    | in-sample 120d    |      614 |             5.12 |         35.7 |            0.6  |        3.29 |        -3.03 |           -47.44 |           -47.44 |
| BTCUSD   | BOS retest                    | out-of-sample 60d |      294 |             4.9  |         32.7 |            0.52 |        1.87 |        -1.75 |           -31.67 |           -32.61 |
| ETHUSD   | trend-pullback (baseline)     | full 180d         |      257 |             1.43 |         35.8 |            0.93 |        9.07 |        -5.46 |            -6.53 |           -13.09 |
| ETHUSD   | trend-pullback (baseline)     | in-sample 120d    |      171 |             1.43 |         35.7 |            0.94 |        9.14 |        -5.4  |            -3.61 |           -10.86 |
| ETHUSD   | trend-pullback (baseline)     | out-of-sample 60d |       86 |             1.43 |         36   |            0.9  |        8.94 |        -5.57 |            -3.03 |            -7.03 |
| ETHUSD   | sweep + CHoCH (market)        | full 180d         |      209 |             1.16 |         39.7 |            0.86 |        6.53 |        -4.98 |            -8.55 |           -11.36 |
| ETHUSD   | sweep + CHoCH (market)        | in-sample 120d    |      147 |             1.23 |         40.8 |            0.88 |        6.44 |        -5.02 |            -5.06 |           -10.75 |
| ETHUSD   | sweep + CHoCH (market)        | out-of-sample 60d |       62 |             1.03 |         37.1 |            0.82 |        6.77 |        -4.89 |            -3.68 |            -4.88 |
| ETHUSD   | sweep confirmed + order block | full 180d         |       42 |             0.23 |         52.4 |            1.42 |        7.63 |        -5.92 |             4.94 |            -3.16 |
| ETHUSD   | sweep confirmed + order block | in-sample 120d    |       29 |             0.24 |         51.7 |            1.28 |        7.26 |        -6.09 |             2.37 |            -3.16 |
| ETHUSD   | sweep confirmed + order block | out-of-sample 60d |       13 |             0.22 |         53.8 |            1.77 |        8.42 |        -5.55 |             2.51 |            -1.36 |
| ETHUSD   | BOS retest                    | full 180d         |     1006 |             5.59 |         35.7 |            0.64 |        3.13 |        -2.71 |           -62.97 |           -64.31 |
| ETHUSD   | BOS retest                    | in-sample 120d    |      672 |             5.6  |         36.2 |            0.64 |        3.56 |        -3.17 |           -49.61 |           -50.49 |
| ETHUSD   | BOS retest                    | out-of-sample 60d |      334 |             5.57 |         34.7 |            0.66 |        2.23 |        -1.8  |           -26.51 |           -29.59 |

![comparison](structure_comparison.png)

## Verdict

Confirmation quality and entry location matter more than the pattern:

1. The raw sweep+CHoCH market entry **loses after fees** on both
   symbols, as does the BOS retest.
2. Adding the wick (fakeout) filter and moving the entry to the order
   block **flips ETHUSD positive in BOTH the in-sample and
   out-of-sample windows** and pulls BTCUSD to roughly breakeven.
   Three effects combine: fewer, higher-quality traps; a better entry
   price on the retest; and maker instead of taker fees.
3. **Trade counts are small** (tens of trades, not hundreds), so this
   edge is not statistically settled. Paper-trade it before believing it.

Run it (paper mode; the 5m timeframe is selected automatically):

```bash
DELTA_STRATEGY=structure DELTA_SYMBOLS=ETHUSD python run_bot.py
```

# Replicating a Claude+Jesse-MCP autonomous strategy-development video, on real Delta Exchange data

Source: a user-provided video demonstrating Claude Code connected via MCP to the open-source Jesse algo-trading framework, given one autonomous prompt: find two trend-following BTC/ETH/SOL strategies (long+short, 3% risk/trade, hourly) with Sharpe > 1 over 4 years, validated with an entry-rule significance test, hyperparameter-optimized, and Monte Carlo stress-tested. Reported result there: TFAtrExitBreakout Sharpe 1.53, TFTrailBreakout Sharpe 1.06 (Binance Perpetual Futures, 2022-07-01 to 2026-06-29).

This replicates the exact entry rule (Bollinger Band breakout + EMA trend filter), exit logic (ATR-fixed vs ATR-trailing), position sizing (3% equity risk/trade, 10%-equity notional cap), and validation pipeline (significance test -> grid optimization -> Monte Carlo) — on **real Delta Exchange India data**, which only has ~2.3 years of common BTC/ETH/SOL history (SOLUSD-limited), not 4 — and adds an in-sample/out-of-sample split around optimization, which the video's own dashboard never showed. Real numbers, not a re-derivation of the video's.

## Strategy 1: trend-following, trailing-stop exit

Best grid params: `{'bb_period': 20, 'bb_dev': 2.5, 'ema_period': 200, 'stop_mult': 2.0, 'exit_mult': 3.0}`

| Segment | Sharpe | Net profit | Max DD | Trades |
|---|---|---|---|---|
| In-sample (70%) | 1.70 | — | — | — |
| Out-of-sample (30%) | -0.35 | -0.5% | -2.1% | 342 |
| Full period (video's own methodology) | 1.14 | +5.9% | -2.4% | 1057 |

**Entry-rule significance test:** real combined Sharpe 1.14 vs. 300 random-entry permutations (same exit logic, same trade count) — null mean -0.56, **p=0.003** (PASSES the video's own bar of 'genuine statistical significance').

**Monte Carlo (200 trade-order resamples):** Sharpe — worst 5% 0.17, median 1.64, best 5% 3.21. Net profit — worst 5% +0.5%, median +5.6%.

**Verdict (out-of-sample Sharpe>1 AND entry significance passes): NOT MET**

## Strategy 2: trend-following, ATR fixed stop/target exit

Best grid params: `{'bb_period': 30, 'bb_dev': 2.5, 'ema_period': 100, 'stop_mult': 1.5, 'exit_mult': 2.0}`

| Segment | Sharpe | Net profit | Max DD | Trades |
|---|---|---|---|---|
| In-sample (70%) | 1.65 | — | — | — |
| Out-of-sample (30%) | 0.90 | +0.9% | -1.3% | 435 |
| Full period (video's own methodology) | 1.43 | +5.1% | -1.5% | 1418 |

**Entry-rule significance test:** real combined Sharpe 1.43 vs. 300 random-entry permutations (same exit logic, same trade count) — null mean -1.89, **p=0.000** (PASSES the video's own bar of 'genuine statistical significance').

**Monte Carlo (200 trade-order resamples):** Sharpe — worst 5% 0.60, median 2.23, best 5% 3.78. Net profit — worst 5% +1.4%, median +5.3%.

**Verdict (out-of-sample Sharpe>1 AND entry significance passes): NOT MET**

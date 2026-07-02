# Delta Exchange 24/7 Scalping Agent

An automated scalping agent for **Delta Exchange India** perpetual futures
(BTCUSD by default). It scans the market continuously, trades a
trend-pullback strategy with ATR-scaled stops/targets, and enforces strict
risk limits. It runs in **paper-trading mode by default** — it will never
touch real money unless you explicitly enable live mode.

> ## ⚠️ Read this first — an honest note about profitability
>
> Every strategy here was validated on real Delta Exchange data with
> realistic fees and slippage, using walk-forward (in-sample /
> out-of-sample) splits. The headline results:
>
> - **trend-pullback** (default): mildly positive on BTCUSD over the last
>   60 days, but **negative over the full 180 days** — its edge is
>   window-dependent.
> - **structure** (confirmed liquidity sweep + order-block entry, plus
>   failure-derived filters): the only strategy positive on BOTH symbols
>   over 180 days — **BTCUSD +3.1% / ETHUSD +4.8%, ~60% win rate, profit
>   factor ~2.0, max drawdown < 1.5%** — but it is very selective
>   (~1 trade/week/symbol; 35 trades total), so the edge is not
>   statistically settled.
>
> - **fib** (0.618-retracement entry, 1.618-extension target, EMA200 trend
>   filter): **BTCUSD +19.2% over 180 days (PF 1.27, 156 trades), positive
>   in both walk-forward phases**; ETHUSD roughly breakeven. The biggest
>   sample in the repo, but a 32% win rate means long losing streaks are
>   normal — the payoff comes from ~4:1 reward:risk.
>
> **No strategy wins every trade.** Scalping crypto after fees is brutally
> hard; treat this as a research platform with good risk hygiene, not a
> money printer. Full numbers:
> [`reports/performance_report.md`](reports/performance_report.md),
> [`reports/market_structure_report.md`](reports/market_structure_report.md)
> and [`reports/fib_report.md`](reports/fib_report.md).

## What it does

Every 15-minute candle close, for each configured symbol:

1. **Scan** — fetches closed candles from Delta's public API.
2. **Signal** — trend-pullback logic:
   - *Long*: EMA20 > EMA50, close > EMA100, and RSI(14) crosses back **up**
     through 45 (a pullback resolving in the trend's direction).
   - *Short*: mirror conditions, RSI crossing back **down** through 55.
   - *Volatility filter*: skip the trade unless the stop distance is at
     least **3× the round-trip trading cost** — fees are what kill scalpers.
3. **Risk check** — the trade is only allowed if:
   - risk per trade ≤ 0.5% of equity (position sized from the stop distance),
   - leverage ≤ 3×,
   - daily realized loss < 2% (otherwise no trades until tomorrow),
   - fewer than 5 consecutive losses (otherwise a 6-hour cool-off).
4. **Execute** — paper mode simulates fills locally; live mode places a
   limit entry with **bracket stop-loss and take-profit orders** so the
   exchange enforces your exits even if the bot goes offline.
5. **Exit** — stop-loss at 1.5×ATR, take-profit at 2.5R, or a time-based
   exit after 8 hours.

## Quick start (paper trading — safe)

```bash
pip install -r requirements.txt
python run_bot.py
```

No credentials needed for paper mode. State persists in
`scalper_state_paper.json`, logs in `scalper.log`. Leave it running 24/7
(e.g. under `tmux`, `systemd`, or Docker).

## Alternative strategy: confirmed market-structure entries

`DELTA_STRATEGY=structure` trades the classic "smart money" scalp with
exact, mechanical entry/exit points and a confirmation stack:

1. a 1h swing low/high gets **swept** by a wick that closes back inside
   (a stop-hunt / liquidity grab);
2. **fakeout quality**: the wick beyond the level must be ≥ 50% of the
   sweep bar's range — a real rejection, not a graze;
3. a **change-of-character** close beyond the sweep bar's local extreme
   confirms the reversal;
4. entry is a **limit order at the order block** (the sweep bar's body
   edge) — filled only on a retest, which means a better price, maker
   fees, and a tighter stop;
5. stop at the sweep extreme (the exact invalidation price), target 2R,
   the unfilled limit cancels after 12 bars;
6. **failure filters** learned from the trade post-mortem (below): the
   sweep bar must carry at least average volume, and the structure must
   be at least 0.45% deep.

Head-to-head backtest over 180 days
([`reports/market_structure_report.md`](reports/market_structure_report.md)):
the raw sweep entry and BOS-retest lose after fees; the confirmed
order-block version with failure filters is the best performer in the
repo — positive on both symbols in a small sample. Paper-trade it first:

```bash
DELTA_STRATEGY=structure DELTA_SYMBOLS=ETHUSD python run_bot.py
```

## Third strategy: Fibonacci retracement/extension ("the 2.618 idea", tested)

`DELTA_STRATEGY=fib` trades the classic fib road-map — impulse A→B,
pullback to a retracement, extension target — after testing what the
ratios actually deliver ([`reports/fib_report.md`](reports/fib_report.md)):
the 0.618 retracement is a good central estimate of pullback depth, but
**2.618 is not a prediction** — price reaches it in only ~25% of
continuations, and 56% of pullbacks fail outright. The validated rules:
limit entry at the 0.618 retracement of a 2h swing leg, stop just beyond
the leg origin, take-profit at the **1.618** extension (which beat 2.618
in the grid), EMA200 trend filter.

```bash
DELTA_STRATEGY=fib DELTA_SYMBOLS=BTCUSD python run_bot.py
```

## Learning from losing trades (the journal)

Winners tell you what worked; losers tell you what to stop doing. Every
trade the bot closes (paper or live) is appended to `trade_journal.csv`
together with the setup context it was taken in — sweep volume ratio,
wick quality, structure depth, trend alignment, stop size. Re-run the
post-mortem any time:

```bash
python backtests/analyze_journal.py
```

The backtest post-mortem found losers clustered in three situations —
low-volume sweeps (29% win rate), structures tighter than 0.45% (35%),
and retests arriving late (41%). The first two became default filters
(`ms_vol_ratio`, `ms_min_stop_pct`) after verifying they improved BOTH
walk-forward phases; the third is available by tightening `ms_wait_bars`.
When the journal accumulates new failure clusters, tighten the matching
config filter — that is the refinement loop.

## Reproduce the backtest / performance report

```bash
python backtests/run_backtest.py
```

Downloads 60 days of 15m candles and regenerates
`reports/performance_report.md`, `reports/equity_curve.png`, and per-trade
CSVs using the exact same strategy code the bot trades.

## Going live (only after paper validation)

1. Create an API key at Delta Exchange India with **trading** permission
   (never share it; restrict by IP if possible).
2. Copy `.env.example`, fill in your key/secret, and export the variables.
3. Run paper mode for **2–4 weeks**. Compare results with the backtest.
4. Only if paper tracks the backtest:

```bash
export DELTA_API_KEY=... DELTA_API_SECRET=...
DELTA_LIVE=1 python run_bot.py   # asks for explicit confirmation
```

Start with the smallest size the exchange allows.

## Configuration

Everything is tunable via environment variables — see
[`.env.example`](.env.example). Strategy parameters live in
[`delta_scalper/config.py`](delta_scalper/config.py).

## Project layout

```
delta_scalper/
  config.py        env-driven configuration + safety validation
  delta_client.py  Delta Exchange v2 REST client (HMAC-signed)
  indicators.py    EMA / RSI / ATR
  strategy.py      trend-pullback signal logic
  risk.py          sizing, daily loss limit, loss-streak kill switch
  paper.py         paper-trading broker (default mode)
  bot.py           24/7 main loop
backtests/
  run_backtest.py  reproducible walk-forward backtest + report generator
reports/           performance report, equity curve, trade logs
run_bot.py         entry point
```

## Disclaimer

This software is for educational and research purposes. Crypto derivatives
are extremely risky and most retail scalpers lose money. Past backtest
performance does not guarantee future results. You are solely responsible
for any live trading you enable.

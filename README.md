# Delta Exchange 24/7 Scalping Agent

An automated scalping agent for **Delta Exchange India** perpetual futures
(BTCUSD by default). It scans the market continuously, trades a
trend-pullback strategy with ATR-scaled stops/targets, and enforces strict
risk limits. It runs in **paper-trading mode by default** — it will never
touch real money unless you explicitly enable live mode.

> ## ⚠️ Read this first — an honest note about profitability
>
> This agent was built and validated on 60 days of real Delta Exchange data
> with realistic fees and slippage. The result: **the edge is small and
> unstable**. BTCUSD was mildly profitable both in-sample (+2.4%, profit
> factor 1.17) and out-of-sample (+0.4%, PF 1.04); ETHUSD lost money and is
> disabled by default. **No strategy wins every trade** — this one wins
> ~40% of trades and relies on winners being ~2.5x bigger than losers.
> Scalping crypto after fees is brutally hard; treat this as a research
> platform with good risk hygiene, not a money printer.
> Full numbers: [`reports/performance_report.md`](reports/performance_report.md).

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

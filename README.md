# Multi-Broker Scalping Agent (Delta Exchange India + Zerodha Kite)

A **rule-based** (no LLM, no ML) automated scalping agent that streams live
market data, detects micro-signals the instant they form, and enters/exits
trades automatically across two brokers:

- **Delta Exchange India** (crypto perpetuals/futures)
- **Zerodha Kite** (NSE / NFO / MCX)

> ⚠️ **Security notice:** earlier commits in this repo's history contained live
> API credentials in `README.md`. **Those keys must be revoked and regenerated
> in the broker dashboards** — deleting them from the file does not remove them
> from git history. All secrets now live in a git-ignored `.env` file.

> ⚠️ **Reality check:** no system can act *before* price moves — that would be
> predicting the future. This agent reacts to micro-signals (order-book
> imbalance, momentum bursts, EMA/VWAP) with millisecond latency, trading *with*
> the move. Scalping is hard to keep profitable after fees and slippage. The
> agent runs in **paper (simulated) mode by default** — validate before going live.

---

## How it works

```
 broker websocket ──▶ MarketState (ticks + rolling bars + order book)
                            │
                            ▼
                    MicroScalper strategy   ← pure technical rules
                    (order-book imbalance + momentum + EMA + volatility gate)
                            │  Signal(ENTER/EXIT/HOLD)
                            ▼
                      RiskManager            ← sizing, TP/SL/trailing/time-stop,
                            │                  daily loss & trade-count caps
                            ▼
                    Broker.place_order / close_position
```

- **`trading_agent/brokers/`** — common `Broker` interface + `delta`, `zerodha`,
  a `paper` wrapper (live data, simulated fills), and an offline `simulator`.
- **`trading_agent/strategy/`** — `MicroScalper` and pure-function `indicators`.
- **`trading_agent/risk/`** — `RiskManager` (the safety layer).
- **`trading_agent/engine/`** — the per-broker decision loop.
- **`config.yaml`** — all tunable parameters. **`.env`** — all secrets.

### Entry logic (all must agree on direction)
1. **Order-book imbalance** beyond `ob_imbalance_threshold`.
2. **Momentum burst** > `momentum_threshold_pct` over `momentum_lookback` ticks.
3. **EMA trend filter** (`ema_fast` vs `ema_slow`) confirms direction.
4. **Volatility gate** — skip dead/choppy markets below `min_atr_pct`.

### Exit logic (RiskManager)
Take-profit, stop-loss, trailing stop, a hard time-stop, or a strategy reversal
signal — whichever fires first.

---

## Quick start

```bash
pip install -r requirements.txt

# 1) Verify the logic with unit tests (no creds, no internet)
python tests/test_core.py

# 2) Watch the full engine trade on synthetic data
python run_simulation.py 20

# 3) Configure for real brokers
cp .env.example .env       # then edit .env with your NEW (rotated) keys
#    edit config.yaml to enable brokers / pick symbols / tune risk

# 4) Run in PAPER mode (default — simulated orders, live data)
python -m trading_agent.main

# 5) Only when you trust it: LIVE mode (sends real orders!)
TRADING_MODE=live python -m trading_agent.main
```

### Zerodha access token
Kite needs a daily access token. Set `KITE_API_KEY`/`KITE_API_SECRET` in `.env`,
run the agent once to print the login URL, complete login, then put the resulting
token in `KITE_ACCESS_TOKEN`. (A `kite__login` MCP flow is also available.)

---

## Safety defaults
- `TRADING_MODE=paper` until you explicitly set `live`.
- Per-trade risk capped at `risk_per_trade_pct` of allocated capital.
- `max_daily_loss_pct` halts trading for the day when breached.
- `max_trades_per_day` and `max_open_positions` limit exposure.
- Positions are flattened on shutdown (Ctrl+C) — no scalps left open.

## Disclaimer
For educational use. Automated trading carries substantial risk of loss. You are
solely responsible for your capital, your keys, and complying with your brokers'
and local regulations. Test thoroughly in paper mode first.

# 24/7 Trading Agent — free to run, your exact tested settings

`run_agent.py` launches the repo's scalping bot (`delta_scalper/bot.py`)
with one of five presets — the **exact** settings from the Strategy Test
Bench console runs you validated by hand (BTC + ETH screenshots). It is
plain Python: no AI calls, no subscription, no hosting fee. It watches
Delta Exchange India candle-by-candle and trades automatically, 24/7, on
any always-on machine you already own.

## Quick start

```bash
pip install -r requirements.txt        # once
python agents/run_agent.py --list      # see all presets
python agents/run_agent.py btc-choch-100        # paper mode (default)
```

Keep it running after you close the terminal (Linux / Mac / Termux):

```bash
nohup python agents/run_agent.py btc-choch-100 > agent_btc_choch.log 2>&1 &
```

Run several presets at once — each in its own process (they keep separate
state files automatically):

```bash
nohup python agents/run_agent.py btc-choch-100  > a1.log 2>&1 &
nohup python agents/run_agent.py eth-choch-50   > a2.log 2>&1 &
```

## The presets

| Preset | Strategy / TF | Screenshot result | Max drawdown |
|---|---|---|---|
| `btc-orderblock-15` | Order Block, BTC 1h, 15% risk, 200x | 106 tr, PF 1.28, +3,076% | **-77.0%** |
| `btc-choch-100` | CHoCH ride, BTC 1h, 100% risk, 200x | 27 tr, PF 6.93, +18,552% | **-55.2%** |
| `btc-riley-24` | Riley v2+P2, BTC 15m, 24% risk, 200x | 89 tr, PF 1.09, +19,773% | **-89.5%** |
| `eth-choch-50` | CHoCH ride, ETH 1h, 50% risk, 200x | 26 tr, PF 9.53, +51,270% | **-74.7%** |
| `eth-riley-26` | Riley v2+P2, ETH 15m, 26% risk, 200x | 101 tr, PF 1.05, +100,501% | **-89.9%** |

The ETH Swing Catcher screenshot (k=8, stop buffer 0.0001×ATR) is **not**
included: a near-zero stop buffer makes risk-based sizing degenerate —
every trade just hits the 200x leverage cap, so "15% risk" doesn't
describe what it actually does (max-leverage sizing on a PF 1.08 edge,
-86.6% max DD). Ask if you want it added anyway.

## Paper vs live — read this

- **Paper (default):** simulated fills against real live prices. All five
  presets run as-is. This is where you confirm the agent behaves like the
  backtest before any real money.
- **Live (`DELTA_LIVE=1` + `DELTA_API_KEY`/`DELTA_API_SECRET`):** the bot
  **refuses** any preset with risk > 2% per trade — that cap is deliberate
  and stays. The huge screenshot returns and the -55% to -90% drawdowns
  are the *same* position-sizing coin, flipped either way. To trade a
  preset's logic live, cap the size:

  ```bash
  DELTA_LIVE=1 python agents/run_agent.py eth-choch-50 --risk 1
  ```

  Identical entries and exits — survivable bet size.

## Why this doesn't "trade in TradingView"

TradingView has **no public order-placement API** — nothing (including
the TradingView MCP, which is read-only market data) can place a trade
inside TradingView programmatically. Trades on TradingView execute at a
connected broker; automating that path needs a paid TradingView plan
(webhook alerts) plus a bridge service. This agent skips all of that and
trades **directly on Delta Exchange**, where the account actually lives.
The matching Pine scripts in `pine/` give you the same signals visually on
TradingView charts (with alerts) if you want the chart experience too.

## Honest expectations

A backtest's +18,552% is not a forecast. The equity curves behind these
numbers all pass through drawdowns that, live, would feel like the
strategy has died — because at this sizing, one more bad streak and the
account *has* died. Paper-trade first, size like you intend to survive,
and judge the agent by its live paper journal (`trade_journal.csv`), not
by the screenshot headlines.

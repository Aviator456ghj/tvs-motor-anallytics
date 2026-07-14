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

## Web interface (dashboard)

```bash
python agents/dashboard.py --password mysecret
# then open  http://localhost:8080  in your browser (login box appears)
```

Start/stop any preset with buttons, watch live paper equity, the open
position, the trade journal, per-agent logs, and an embedded TradingView
chart — all in one page. Agents started from the dashboard keep running
even if you close the browser or stop the dashboard itself.

To open it from your phone on the same Wi-Fi:

```bash
python agents/dashboard.py --host 0.0.0.0 --password mysecret
# phone browser -> http://<your-pc's-LAN-IP>:8080
```

(The dashboard refuses to bind beyond localhost without a password. Never
port-forward it to the open internet.)

**Why there's no TradingView login:** the agent deliberately does not log
into TradingView. A login adds zero trading capability — TradingView has
no public order API, and Delta Exchange India is not a TradingView
broker — and automating their login violates their terms and breaks at
the first captcha/2FA. The chart in the dashboard is TradingView's
official free embed (view-only, no account needed); execution happens
directly on Delta Exchange.

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

Also available: `btc/eth/sol/xrp-liqfakeout` (Liquidity Sweep Fakeout,
1h, genuinely walk-forward-validated, 1% risk — see
`reports/liquidity_fakeout_report.md`).

### TF Breakout presets — included despite not fully validating

`btc/eth/sol-tfbreakout-trail` and `btc/eth/sol-tfbreakout-atr` replicate
a strategy from a user-provided video of Claude Code (via an MCP bridge
to the Jesse algo-trading framework) autonomously developing a Bollinger
Band + EMA trend-following breakout, in two exit flavors. Full write-up
and methodology: `reports/tf_breakout_jesse_replication_report.md`.

**Read this before running them:** both variants pass an entry-rule
statistical significance test (p<0.01) and Monte Carlo stress test on
the full backtest period with no train/test split — exactly what the
source video's own methodology would call "validated." Add a walk-forward
out-of-sample split on top (this repo's standing practice for every other
preset) and neither clears the video's own Sharpe>1 target: the trailing
exit collapses to Sharpe -0.35 out-of-sample, the fixed exit lands at
0.90 — close, but under. They're included anyway, at the user's request,
so their live paper journal (not the full-period backtest number) can
build a real track record. Judge them the same way this repo's README
already asks you to judge everything: by `trade_journal.csv`, live.

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

## Market Intelligence Agent — a different kind of agent, on purpose

Every preset above, including the new TF Breakout ones, is a mechanical
rule, backtested with a measured win rate and profit factor, run from
`run_agent.py` and shown in `dashboard.py`. `market_intel_agent.py`/
`intel_dashboard.py` is deliberately **not** that — you asked earlier
for it to be kept as its own separate app precisely so it wouldn't turn
into another preset runner. It's a real-time **monitor**, built to
answer "find the big money moves, market conditions, and order books,
with self-thinking" directly, and its own demo-trade (if you turn it on)
is driven by the LLM's read, not a fixed rule — so the TF Breakout
strategies don't get a copy inside it. What it DOES give you for BTC/ETH/
SOL while the TF Breakout presets run in the main dashboard: live order-
book imbalance, whale prints, funding/OI, and volatility/trend regime for
those same symbols, right alongside them — open both dashboards together
(ports 8080 and 8090) for the full picture.

```bash
python agents/market_intel_agent.py --symbol BTCUSD
```

or through its **own separate dashboard** — a different app, on purpose,
from `agents/dashboard.py` above (that one is for the mechanical
scalper/pattern presets; this one is the continuous "second brain"
monitor and gets its own full UI):

```bash
python agents/intel_dashboard.py --password mysecret
# then open  http://localhost:8090  in your browser
```

Different port (8090 vs 8080), different login, different pid/log
files (`intel_<symbol>.*` vs `<preset>.*`) — the two run side by side
without touching each other. The intel dashboard has a card per symbol
(BTC/ETH/SOL/XRP) with its own Start/Stop and `reason`/`demo-trade`
toggles, plus a price/demo-equity timeline sparkline (from a rolling
`market_intel_<symbol>_history.jsonl`, not just the latest snapshot) and
a full alert-history log per symbol.

It also has a **Live chart** panel: the free TradingView widget (same
view-only embed as `dashboard.py`, no login) side-by-side with a
self-hosted chart (`lightweight-charts`, free/open-source, no account)
that the agent draws its own analysis onto — the biggest resting bid/ask
walls as horizontal lines, whale trades as up/down markers, and (if a
demo trade is open) its entry/stop/target lines — all live from real
Delta Exchange data, refreshed automatically. Both chart libraries load
from a public CDN; if either is unreachable (offline, blocked network)
the panel says so and the rest of the dashboard keeps working.

And a **Broker — Delta Exchange TESTNET** panel: save your *testnet*
(practice-money) API key/secret from testnet.delta.exchange to see your
testnet wallet balance — completely separate from `dashboard.py`'s live
broker panel (different keys file, different Delta Exchange environment,
`cdn-ind.testnet.deltaex.org` not `api.india.delta.exchange`). It also
shows the public IP this machine is making requests from, for pasting
into Delta Exchange's API key IP-whitelist field. Like the live broker
panel, this is read-only balance-checking only — nothing in this repo
places an order through it.

What it actually watches, all real Delta Exchange India public data:
- **Order book**: bid/ask depth imbalance and the single largest resting
  wall on each side (a real, visible large limit order)
- **Recent trades**: aggressive taker buy/sell volume ratio, and individual
  "whale" prints (trades in the top 1% of recent size)
- **Open interest change (6h) and funding rate** — futures-specific
  positioning: rising OI + one-sided funding often means new money, not
  just existing positions changing hands
- **Volatility and trend regime** (ATR percentile vs its own history;
  ADX-style directional strength) — "market conditions"
- **Crypto news** (CoinDesk public RSS, no key needed), keyword-flagged for
  regulation/ETF/hack/macro headlines — the categories most likely to move
  crypto independent of chart structure

All of that is deterministic and always on — **no API key needed, ever,
for any of it.** The "self-thinking" part is optional and separate, and
has a genuinely free option:

```bash
# free: local model via Ollama (https://ollama.com — install once, both free)
ollama pull llama3.2
python agents/market_intel_agent.py --symbol BTCUSD --reason

# paid alternative: your own Anthropic key, better quality
ANTHROPIC_API_KEY=sk-... python agents/market_intel_agent.py --symbol BTCUSD --reason --llm-backend anthropic
```

`--reason` sends the structured snapshot to whichever backend you picked
and gets back a plain-English synthesis, a bias
(bullish/bearish/neutral/conflicting), a confidence level, and — this
matters — explicit caveats about what would make it wrong. **This step has
no win rate**, on either backend. An LLM call isn't a deterministic
function you can cheaply replay against years of history the way a candle
rule is, so there is no backtest for it and no validation claim — treat it
as a second opinion to think about, not a signal to size into. It never
places an order; it only writes alerts to
`agents/logs/market_intel_<symbol>.json` (which the dashboard reads).
Wiring an LLM's judgment directly into order placement would be a
materially bigger, riskier step this script deliberately does not take.

**Ollama vs Anthropic, honestly:** Ollama is free and unlimited but runs a
much smaller model than Claude — its reads will be rougher, occasionally
wrong in ways a bigger model wouldn't be, and it needs a few GB of RAM to
run smoothly. Anthropic's API gives noticeably better reasoning but costs
real money past a small one-time free trial credit new accounts get (not
enough for sustained 24/7 use). If you can't pay for API access, Ollama is
the right default — you still get the entire whale/order-book/regime/news
monitor either way; only this one synthesis layer changes.

## Honest expectations

A backtest's +18,552% is not a forecast. The equity curves behind these
numbers all pass through drawdowns that, live, would feel like the
strategy has died — because at this sizing, one more bad streak and the
account *has* died. Paper-trade first, size like you intend to survive,
and judge the agent by its live paper journal (`trade_journal.csv`), not
by the screenshot headlines.

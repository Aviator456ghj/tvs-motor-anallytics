# Delta Live Bot — v1 Breakout-Continuation, automated

Live monitoring + execution agent for the **v1 breakout-continuation**
ruleset from `swing_strategy/breakout_continuation_backtest.py`
(71.4% WR, +$118, n=7 at 8% zig-zag threshold). This is the exact v1 math,
not the v2 redesign — deployed as-is per explicit choice, despite v1 not
surviving a threshold sweep robustly (see `swing_strategy/README.md`,
"v1 root cause and the v2 redesign"). Know that going in: this is trading
real money on a single historically-favorable sample, not a proven edge.

Trades BTCUSD perpetual futures on Delta Exchange India, on daily candles,
sizing each position at 1% of account balance risked between entry and
stop — same convention as the backtest.

## Files

- `config.py` — all tunables and the two safety gates. Secrets are read
  from environment variables only.
- `delta_client.py` — minimal signed REST client. Run `python3 delta_client.py`
  standalone first: it hits the real API and reports which candle path,
  wallet-balance call, and products call actually work on your account.
  Don't trust the hardcoded `CANDLE_PATHS` list — trust what this reports.
- `strategy.py` — zig-zag pivot detection (ported from
  `measured_swing_backtest.py::find_pivots`) and breakout trigger logic,
  anchored off the last fully *confirmed* leg (`pivots[-3]`/`pivots[-2]`),
  never the provisional running extreme at `pivots[-1]`.
- `bot.py` — orchestration: fetch candles -> evaluate breakout -> size
  off live balance -> place bracket order (or log dry-run) -> persist
  which leg was acted on so it never fires twice.

## Setup

```
cd delta_live_bot
pip install requests
cp .env.example .env   # fill in DELTA_API_KEY / DELTA_API_SECRET, keep DRY_RUN=true
export $(grep -v '^#' .env | xargs)   # or use a proper env loader
python3 delta_client.py                # selftest - confirm endpoints work
python3 bot.py                          # single dry-run pass
```

## Safety model

Two independent gates, both required before any real order is sent:

```
DRY_RUN=false
LIVE_TRADING_CONFIRM=I_UNDERSTAND_THE_RISK
```

Until both are set exactly, `bot.py` only logs `[DRY RUN]` lines — it
still fetches live data and computes the real trigger/size, just doesn't
call `place_order`. Verify several dry-run passes look correct before
flipping the gates.

## Running it continuously

`python3 bot.py --loop 3600` re-checks hourly forever (cheap, since
candles are daily — triggers only change once a new candle closes).
This is a foreground process: it stops the moment the host running it
stops. If you're running it inside an ephemeral Claude Code session
container, it will NOT survive container reclamation — for real 24/7
monitoring, run it on infrastructure you control (a small VM/systemd
service, your own server, etc.), with `--loop` or an external cron
calling it on a schedule.

## Known gaps / things to verify empirically, not assume

- The exact candle endpoint path, response field names, and timestamp
  units are unconfirmed against the live API as of writing — `delta_client.py`
  tries multiple candidates and `selftest()` reports back which works.
- `contract_value` (used to convert risk-based BTC sizing into Delta's
  integer contract count) is read live from `/v2/products` per pass, not
  hardcoded — confirm it looks sane for BTCUSD before trusting a live order.
- Wallet balance lookup assumes a `USD` or `USDT` entry in
  `/v2/wallet/balances`; adjust `get_usd_balance()` in `bot.py` if your
  account's margin asset is named differently.

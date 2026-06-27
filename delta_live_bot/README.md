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
pip install -r requirements.txt
cp .env.example .env   # fill in DELTA_API_KEY / DELTA_API_SECRET, keep DRY_RUN=true
set -a && source .env && set +a
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

## Running it continuously (systemd)

`python3 bot.py --loop 3600` re-checks forever in the foreground, but
dies the moment your SSH session or terminal closes. For real 24/7
monitoring on the VPS, install it as a systemd service instead:

```
sudo cp deploy/delta-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now delta-bot.service
journalctl -u delta-bot.service -f       # tail logs
```

Edit `deploy/delta-bot.service` first if your checkout path or user isn't
`/home/ubuntu/tvs-motor-anallytics` / `ubuntu`. `Restart=always` means it
comes back up after a crash or a reboot. Each pass writes a snapshot to
`status.json` (or wherever `BOT_STATUS_FILE` points) — that's what the
dashboard below reads.

## Monitoring dashboard

`dashboard/app.py` is a small Flask app showing the current trading mode,
service state, the leg it's currently watching, the most recent trigger,
and wallet balance (fetched on demand). It can start/stop/restart the
`delta-bot.service` unit, but it never touches `.env` or the `DRY_RUN`/
`LIVE_TRADING_CONFIRM` gates — those stay a deliberate, SSH-only edit.

```
sudo cp deploy/delta-dashboard.service /etc/systemd/system/
sudo cp deploy/sudoers-delta-bot /etc/sudoers.d/delta-bot   # see its header first
sudo chmod 440 /etc/sudoers.d/delta-bot
sudo systemctl daemon-reload
sudo systemctl enable --now delta-dashboard.service
```

**Set `DASHBOARD_USER` and `DASHBOARD_PASSWORD` in `.env` before exposing
this anywhere beyond localhost** — without both set, `dashboard/app.py`
refuses to bind to anything but `127.0.0.1` on purpose, since an
unauthenticated page that can start/stop a trading bot should never be
reachable from the public internet. Even with credentials set, this is
plain HTTP Basic Auth with no TLS — fine over an SSH tunnel
(`ssh -L 8080:localhost:8080 ubuntu@<vps-ip>`, then browse
`http://localhost:8080`), risky if bound to a public IP/port directly. If
you do want it reachable by URL, put it behind a reverse proxy (nginx +
Let's Encrypt) rather than exposing Flask's dev server raw.

## Adding more strategies later

Right now `strategy.py`/`bot.py` hardcode the one breakout-continuation
ruleset. `swing_strategy/` already has several other backtested
candidates (`breakout_continuation_v2_backtest.py`, `cvd_divergence_backtest.py`,
`measured_swing_backtest.py`, `trend_filtered_backtest.py`) that aren't
wired into live trading yet. `status.json`'s schema (`symbol`, `watching`,
`last_trigger`) and the dashboard's card layout were kept generic enough
that adding a second live strategy mostly means: a second `STATUS_FILE`/
state file pair, a second systemd unit, and another card on the dashboard
reading that strategy's status file — not a rewrite.

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

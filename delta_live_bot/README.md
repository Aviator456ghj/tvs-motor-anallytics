# Delta Live Bot — v1 + v2 Breakout-Continuation, Cycle Sine-Wave

Live monitoring + execution agent running **three independent strategies
concurrently** against the same BTCUSD daily candle feed:

| Strategy | Source backtest | Entry | SL / TP |
|---|---|---|---|
| v1 breakout-continuation | `swing_strategy/breakout_continuation_backtest.py` | wick touch of breakout level | leg origin ±2% / 100% measured move |
| v2 breakout-continuation | `swing_strategy/breakout_continuation_v2_backtest.py` | close beyond breakout level, fills next bar's open | breakout level retraced 61.8% of leg range / 161.8% extension |
| Cycle sine-wave | `swing_strategy/cycle_sine_backtest.py` | periodogram-fit derivative trough/crest + momentum confirm, fills next bar's open | structural swing-lookback stop / ±1x fitted amplitude |

**Robustness caveats, carried forward honestly from `swing_strategy/README.md`:**
v1 is deployed as the exact math the user explicitly chose, despite not
surviving a zig-zag threshold sweep robustly (71.4% WR, +$118, n=7 is a
thin, cherry-picked-looking sample) — see "v1 root cause and the v2
redesign" in that README. v2 is the only one of the eleven logics tested
across this whole project that stays net-positive across its own parameter
sweep, i.e. the most defensible of the three. Cycle sine-wave flips sign
depending on the TP amplitude multiple and its fitted dominant period
tends to hug the scan's upper boundary — treat it as the weakest of the
three, kept live mainly because the user explicitly asked for all three.
None of this is a guarantee: this bot risks real money on strategies with
mixed historical robustness, not a proven edge.

Trades BTCUSD perpetual futures on Delta Exchange India, on daily candles,
sizing each position at 1% of account balance risked between entry and
stop — same convention as the backtests. If more than one strategy
triggers in the same pass, each re-fetches the live wallet balance before
sizing, so a balance already drawn down by an earlier trigger in that same
pass naturally caps how big the next trigger's position can be — there is
no extra cross-strategy risk cap beyond that.

## Files

- `config.py` — all tunables and the two safety gates. Secrets are read
  from environment variables only.
- `delta_client.py` — minimal signed REST client. Run `python3 delta_client.py`
  standalone first: it hits the real API and reports which candle path,
  wallet-balance call, and products call actually work on your account.
  Don't trust the hardcoded `CANDLE_PATHS` list — trust what this reports.
- `strategy.py` — zig-zag pivot detection (ported from
  `measured_swing_backtest.py::find_pivots`) and v1 breakout trigger logic,
  anchored off the last fully *confirmed* leg (`pivots[-3]`/`pivots[-2]`),
  never the provisional running extreme at `pivots[-1]`.
- `strategy_v2.py` — reuses `strategy.py`'s pivot detector; v2's
  close-confirmed breakout trigger logic, same anchor.
- `strategy_cycle.py` — periodogram fit / derivative turning-point logic
  ported from `cycle_sine_backtest.py`, duplicated rather than imported
  (same reasoning as `strategy.py` duplicating `find_pivots`: no
  cross-package relative-path dependency). Not pivot-anchored — idempotency
  is keyed off the confirming bar's date + direction instead of a leg key.
- `bot.py` — orchestration: fetch candles -> evaluate all three strategies
  independently -> for each new trigger, size off a freshly-fetched live
  balance -> place bracket order (or log dry-run) -> persist which
  leg/signal was acted on (one key per strategy) so none ever fires twice.

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
service state, what each of the three strategies is currently watching,
each strategy's most recent trigger, and wallet balance (fetched on
demand). It can start/stop/restart the `delta-bot.service` unit, but it
never touches `.env` or the `DRY_RUN`/`LIVE_TRADING_CONFIRM` gates — those
stay a deliberate, SSH-only edit.

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

`bot_state.json` and `status.json` use one key per strategy
(`last_handled_leg_key`/`watching`/`last_trigger` for v1,
the `_v2` and `_cycle` suffixed equivalents for the other two — see
`bot.py`'s `LEG_KEY_FIELD`/`STATE_FIELD`/`TRIGGER_STATUS_FIELD` lookup
tables). `swing_strategy/` still has other backtested candidates
(`cvd_divergence_backtest.py`, `measured_swing_backtest.py`,
`trend_filtered_backtest.py`, `gravity_field_backtest.py`,
`phase_rotation_backtest.py`) not wired into live trading. Adding one more
means: a new `strategy_<name>.py` with an `evaluate_latest_*()` /
`current_watch_*()` pair, a new entry in those three lookup tables and in
`run_once()`'s `watches`/`setups` dicts, and a new pair of dashboard cards
— not a rewrite of the loop itself.

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

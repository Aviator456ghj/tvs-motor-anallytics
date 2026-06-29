# Delta Liquidity-Sweep Swing Bot

Automated BTCUSD swing bot for **Delta Exchange (India)**. It trades the
liquidity-sweep / market-structure strategy we built: it only acts at the
**edges of the range** (where stop-hunts reverse), demands a **close-back-inside
reclaim** plus **above-average volume**, and **filters out mid-range fakeouts**.

> ⚠️ **Real money.** Trading derivatives with leverage can lose your whole
> balance. This bot ships in **dry-run** mode and will not send a single order
> until you set `LIVE=true`. Test on **testnet** first. No strategy wins every
> time — size responsibly. This is software, not financial advice.

## Strategy (what fires a trade)

All evaluation happens on the **closed** signal candle (`SIGNAL_TF`, default 1h),
using swing structure from `STRUCTURE_TF` (default 4h).

| Signal | Condition | Stop | Target |
|---|---|---|---|
| **Long sweep** (HL reversal) | wick pierces a swing **low near the range bottom**, then **closes back above** it on `>VOL_FACTOR×` avg volume | below the sweep wick | `TP_R_MULTIPLE` × risk |
| **Short sweep** (LH rejection) | wick pierces a swing **high near the range top**, then **closes back below** it on high volume | above the sweep wick | `TP_R_MULTIPLE` × risk |
| **Structure flip** (breakout) | candle **closes** beyond the range extreme by `FLIP_BUFFER` on high volume | broken extreme | `TP_R_MULTIPLE` × risk |

### Fakeout filters (the part that keeps you out of traps)
1. **Edges only** — a sweep level must sit within `EDGE_BAND` of a range extreme. Mid-range = no trade.
2. **Reclaim required** — the candle must *close* back inside the level, never just wick it.
3. **Volume confirmation** — the sweep/flip candle must beat average volume by `VOL_FACTOR`.
4. **One bar, one signal** — state file prevents re-firing on the same candle; new entries blocked while a position is open.

## Setup

```bash
cd delta-liquidity-bot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit .env
```

1. On Delta: **Account → API Keys** → create a key with **Trading** enabled. Whitelist your server IP.
2. Put `DELTA_API_KEY` / `DELTA_API_SECRET` in `.env`.
3. Leave `LIVE=false` to start.

## Backtest first

```bash
python -m bot.backtest --tf 1h --bars 1500
```

Prints signals found, wins/losses, win-rate and net **R** — per signal type.
Use it to tune `VOL_FACTOR`, `EDGE_BAND`, `RANGE_LOOKBACK` before going live.

## Run

```bash
python -m bot.bot            # dry-run: logs the exact orders it WOULD place
```

When the dry-run logs look right, set `LIVE=true` in `.env` and restart. Consider
pointing `DELTA_BASE_URL` at testnet for a live-fire rehearsal with fake funds.

## Layout

```
bot/
  config.py        # all knobs, loaded from .env
  delta_client.py  # Delta v2 REST + HMAC auth (candles, wallet, positions, orders)
  structure.py     # swings, sweeps, fakeout filters  <-- the strategy core
  risk.py          # 2%-risk position sizing, stop/target from structure
  bot.py           # main loop: fetch -> detect -> size -> place (or dry-run)
  backtest.py      # walk-forward validation + win-rate report
```

## Tuning notes
- **Too many fakeouts slipping through?** raise `VOL_FACTOR` (e.g. 1.5) and/or shrink `EDGE_BAND` (e.g. 0.15).
- **Too few trades?** loosen `EDGE_BAND` (0.30) or lower `VOL_FACTOR` (1.2).
- **Whippy stops?** increase `SWING_LEFT/RIGHT` for cleaner pivots; widen the stop pad in `risk.py`.
- Always re-backtest after changing a knob.

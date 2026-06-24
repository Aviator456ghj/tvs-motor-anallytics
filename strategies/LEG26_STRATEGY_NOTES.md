# Leg/2.6 Confluence Strategy — Analysis Notes

This documents the analysis trail for `leg26_confluence_strategy.py`. This is a
**secondary** strategy, weaker than `fib_zone_strategy.py` — saved for reference
and future "analyze" requests, not as the primary signal generator.

## 1. Origin

Saide's "leg/2.6" video method (demoed on XAUUSD): measure a price leg (swing
high to swing low), divide the leg size by 2.6, and project that value further
in the leg's direction from its endpoint. Stack the last few legs; where 2+
projected levels cluster within 0.25% of each other, that's a confluence zone.

`2.6` is a custom divisor, not a standard Fibonacci ratio (close to but not
exactly 2.618 = φ²).

## 2. Direction correction (from user's reference screenshot)

The first pass (earlier in this project's history) treated down-leg-derived
levels as LONG bounce/support targets. The user supplied a screenshot showing
side-by-side leg measurement boxes on a downtrend chart and clarified: **that
configuration (down legs) is for SHORT entries, not long bounces** — exactly
the opposite of the original implementation. The mirror (up legs, L→H) is for
LONG entries.

Corrected geometry, implemented in `leg26_confluence_strategy.py`:
- **Down leg** (H→L): `level = low − leg_size/2.6`, projected further DOWN.
  Confluence zone = SHORT continuation zone.
- **Up leg** (L→H): `level = high + leg_size/2.6`, projected further UP.
  Confluence zone = LONG continuation zone.
- Entry requires price to touch the zone and close back against it in the
  trend direction (bearish rejection for SHORT, bullish rejection for LONG) —
  same "basic" confirmation rule that won the confirmation-pattern sweep for
  the Fib-zone strategy.
- Exit: fixed 2R target (the video defines no exit rule), stop just beyond the
  zone edge, max hold = 6 days worth of bars on whichever TF is used.

## 3. Everything tested, in order, with results

Instruction from the user for this pass: **"use 4hr totally, no confirmation
with lower time frame"** — single timeframe only, no MTF.

| # | Variant | Result | Verdict |
|---|---|---|---|
| 1 | 4h single-TF, both directions, no filter (BTC+ETH+SOL) | 38 trades combined, PF 0.53, Total R -14.00. SHORT catastrophic: 18 trades, 5.6% win, -15.00R | Looked broken, but sample (38 trades/yr) too small to trust |
| 2 | Same spec, re-verified without the "must overshoot zone first" entry condition | Identical numbers — confirms #1 wasn't an artifact of that condition | — |
| 3 | **Timeframe sweep** (1h/30m/15m/5m, both directions, no filter, combined BTC+ETH+SOL) | 1h: 221 trades, PF 1.18, +25.00R. 30m: 259 trades, PF 1.03, +5.00R. 15m: 574 trades, PF 0.97, -10.00R. 5m: 1387 trades, PF 1.02, +17.49R | 1h clearly best; 4h sample was too small/noisy to judge fairly |
| 4 | 1h + 4h EMA9/EMA21 trend filter (LONG only if 4h trend UP, SHORT only if DOWN) | Combined: 130 trades, PF 1.29, +23.00R, MaxDD -10.00 (vs -16.00 unfiltered). **All 3 assets individually positive** (BTC flipped from -6.00R to +3.00R) | Real improvement, more robust — **but user chose not to keep this filter**, see §4 |
| 5 | Per-TF/per-direction isolation check: re-ran 1h/30m/15m/5m each as standalone single-direction backtests (not sliced from a combined-both-directions run) | 1h (both): 226 trades, PF 1.18, +26.00R. 30m (SHORT only): 133 trades, PF 1.20, +17.00R. 15m (SHORT only): 388 trades, **PF 0.96, -10.00R — losing**. 5m (SHORT only): 1246 trades, **PF 1.00, -3.42R — breakeven** | Isolating a direction changes which trades actually fire (occupancy lock no longer shared with the other direction) — 15m and 5m do NOT hold up once isolated properly |

## 4. Why only 1h + 30m were saved

Per user's explicit instruction: **"remove 5 and 15 save only 1h and 30 min."**

Final saved config, no trend filter (the EMA filter from variant #4 was tested,
shown to help, but the user chose to save the unfiltered version instead):

| TF | Directions traded | Trades | Win% | Total R | PF | Per-asset |
|---|---|---|---|---|---|---|
| 1h | LONG + SHORT | 226 | 37.2% | +26.00 | 1.18 | BTC -6.00 (PF 0.91), ETH +20.00 (PF 1.42), SOL +12.00 (PF 1.43) |
| 30m | SHORT only | 133 | 37.6% | +17.00 | 1.20 | BTC +12.00 (PF 1.35), ETH -1.00 (PF 0.97), SOL +6.00 (PF 1.38) |

**Known weak points, read before trusting this live:**
- BTC is net-negative on the 1h leg (-6.00R) — the combined 1h number is carried
  by ETH and SOL.
- ETH is roughly breakeven on the 30m leg (-1.00R, PF 0.97).
- No single asset is positive on *both* saved configs simultaneously — this is
  weaker, less-robust evidence than `fib_zone_strategy.py`, where all 3 assets
  were positive in its one chosen config.
- The 4h EMA trend filter (variant #4) measurably improved robustness (all 3
  assets positive, higher PF, lower drawdown) but was explicitly **not** the
  version the user asked to save — if revisiting this strategy later, that
  filtered version is the stronger candidate.
- No fees/slippage modeled. Not walk-forward tested across disjoint periods.
- 1h data window: ~180 days ending 2026-06-24. 30m data window: ~75 days ending
  2026-06-24 (different lengths, fetched at different points in the session).
- This is a backtested signal generator, not an execution system — **never
  auto-execute real trades, only generate/notify signals.**

## 5. How to reproduce or re-run

```bash
cd strategies/
python3 fetch_data.py BTCUSD 1h  180 btcusd_1h_history.json
python3 fetch_data.py BTCUSD 30m 75  btcusd_30m_history.json
# repeat for ETHUSD, SOLUSD
```

```python
from leg26_confluence_strategy import run_backtest, find_live_setup
import json

def load(f):
    with open(f) as fh:
        return json.load(fh)

trades_1h = run_backtest(load("btcusd_1h_history.json"), "1h")
trades_30m = run_backtest(load("btcusd_30m_history.json"), "30m")

# For live monitoring (no lookahead, causal):
live = find_live_setup(load("btcusd_1h_history.json"), "1h")
# live is None, or a dict: {direction, zone_lo, zone_hi, confirmed, current_close}
```

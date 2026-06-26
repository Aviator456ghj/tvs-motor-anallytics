# BTCUSD Backtest Results — Trident FVG + Doji Strategy

Mechanical proxy backtest of the TG Capital "Trident" FVG + doji trend-continuation
strategy, run against BTCUSD 30-minute candles (Bitfinex, 2019-01-01 to present).

Two versions of the FVG retracement check are implemented in `trident_backtest.py`,
selected via the `legacy_midline` flag on `run_backtest()`:

- **Legacy (`legacy_midline=True`)**: requires the doji to wick exactly through the
  FVG's 50% line (`low <= mid <= high`).
- **Current (`legacy_midline=False`, default)**: requires the doji to wick into the
  lower half of the FVG as a *zone/band* (`gap_lo` to the 50% line), matching the
  trader's chart markup where the retracement target is drawn as a rectangle, not
  a single level.

## Kill zone ON (London kill zone, 03:00-06:30 America/New_York)

| Logic | Stop type | Trades | Win rate | Total R | Max DD |
|---|---|---|---|---|---|
| Legacy (midline) | close-based | 136 | 30.1% | +67.90R | -50.10R |
| Legacy (midline) | intrabar (hard stop) | 136 | 25.0% | **+120.86R** | -25.12R |
| Current (zone) | intrabar (hard stop) | 140 | 25.0% | +137.86R | -20.60R |

## Kill zone OFF (no time-of-day filter)

| Logic | Stop type | Trades | Win rate | Total R | Max DD |
|---|---|---|---|---|---|
| Legacy (midline) | close-based | 685 | 25.1% | **+101.06R** | -241.47R |
| Legacy (midline) | intrabar (hard stop) | 704 | 19.0% | +498.11R | -44.28R |
| Current (zone) | intrabar (hard stop) | 726 | 18.7% | **+483.22R** | -49.28R |

## BOS/ChoCh structure filter (added after comparing against trader's whiteboard + chart frames)

The trader's chart markup shows explicit BOS (break of structure) / ChoCh labels as part of
his confirmation, which the base engine above does not model. `add_swing_structure()` adds a
no-lookahead fractal swing-high detector and `bos_up` flag (a fresh close above the most
recently confirmed swing high); `run_backtest(..., require_bos=True)` requires a bullish BOS
within `bos_lookback` (default 6) bars of the FVG bar before accepting the setup, on the theory
that the AMD-diagram sequence is sweep -> break of structure -> FVG forms in the expansion leg.

Current (zone), intrabar (hard stop):

| Kill zone | BOS filter | Trades | Win rate | Total R | Max DD |
|---|---|---|---|---|---|
| ON | off | 140 | 25.0% | +137.86R | -20.60R |
| ON | on | 93 | 28.0% | +98.78R | -15.00R |
| OFF | off | 726 | 18.7% | +483.22R | -49.28R |
| OFF | on | 535 | 17.9% | +312.09R | -33.57R |

**Verdict: the BOS filter is not worth keeping as currently specified.** It cuts trade
frequency by ~25-34% but only nudges win rate (+3pp with kill zone, -0.8pp without) — it screens
out winners along with losers, so total R drops in every config despite the marginally smaller
drawdown. The real trader's discretionary BOS reading is evidently doing more than "did price
recently break a fractal swing high"; a naive structural filter doesn't capture it. Left in the
module (`require_bos` defaults to `False`, base results above are unaffected) for anyone who
wants to refine the BOS logic further, but not adopted as the default.

## Reproduce

```bash
python3 backtests/trident_backtest.py data/btcusd_30m.csv data/btcusd_1d.csv            # kill zone on
python3 backtests/trident_backtest.py data/btcusd_30m.csv data/btcusd_1d.csv nokillzone  # kill zone off
```

For the legacy midline variant, call `run_backtest(..., legacy_midline=True)` directly
(not exposed as a CLI flag — see the module's `__main__` block to wire one up if needed).

## Notes

- Close-based stops produce far fatter tail losses on BTC (worst trade -90.40R under
  the legacy no-killzone/close-stop config) because a single 30m candle can close many
  R below the stop level in a volatile move. Intrabar (hard) stops cap every loss at
  -1R and are the more realistic choice for this market.
- This is a rule-based approximation, not a replication of the trader's real
  (~80% mechanical / 20% discretionary) execution — see the module docstring.

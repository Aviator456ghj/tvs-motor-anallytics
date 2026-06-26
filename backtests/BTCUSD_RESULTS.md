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

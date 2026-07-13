# Strategy B (Order Block Execution) — literal AI-Mode recipe, cross-asset

1h structure + 15m execution, last 180 days, tested on BTCUSD, ETHUSD, SOLUSD, XRPUSD — cross-asset, the same way this repo's other validated strategies are tested, because (as the single-BTC run showed) this literal recipe's setup is rare enough that one symbol alone doesn't produce a trustworthy sample size.

**Disclosed substitutions:** "Verify the CME Gap" is not testable — Delta Exchange's public API has no historical CME futures data; not applied. The zone is the OB candle's BODY only (open-close), exactly as Step 1 specifies — a real difference from this repo's existing order_block.py, which uses the full wick range. Entry is tested as both options the spec gives (structural-candle-open and 1h-zone 50% equilibrium); stop is tested both literally ($10) and at a realistic 0.15%, same reasoning as the Strategy A test. Take-profit is the CHoCH setup's pre-pullback swing origin, but ONLY taken when it clears the spec's own stated minimum 1:3 R:R — otherwise the setup is skipped, not force-fit.

Walk-forward: 60% in-sample / 40% out-of-sample by time, 2% risk/trade, cost 0.110%/round-trip.

| Symbol | Entry variant | Stop buffer | IS trades | IS WR | IS PF | IS ret | OOS trades | OOS WR | OOS PF | OOS ret | OOS maxDD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSD | 15m structural open | literal $10 | 3 | 33% | 1.25 | +1.2% | 3 | 0% | 0.00 | -6.8% | -6.8% |
| BTCUSD | 15m structural open | realistic 0.15% | 0 | 0% | 0.00 | +0.0% | 2 | 0% | 0.00 | -4.6% | -4.6% |
| BTCUSD | 1h 50% equilibrium | literal $10 | 6 | 33% | 3.68 | +47.9% | 6 | 0% | 0.00 | -32.6% | -32.6% |
| BTCUSD | 1h 50% equilibrium | realistic 0.15% | 6 | 33% | 2.63 | +19.6% | 6 | 0% | 0.00 | -17.2% | -17.2% |
| ETHUSD | 15m structural open | literal $10 | 1 | 100% | inf | +7.9% | 1 | 100% | inf | +6.8% | 0.0% |
| ETHUSD | 15m structural open | realistic 0.15% | 4 | 25% | 1.45 | +3.0% | 2 | 50% | 3.93 | +6.8% | -2.3% |
| ETHUSD | 1h 50% equilibrium | literal $10 | 5 | 0% | 0.00 | -11.3% | 4 | 25% | 0.94 | -0.4% | -4.6% |
| ETHUSD | 1h 50% equilibrium | realistic 0.15% | 7 | 0% | 0.00 | -17.7% | 5 | 20% | 1.25 | +2.6% | -10.4% |
| SOLUSD | 15m structural open | literal $10 | 0 | 0% | 0.00 | +0.0% | 0 | 0% | 0.00 | +0.0% | 0.0% |
| SOLUSD | 15m structural open | realistic 0.15% | 2 | 0% | 0.00 | -15.7% | 1 | 100% | inf | +6.0% | 0.0% |
| SOLUSD | 1h 50% equilibrium | literal $10 | 0 | 0% | 0.00 | +0.0% | 0 | 0% | 0.00 | +0.0% | 0.0% |
| SOLUSD | 1h 50% equilibrium | realistic 0.15% | 13 | 8% | 0.85 | -5.4% | 4 | 25% | 2.06 | +8.8% | -5.0% |
| XRPUSD | 15m structural open | literal $10 | 0 | 0% | 0.00 | +0.0% | 0 | 0% | 0.00 | +0.0% | 0.0% |
| XRPUSD | 15m structural open | realistic 0.15% | 1 | 0% | 0.00 | -2.2% | 1 | 100% | inf | +5.8% | 0.0% |
| XRPUSD | 1h 50% equilibrium | literal $10 | 0 | 0% | 0.00 | +0.0% | 0 | 0% | 0.00 | +0.0% | 0.0% |
| XRPUSD | 1h 50% equilibrium | realistic 0.15% | 5 | 20% | 1.52 | +6.3% | 6 | 33% | 1.92 | +14.2% | -11.9% |

**Pooled sample size across all 4 assets x 4 variants: 53 in-sample trades, 41 out-of-sample trades (pooled OOS win rate 22%).** Even pooled across every asset and every entry/stop variant tested, this is still a thin sample — treat every number in this report as directional, not statistically conclusive, and weight it far below the already-validated strategies in this repo.

For comparison, the already-validated `delta_scalper/order_block.py` (full wick-to-wick zone, same-bar retest entry, ATR stop, ride exit) scores **106 trades, PF 1.28, +3,076% (at 15% risk/trade), -77.0% max DD** on the same underlying setup family, and it earned that grade on a real sample size — kept here as the benchmark this literal recipe is being measured against.

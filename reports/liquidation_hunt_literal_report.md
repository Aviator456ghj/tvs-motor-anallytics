# Strategy A (Liquidation Hunt) — literal AI-Mode recipe vs real BTCUSD data

15m execution bars, PDH/PDL from the prior UTC day, last 180 days (1768410900 -> 1783962000, 17280 bars).

**Disclosed substitution:** the spec's "OI crash confirmation" needs a historical open-interest series Delta Exchange's public API doesn't expose; replaced with the spec's own volume-spike confirmation (2.0x the 20-bar average, exactly as written in Phase 2 Step 2). Funding-rate directional bias is also unavailable historically and was not applied — flagged as an untested piece of the spec, not silently dropped.

Total confirmed entries (sweep + volume spike + close-back-inside) over 180 days: **163**.

Walk-forward: 60% in-sample, 40% out-of-sample, 2% risk/trade, cost 0.110%/round-trip. TP1/TP2 = 50%/100% of yesterday's range, exactly as specified. Two stop-buffer variants tested since the literal "$5-10" figure is a few basis points at current BTC prices (below normal 15m noise):

| Stop buffer | IS trades | IS WR | IS PF | IS ret | IS maxDD | OOS trades | OOS WR | OOS PF | OOS ret | OOS maxDD |
|---|---|---|---|---|---|---|---|---|---|---|
| literal $5-10 | 60 | 27% | 0.39 | -45.9% | -51.3% | 55 | 25% | 0.49 | -37.6% | -43.5% |
| realistic 0.15% | 56 | 32% | 0.54 | -31.2% | -41.1% | 54 | 22% | 0.45 | -36.0% | -39.5% |

For comparison, the already-validated `delta_scalper/liquidity_fakeout.py` (same-bar entry, ATR stop, single R-multiple target, 1h timeframe) scores BTCUSD OOS PF **1.42** — kept here as the benchmark this literal recipe is being measured against, not just against breakeven.

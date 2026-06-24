# Trend-Based Fibonacci Zone Strategy — Analysis Notes

This documents the full analysis trail that led to the strategy saved in
`fib_zone_strategy.py`. Read this before re-running or trusting the numbers —
it includes what was tried and rejected, not just the winner.

## 1. Origin

Two separate video-based methodologies were investigated for BTCUSD/ETHUSD/SOLUSD:

**A. "Leg / 2.6 divisor" method** (Saide's video): measure a downward price leg
(swing high to swing low), divide the leg size by 2.6, project that value up
from the low to get a single level. Stack levels from the last few legs;
where 2+ levels cluster within 0.25% of each other ("confluence"), treat it
as a support zone for long bounces.

Math note: 2.6 ≈ 2.618 = φ², and 1/2.618 ≈ 0.382 — this is mathematically
just the standard 38.2% Fibonacci retracement in disguise, not a novel ratio.

**B. "Trend-Based Fibonacci Extension" 3-point method** (the one ultimately
adopted): for an uptrend continuation —
- Point1 = a confirmed Higher High (HH)
- Point2 = the confirmed Higher Low (HL) that follows Point1
- leg = |Point1 − Point2|
- Point3 = a later retest of Point1's price level (creates the "drag back"
  / 90°-angle visual seen on the reference chart)
- Fibonacci zones are then projected DOWN from Point3 by ratios × leg, as
  paired boxes, not single lines:
  - Red zone: 0.5–0.618 × leg below Point3
  - Teal zone: 1.414–1.618 × leg below Point3
  - Yellow zone: 2.0–2.272 × leg below Point3
  - 0 and 2.618 are plain anchor/boundary lines — NOT independently tradable
- For downtrend continuation (shorts), everything mirrors: Point1 = LL,
  Point2 = LH after it, zones project UP from Point3.

The user corrected an earlier wrong implementation (treating all 7 ratios as
independent tradable lines) with a screenshot showing the actual paired-box
structure — that correction is what's encoded in `ZONES` in the saved module.
A second screenshot (XAUUSD, "2.6 strategy", long-side example) was used to
independently verify the box/diagonal geometry matched what was implemented;
no further fix was needed at that point — a numeric audit (`verify_setups.py`
in the working session) confirmed the HH/HL and LL/LH detection and the
zone math were correctly signed and oriented in both directions.

## 2. Everything tested, in order, with results

All backtests are causal (no lookahead), R-multiple based, no fees/slippage
included anywhere unless explicitly noted.

| # | Variant | Result | Verdict |
|---|---|---|---|
| 1 | Donchian channel range mean-reversion (1h, 180d, BTCUSD) | Near-breakeven across parameter variants | No edge, dropped |
| 2 | Leg/2.6 confluence, standalone (5m, BTCUSD) | 232 trades, 31.5% win, Total R **-16.99**, PF 0.89 | Unprofitable |
| 3 | Leg/2.6 confluence + 1h EMA9>EMA21 trend filter | 96 trades, 36.5% win, Total R **+6.34**, PF 1.10, MaxDD -10.00R | Mildly profitable, weak |
| 4 | 3-point Fib, 7 ratios as independent single levels (5m, BTC+ETH+SOL) | 459 trades, Total R 180.82, PF 1.76 | **Misleading** — ~80% of profit came from the trivial ratio=0 retest level. Discarded after diagnosis. |
| 5 | 3-point Fib, corrected paired zone boxes (Red/Teal/Yellow), 5m, single-attempt | 421 trades, Win 53.7%, Total R 49.24, PF 1.30, MaxDD -18.50R | Real edge, but thin |
| 6 | Teal zone isolated as standalone strategy (true rerun, not filtered subset) | 234 trades, PF 1.13 combined; **BTCUSD alone PF 1.00** | Confirmed the per-zone breakdown of #5 was inflated by selection bias — teal alone is not a standalone edge |
| 7 | Entry confirmation pattern sweep (basic / pinbar / engulfing / break-next / volume-spike) | basic PF 1.30 (best) vs engulfing PF 0.93, volume PF 0.92 (both net negative) | Stricter confirmation filters hurt — basic "close back inside zone" rule wins |
| 8 | Standalone timeframe sweep, BTCUSD, 5m→4h | 30m: PF 1.64 (best); 2h: losing; 4h: only 20 trades | 30m flagged as best single TF, but small samples at higher TFs |
| 9 | **MTF: 30m structure + 5m entry confirmation, single-attempt** (BTC+ETH+SOL) | 200 trades, Win 50.0%, Total R **49.20**, PF **1.51**, MaxDD -9.15R. Per-asset: BTC PF 1.70, ETH PF 1.61, SOL PF 1.27 — **all three profitable** | **CHOSEN** — see §3 |
| 10 | MTF: 30m structure + 15m entry confirmation | Total R 9.93, PF 1.39 | Worse than 5m entry — rejected |
| 11 | Cascade (retry next zone if current zone stops out), 30m/5m, BTC+ETH+SOL | 227 trades, Total R 43.74, PF 1.36, MaxDD -12.48R. Helped BTC (PF 1.70→1.85) but hurt ETH (1.61→1.28) and SOL (1.27→1.02) | Net worse combined — rejected |
| 12 | Cascade, structure-TF sweep (15m/30m/1h/2h/4h, BTC only) | 1h stood out: PF 3.01, but only 32 trades | Flagged as possibly overfit to small sample |
| 13 | Cascade, 1h structure + 5m entry, BTC+ETH+SOL | 106 trades, PF 1.72, Total R 39.87, MaxDD -10.00R. BTC PF 3.01, **ETH only PF 1.04** (~breakeven) | Doesn't hold up cross-asset — rejected in favor of #9 |

## 3. Why #9 was chosen as final

Comparing the three realistic finalist candidates:

| Candidate | Combined PF | Total R | MaxDD | Trades | Per-asset PF |
|---|---|---|---|---|---|
| **30m struct + 5m entry, single-attempt** | **1.51** | 49.20 | -9.15 | 200 | 1.70 / 1.61 / 1.27 — all positive |
| 30m struct + 5m entry, cascade | 1.36 | 43.74 | -12.48 | 227 | worse on 2 of 3 assets |
| 1h struct + 5m entry, cascade | 1.72 | 39.87 | -10.00 | 106 | ETH ~breakeven, thin sample |

#9 wins on robustness, not just on the highest single metric: it's the only
configuration where every one of the three assets tested was independently
profitable, on the largest sample size of the finalists (200 trades vs 106),
which matters more for trusting the result than chasing the highest PF off
a 32-trade subsample (as #12/#13 risked).

## 4. Known caveats — read before trusting this live

- **No fees or slippage modeled anywhere in this analysis.** At combined PF
  1.51 there's real margin to absorb realistic taker fees (~0.05–0.1%/side
  on Delta), but this has NOT been explicitly verified — do that before
  sizing real capital against it.
- Single snapshot in time: structure data covers ~75 days ending 2026-06-24.
  Not walk-forward tested across multiple disjoint historical periods —
  the edge could be specific to this market regime.
- 200 combined trades over 75 days is a real sample but not a huge one;
  treat PF 1.51 as "plausible edge," not "proven edge."
- SOLUSD is the weakest contributor (PF 1.27) — if SOL conditions change,
  re-check that it isn't dragging the combined number down further.
- This is a backtested signal generator, not an execution system. Per
  durable session instructions: **never auto-execute real trades — only
  generate/notify signals.**

## 5. How to reproduce or re-run

```bash
cd strategies/
python3 fetch_data.py BTCUSD 30m 75 btcusd_30m_history.json
python3 fetch_data.py BTCUSD 5m  75 btcusd_5m_history.json
# repeat for ETHUSD, SOLUSD
```

```python
from fib_zone_strategy import run_backtest, find_live_setup
import json

def load(f):
    with open(f) as fh:
        return json.load(fh)

trades = run_backtest(load("btcusd_30m_history.json"), load("btcusd_5m_history.json"))

# For live monitoring (no lookahead, causal):
live = find_live_setup(load("btcusd_30m_history.json"), load("btcusd_5m_history.json"))
# live is None, or a dict: {direction, zone, zone_lo, zone_hi, p1, p3, leg, confirmed, current_close}
```

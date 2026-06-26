# NYS Markets / Udit "REM" Liquidity Sweep + FVG (AMD Model) Backtest Results

Mechanical proxy backtest of the NYS Markets prop-firm strategy: a 4H liquidity sweep
(candle1 body >50%, candle2 sweeps exactly one side of candle1 while closing its body
back inside candle1's range) followed by a Fair Value Gap + retest entry on a finer
entry timeframe, filtered to the London session (07:00-11:00 UTC) and Tue/Wed/Thu only
(his stated day-of-week rule). Risk:reward target is fixed at 1:2. See
`nys_amd_backtest.py`'s module docstring for the simplifications vs. his real (taught)
strategy — most importantly, his fractal 4H->15m->5m->3m confirmation drill-down is
collapsed into a single entry timeframe (1h for FX/Gold, 30m for BTC/TVS Motor), which
is the main reason these mechanical win rates run far below his claimed ~90%.

## Filters ON (London session + Tue/Wed/Thu only)

| Instrument | Trades | Win rate | Total R | Max DD |
|---|---|---|---|---|
| GOLD | 20 | 55.0% | +13.00R | -2.00R |
| NZDUSD | 32 | 50.0% | +16.00R | -4.00R |
| GBPUSD | 32 | 43.8% | +10.00R | -5.00R |
| USDJPY | 27 | 37.0% | +3.00R | -7.00R |
| EURUSD | 26 | 30.8% | -2.00R | -8.00R |
| BTCUSD | 96 | 31.2% | -6.00R | -8.00R |
| TVS Motor | 30 | 26.7% | -6.00R | -6.00R |
| USDCAD | 17 | 23.5% | -5.00R | -8.00R |

## Filters OFF (no session/day-of-week restriction)

| Instrument | Trades | Win rate | Total R | Max DD |
|---|---|---|---|---|
| GOLD | 174 | 40.2% | +36.00R | -22.00R |
| BTCUSD | 1468 | 32.6% | -31.00R | -57.00R |
| GBPUSD | 286 | 32.9% | -3.00R | -27.00R |
| TVS Motor | 165 | 32.7% | -3.00R | -21.00R |
| NZDUSD | 286 | 32.5% | -7.00R | -36.00R |
| EURUSD | 310 | 32.3% | -11.84R | -28.00R |

Turning the session/day filters off multiplies trade count 5-15x but drags every
instrument toward breakeven or negative — the filters are doing real work, consistent
with the trader's own emphasis on London-session, Tue/Wed/Thu-only execution.

## Reproduce

```bash
python3 backtests/nys_amd_backtest.py data/btcusd_30m.csv BTCUSD            # filters on
python3 backtests/nys_amd_backtest.py data/btcusd_30m.csv BTCUSD nofilters  # filters off
python3 backtests/nys_amd_backtest.py data/fx/GOLD_60m.csv GOLD
python3 backtests/nys_amd_backtest.py data/fx/NZDUSD_60m.csv NZDUSD
python3 backtests/nys_amd_backtest.py data/fx/EURUSD_60m.csv EURUSD
python3 backtests/nys_amd_backtest.py data/fx/GBPUSD_60m.csv GBPUSD
python3 backtests/nys_amd_backtest.py data/fx/USDCAD_60m.csv USDCAD
python3 backtests/nys_amd_backtest.py data/fx/USDJPY_60m.csv USDJPY
python3 backtests/nys_amd_backtest.py data/tvs/tvsmotor_30m.csv "TVS Motor"
```

## Notes

- Best mechanical performers (GOLD, NZDUSD, GBPUSD) are exactly the instruments his
  taught approach also leans on (Gold and majors with clean session structure);
  BTCUSD (24/7, no real "Asian/London/NY" session boundaries) and TVS Motor (NSE
  hours don't map onto a London-session liquidity sweep) are the weakest fits, which
  matches the strategy's design assumptions rather than contradicting them.
- A 1% risk / fixed 1:2 R:R proxy with a 30-55% win rate at filters-on is close to
  breakeven-to-mildly-profitable, not the ~90% win rate claimed in the transcript.
  The gap is consistent with the multi-timeframe drill-down (4H->15m->5m->3m) and
  discretionary "best R:R trade of the day" selection that this mechanical version
  does not replicate — see the script's module docstring.
- This is a rule-based approximation, not a replication of the trader's real
  execution.

"""
Quick walk-forward backtest of the liquidity-sweep strategy on Delta candles.
Reports: signals found, wins, losses, win-rate, and expectancy in R.

Run:  python -m bot.backtest --tf 1h --bars 1500
"""

from __future__ import annotations

import argparse
import time

from .config import Config
from .delta_client import DeltaClient
from .structure import detect_signal

TF_SECONDS = {"5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}


def run(tf: str, bars: int) -> None:
    cfg = Config()
    client = DeltaClient(cfg.api_key or "x", cfg.api_secret or "x", cfg.base_url)
    end = int(time.time())
    start = end - TF_SECONDS[tf] * (bars + 5)
    candles = client.get_candles(cfg.symbol, tf, start, end)
    print(f"loaded {len(candles)} {tf} candles for {cfg.symbol}")

    need = cfg.range_lookback + cfg.vol_lookback + 5
    trades = []  # (kind, side, R-result)

    for i in range(need, len(candles) - 1):
        window = candles[: i + 1]
        sig = detect_signal(
            window,
            range_lookback=cfg.range_lookback,
            vol_lookback=cfg.vol_lookback,
            vol_factor=cfg.vol_factor,
            edge_band=cfg.edge_band,
            reclaim_buffer=cfg.reclaim_buffer,
            flip_buffer=cfg.flip_buffer,
        )
        if sig is None:
            continue

        entry = sig.entry
        stop = sig.stop
        r = abs(entry - stop)
        if r <= 0:
            continue
        tp = entry + r * cfg.tp_r_multiple if sig.side == "buy" else entry - r * cfg.tp_r_multiple

        # Walk forward: did TP or SL hit first?
        outcome = None
        for fwd in candles[i + 1 :]:
            if sig.side == "buy":
                if fwd["low"] <= stop:
                    outcome = -1.0
                    break
                if fwd["high"] >= tp:
                    outcome = cfg.tp_r_multiple
                    break
            else:
                if fwd["high"] >= stop:
                    outcome = -1.0
                    break
                if fwd["low"] <= tp:
                    outcome = cfg.tp_r_multiple
                    break
        if outcome is not None:
            trades.append((sig.kind, sig.side, outcome))

    if not trades:
        print("no signals in range")
        return

    wins = [t for t in trades if t[2] > 0]
    losses = [t for t in trades if t[2] < 0]
    total_r = sum(t[2] for t in trades)
    print("-" * 56)
    print(f"signals found : {len(trades)}")
    print(f"wins          : {len(wins)}")
    print(f"losses        : {len(losses)}")
    print(f"win-rate      : {100 * len(wins) / len(trades):.1f}%")
    print(f"net result    : {total_r:+.2f}R  (avg {total_r / len(trades):+.2f}R/trade)")
    print("-" * 56)
    for kind in sorted({t[0] for t in trades}):
        sub = [t for t in trades if t[0] == kind]
        w = sum(1 for t in sub if t[2] > 0)
        print(f"  {kind:12s} n={len(sub):3d}  wins={w:3d}  net={sum(t[2] for t in sub):+.2f}R")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="1h", choices=list(TF_SECONDS))
    ap.add_argument("--bars", type=int, default=1500)
    args = ap.parse_args()
    run(args.tf, args.bars)

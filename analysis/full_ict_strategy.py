"""Full ICT / Smart Money Concepts playbook backtest: combine every major
concept in one mechanical setup, not just one isolated rule.

Bullish setup ("sweep -> BOS -> FVG/OTE"):
  L_prev(low) -> H_before(high) -> L(low, L < L_prev: SWEEPS the prior
  low's resting liquidity) -> H_after(high, H_after > H_before: BREAK OF
  STRUCTURE confirming the reversal). The impulse leg is L -> H_after.
  Entry = retracement into a bullish Fair Value Gap inside that leg,
  filtered to the DISCOUNT half (below the leg's 50% level) - the
  "Optimal Trade Entry" idea. Stop = below the sweep wick. Target =
  fixed R-multiple.

Bearish setup is the exact mirror (sweep of a high, BOS down, bearish
FVG in the PREMIUM half, stop above the sweep wick).

This is tested against two baselines on the *same* sweep+BOS events,
to find out which piece of the confluence (if any) is doing real work:
  - "BOS only": enter immediately at BOS confirmation, same stop, same
    R-multiple targets, no FVG/discount-premium filter at all.
  - "random control": same number of trades, random entry bar/direction,
    stop distance resampled from the real setups, same R targets.
"""
import random

import numpy as np

from smc_backtest import INSTRUMENTS, load
from pressure_formula import build_alternating_swings

FRACTAL_N = 2
STOP_BUFFER = 0.0005
RISK_PCT_PER_TRADE = 0.01
STARTING_CAPITAL = 10_000.0
HORIZON_BARS = 200
FILL_HORIZON_BARS = 100      # bars allowed for price to retrace into the FVG
TARGET_RR = [1.5, 2.0, 3.0]
N_RANDOM_TRIALS = 100


def detect_ict_setups(df, fractal_n=FRACTAL_N):
    swings = build_alternating_swings(df, fractal_n)
    setups = []
    for k in range(2, len(swings) - 1):
        s0, s1, s2, s3 = swings[k - 2], swings[k - 1], swings[k], swings[k + 1]
        types = (s0[1], s1[1], s2[1], s3[1])
        if types == ("low", "high", "low", "high") and s2[2] < s0[2] and s3[2] > s1[2]:
            setups.append({"direction": "bullish", "sweep_idx": s2[0], "sweep_price": s2[2],
                            "bos_idx": s3[0], "bos_price": s3[2]})
        elif types == ("high", "low", "high", "low") and s2[2] > s0[2] and s3[2] < s1[2]:
            setups.append({"direction": "bearish", "sweep_idx": s2[0], "sweep_price": s2[2],
                            "bos_idx": s3[0], "bos_price": s3[2]})
    return setups


def find_best_fvg(df, start_idx, end_idx, direction, midpoint):
    """Deepest-discount (bullish) / highest-premium (bearish) FVG inside
    [start_idx, end_idx] that lies fully on the discount/premium side of
    the leg's 50% midpoint. None if no qualifying gap exists."""
    high, low = df["high"].values, df["low"].values
    best = None
    for i in range(max(start_idx + 1, 2), min(end_idx, len(df) - 1)):
        if direction == "bullish" and low[i + 1] > high[i - 1]:
            gap_lo, gap_hi = high[i - 1], low[i + 1]
            if gap_hi <= midpoint and (best is None or gap_lo < best[0]):
                best = (gap_lo, gap_hi)
        if direction == "bearish" and high[i + 1] < low[i - 1]:
            gap_lo, gap_hi = high[i + 1], low[i - 1]
            if gap_lo >= midpoint and (best is None or gap_hi > best[1]):
                best = (gap_lo, gap_hi)
    return best


def walk_trade(df, entry_idx, entry_price, stop_price, target_price, direction, horizon):
    high, low, close = df["high"].values, df["low"].values, df["close"].values
    risk = abs(entry_price - stop_price)
    end = min(entry_idx + 1 + horizon, len(df))
    for j in range(entry_idx + 1, end):
        if direction == "bullish":
            if low[j] <= stop_price:
                return -1.0, "loss"
            if high[j] >= target_price:
                return (target_price - entry_price) / risk, "win"
        else:
            if high[j] >= stop_price:
                return -1.0, "loss"
            if low[j] <= target_price:
                return (entry_price - target_price) / risk, "win"
    last = close[end - 1]
    pnl = (last - entry_price) if direction == "bullish" else (entry_price - last)
    return pnl / risk, "timeout"


def simulate_full_setup(df, setups, rr):
    high, low = df["high"].values, df["low"].values
    trades = []
    for s in setups:
        midpoint = (s["sweep_price"] + s["bos_price"]) / 2
        fvg = find_best_fvg(df, s["sweep_idx"], s["bos_idx"], s["direction"], midpoint)
        if fvg is None:
            continue
        gap_lo, gap_hi = fvg
        entry_price = (gap_lo + gap_hi) / 2

        fill_end = min(s["bos_idx"] + 1 + FILL_HORIZON_BARS, len(df))
        entry_idx = None
        for j in range(s["bos_idx"] + 1, fill_end):
            if low[j] <= gap_hi and high[j] >= gap_lo:
                entry_idx = j
                break
        if entry_idx is None:
            continue

        if s["direction"] == "bullish":
            stop_price = s["sweep_price"] * (1 - STOP_BUFFER)
            risk = entry_price - stop_price
            if risk <= 0:
                continue
            target_price = entry_price + rr * risk
        else:
            stop_price = s["sweep_price"] * (1 + STOP_BUFFER)
            risk = stop_price - entry_price
            if risk <= 0:
                continue
            target_price = entry_price - rr * risk

        r, outcome = walk_trade(df, entry_idx, entry_price, stop_price, target_price, s["direction"], HORIZON_BARS)
        trades.append({"r": r, "outcome": outcome})
    return trades


def simulate_bos_only(df, setups, rr):
    close = df["close"].values
    trades = []
    for s in setups:
        entry_idx = s["bos_idx"]
        entry_price = close[entry_idx]
        if s["direction"] == "bullish":
            stop_price = s["sweep_price"] * (1 - STOP_BUFFER)
            risk = entry_price - stop_price
            if risk <= 0:
                continue
            target_price = entry_price + rr * risk
        else:
            stop_price = s["sweep_price"] * (1 + STOP_BUFFER)
            risk = stop_price - entry_price
            if risk <= 0:
                continue
            target_price = entry_price - rr * risk
        r, outcome = walk_trade(df, entry_idx, entry_price, stop_price, target_price, s["direction"], HORIZON_BARS)
        trades.append({"r": r, "outcome": outcome})
    return trades


def simulate_random(df, n_trades, risk_pcts, rr, seed):
    rng = random.Random(seed)
    close = df["close"].values
    trades = []
    for _ in range(n_trades):
        idx = rng.randint(50, len(df) - HORIZON_BARS - 2)
        direction = rng.choice(["bullish", "bearish"])
        entry_price = close[idx]
        risk_pct = rng.choice(risk_pcts)
        if risk_pct <= 0:
            continue
        if direction == "bullish":
            stop_price = entry_price * (1 - risk_pct)
            target_price = entry_price + rr * (entry_price - stop_price)
        else:
            stop_price = entry_price * (1 + risk_pct)
            target_price = entry_price - rr * (stop_price - entry_price)
        r, outcome = walk_trade(df, idx, entry_price, stop_price, target_price, direction, HORIZON_BARS)
        trades.append({"r": r, "outcome": outcome})
    return trades


def summarize(trades, label):
    if not trades:
        return {"label": label, "n": 0}
    rs = np.array([t["r"] for t in trades])
    wins = sum(1 for t in trades if t["outcome"] == "win")
    equity, peak, max_dd = STARTING_CAPITAL, STARTING_CAPITAL, 0.0
    for r in rs:
        equity *= (1 + RISK_PCT_PER_TRADE * r)
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak)
    return {
        "label": label, "n": len(trades), "win_rate": wins / len(trades),
        "avg_r": float(rs.mean()), "total_r": float(rs.sum()),
        "final_equity": equity, "total_return_pct": (equity / STARTING_CAPITAL - 1) * 100,
        "max_drawdown_pct": max_dd * 100,
    }


def print_summary(s):
    if s["n"] == 0:
        print(f"  {s['label']}: no trades")
        return
    print(f"  {s['label']}: n={s['n']} win_rate={s['win_rate']:.1%} avg_R={s['avg_r']:+.3f} "
          f"total_R={s['total_r']:+.1f} final_equity=${s['final_equity']:,.0f} "
          f"({s['total_return_pct']:+.1f}%) max_drawdown={s['max_drawdown_pct']:.1f}%")


def run_instrument(instrument):
    df = load(instrument)
    setups = detect_ict_setups(df)
    print(f"\n=== {instrument} ({len(df)} candles, {len(setups)} sweep+BOS structure setups) ===")

    for rr in TARGET_RR:
        print(f" -- target {rr}R --")
        full_trades = simulate_full_setup(df, setups, rr)
        s_full = summarize(full_trades, f"full setup (sweep+BOS+FVG+OTE, {rr}R)")
        print_summary(s_full)

        bos_trades = simulate_bos_only(df, setups, rr)
        s_bos = summarize(bos_trades, f"BOS only, no FVG filter ({rr}R)")
        print_summary(s_bos)

        close = df["close"].values
        risk_pcts = [abs(close[s["bos_idx"]] - s["sweep_price"]) / close[s["bos_idx"]] for s in setups]
        risk_pcts = [r for r in risk_pcts if r > 0] or [0.01]
        n_trades = s_full["n"] if s_full["n"] else len(setups)
        rand_summaries = [summarize(simulate_random(df, n_trades, risk_pcts, rr, seed), "random")
                           for seed in range(N_RANDOM_TRIALS)]
        rand_summaries = [r for r in rand_summaries if r["n"]]
        if rand_summaries and s_full["n"]:
            rand_avg_rs = [r["avg_r"] for r in rand_summaries]
            rand_mean, rand_std = float(np.mean(rand_avg_rs)), float(np.std(rand_avg_rs))
            z = (s_full["avg_r"] - rand_mean) / rand_std if rand_std > 0 else float("nan")
            print(f"    random control ({len(rand_summaries)} trials, n~{n_trades}/trial): "
                  f"avg_R={rand_mean:+.3f}±{rand_std:.3f}  z(full vs random)={z:.2f}")


if __name__ == "__main__":
    for inst in INSTRUMENTS:
        run_instrument(inst)

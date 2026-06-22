"""Backtest the 'sweep/BOS swing price / 2.6 = reaction level' strategy.

Mechanical rules (locked in from conversation, since the social-media
description was a single anecdote, not a spec):

- Swing high/low = 5-bar fractal (FRACTAL_N bars on each side).
- A swing only becomes "active" FRACTAL_N bars after it forms (no
  lookahead) and stays active until price interacts with it.
- Bearish event: price wicks above (sweep) or closes above (BOS) the
  active swing high -> projected level = swing_high_price / 2.6.
- Bullish event: price wicks below (sweep) or closes below (BOS) the
  active swing low -> projected level = swing_low_price * 2.6.
- A "hit" = price trades within HIT_TOL of the projected level within
  HORIZON_BARS bars of the event. A "reaction" = after the hit, price
  moves away from the level by REACTION_MOVE within REACTION_BARS.

Baselines (fixed divisors + random draws) are run on the *same* events
so we can tell whether 2.6 has any edge over chance, not just whether
the rule "hits" in isolation.
"""
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
INSTRUMENTS = ["BTC_USDT", "ETH_USDT", "SOL_USDT"]

FRACTAL_N = 2          # bars each side defining a swing (5-bar fractal)
HIT_TOL = 0.0025        # 0.25% proximity counts as touching the level
HORIZON_BARS = 384      # ~4 days on 15m to reach the level
REACTION_MOVE = 0.01    # 1% move away from level counts as a reaction
REACTION_BARS = 20      # within ~5h of the hit
FIXED_BASELINES = [1.618, 2.0, 2.618, 3.0, 4.236, 1.272]
N_RANDOM_TRIALS = 200
RANDOM_RANGE = (1.5, 4.5)


def load(instrument: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / f"{instrument}_15m.csv")
    df = df.sort_values("timestamp_ms").reset_index(drop=True)
    return df


def find_fractals(df: pd.DataFrame, n: int = FRACTAL_N):
    high, low = df["high"].values, df["low"].values
    m = len(df)
    swing_high_idx, swing_low_idx = [], []
    for i in range(n, m - n):
        window_h = high[i - n : i + n + 1]
        if high[i] == window_h.max() and np.argmax(window_h) == n:
            swing_high_idx.append(i)
        window_l = low[i - n : i + n + 1]
        if low[i] == window_l.min() and np.argmin(window_l) == n:
            swing_low_idx.append(i)
    return swing_high_idx, swing_low_idx


@dataclass
class Event:
    idx: int
    direction: str   # 'bearish' (swing high broken) or 'bullish' (swing low broken)
    kind: str        # 'sweep' or 'bos'
    level_price: float
    leg_range: float | None  # |this swing - preceding opposite swing|, for Fib-extension-style projection


def detect_events(df: pd.DataFrame, n: int = FRACTAL_N) -> list[Event]:
    swing_high_idx, swing_low_idx = find_fractals(df, n)
    confirm_high = {i + n: i for i in swing_high_idx}
    confirm_low = {i + n: i for i in swing_low_idx}

    high, low, close = df["high"].values, df["low"].values, df["close"].values
    swing_high_price = {i: high[i] for i in swing_high_idx}
    swing_low_price = {i: low[i] for i in swing_low_idx}

    active_high_idx = active_low_idx = None
    consumed_high = consumed_low = True
    last_confirmed_low_price = last_confirmed_high_price = None
    events = []

    for i in range(len(df)):
        if i in confirm_high:
            active_high_idx = confirm_high[i]
            consumed_high = False
            active_high_leg = (
                abs(swing_high_price[active_high_idx] - last_confirmed_low_price)
                if last_confirmed_low_price is not None
                else None
            )
            last_confirmed_high_price = swing_high_price[active_high_idx]
        if i in confirm_low:
            active_low_idx = confirm_low[i]
            consumed_low = False
            active_low_leg = (
                abs(last_confirmed_high_price - swing_low_price[active_low_idx])
                if last_confirmed_high_price is not None
                else None
            )
            last_confirmed_low_price = swing_low_price[active_low_idx]

        if active_high_idx is not None and not consumed_high:
            level = swing_high_price[active_high_idx]
            if high[i] > level:
                kind = "sweep" if close[i] < level else "bos"
                events.append(Event(i, "bearish", kind, level, active_high_leg))
                consumed_high = True

        if active_low_idx is not None and not consumed_low:
            level = swing_low_price[active_low_idx]
            if low[i] < level:
                kind = "sweep" if close[i] > level else "bos"
                events.append(Event(i, "bullish", kind, level, active_low_leg))
                consumed_low = True

    return events


def project_level(event: Event, divisor: float) -> float:
    """Raw-price interpretation: divide/multiply the absolute swing price."""
    return event.level_price / divisor if event.direction == "bearish" else event.level_price * divisor


def project_level_range(event: Event, divisor: float) -> float | None:
    """Fib-extension-style interpretation: project divisor-scaled leg range from the broken swing."""
    if event.leg_range is None:
        return None
    offset = event.leg_range / divisor
    return event.level_price - offset if event.direction == "bearish" else event.level_price + offset


def test_hit_and_reaction(df: pd.DataFrame, event: Event, target: float):
    high, low, close = df["high"].values, df["low"].values, df["close"].values
    end = min(event.idx + 1 + HORIZON_BARS, len(df))
    lo_band, hi_band = target * (1 - HIT_TOL), target * (1 + HIT_TOL)

    for j in range(event.idx + 1, end):
        if low[j] <= hi_band and high[j] >= lo_band:
            hit_idx = j
            reaction = False
            r_end = min(hit_idx + 1 + REACTION_BARS, len(df))
            for k in range(hit_idx, r_end):
                if event.direction == "bearish" and close[k] >= target * (1 + REACTION_MOVE):
                    reaction = True
                    break
                if event.direction == "bullish" and close[k] <= target * (1 - REACTION_MOVE):
                    reaction = True
                    break
            return True, hit_idx - event.idx, reaction
    return False, None, False


def evaluate_divisor(df: pd.DataFrame, events: list[Event], divisor: float, mode: str = "raw"):
    hits, bars_list, reactions, evaluated = 0, [], 0, 0
    for ev in events:
        target = project_level(ev, divisor) if mode == "raw" else project_level_range(ev, divisor)
        if target is None:
            continue
        evaluated += 1
        hit, bars, reacted = test_hit_and_reaction(df, ev, target)
        if hit:
            hits += 1
            bars_list.append(bars)
            if reacted:
                reactions += 1
    return {
        "divisor": divisor,
        "n_events": evaluated,
        "hit_rate": hits / evaluated if evaluated else 0.0,
        "avg_bars_to_hit": float(np.mean(bars_list)) if bars_list else None,
        "reaction_rate_given_hit": reactions / hits if hits else 0.0,
    }


def run_instrument(instrument: str, mode: str):
    df = load(instrument)
    events = detect_events(df)
    label = "raw price / 2.6" if mode == "raw" else "leg-range / 2.6 (Fib-extension style)"
    print(f"\n=== {instrument} [{label}] ({len(df)} candles, {len(events)} structure events) ===")

    result_26 = evaluate_divisor(df, events, 2.6, mode)
    print(f"  2.6 divisor: n={result_26['n_events']} hit_rate={result_26['hit_rate']:.1%}  "
          f"avg_bars_to_hit={result_26['avg_bars_to_hit']}  "
          f"reaction_given_hit={result_26['reaction_rate_given_hit']:.1%}")

    for d in FIXED_BASELINES:
        r = evaluate_divisor(df, events, d, mode)
        print(f"  {d} divisor: hit_rate={r['hit_rate']:.1%}  "
              f"reaction_given_hit={r['reaction_rate_given_hit']:.1%}")

    random.seed(42)
    random_hit_rates = []
    for _ in range(N_RANDOM_TRIALS):
        d = random.uniform(*RANDOM_RANGE)
        r = evaluate_divisor(df, events, d, mode)
        random_hit_rates.append(r["hit_rate"])
    random_mean, random_std = float(np.mean(random_hit_rates)), float(np.std(random_hit_rates))
    z = (result_26["hit_rate"] - random_mean) / random_std if random_std > 0 else float("nan")
    print(f"  random divisor baseline ({N_RANDOM_TRIALS} trials, range {RANDOM_RANGE}): "
          f"mean_hit_rate={random_mean:.1%} std={random_std:.1%}")
    print(f"  2.6 vs random baseline: z={z:.2f}")

    return {
        "instrument": instrument,
        "mode": mode,
        "n_events": result_26["n_events"],
        "result_26": result_26,
        "random_mean": random_mean,
        "random_std": random_std,
        "z": z,
    }


if __name__ == "__main__":
    print("##### Variant A: raw swing price divided by 2.6 #####")
    summary_raw = [run_instrument(inst, "raw") for inst in INSTRUMENTS]

    print("\n##### Variant B: leg-range divided by 2.6, projected from breakout (Fib-extension style) #####")
    summary_range = [run_instrument(inst, "range") for inst in INSTRUMENTS]

    print("\n=== Combined verdict ===")
    for label, summary in [("raw price / 2.6", summary_raw), ("leg-range / 2.6", summary_range)]:
        print(f"\n -- {label} --")
        for s in summary:
            verdict = "edge over random" if s["z"] > 1.96 else "no statistically significant edge"
            print(f"  {s['instrument']}: 2.6 hit_rate={s['result_26']['hit_rate']:.1%} "
                  f"vs random {s['random_mean']:.1%}±{s['random_std']:.1%} (z={s['z']:.2f}) -> {verdict}")

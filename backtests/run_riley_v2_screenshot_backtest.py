#!/usr/bin/env python3
"""Riley Coleman "5-Step Checklist" v2 (+ Part 2 fast-fill/BOS-volume
filter) — reproduces ONE specific Strategy Test Bench console screenshot,
at the user's explicit request. delta_scalper/riley.py (the live bot's
strategy module) only implements Part 1 — Part 2 lives in
pine/riley_checklist_v2.pine and here; this script reuses riley.py's
swing/FVG helpers and adds the Part 2 filter inline rather than modifying
the live bot's shared strategy class.

Screenshot settings: BTCUSD 15m, $1000 start, swing width k=3, min FVG
0.2x ATR, Part 2 filter ON (max fill delay 3 bars, min BOS volume 1.3x
20-bar avg), swing-trail exit, 24% risk/trade, 200x leverage cap.
Screenshot result (console's 270-day trimmed 15m window): 89 trades,
47.2% win rate, PF 1.09, +19772.97% return, -89.5% MAX DRAWDOWN. This
script uses the repo's standard FULL 540-day window instead (same
convention as backtests/run_riley_backtest.py) for a larger sample: 141
trades, 46.8% win rate, PF 1.06, +116334.19% return, -89.5% MAX DRAWDOWN
— same verdict, bigger sample, same catastrophic drawdown. Set DAYS=270
below to reproduce the screenshot's exact trade count instead.

⚠️ HONESTY NOTE: PF 1.09 is barely above break-even — over 89 trades this
edge is thin and easily within noise. The +19,772.97% headline return and
the -89.5% drawdown are both the same leverage/position-size artifact:
risking 24% of equity on every trade at up to 200x notional. A -89.5%
drawdown means a realistic losing streak leaves the account with a tenth
of its value; this is not a validated, sizeable edge, it is a coin-flip-
adjacent strategy run at gambler's-ruin position sizing. This script
reproduces the exact tested numbers for the record; it is a
backtest/research script, not wired into the live-trading bot
(delta_scalper/bot.py), and delta_scalper/config.py's hard
risk_per_trade > 2% safety cap is untouched by this file.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from delta_scalper.config import Config  # noqa: E402
from delta_scalper.delta_client import DeltaClient  # noqa: E402
from delta_scalper.riley import _swing_state, _has_fvg, trailing_swing_levels  # noqa: E402
from _screenshot_common import (  # noqa: E402
    TAKER, SLIP, BTCUSD_CONTRACT_VALUE, atr_arr, size_lots, stats,
    print_report, fetch_candles,
)

SYMBOL = "BTCUSD"
DAYS = 540
EQ0 = 1000.0
SWING_K = 3
FVG_MULT = 0.2
RETEST_WINDOW = 12
FILL_WINDOW = 12
MAX_HOLD = 2000
USE_P2 = True
MAX_FILL_DELAY = 3
MIN_VOL_RATIO = 1.3
RISK_PCT = 0.24    # 24% of equity per trade — matches the screenshot, NOT a safe setting
LEVERAGE = 200


def run(df, k, fvg_mult, retest_window, fill_window, eq0, risk_pct, leverage,
        use_p2, max_fill_delay, min_vol_ratio, max_hold=2000):
    o, h, l, c, v = df.open.values, df.high.values, df.low.values, df.close.values, df.volume.values
    n = len(df)
    atr_v = atr_arr(df)
    cost = 2 * (TAKER + SLIP)
    hp, ha, hp2, ha2, lp, la, lp2, la2, seq = _swing_state(df, k)
    trail_lo, trail_hi = trailing_swing_levels(seq, n)
    vol_sma = pd.Series(v).rolling(20).mean().values
    equity, trades, used_until = eq0, [], 0
    t = 0
    while t < n - 2:
        if t < used_until or np.isnan(hp[t]) or np.isnan(hp2[t]) or np.isnan(lp[t]) or np.isnan(lp2[t]):
            t += 1
            continue
        d = 0
        if ha[t] > la[t] and hp2[t] < hp[t] and lp2[t] < lp[t]:
            d, ref_price, break_level = -1, hp[t], lp[t]
            leg_start, leg_end, fvg_kind = la[t], ha[t], "bull"
        elif la[t] > ha[t] and lp2[t] > lp[t] and hp2[t] > hp[t]:
            d, ref_price, break_level = 1, lp[t], hp[t]
            leg_start, leg_end, fvg_kind = ha[t], la[t], "bear"
        if d == 0:
            t += 1
            continue
        if not _has_fvg(h, l, atr_v, leg_start, leg_end, fvg_kind, fvg_mult):
            t += 1
            continue
        bos_bar = None
        for j in range(t, min(t + 200, n - 1)):
            if (c[j] < break_level) if d == -1 else (c[j] > break_level):
                bos_bar = j
                break
        if bos_bar is None:
            t += 1
            continue
        w0 = bos_bar + 1
        w1 = min(bos_bar + 1 + retest_window, n - 1)
        if w1 <= w0:
            t += 1
            continue
        if d == -1:
            rb = w0 + int(np.argmax(h[w0:w1]))
            bounce_extreme = h[rb]
            failed = bounce_extreme < ref_price
        else:
            rb = w0 + int(np.argmin(l[w0:w1]))
            bounce_extreme = l[rb]
            failed = bounce_extreme > ref_price
        if not failed:
            t += 1
            continue
        entry_level = l[rb] if d == -1 else h[rb]
        fill = None
        for j in range(rb + 1, min(rb + 1 + fill_window, n)):
            if (l[j] <= entry_level) if d == -1 else (h[j] >= entry_level):
                fill = j
                break
            if (h[j] > ref_price) if d == -1 else (l[j] < ref_price):
                break
        if fill is None:
            t += 1
            continue
        entry = entry_level * (1 + SLIP * d)
        stop = bounce_extreme
        stop_d = abs(entry - stop)
        if stop_d <= 0 or stop_d / entry < 3 * cost:
            t = fill + 1
            continue
        if use_p2:
            fill_delay = fill - rb
            if fill_delay > max_fill_delay:
                t = fill + 1
                continue
            vol_ratio_bos = v[bos_bar] / vol_sma[bos_bar] if vol_sma[bos_bar] > 0 else 1.0
            if vol_ratio_bos < min_vol_ratio:
                t = fill + 1
                continue
        notional, lots = size_lots(equity, entry, stop_d, risk_pct, leverage, BTCUSD_CONTRACT_VALUE)
        cur_stop, exit_px, exit_j = stop, None, fill
        for ex in range(fill, min(fill + max_hold, n)):
            exit_j = ex
            if (l[ex] <= cur_stop) if d == 1 else (h[ex] >= cur_stop):
                exit_px = cur_stop
                break
            cand = trail_lo[ex] if d == 1 else trail_hi[ex]
            if cand == cand:  # not NaN
                if d == 1 and cand > cur_stop:
                    cur_stop = cand
                if d == -1 and cand < cur_stop:
                    cur_stop = cand
        if exit_px is None:
            exit_j = min(fill + max_hold, n - 1)
            exit_px = c[exit_j]
        ret = d * (exit_px - entry) / entry - cost
        pnl = notional * ret
        equity = max(0.0, equity + pnl)
        trades.append({"dir": d, "entry_bar": fill, "exit_bar": exit_j,
                        "lots": lots, "pnl": pnl, "equity": equity,
                        # per-unit-notional return and stop distance, so
                        # R-multiples (Kelly math) are exact: R = ret/stop
                        "ret_frac": ret, "stop_frac": stop_d / entry})
        used_until = exit_j + 1
        t = exit_j + 1
    return pd.DataFrame(trades)


def main():
    cfg = Config()
    client = DeltaClient(cfg.base_url)
    print(f"fetching {SYMBOL} 15m x {DAYS}d ...")
    df = fetch_candles(client, SYMBOL, "15m", DAYS)
    trades = run(df, SWING_K, FVG_MULT, RETEST_WINDOW, FILL_WINDOW, EQ0,
                 RISK_PCT, LEVERAGE, USE_P2, MAX_FILL_DELAY, MIN_VOL_RATIO, MAX_HOLD)
    st = stats(trades, EQ0)
    print_report(
        f"Riley v2 (+Part2) — {SYMBOL} 15m, k={SWING_K}, fvgMult={FVG_MULT}, "
        f"risk={RISK_PCT*100:.0f}%, leverage={LEVERAGE}x", st)
    out = os.path.join(os.path.dirname(__file__), "..", "reports", "riley_v2_screenshot_trades.csv")
    trades.to_csv(out, index=False)
    print(f"trade log -> {out}")


if __name__ == "__main__":
    main()

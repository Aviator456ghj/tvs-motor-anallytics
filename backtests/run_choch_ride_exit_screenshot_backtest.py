#!/usr/bin/env python3
"""CHoCH — ride exit — reproduces ONE specific Strategy Test Bench console
screenshot, at the user's explicit request. This is a DIFFERENT entry mode
from backtests/run_choch_backtest.py (which tests the "limit at 0.5 zone,
fixed 2.618 target" mode) — this is the candle-confirmation entry +
swing-trail ride exit mode (delta_scalper/choch.py's
ChochFibStrategy._signal_candle_confirm with choch_exit_mode="trend").

Screenshot settings: BTCUSD 1h, $1000 start, swing width k=5, stop buffer
0.8x the A->B swing leg, min displacement 1x ATR, void level (disrespect)
0.786, require-engulf confirmation on, 100% risk/trade, 200x leverage cap.
Screenshot result: 27 trades, 40.7% win rate, PF 6.93, +18551.92% return,
-55.2% MAX DRAWDOWN.

⚠️ HONESTY NOTE: this is the SAME 27-trade sequence as the validated 10%-
risk run of this exact setup (buf=0.9, PF 8.56, +206.96%, only -5.3% max
drawdown) — same win rate, same trades, just sized ~10x bigger. PF is even
slightly LOWER here (6.93 vs 8.56) because whole-lot rounding and the
200x-leverage notional cap bind differently at this size. The
+18,551.92% headline is a leverage artifact, not a better edge, and a
-55.2% drawdown is a real risk of ruin. This script reproduces the exact
tested numbers for the record; it is a backtest/research script, not
wired into the live-trading bot (delta_scalper/bot.py), and
delta_scalper/config.py's hard risk_per_trade > 2% safety cap (enforced
in Config.validate(), called only by bot.py before it places real orders)
is untouched by this file.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from delta_scalper.choch import find_choch_setups  # noqa: E402
from delta_scalper.config import Config  # noqa: E402
from delta_scalper.delta_client import DeltaClient  # noqa: E402
from _screenshot_common import (  # noqa: E402
    TAKER, SLIP, BTCUSD_CONTRACT_VALUE, atr_arr, swing_trail, size_lots,
    stats, print_report, fetch_candles,
)

SYMBOL = "BTCUSD"
DAYS = 540
EQ0 = 1000.0
SWING_K = 5
ZONE = 0.5            # entry retracement zone (unchanged from validated default)
BUF = 0.8              # stop buffer, as a FRACTION of the A->B swing leg (screenshot value)
DISRESPECT_R = 0.786   # a close past this level voids the setup
MIN_BREAK_ATR = 1.0
WAIT = 120
MAX_HOLD = 2000
REQUIRE_ENGULF = True
RISK_PCT = 1.00        # 100% of equity per trade — matches the screenshot, NOT a safe setting
LEVERAGE = 200


def run(df, k, zone, buf, disrespect_r, min_break_atr, wait, eq0, risk_pct,
        leverage, max_hold=2000, require_engulf=True):
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    n = len(df)
    trail_lo, trail_hi = swing_trail(df, k)
    a = atr_arr(df)
    cost = 2 * (TAKER + SLIP)
    equity, trades, used_until = eq0, [], 0
    for s in find_choch_setups(df, k):
        if equity <= 1e-9:
            break
        d, A, B = s["dir"], s["A"], s["B"]
        rng = abs(B - A)
        start = s["ready_bar"] + 1
        if rng <= 0 or start >= n or start < used_until:
            continue
        bb = s["break_bar"]
        break_str = abs(c[bb] - B) / a[bb] if a[bb] > 0 else float("nan")
        if break_str != break_str or break_str < min_break_atr:
            continue
        z_near = B - d * zone * rng
        void_lvl = B - d * disrespect_r * rng
        fill = None
        for j in range(start, min(start + wait, n - 1)):
            if (c[j] > B) if d == 1 else (c[j] < B):
                break
            if (c[j] < void_lvl) if d == 1 else (c[j] > void_lvl):
                break
            touched = (l[j] <= z_near) if d == 1 else (h[j] >= z_near)
            counter = (c[j] < o[j]) if d == 1 else (c[j] > o[j])
            if touched and counter:
                ok = (c[j + 1] > o[j + 1]) if d == 1 else (c[j + 1] < o[j + 1])
                if ok:
                    if require_engulf:
                        engulfed = (o[j + 1] <= c[j] and c[j + 1] >= o[j]) if d == 1 else \
                                   (o[j + 1] >= c[j] and c[j + 1] <= o[j])
                        if not engulfed:
                            break
                    fill = j + 1
                    break
        if fill is None or fill >= n - 1:
            continue
        entry = c[fill] * (1 + SLIP * d)
        hard_stop = A - d * buf * rng
        stop_d = abs(entry - hard_stop)
        if stop_d <= 0 or stop_d / entry < 3 * cost:
            continue
        notional, lots = size_lots(equity, entry, stop_d, risk_pct, leverage, BTCUSD_CONTRACT_VALUE)
        remaining, pnl_tot, exit_j = 1.0, 0.0, fill
        for j in range(fill, min(fill + max_hold, n)):
            exit_j = j
            if (l[j] <= hard_stop) if d == 1 else (h[j] >= hard_stop):
                pnl_tot = notional * (d * (hard_stop - entry) / entry - cost)
                remaining = 0.0
                break
            trail = trail_lo[j] if d == 1 else trail_hi[j]
            if trail == trail:
                active = (trail > A) if d == 1 else (trail < A)
                if active and ((c[j] < trail) if d == 1 else (c[j] > trail)):
                    px = c[j] * (1 - SLIP * d)
                    pnl_tot = notional * (d * (px - entry) / entry - cost)
                    remaining = 0.0
                    break
        if remaining > 0:
            pnl_tot = notional * (d * (c[exit_j] - entry) / entry - cost)
        equity = max(0.0, equity + pnl_tot)
        trades.append({"dir": d, "entry_bar": fill, "exit_bar": exit_j,
                        "lots": lots, "pnl": pnl_tot, "equity": equity})
        used_until = exit_j + 1
    return pd.DataFrame(trades)


def main():
    cfg = Config()
    client = DeltaClient(cfg.base_url)
    print(f"fetching {SYMBOL} 1h x {DAYS}d ...")
    df = fetch_candles(client, SYMBOL, "1h", DAYS)
    trades = run(df, SWING_K, ZONE, BUF, DISRESPECT_R, MIN_BREAK_ATR, WAIT,
                 EQ0, RISK_PCT, LEVERAGE, MAX_HOLD, REQUIRE_ENGULF)
    st = stats(trades, EQ0)
    print_report(
        f"CHoCH ride exit — {SYMBOL} 1h, k={SWING_K}, buf={BUF}xleg, "
        f"disrespectR={DISRESPECT_R}, risk={RISK_PCT*100:.0f}%, leverage={LEVERAGE}x", st)
    out = os.path.join(os.path.dirname(__file__), "..", "reports", "choch_ride_exit_screenshot_trades.csv")
    trades.to_csv(out, index=False)
    print(f"trade log -> {out}")


if __name__ == "__main__":
    main()

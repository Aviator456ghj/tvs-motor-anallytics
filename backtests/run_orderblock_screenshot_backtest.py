#!/usr/bin/env python3
"""Order Block Retest — reproduces ONE specific Strategy Test Bench console
screenshot, at the user's explicit request. This is NOT the repo's
validated Order Block config (pine/order_block_retest.pine's own header
documents the validated numbers: BTCUSD 85 trades, PF 1.75, +23.49%,
0.5% risk/3x leverage).

Screenshot settings: BTCUSD 1h, $100 start, swing width k=4, stop buffer
0.9x ATR, min displacement 1x ATR, max wait 120 bars, 15% risk/trade,
200x leverage cap.
Screenshot result: 106 trades, 25.5% win rate, PF 1.28, +3075.83% return,
-77.0% MAX DRAWDOWN.

⚠️ HONESTY NOTE: PF 1.28 is a thin edge (barely above break-even once you
account for variance in a 106-trade sample). The +3075% headline number is
almost entirely a position-sizing artifact — risking 15% of equity on
every trade at up to 200x notional turns a modest edge into an enormous
number AND an enormous drawdown. A -77% drawdown means a realistic string
of losses wipes most of the account. This script reproduces the exact
tested numbers for the record; it is a backtest/research script, not
wired into the live-trading bot (delta_scalper/bot.py), and
delta_scalper/config.py's hard risk_per_trade > 2% safety cap is
untouched by this file.
"""
import os
import sys

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
EQ0 = 100.0
SWING_K = 4
BUF_ATR = 0.9
MIN_BREAK_ATR = 1.0
WAIT = 120
MAX_HOLD = 2000
RISK_PCT = 0.15   # 15% of equity per trade — matches the screenshot, NOT the validated 0.5%
LEVERAGE = 200


def run(df, k, buf_atr, min_break_atr, wait, eq0, risk_pct, leverage, max_hold=2000):
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    n = len(df)
    trail_lo, trail_hi = swing_trail(df, k)
    a = atr_arr(df)
    cost = 2 * (TAKER + SLIP)
    equity, trades, used_until = eq0, [], 0
    for s in find_choch_setups(df, k):
        if equity <= 1e-9:
            break
        d, A_bar, bb, start = s["dir"], s["A_bar"], s["break_bar"], s["ready_bar"] + 1
        if start >= n or start < used_until:
            continue
        break_str = abs(c[bb] - s["B"]) / a[bb] if a[bb] > 0 else float("nan")
        if break_str != break_str or break_str < min_break_atr:  # NaN check
            continue
        ob = None
        for j in range(bb - 1, A_bar, -1):
            is_counter = (c[j] < o[j]) if d == 1 else (c[j] > o[j])
            if is_counter:
                ob = j
                break
        if ob is None:
            continue
        ob_lo, ob_hi = l[ob], h[ob]
        fill = None
        for j in range(bb + 1, min(bb + 1 + wait, n - 1)):
            touched = (l[j] <= ob_hi) if d == 1 else (h[j] >= ob_lo)
            if not touched:
                continue
            confirm = (c[j] > o[j]) if d == 1 else (c[j] < o[j])
            if confirm:
                fill = j
                break
            if (d == 1 and c[j] < ob_lo) or (d == -1 and c[j] > ob_hi):
                break
        if fill is None or fill >= n - 1:
            continue
        entry = c[fill] * (1 + SLIP * d)
        hard_stop = (ob_lo - buf_atr * a[fill]) if d == 1 else (ob_hi + buf_atr * a[fill])
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
            if trail == trail:  # not NaN
                active = (trail > hard_stop) if d == 1 else (trail < hard_stop)
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
    import pandas as pd
    return pd.DataFrame(trades)


def main():
    cfg = Config()
    client = DeltaClient(cfg.base_url)
    print(f"fetching {SYMBOL} 1h x {DAYS}d ...")
    df = fetch_candles(client, SYMBOL, "1h", DAYS)
    trades = run(df, SWING_K, BUF_ATR, MIN_BREAK_ATR, WAIT, EQ0, RISK_PCT, LEVERAGE, MAX_HOLD)
    st = stats(trades, EQ0)
    print_report(
        f"Order Block Retest — {SYMBOL} 1h, k={SWING_K}, bufATR={BUF_ATR}, "
        f"risk={RISK_PCT*100:.0f}%, leverage={LEVERAGE}x", st)
    out = os.path.join(os.path.dirname(__file__), "..", "reports", "orderblock_screenshot_trades.csv")
    trades.to_csv(out, index=False)
    print(f"trade log -> {out}")


if __name__ == "__main__":
    main()

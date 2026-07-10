#!/usr/bin/env python3
"""24/7 trading agent launcher — the exact Strategy Test Bench presets.

This is the "free 24/7 agent": plain Python, no AI calls, no hosting fees.
It runs the repo's existing scalping bot (delta_scalper/bot.py) with one of
the preset configurations below — the exact settings from the Strategy
Test Bench console runs the user validated by hand (BTC and ETH
screenshots, July 2026). It polls Delta Exchange India for each closed
candle, evaluates the strategy, and places trades automatically. Leave it
running on any always-on computer (your PC, a Raspberry Pi, Termux on an
old Android phone) and it works around the clock for the cost of
electricity.

Usage:
    python agents/run_agent.py --list
    python agents/run_agent.py btc-choch-100          # paper mode (default, safe)
    DELTA_LIVE=1 python agents/run_agent.py ...        # LIVE — see warning below

Run it 24/7 (Linux/Mac):
    nohup python agents/run_agent.py btc-choch-100 > agent.log 2>&1 &

⚠️ RISK WARNING — READ BEFORE RUNNING ANYTHING LIVE ⚠️
These presets reproduce backtests whose huge returns came with equally
huge drawdowns (-55% to -90% of the account at the worst point). That is
the position sizing (15-100% of equity risked per trade at up to 200x
leverage), not a stronger edge. For that reason the bot's hard safety cap
in delta_scalper/config.py REFUSES to run any preset with risk > 2% in
LIVE mode — they are paper-only by design. To trade a preset live, pass
--risk 2 (or lower) to override the preset's sizing with something
survivable. The strategy logic is identical either way; only the bet size
changes.

TradingView note: TradingView has no public order-placement API — no tool
can "place trades in TradingView" directly. The Pine scripts in pine/
mirror these same strategies for TradingView charts (signals + alerts);
actual automated execution happens here, against Delta Exchange directly.
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Presets: field overrides applied on top of the repo's Config defaults.
# Every number is taken verbatim from the corresponding console screenshot.
PRESETS = {
    # ── BTCUSD ────────────────────────────────────────────────────────────
    "btc-orderblock-15": dict(
        _desc="Order Block Retest, BTCUSD 1h — k=4, stop 0.9xATR, 15% risk, 200x. "
              "Screenshot: 106 trades, 25.5% WR, PF 1.28, +3076%, -77.0% max DD.",
        symbols=("BTCUSD",), strategy="orderblock", timeframe_minutes=60,
        ob_swing_k=4, ob_buf_atr=0.9, ob_min_break_atr=1.0, ob_wait_bars=120,
        risk_per_trade=0.15, max_leverage=200,
    ),
    "btc-choch-100": dict(
        _desc="CHoCH ride exit, BTCUSD 1h — k=5, stop 0.8xleg, engulf on, 100% risk, "
              "200x. Screenshot: 27 trades, 40.7% WR, PF 6.93, +18552%, -55.2% max DD.",
        symbols=("BTCUSD",), strategy="choch", timeframe_minutes=60,
        choch_swing_k=5, choch_entry_r=0.5, choch_disrespect_r=0.786,
        choch_stop_buffer=0.8, choch_min_break_atr=1.0, choch_wait_bars=120,
        choch_exit_mode="trend", choch_entry_mode="candle",
        choch_require_engulf=True,
        risk_per_trade=1.00, max_leverage=200,
    ),
    "btc-riley-24": dict(
        _desc="Riley v2 + Part2, BTCUSD 15m — k=3, FVG 0.2xATR, 24% risk, 200x. "
              "Screenshot: 89 trades, 47.2% WR, PF 1.09, +19773%, -89.5% max DD.",
        symbols=("BTCUSD",), strategy="riley", timeframe_minutes=15,
        riley_swing_k=3, riley_fvg_mult=0.2, riley_exit_mode="trail",
        riley_use_p2=True, riley_max_fill_delay=3, riley_min_vol_ratio=1.3,
        risk_per_trade=0.24, max_leverage=200,
    ),
    # ── ETHUSD ────────────────────────────────────────────────────────────
    "eth-choch-50": dict(
        _desc="CHoCH ride exit, ETHUSD 1h — k=5, stop 0.10xleg, engulf on, 50% risk, "
              "200x. Screenshot: 26 trades, 42.3% WR, PF 9.53, +51270%, -74.7% max DD.",
        symbols=("ETHUSD",), strategy="choch", timeframe_minutes=60,
        choch_swing_k=5, choch_entry_r=0.5, choch_disrespect_r=0.786,
        choch_stop_buffer=0.10, choch_min_break_atr=1.0, choch_wait_bars=120,
        choch_exit_mode="trend", choch_entry_mode="candle",
        choch_require_engulf=True,
        risk_per_trade=0.50, max_leverage=200,
    ),
    "eth-riley-26": dict(
        _desc="Riley v2 + Part2, ETHUSD 15m — k=3, FVG 0.2xATR, 26% risk, 200x. "
              "Screenshot: 101 trades, 45.5% WR, PF 1.05, +100501%, -89.9% max DD.",
        symbols=("ETHUSD",), strategy="riley", timeframe_minutes=15,
        riley_swing_k=3, riley_fvg_mult=0.2, riley_exit_mode="trail",
        riley_use_p2=True, riley_max_fill_delay=3, riley_min_vol_ratio=1.3,
        risk_per_trade=0.26, max_leverage=200,
    ),
    # NOTE: the ETH "Swing Catcher k=8, stop buffer 0.0001xATR, 15% risk"
    # screenshot is deliberately NOT a preset. A 0.0001xATR buffer puts the
    # stop essentially AT the swing price, which makes the risk-based sizing
    # formula degenerate: nearly every trade slams into the 200x leverage
    # cap, so the "15% risk" label doesn't describe what it actually does
    # (max-leverage sizing on a PF 1.08 coin flip, -86.6% max DD). If you
    # want it anyway, say so and it can be added with the same warning.
}


def build_config(preset_name: str, risk_override: float | None):
    from delta_scalper.config import Config

    overrides = dict(PRESETS[preset_name])
    desc = overrides.pop("_desc")
    cfg = Config()
    for field, value in overrides.items():
        setattr(cfg, field, value)
    if risk_override is not None:
        cfg.risk_per_trade = risk_override / 100.0
    # one loss at this sizing would trip the default 2%-day limit instantly
    # and halt the preset after its first trade; scale the circuit breaker
    # to the preset's own per-trade risk (still halts on a bad streak).
    if "DELTA_DAILY_LOSS_LIMIT" not in os.environ:
        cfg.daily_loss_limit = max(cfg.daily_loss_limit, min(0.95, 3 * cfg.risk_per_trade))
    # keep separate state/journal files per preset so runs don't collide
    if "DELTA_STATE_FILE" not in os.environ:
        cfg.state_file = f"scalper_state_{preset_name}.json"
    return cfg, desc


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("preset", nargs="?", choices=sorted(PRESETS), metavar="PRESET",
                    help="one of: " + ", ".join(sorted(PRESETS)))
    ap.add_argument("--list", action="store_true", help="show all presets and exit")
    ap.add_argument("--risk", type=float, default=None, metavar="PCT",
                    help="override the preset's risk%% per trade (required <= 2 for live)")
    args = ap.parse_args()

    if args.list or not args.preset:
        print("Available presets (exact Strategy Test Bench screenshot configs):\n")
        for name, p in sorted(PRESETS.items()):
            print(f"  {name}\n      {p['_desc']}\n")
        print("Paper mode is the default. LIVE requires DELTA_LIVE=1 + API keys,")
        print("and refuses risk > 2%: add e.g. --risk 1 to run a preset live.")
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    cfg, desc = build_config(args.preset, args.risk)
    print(f"\npreset: {args.preset}\n  {desc}\n")
    if not cfg.live and cfg.risk_per_trade > 0.02:
        print("  MODE: PAPER (simulated). This preset's sizing produced a "
              "-55% to -90% class max drawdown in backtest — it is blocked "
              "from live trading; use --risk 2 or lower to trade it live.\n")

    from delta_scalper.bot import ScalpingBot
    ScalpingBot(cfg).run_forever()


if __name__ == "__main__":
    main()

"""Unit tests for the deterministic pieces: indicators, risk, order-book imbalance."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trading_agent.brokers.base import OrderBook, Side  # noqa: E402
from trading_agent.risk.manager import RiskManager  # noqa: E402
from trading_agent.strategy.indicators import atr_pct, ema, momentum_pct  # noqa: E402


def test_ema_constant_series():
    assert ema([5, 5, 5, 5, 5], 3) == 5.0


def test_momentum_direction():
    up = momentum_pct([100, 101, 102, 103, 104, 105], 5)
    down = momentum_pct([105, 104, 103, 102, 101, 100], 5)
    assert up > 0 and down < 0


def test_atr_nonzero_when_volatile():
    highs = [10, 11, 12, 11, 13]
    lows = [9, 10, 10, 9, 11]
    closes = [9.5, 10.5, 11, 10, 12]
    assert atr_pct(highs, lows, closes) > 0


def test_orderbook_imbalance():
    ob = OrderBook("X", bids=[(100, 20)], asks=[(101, 5)])
    assert ob.imbalance() == 4.0


def test_risk_sizing_respects_risk_pct():
    rm = RiskManager({"capital_per_broker": 1000, "risk_per_trade_pct": 1.0,
                      "stop_loss_pct": 0.5})
    qty = rm.size_for(100.0)
    # risk amount = 10; per-unit risk = 100 * 0.5% = 0.5 -> qty = 20
    assert abs(qty - 20.0) < 1e-9


def test_risk_take_profit_and_stop():
    rm = RiskManager({"capital_per_broker": 1000, "take_profit_pct": 1.0,
                      "stop_loss_pct": 1.0, "use_trailing_stop": False,
                      "max_hold_seconds": 9999})
    pos = rm.open_position("X", Side.BUY, 1, 100.0)
    assert rm.check_exit(pos, 101.5) == "take-profit"
    assert rm.check_exit(pos, 98.5) == "stop-loss"
    assert rm.check_exit(pos, 100.2) is None


def test_daily_loss_halts_trading():
    # 2% of 1000 capital => halt once daily loss reaches -20.
    rm = RiskManager({"capital_per_broker": 1000, "max_daily_loss_pct": 2.0})
    rm.realized_pnl = -15.0
    ok, _ = rm.can_open(0)
    assert ok is True
    rm.realized_pnl = -25.0
    ok, _ = rm.can_open(0)
    assert ok is False


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)

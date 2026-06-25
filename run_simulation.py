"""Run the full engine on synthetic data - no broker, no creds, no internet.

    python run_simulation.py [seconds]

Watch it stream ticks, fire scalp entries, and exit on TP/SL/trailing/time.
This is the fastest way to confirm everything is wired correctly.
"""

import sys
import time

from trading_agent.brokers.simulator import make_simulator
from trading_agent.engine.engine import TradingEngine
from trading_agent.risk.manager import RiskManager
from trading_agent.strategy.scalper import MicroScalper
from trading_agent.config import load_config


def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    cfg = load_config()
    symbols = ["SIMUSD"]

    broker = make_simulator(symbols)
    # Loosen thresholds a touch so the demo actually trades on synthetic data.
    scfg = dict(cfg["strategy"])
    scfg.update(ob_imbalance_threshold=1.3, momentum_threshold_pct=0.01, min_atr_pct=0.0,
                ema_fast=3, ema_slow=8)
    strategy = MicroScalper(scfg)
    risk = RiskManager(cfg["risk"])
    engine = TradingEngine(broker, symbols, strategy, risk,
                           {**cfg["engine"], "timeframe_seconds": 1})
    engine.start()

    print(f"Simulating for {duration}s... (Ctrl+C to stop early)")
    try:
        time.sleep(duration)
    except KeyboardInterrupt:
        pass
    engine.stop()
    print(f"\nDone. Day PnL = {risk.realized_pnl:.4f} over {risk.trades_today} trades.")


if __name__ == "__main__":
    main()

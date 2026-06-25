"""Entrypoint: build brokers + engines from config and run them.

Usage:
    python -m trading_agent.main            # uses config.yaml
    TRADING_MODE=live python -m trading_agent.main   # DANGER: real orders
"""

from __future__ import annotations

import signal
import sys
import time

from .config import Credentials, load_config, trading_mode
from .brokers.base import Broker
from .brokers.paper import PaperBroker
from .engine.engine import TradingEngine
from .risk.manager import RiskManager
from .strategy.scalper import MicroScalper
from .utils.logging import get_logger


def build_real_broker(kind: str, creds: Credentials, bcfg: dict) -> Broker:
    if kind == "delta":
        from .brokers.delta import DeltaBroker
        return DeltaBroker(creds.delta_api_key, creds.delta_api_secret, creds.delta_base_url)
    if kind == "zerodha":
        from .brokers.zerodha import ZerodhaBroker
        return ZerodhaBroker(creds.kite_api_key, creds.kite_api_secret,
                             creds.kite_access_token, bcfg.get("exchange", "NFO"))
    raise ValueError(f"unknown broker {kind}")


def main() -> int:
    cfg = load_config()
    creds = Credentials()
    mode = trading_mode()
    log = get_logger("main", cfg["engine"].get("log_level", "INFO"))

    log.info("=" * 60)
    log.info("Rule-based scalping agent starting | MODE = %s", mode.upper())
    if mode != "live":
        log.info("PAPER MODE: orders are simulated, no real money at risk.")
    else:
        log.warning("LIVE MODE: real orders will be sent to the broker!")
    log.info("=" * 60)

    engines: list[TradingEngine] = []
    threads = []

    for kind, bcfg in cfg["brokers"].items():
        if not bcfg.get("enabled"):
            continue
        symbols = bcfg.get("symbols", [])
        if not symbols:
            continue
        try:
            real = build_real_broker(kind, creds, bcfg)
        except Exception as e:  # noqa: BLE001
            log.error("Could not build broker %s: %s", kind, e)
            continue

        broker: Broker = real if mode == "live" else PaperBroker(real)
        strategy = MicroScalper(cfg["strategy"])
        risk = RiskManager(cfg["risk"])
        engine_cfg = {**cfg["engine"], "timeframe_seconds": cfg["strategy"]["timeframe_seconds"]}
        engine = TradingEngine(broker, symbols, strategy, risk, engine_cfg)
        engines.append(engine)
        threads.append(engine.start())

    if not engines:
        log.error("No brokers enabled in config.yaml. Nothing to do.")
        return 1

    stop = {"flag": False}

    def handle_sigint(signum, frame):
        log.info("Shutdown requested, flattening positions...")
        stop["flag"] = True

    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    try:
        while not stop["flag"]:
            time.sleep(0.5)
    finally:
        for e in engines:
            e.stop()
        log.info("Stopped cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

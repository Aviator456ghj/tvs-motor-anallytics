#!/usr/bin/env python3
"""Entry point for the Delta Exchange scalping agent.

Paper mode (default, no risk):   python run_bot.py
Live mode (real orders):         DELTA_LIVE=1 python run_bot.py

Credentials (live mode only): set DELTA_API_KEY and DELTA_API_SECRET.
"""
import logging
import sys

from delta_scalper.bot import ScalpingBot
from delta_scalper.config import Config


def main():
    cfg = Config()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(cfg.log_file),
        ],
    )
    if cfg.live:
        print("!" * 70)
        print("LIVE MODE — this will place REAL orders with REAL money.")
        print("Past backtest performance was marginal; there is NO guarantee of profit.")
        print("!" * 70)
        confirm = input("Type 'I UNDERSTAND' to continue: ")
        if confirm.strip() != "I UNDERSTAND":
            sys.exit("aborted")
    ScalpingBot(cfg).run_forever()


if __name__ == "__main__":
    main()

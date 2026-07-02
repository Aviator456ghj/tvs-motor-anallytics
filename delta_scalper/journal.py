"""Trade journal: every closed trade is appended to a CSV together with the
setup context it was taken in, so failures can be analyzed and the strategy
refined instead of repeating the same mistakes.

Analyze it any time with:  python backtests/analyze_journal.py [journal.csv]
"""
import csv
import logging
import os

log = logging.getLogger("delta.journal")

FIELDS = [
    "closed_at", "symbol", "strategy", "side", "entry", "exit", "notional",
    "pnl", "r_outcome", "exit_reason",
    # setup context (filled from Signal.context when present)
    "setup", "sweep_bar_time", "level", "wick_ratio", "sweep_depth_atr",
    "vol_ratio", "trend_align", "stop_pct",
]


class TradeJournal:
    def __init__(self, path: str = "trade_journal.csv"):
        self.path = path

    def record(self, row: dict):
        exists = os.path.exists(self.path)
        try:
            with open(self.path, "a", newline="") as f:
                w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
                if not exists:
                    w.writeheader()
                w.writerow(row)
        except OSError as e:
            log.warning("could not write trade journal: %s", e)

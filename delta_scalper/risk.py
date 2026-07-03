"""Risk management: position sizing, daily loss limit, kill switch."""
import json
import logging
import os
import time
from dataclasses import dataclass

from .config import Config

log = logging.getLogger("delta.risk")


@dataclass
class RiskDecision:
    allowed: bool
    reason: str = ""
    notional: float = 0.0


class RiskManager:
    """Persists daily PnL and loss streaks across restarts via a state file."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.state = {
            "day": self._today(),
            "day_start_equity": None,
            "realized_pnl_today": 0.0,
            "consecutive_losses": 0,
            "halted_until": 0,
        }
        self._load()

    @staticmethod
    def _today() -> str:
        return time.strftime("%Y-%m-%d", time.gmtime())

    def _load(self):
        if os.path.exists(self.cfg.state_file):
            try:
                with open(self.cfg.state_file) as f:
                    self.state.update(json.load(f))
            except (json.JSONDecodeError, OSError) as e:
                log.warning("could not load state file: %s", e)

    def _save(self):
        with open(self.cfg.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def _roll_day(self, equity: float):
        today = self._today()
        if self.state["day"] != today:
            self.state.update(
                day=today,
                day_start_equity=equity,
                realized_pnl_today=0.0,
            )
            self._save()
        if self.state["day_start_equity"] is None:
            self.state["day_start_equity"] = equity
            self._save()

    def check_new_trade(self, equity: float, stop_distance_frac: float) -> RiskDecision:
        """stop_distance_frac: |entry - stop| / entry."""
        self._roll_day(equity)
        now = time.time()
        if now < self.state["halted_until"]:
            return RiskDecision(False, "halted (kill switch active)")
        day_dd = self.state["realized_pnl_today"] / max(self.state["day_start_equity"], 1e-9)
        if day_dd <= -self.cfg.daily_loss_limit:
            return RiskDecision(
                False, f"daily loss limit hit ({day_dd:.2%}), no trades until tomorrow"
            )
        if self.state["consecutive_losses"] >= self.cfg.max_consecutive_losses:
            # cool off for 6 hours after a losing streak
            self.state["halted_until"] = now + 6 * 3600
            self.state["consecutive_losses"] = 0
            self._save()
            return RiskDecision(False, "loss streak — cooling off 6h")
        if stop_distance_frac <= 0:
            return RiskDecision(False, "invalid stop distance")
        if self.cfg.sizing == "compound":
            # full balance staked every trade, compounding wins and losses
            notional = equity * self.cfg.compound_leverage
        else:
            notional = equity * self.cfg.risk_per_trade / stop_distance_frac
            notional = min(notional, equity * self.cfg.max_leverage)
        return RiskDecision(True, "ok", notional)

    def record_trade(self, pnl: float):
        self.state["realized_pnl_today"] += pnl
        if pnl <= 0:
            self.state["consecutive_losses"] += 1
        else:
            self.state["consecutive_losses"] = 0
        self._save()
        log.info(
            "trade pnl=%.4f, today=%.4f, loss streak=%d",
            pnl, self.state["realized_pnl_today"], self.state["consecutive_losses"],
        )

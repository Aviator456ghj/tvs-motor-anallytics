"""Risk management: position sizing, TP/SL/trailing/time exits, daily limits.

This is the safety layer. Even if the strategy misbehaves, the RiskManager
caps how much can be lost per trade and per day, and force-closes stale scalps.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from ..brokers.base import Side
from ..utils.logging import get_logger

log = get_logger("risk")


@dataclass
class ManagedPosition:
    symbol: str
    side: Side
    quantity: float
    entry_price: float
    opened_at: float
    take_profit: float
    stop_loss: float
    trail_high_water: float = 0.0   # best favourable price seen
    trailing_active: bool = False


class RiskManager:
    def __init__(self, cfg: dict):
        self.capital = float(cfg.get("capital_per_broker", 1000))
        self.risk_pct = float(cfg.get("risk_per_trade_pct", 0.5))
        self.max_open = int(cfg.get("max_open_positions", 1))
        self.max_daily_loss_pct = float(cfg.get("max_daily_loss_pct", 3.0))
        self.max_trades = int(cfg.get("max_trades_per_day", 40))
        self.tp_pct = float(cfg.get("take_profit_pct", 0.12))
        self.sl_pct = float(cfg.get("stop_loss_pct", 0.08))
        self.use_trail = bool(cfg.get("use_trailing_stop", True))
        self.trail_activate_pct = float(cfg.get("trail_activate_pct", 0.08))
        self.trail_pct = float(cfg.get("trail_pct", 0.05))
        self.max_hold = float(cfg.get("max_hold_seconds", 120))

        self.realized_pnl = 0.0
        self.trades_today = 0
        self._day = time.strftime("%Y-%m-%d")

    # ---- daily guards ----
    def _roll_day(self) -> None:
        today = time.strftime("%Y-%m-%d")
        if today != self._day:
            log.info("New trading day. Resetting daily counters.")
            self._day = today
            self.realized_pnl = 0.0
            self.trades_today = 0

    def can_open(self, open_count: int) -> tuple[bool, str]:
        self._roll_day()
        if open_count >= self.max_open:
            return False, "max open positions reached"
        if self.trades_today >= self.max_trades:
            return False, "max trades/day reached"
        loss_limit = -(self.capital * self.max_daily_loss_pct / 100.0)
        if self.realized_pnl <= loss_limit:
            return False, f"daily loss limit hit (pnl={self.realized_pnl:.2f})"
        return True, "ok"

    def size_for(self, price: float) -> float:
        """Quantity such that a stop-out loses ~risk_pct of capital."""
        risk_amount = self.capital * self.risk_pct / 100.0
        per_unit_risk = price * self.sl_pct / 100.0
        if per_unit_risk <= 0:
            return 0.0
        return max(0.0, risk_amount / per_unit_risk)

    def open_position(self, symbol: str, side: Side, qty: float, price: float) -> ManagedPosition:
        if side is Side.BUY:
            tp = price * (1 + self.tp_pct / 100.0)
            sl = price * (1 - self.sl_pct / 100.0)
        else:
            tp = price * (1 - self.tp_pct / 100.0)
            sl = price * (1 + self.sl_pct / 100.0)
        self.trades_today += 1
        return ManagedPosition(symbol, side, qty, price, time.time(), tp, sl,
                               trail_high_water=price)

    def check_exit(self, pos: ManagedPosition, price: float) -> str | None:
        """Return an exit reason if TP/SL/trail/time triggers, else None."""
        now = time.time()
        if now - pos.opened_at >= self.max_hold:
            return "time-stop"

        if pos.side is Side.BUY:
            if price >= pos.take_profit:
                return "take-profit"
            if price <= pos.stop_loss:
                return "stop-loss"
            self._update_trail_long(pos, price)
            if pos.trailing_active and price <= pos.stop_loss:
                return "trailing-stop"
        else:
            if price <= pos.take_profit:
                return "take-profit"
            if price >= pos.stop_loss:
                return "stop-loss"
            self._update_trail_short(pos, price)
            if pos.trailing_active and price >= pos.stop_loss:
                return "trailing-stop"
        return None

    def _update_trail_long(self, pos: ManagedPosition, price: float) -> None:
        if not self.use_trail:
            return
        pos.trail_high_water = max(pos.trail_high_water, price)
        gain_pct = (pos.trail_high_water - pos.entry_price) / pos.entry_price * 100.0
        if gain_pct >= self.trail_activate_pct:
            pos.trailing_active = True
            new_sl = pos.trail_high_water * (1 - self.trail_pct / 100.0)
            pos.stop_loss = max(pos.stop_loss, new_sl)

    def _update_trail_short(self, pos: ManagedPosition, price: float) -> None:
        if not self.use_trail:
            return
        pos.trail_high_water = min(pos.trail_high_water, price)
        gain_pct = (pos.entry_price - pos.trail_high_water) / pos.entry_price * 100.0
        if gain_pct >= self.trail_activate_pct:
            pos.trailing_active = True
            new_sl = pos.trail_high_water * (1 + self.trail_pct / 100.0)
            pos.stop_loss = min(pos.stop_loss, new_sl)

    def record_close(self, pos: ManagedPosition, exit_price: float) -> float:
        if pos.side is Side.BUY:
            pnl = (exit_price - pos.entry_price) * pos.quantity
        else:
            pnl = (pos.entry_price - exit_price) * pos.quantity
        self.realized_pnl += pnl
        log.info("Closed %s %s pnl=%.4f (day pnl=%.4f, trades=%d)",
                 pos.side.value, pos.symbol, pnl, self.realized_pnl, self.trades_today)
        return pnl

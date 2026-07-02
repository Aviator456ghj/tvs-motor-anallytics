"""Paper-trading broker: simulates fills against live market prices so the
agent can run 24/7 with zero financial risk. This is the default mode."""
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field

from .config import Config
from .journal import TradeJournal

log = logging.getLogger("delta.paper")


@dataclass
class PaperPosition:
    symbol: str
    side: str            # "buy" | "sell"
    notional: float
    entry_price: float
    stop_loss: float
    take_profit: float
    opened_at: float
    expires_at: float    # time-based exit
    context: dict | None = None  # setup features for the trade journal


@dataclass
class PaperAccount:
    equity: float
    position: dict | None = None
    pending: dict | None = None   # resting limit order awaiting a retest fill
    trades: list = field(default_factory=list)


class PaperBroker:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.path = cfg.state_file.replace(".json", "_paper.json")
        self.account = PaperAccount(equity=cfg.paper_start_equity)
        self.journal = TradeJournal()
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path) as f:
                    data = json.load(f)
                self.account = PaperAccount(**data)
            except (json.JSONDecodeError, TypeError, OSError) as e:
                log.warning("could not load paper state: %s", e)

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(asdict(self.account), f, indent=2)

    @property
    def equity(self) -> float:
        return self.account.equity

    @property
    def position(self) -> PaperPosition | None:
        return PaperPosition(**self.account.position) if self.account.position else None

    def place_limit(self, symbol: str, side: str, notional: float, limit: float,
                    stop_loss: float, take_profit: float, expiry_seconds: float,
                    max_hold_seconds: float, context: dict | None = None):
        """Rest a limit order that fills only when price trades to it."""
        self.account.pending = {
            "symbol": symbol, "side": side, "notional": notional, "limit": limit,
            "stop_loss": stop_loss, "take_profit": take_profit,
            "expires_at": time.time() + expiry_seconds,
            "max_hold_seconds": max_hold_seconds,
            "context": context,
        }
        self._save()
        log.info("[PAPER] resting %s limit %s notional=%.2f @ %.2f",
                 side, symbol, notional, limit)

    def check_pending(self, last_price: float):
        """Fill, expire, or keep the resting limit order."""
        p = self.account.pending
        if p is None:
            return
        if time.time() >= p["expires_at"]:
            self.account.pending = None
            self._save()
            log.info("[PAPER] limit on %s expired unfilled", p["symbol"])
            return
        touched = (p["side"] == "buy" and last_price <= p["limit"]) or \
                  (p["side"] == "sell" and last_price >= p["limit"])
        if touched:
            self.account.pending = None
            self.open_position(
                p["symbol"], p["side"], p["notional"], p["limit"],
                p["stop_loss"], p["take_profit"], p["max_hold_seconds"],
                is_limit=True, context=p.get("context"),
            )

    def open_position(self, symbol: str, side: str, notional: float, price: float,
                      stop_loss: float, take_profit: float, max_hold_seconds: float,
                      is_limit: bool = False, context: dict | None = None):
        # maker fills happen exactly at the limit price; market entries slip
        slip = 1.0 if is_limit else 1 + self.cfg.slippage * (1 if side == "buy" else -1)
        entry = price * slip
        now = time.time()
        self.account.position = asdict(PaperPosition(
            symbol=symbol, side=side, notional=notional, entry_price=entry,
            stop_loss=stop_loss, take_profit=take_profit,
            opened_at=now, expires_at=now + max_hold_seconds,
            context=context,
        ))
        # entry fee (assume maker)
        self.account.equity -= notional * self.cfg.maker_fee
        self._save()
        log.info("[PAPER] opened %s %s notional=%.2f @ %.2f sl=%.2f tp=%.2f",
                 side, symbol, notional, entry, stop_loss, take_profit)

    def check_exit(self, last_price: float, high: float | None = None,
                   low: float | None = None) -> float | None:
        """Returns realized pnl if the position closed, else None."""
        pos = self.position
        if pos is None:
            return None
        hi = high if high is not None else last_price
        lo = low if low is not None else last_price
        exit_price = None
        reason = ""
        if pos.side == "buy":
            if lo <= pos.stop_loss:
                exit_price, reason = pos.stop_loss, "stop-loss"
            elif hi >= pos.take_profit:
                exit_price, reason = pos.take_profit, "take-profit"
        else:
            if hi >= pos.stop_loss:
                exit_price, reason = pos.stop_loss, "stop-loss"
            elif lo <= pos.take_profit:
                exit_price, reason = pos.take_profit, "take-profit"
        if exit_price is None and time.time() >= pos.expires_at:
            exit_price, reason = last_price, "time-exit"
        if exit_price is None:
            return None
        direction = 1 if pos.side == "buy" else -1
        slip = 1 - self.cfg.slippage * direction
        exit_eff = exit_price * slip
        gross = pos.notional * direction * (exit_eff - pos.entry_price) / pos.entry_price
        fee = pos.notional * self.cfg.taker_fee
        pnl = gross - fee
        self.account.equity += pnl
        self.account.trades.append({
            "symbol": pos.symbol, "side": pos.side, "entry": pos.entry_price,
            "exit": exit_eff, "notional": pos.notional, "pnl": pnl,
            "reason": reason, "closed_at": time.time(),
        })
        stop_frac = abs(pos.entry_price - pos.stop_loss) / pos.entry_price
        self.journal.record({
            "closed_at": time.time(), "symbol": pos.symbol,
            "strategy": self.cfg.strategy, "side": pos.side,
            "entry": pos.entry_price, "exit": exit_eff,
            "notional": pos.notional, "pnl": round(pnl, 4),
            "r_outcome": round(pnl / max(pos.notional * stop_frac, 1e-9), 3),
            "exit_reason": reason,
            **(pos.context or {}),
        })
        self.account.position = None
        self._save()
        log.info("[PAPER] closed %s via %s pnl=%.4f equity=%.2f",
                 pos.symbol, reason, pnl, self.account.equity)
        return pnl

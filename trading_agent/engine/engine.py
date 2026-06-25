"""The decision loop: wires data -> strategy -> risk -> broker for one broker.

One TradingEngine runs per active broker. Market data arrives asynchronously on
the broker's websocket thread and updates MarketState; the engine's own loop
runs every `loop_interval_ms`, evaluates the strategy, and acts.
"""

from __future__ import annotations

import threading
import time

from ..brokers.base import Broker, Order, Side
from ..data.feed import MarketState
from ..risk.manager import ManagedPosition, RiskManager
from ..strategy.base import Strategy
from ..utils.logging import get_logger


class TradingEngine:
    def __init__(self, broker: Broker, symbols: list[str], strategy: Strategy,
                 risk: RiskManager, cfg: dict):
        self.broker = broker
        self.symbols = symbols
        self.strategy = strategy
        self.risk = risk
        self.loop_interval = float(cfg.get("loop_interval_ms", 50)) / 1000.0
        tf = int(cfg.get("timeframe_seconds", 5))
        self.states: dict[str, MarketState] = {
            s: MarketState(s, timeframe_seconds=tf) for s in symbols
        }
        self.open: dict[str, ManagedPosition] = {}
        self.log = get_logger(f"engine:{broker.name}")
        self._running = False

    # ---- data callbacks (websocket thread) ----
    def _on_tick(self, tick):
        st = self.states.get(tick.symbol)
        if st:
            st.on_tick(tick)

    def _on_book(self, book):
        st = self.states.get(book.symbol)
        if st:
            st.on_book(book)

    # ---- lifecycle ----
    def start(self) -> threading.Thread:
        self.broker.connect()
        self.broker.subscribe(self.symbols, self._on_tick, self._on_book)
        self._running = True
        t = threading.Thread(target=self._loop, name=f"loop-{self.broker.name}", daemon=True)
        t.start()
        self.log.info("Engine started for %s on %s", self.broker.name, self.symbols)
        return t

    def stop(self) -> None:
        self._running = False
        # Flatten everything on shutdown - never leave scalps open.
        for sym, pos in list(self.open.items()):
            self._exit(sym, pos, self.states[sym].last_price, "shutdown")
        self.broker.disconnect()

    # ---- core loop ----
    def _loop(self) -> None:
        while self._running:
            t0 = time.time()
            try:
                for sym in self.symbols:
                    self._evaluate_symbol(sym)
            except Exception as e:  # noqa: BLE001 - loop must never die
                self.log.exception("loop error: %s", e)
            elapsed = time.time() - t0
            time.sleep(max(0.0, self.loop_interval - elapsed))

    def _evaluate_symbol(self, sym: str) -> None:
        st = self.states[sym]
        price = st.last_price
        if price <= 0:
            return

        pos = self.open.get(sym)

        # 1) Risk-driven exits take priority over strategy.
        if pos is not None:
            reason = self.risk.check_exit(pos, price)
            if reason:
                self._exit(sym, pos, price, reason)
                return

        sig = self.strategy.evaluate(st, in_position=pos is not None,
                                     position_side=pos.side if pos else None)

        if pos is not None and sig.action == "EXIT":
            self._exit(sym, pos, price, sig.reason)
            return

        if pos is None and sig.action == "ENTER" and sig.side is not None:
            self._enter(sym, sig.side, price, sig.reason)

    def _enter(self, sym: str, side: Side, price: float, reason: str) -> None:
        ok, why = self.risk.can_open(len(self.open))
        if not ok:
            return
        qty = self.risk.size_for(price)
        if qty <= 0:
            return
        order = self.broker.place_order(Order(symbol=sym, side=side, quantity=qty,
                                              order_type="MARKET"))
        if order.status in ("REJECTED",):
            self.log.warning("Entry rejected for %s", sym)
            return
        fill = order.filled_price or price
        self.open[sym] = self.risk.open_position(sym, side, qty, fill)
        self.log.info("ENTER %s %s qty=%.4f @ %.2f | %s", side.value, sym, qty, fill, reason)

    def _exit(self, sym: str, pos: ManagedPosition, price: float, reason: str) -> None:
        from ..brokers.base import Position as BrokerPos
        order = self.broker.close_position(BrokerPos(
            symbol=sym, side=pos.side, quantity=pos.quantity, entry_price=pos.entry_price,
        ))
        fill = order.filled_price or price
        self.risk.record_close(pos, fill)
        self.open.pop(sym, None)
        self.log.info("EXIT %s @ %.2f | %s", sym, fill, reason)

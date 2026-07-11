"""24/7 scalping agent main loop.

Flow (each new closed candle):
  1. fetch candles, evaluate strategy on the closed bar
  2. if flat and a signal fires, ask RiskManager for permission + size
  3. paper mode: simulate; live mode: place a limit entry with bracket SL/TP
  4. between candles, poll price to manage paper exits / time-based exits

Run:  python run_bot.py            (paper mode — default, safe)
      DELTA_LIVE=1 python run_bot.py   (real orders — only after paper validation)
"""
import logging
import math
import time

import pandas as pd

from .config import Config
from .delta_client import DeltaClient
from .paper import PaperBroker
from .risk import RiskManager
from .choch import ChochFibStrategy
from .fib import FibRetracementStrategy
from .order_block import OrderBlockStrategy
from .liquidity_fakeout import LiquidityFakeoutStrategy
from .riley import RileyReversalStrategy, last_confirmed_swings as riley_last_swings
from .strategy import TrendPullbackStrategy
from .structure import MarketStructureStrategy

log = logging.getLogger("delta.bot")

STRATEGIES = {
    "pullback": TrendPullbackStrategy,
    "structure": MarketStructureStrategy,
    "fib": FibRetracementStrategy,
    "choch": ChochFibStrategy,
    "riley": RileyReversalStrategy,
    "orderblock": OrderBlockStrategy,
    "liqfakeout": LiquidityFakeoutStrategy,
}


class ScalpingBot:
    def __init__(self, cfg: Config):
        cfg.validate()
        self.cfg = cfg
        self.client = DeltaClient(cfg.base_url, cfg.api_key, cfg.api_secret)
        if cfg.strategy not in STRATEGIES:
            raise SystemExit(f"unknown DELTA_STRATEGY={cfg.strategy!r}; "
                             f"choose from {sorted(STRATEGIES)}")
        self.strategy = STRATEGIES[cfg.strategy](cfg)
        self.risk = RiskManager(cfg)
        self.paper = PaperBroker(cfg) if not cfg.live else None
        self.products = {}
        self.last_signal_bar: dict[str, int] = {}
        self.live_entry_deadline: dict[str, float] = {}
        self._trail_bar: dict[str, int] = {}

    # ---------- data ----------

    def fetch_closed_candles(self, symbol: str, bars: int = 400) -> pd.DataFrame:
        tf = self.cfg.timeframe_minutes
        now = int(time.time())
        res = "1h" if tf == 60 else f"{tf}m"
        data = self.client.get_candles(symbol, res, now - bars * tf * 60, now)
        df = pd.DataFrame(data)
        if df.empty:
            return df
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        df = df.sort_values("time").reset_index(drop=True)
        # drop the still-forming candle
        current_bucket = now - now % (tf * 60)
        return df[df["time"] < current_bucket].reset_index(drop=True)

    def last_price(self, symbol: str) -> float:
        t = self.client.get_ticker(symbol)
        for key in ("close", "mark_price", "spot_price"):
            if t.get(key):
                return float(t[key])
        raise RuntimeError(f"no price in ticker for {symbol}")

    # ---------- account ----------

    def equity(self) -> float:
        if self.paper:
            return self.paper.equity
        balances = self.client.get_balances()
        for b in balances:
            if b.get("asset_symbol") in ("USD", "USDT"):
                return float(b["available_balance"]) + float(
                    b.get("position_margin", 0) or 0
                )
        raise RuntimeError("no USD/USDT balance found")

    def product(self, symbol: str) -> dict:
        if symbol not in self.products:
            self.products[symbol] = self.client.get_product(symbol)
        return self.products[symbol]

    # ---------- trading ----------

    def try_enter(self, symbol: str, candles: pd.DataFrame):
        sig = self.strategy.signal(candles)
        if sig is None:
            return
        bar_time = int(candles["time"].iloc[-1])
        if self.last_signal_bar.get(symbol) == bar_time:
            return  # already acted on this bar
        self.last_signal_bar[symbol] = bar_time

        equity = self.equity()
        stop_frac = abs(sig.entry_ref - sig.stop_loss) / sig.entry_ref
        decision = self.risk.check_new_trade(equity, stop_frac)
        if not decision.allowed:
            log.info("signal on %s skipped: %s", symbol, decision.reason)
            return
        log.info("ENTRY signal %s %s %s ref=%.2f sl=%.2f tp=%.2f notional=%.2f",
                 sig.side, sig.entry_type, symbol, sig.entry_ref, sig.stop_loss,
                 sig.take_profit, decision.notional)
        if self.cfg.strategy == "choch":
            hold_bars = self.cfg.choch_max_hold_bars
        elif self.cfg.strategy == "orderblock" or (
                self.cfg.strategy == "riley" and self.cfg.riley_exit_mode == "trail"):
            hold_bars = 2000  # trailing rides run for days; don't time-cut them
        else:
            hold_bars = self.cfg.max_hold_bars
        max_hold_s = hold_bars * self.cfg.timeframe_minutes * 60
        if self.paper:
            if sig.entry_type == "limit":
                self.paper.place_limit(
                    symbol, sig.side, decision.notional, sig.entry_ref,
                    sig.stop_loss, sig.take_profit,
                    expiry_seconds=sig.expires_bars * self.cfg.timeframe_minutes * 60,
                    max_hold_seconds=max_hold_s, context=sig.context,
                )
            else:
                self.paper.open_position(
                    symbol, sig.side, decision.notional, sig.entry_ref,
                    sig.stop_loss, sig.take_profit, max_hold_seconds=max_hold_s,
                    context=sig.context,
                )
        else:
            self._place_live(symbol, sig, decision.notional)
            if sig.entry_type == "limit" and sig.expires_bars:
                self.live_entry_deadline[symbol] = (
                    time.time() + sig.expires_bars * self.cfg.timeframe_minutes * 60
                )

    def _place_live(self, symbol: str, sig, notional: float):
        p = self.product(symbol)
        contract_value = float(p["contract_value"])  # in underlying units
        tick = float(p["tick_size"])
        size = max(1, math.floor(notional / (contract_value * sig.entry_ref)))

        def round_tick(x):
            return f"{round(x / tick) * tick:.10f}".rstrip("0").rstrip(".")

        self.client.place_order(
            product_id=p["id"],
            side=sig.side,
            size=size,
            order_type="limit_order",
            limit_price=round_tick(sig.entry_ref),
            time_in_force="gtc",
            bracket_stop_loss_price=round_tick(sig.stop_loss),
            bracket_take_profit_price=round_tick(sig.take_profit),
        )
        log.info("live order placed: %s %s x%d", sig.side, symbol, size)

    def manage_open(self, symbol: str):
        """Paper: check SL/TP/time exits. Live: enforce time-based exit
        (SL/TP are bracket orders handled by the exchange)."""
        if self.paper:
            pos = self.paper.position
            pending = self.paper.account.pending
            involved = (pos and pos.symbol == symbol) or \
                       (pending and pending["symbol"] == symbol)
            if involved:
                price = self.last_price(symbol)
                self.paper.check_pending(price)
                pnl = self.paper.check_exit(price)
                if pnl is not None:
                    self.risk.record_trade(pnl)
                elif pos and ((self.cfg.strategy == "choch" and
                               self.cfg.choch_exit_mode == "trend") or
                              self.cfg.strategy == "orderblock"):
                    pnl = self._trend_ride_exit(symbol, pos)
                    if pnl is not None:
                        self.risk.record_trade(pnl)
                elif pos and self.cfg.strategy == "riley" and \
                        self.cfg.riley_exit_mode == "trail":
                    self._riley_trail_stop(symbol, pos)
        else:
            # cancel a resting limit entry that outlived its validity window
            deadline = self.live_entry_deadline.get(symbol)
            if deadline and time.time() > deadline:
                p = self.product(symbol)
                for order in self.client.get_live_orders(p["id"]):
                    self.client.cancel_order(p["id"], order["id"])
                    log.info("canceled stale entry order %s on %s",
                             order["id"], symbol)
                del self.live_entry_deadline[symbol]
            p = self.product(symbol)
            positions = self.client.get_positions(p["id"])
            size = int(positions.get("size", 0) or 0)
            if size != 0:
                entry_ts = self.last_signal_bar.get(symbol, 0)
                hold_bars = self.cfg.choch_max_hold_bars \
                    if self.cfg.strategy in ("choch", "orderblock") \
                    else self.cfg.max_hold_bars
                max_hold_s = hold_bars * self.cfg.timeframe_minutes * 60
                if entry_ts and time.time() - entry_ts > max_hold_s:
                    side = "sell" if size > 0 else "buy"
                    self.client.close_position(p["id"], abs(size), side)
                    log.info("time-exit: closed %s position of %d", symbol, size)

    def _trend_ride_exit(self, symbol: str, pos) -> float | None:
        """Ride-the-trend exit: close when a 1h candle CLOSES through the
        most recent confirmed swing trail (the opposite change of
        character). Evaluated once per new closed bar."""
        from .choch import last_confirmed_swings
        candles = self.fetch_closed_candles(symbol)
        if candles.empty:
            return None
        newest = int(candles["time"].iloc[-1])
        if self._trail_bar.get(symbol) == newest:
            return None
        self._trail_bar[symbol] = newest
        trail_k = self.cfg.ob_swing_k if self.cfg.strategy == "orderblock" \
            else self.cfg.choch_swing_k
        lo, hi = last_confirmed_swings(candles, trail_k)
        close = float(candles["close"].iloc[-1])
        d = 1 if pos.side == "buy" else -1
        trail = lo if d == 1 else hi
        if trail is None:
            return None
        # only trail once structure has moved past the entry stop (beyond A)
        active = trail > pos.stop_loss if d == 1 else trail < pos.stop_loss
        crossed = close < trail if d == 1 else close > trail
        if active and crossed:
            log.info("trend-ride exit: %s closed through trail %.2f", symbol, trail)
            return self.paper.force_close(close, "trend-exit (opposite CHoCH)")
        return None

    def _riley_trail_stop(self, symbol: str, pos):
        """Swing-ratcheted trailing stop: tighten toward the most recent
        confirmed swing in the trade's favor, never loosen. Evaluated once
        per new closed bar."""
        candles = self.fetch_closed_candles(symbol)
        if candles.empty:
            return
        newest = int(candles["time"].iloc[-1])
        if self._trail_bar.get(symbol) == newest:
            return
        self._trail_bar[symbol] = newest
        lo, hi = riley_last_swings(candles, self.cfg.riley_swing_k)
        cand = lo if pos.side == "buy" else hi
        if cand is not None:
            self.paper.tighten_stop(cand)

    # ---------- main loop ----------

    def run_forever(self):
        cfg = self.cfg
        mode = "LIVE" if cfg.live else "PAPER"
        log.info("starting scalping agent [%s] strategy=%s symbols=%s tf=%dm risk/trade=%.2f%%",
                 mode, cfg.strategy, cfg.symbols, cfg.timeframe_minutes,
                 cfg.risk_per_trade * 100)
        if cfg.strategy in ("structure", "fib", "choch", "riley", "orderblock", "liqfakeout"):
            log.warning("%s strategy: positive but small-sample backtest — "
                        "validate in paper mode before any live size",
                        cfg.strategy)
        last_bar_seen: dict[str, int] = {}
        while True:
            try:
                for symbol in cfg.symbols:
                    self.manage_open(symbol)
                    busy = bool(self.paper and (self.paper.position or
                                                self.paper.account.pending))
                    if busy:
                        continue
                    candles = self.fetch_closed_candles(symbol)
                    if candles.empty:
                        continue
                    newest = int(candles["time"].iloc[-1])
                    if last_bar_seen.get(symbol) != newest:
                        last_bar_seen[symbol] = newest
                        self.try_enter(symbol, candles)
                if not cfg.live:
                    log.debug("equity=%.2f", self.paper.equity)
            except KeyboardInterrupt:
                log.info("stopped by user")
                return
            except Exception:
                log.exception("loop error — continuing")
            time.sleep(cfg.poll_seconds)

"""
Delta Exchange liquidity-sweep swing bot.

Loop:
  1. Pull structure-timeframe + signal-timeframe candles.
  2. Build market structure, detect a liquidity sweep / structure flip on the
     last CLOSED signal candle (all fakeout guards live in structure.py).
  3. If flat and a signal fires, size it to RISK_PCT and place a bracketed
     market order (or log it in dry-run).

Run:  python -m bot.bot
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone

from .config import Config
from .delta_client import DeltaClient, DeltaError
from .risk import build_plan
from .structure import classify_trend, compute_range, detect_signal, find_swings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("bot")

TF_SECONDS = {
    "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "2h": 7200, "4h": 14400, "6h": 21600, "1d": 86400,
}


class Bot:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.client = DeltaClient(cfg.api_key, cfg.api_secret, cfg.base_url)
        self.state = self._load_state()
        product = self.client.get_product(cfg.symbol)
        self.product_id = int(product["id"])
        self.tick_size = float(product.get("tick_size", 0.5))
        self.contract_value = cfg.contract_value or float(product.get("contract_value", 0.001))
        self.last_event = None  # last SIGNAL/PLAN, surfaced on the dashboard
        log.info(
            "Product %s id=%s tick=%s contract_value=%s | mode=%s",
            cfg.symbol, self.product_id, self.tick_size, self.contract_value,
            "LIVE" if cfg.live else "DRY-RUN",
        )

    def _write_status(self, price: float, trend: str, box) -> None:
        """Snapshot current state to status_file for the web dashboard."""
        status = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "symbol": self.cfg.symbol,
            "mode": "LIVE" if self.cfg.live else "DRY-RUN",
            "price": round(price, 4),
            "trend": trend,
            "range_low": round(box.low, 2),
            "range_high": round(box.high, 2),
            "mid": round(box.mid, 2),
            "last_event": self.last_event,
        }
        try:
            with open(self.cfg.status_file, "w") as f:
                json.dump(status, f)
        except OSError:
            pass

    # ----------------------------------------------------------- state
    def _load_state(self) -> dict:
        if os.path.exists(self.cfg.state_file):
            with open(self.cfg.state_file) as f:
                return json.load(f)
        return {"last_signal_bar": 0}

    def _save_state(self) -> None:
        with open(self.cfg.state_file, "w") as f:
            json.dump(self.state, f)

    # ----------------------------------------------------------- data
    def _fetch(self, resolution: str, bars: int) -> list[dict]:
        secs = TF_SECONDS[resolution]
        end = int(time.time())
        start = end - secs * (bars + 2)
        return self.client.get_candles(self.cfg.symbol, resolution, start, end)

    def _equity(self) -> float:
        for w in self.client.get_wallet():
            if w.get("asset_symbol") == self.cfg.settle_asset or w.get("asset", {}).get("symbol") == self.cfg.settle_asset:
                return float(w.get("balance", w.get("available_balance", 0.0)))
        # Fallback: first wallet with a positive balance.
        for w in self.client.get_wallet():
            bal = float(w.get("balance", 0.0))
            if bal > 0:
                return bal
        return 0.0

    def _has_open_position(self) -> bool:
        try:
            for p in self.client.get_positions(self.product_id):
                if p and abs(float(p.get("size", 0) or 0)) > 0:
                    return True
        except DeltaError as e:
            log.warning("position check failed: %s", e)
        return False

    # ----------------------------------------------------------- core
    def evaluate_once(self) -> None:
        cfg = self.cfg
        structure = self._fetch(cfg.structure_tf, cfg.range_lookback + 10)
        signal_tf = self._fetch(cfg.signal_tf, cfg.range_lookback + 10)
        if len(signal_tf) < cfg.range_lookback + 5:
            log.info("not enough candles yet (%d)", len(signal_tf))
            return

        # Drop the still-forming candle: only evaluate CLOSED bars.
        closed = signal_tf[:-1]
        last = closed[-1]

        swings = find_swings(structure, cfg.swing_left, cfg.swing_right)
        trend = classify_trend(swings)
        box = compute_range(structure, cfg.range_lookback)
        log.info(
            "px=%.1f  trend=%s  range=[%.0f .. %.0f]  mid=%.0f",
            last["close"], trend, box.low, box.high, box.mid,
        )
        self._write_status(last["close"], trend, box)

        if last["time"] <= self.state.get("last_signal_bar", 0):
            return  # already handled this bar
        if self._has_open_position():
            log.info("position already open -> skip new entries")
            return

        sig = detect_signal(
            closed,
            swing_left=cfg.swing_left,
            swing_right=cfg.swing_right,
            range_lookback=cfg.range_lookback,
            vol_lookback=cfg.vol_lookback,
            vol_factor=cfg.vol_factor,
            edge_band=cfg.edge_band,
            reclaim_buffer=cfg.reclaim_buffer,
            flip_buffer=cfg.flip_buffer,
            enable_long_sweep=cfg.enable_long_sweep,
            enable_short_sweep=cfg.enable_short_sweep,
            enable_flip=cfg.enable_flip,
        )
        if sig is None:
            return

        log.info("SIGNAL %s (%s): %s", sig.kind, sig.side, sig.reason)
        equity = self._equity()
        if equity <= 0:
            log.warning("equity is 0 (check wallet/SETTLE_ASSET) -> cannot size")
            return

        plan = build_plan(
            side=sig.side,
            entry=sig.entry,
            stop=sig.stop,
            equity=equity,
            risk_pct=cfg.risk_pct,
            tp_r_multiple=cfg.tp_r_multiple,
            contract_value=self.contract_value,
            tick_size=self.tick_size,
            max_leverage=cfg.max_leverage,
        )
        if plan is None:
            log.warning("could not build a valid plan (stop distance / size) -> skip")
            return

        log.info(
            "PLAN %s size=%d entry~%.1f stop=%.1f tp=%.1f risk=%.2f %s notional=%.0f",
            plan.side, plan.size, plan.entry, plan.stop, plan.take_profit,
            plan.risk_amount, cfg.settle_asset, plan.notional,
        )

        self.last_event = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "kind": sig.kind,
            "side": plan.side,
            "size": plan.size,
            "entry": round(plan.entry, 4),
            "stop": round(plan.stop, 4),
            "take_profit": round(plan.take_profit, 4),
            "reason": sig.reason,
            "mode": "LIVE" if cfg.live else "DRY-RUN",
        }
        self._write_status(sig.entry, trend, box)

        self.state["last_signal_bar"] = last["time"]
        self._save_state()

        if not cfg.live:
            log.info("DRY-RUN: would place the above bracketed market order. Set LIVE=true to arm.")
            return

        try:
            res = self.client.place_bracket_market_order(
                product_id=self.product_id,
                size=plan.size,
                side=plan.side,
                stop_loss_price=plan.stop,
                take_profit_price=plan.take_profit,
            )
            log.info("ORDER PLACED id=%s state=%s", res.get("id"), res.get("state"))
        except DeltaError as e:
            log.error("order failed: %s", e)

    def run(self) -> None:
        log.info("starting loop (poll every %ss)", self.cfg.poll_seconds)
        while True:
            try:
                self.evaluate_once()
            except DeltaError as e:
                log.error("api error: %s", e)
            except Exception:  # noqa: BLE001 - keep the loop alive
                log.exception("unexpected error")
            time.sleep(self.cfg.poll_seconds)


def main() -> None:
    cfg = Config()
    cfg.validate()
    Bot(cfg).run()


if __name__ == "__main__":
    main()

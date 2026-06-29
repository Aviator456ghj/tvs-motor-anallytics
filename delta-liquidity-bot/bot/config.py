"""Configuration loaded from environment (.env). Nothing secret is hard-coded."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _clean(name: str, default) -> str:
    """Read an env var, tolerating systemd EnvironmentFile semantics.

    python-dotenv strips trailing ``# comments`` from values, but systemd's
    ``EnvironmentFile=`` keeps everything after ``=`` verbatim. Strip inline
    comments and surrounding whitespace here so both paths behave the same.
    """
    raw = os.getenv(name)
    if raw is None:
        return str(default)
    return raw.split("#", 1)[0].strip()


def _b(name: str, default: bool) -> bool:
    return _clean(name, default).lower() in ("1", "true", "yes", "on")


def _f(name: str, default: float) -> float:
    return float(_clean(name, default))


def _i(name: str, default: int) -> int:
    return int(_clean(name, default))


@dataclass
class Config:
    # --- credentials / endpoint
    api_key: str = os.getenv("DELTA_API_KEY", "")
    api_secret: str = os.getenv("DELTA_API_SECRET", "")
    base_url: str = os.getenv("DELTA_BASE_URL", "https://api.india.delta.exchange")

    # --- safety
    live: bool = _b("LIVE", False)            # False = dry-run (logs orders, sends nothing)

    # --- market / timeframes
    symbol: str = os.getenv("SYMBOL", "BTCUSD")
    structure_tf: str = os.getenv("STRUCTURE_TF", "4h")   # swing structure timeframe
    signal_tf: str = os.getenv("SIGNAL_TF", "1h")         # confirmation-close timeframe

    # --- risk / sizing
    risk_pct: float = _f("RISK_PCT", 2.0)                 # % of equity risked per trade
    tp_r_multiple: float = _f("TP_R_MULTIPLE", 2.0)       # take-profit at N x risk
    max_leverage: float = _f("MAX_LEVERAGE", 10.0)
    contract_value: float = _f("CONTRACT_VALUE", 0.0)     # 0 => fetch from product metadata
    settle_asset: str = os.getenv("SETTLE_ASSET", "USDT") # wallet asset to read equity from

    # --- which signals to trade
    enable_long_sweep: bool = _b("ENABLE_LONG_SWEEP", True)
    enable_short_sweep: bool = _b("ENABLE_SHORT_SWEEP", True)
    enable_flip: bool = _b("ENABLE_FLIP", True)

    # --- strategy params (fakeout guards)
    swing_left: int = _i("SWING_LEFT", 2)
    swing_right: int = _i("SWING_RIGHT", 2)
    range_lookback: int = _i("RANGE_LOOKBACK", 40)
    vol_lookback: int = _i("VOL_LOOKBACK", 20)
    vol_factor: float = _f("VOL_FACTOR", 1.3)
    edge_band: float = _f("EDGE_BAND", 0.25)
    reclaim_buffer: float = _f("RECLAIM_BUFFER", 0.0005)
    flip_buffer: float = _f("FLIP_BUFFER", 0.0010)

    # --- loop
    poll_seconds: int = _i("POLL_SECONDS", 60)
    cooldown_bars: int = _i("COOLDOWN_BARS", 1)
    state_file: str = os.getenv("STATE_FILE", "bot_state.json")
    status_file: str = os.getenv("STATUS_FILE", "bot_status.json")
    dashboard_port: int = _i("DASHBOARD_PORT", 8080)

    def validate(self) -> None:
        if not self.api_key or not self.api_secret:
            raise SystemExit("DELTA_API_KEY / DELTA_API_SECRET are required (set them in .env)")
        if self.risk_pct <= 0 or self.risk_pct > 10:
            raise SystemExit("RISK_PCT must be between 0 and 10")

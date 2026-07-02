"""Configuration for the Delta Exchange scalping agent.

All secrets come from environment variables — never hardcode credentials.

Required for live/paper trading against your account:
    DELTA_API_KEY      your Delta Exchange India API key
    DELTA_API_SECRET   your Delta Exchange India API secret

Safety:
    DELTA_LIVE=1       must be set explicitly to place real orders.
                       Anything else -> paper trading (default).
"""
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # --- connection ---
    base_url: str = os.environ.get("DELTA_BASE_URL", "https://api.india.delta.exchange")
    api_key: str = os.environ.get("DELTA_API_KEY", "")
    api_secret: str = os.environ.get("DELTA_API_SECRET", "")
    live: bool = os.environ.get("DELTA_LIVE", "") == "1"

    # --- market ---
    symbols: tuple = tuple(os.environ.get("DELTA_SYMBOLS", "BTCUSD").split(","))
    timeframe_minutes: int = int(os.environ.get("DELTA_TIMEFRAME_MIN", "15"))

    # --- strategy selection ---
    # "pullback"  (default): trend-pullback — the only one that validated
    #                        positive out-of-sample on BTCUSD
    # "structure":           HTF liquidity sweep + CHoCH (market structure);
    #                        NEGATIVE expectancy in backtests — research only
    strategy: str = os.environ.get("DELTA_STRATEGY", "pullback")

    # --- strategy (walk-forward selected; see backtests/README section in repo README) ---
    ema_fast: int = 20
    ema_slow: int = 50
    ema_trend: int = 100
    rsi_period: int = 14
    rsi_long_cross: float = 45.0   # RSI crosses back up through this in an uptrend
    rsi_short_cross: float = 55.0  # RSI crosses back down through this in a downtrend
    atr_period: int = 14
    sl_atr_mult: float = 1.5       # stop-loss distance in ATRs
    tp_r_multiple: float = 2.5     # take-profit at 2.5x the stop distance (2.5R)
    max_hold_bars: int = 32        # time-based exit (32 x 15m = 8h)
    min_move_cost_ratio: float = 3.0  # SL distance must be >= this x round-trip cost

    # --- market-structure strategy parameters (DELTA_STRATEGY=structure) ---
    ms_htf_minutes: int = 60       # higher timeframe holding the liquidity levels
    ms_swing_k: int = 3            # fractal half-width for HTF swings
    ms_micro_bars: int = 3         # lookback for the CHoCH trigger level
    ms_confirm_bars: int = 6       # bars allowed between sweep and confirmation
    ms_r_multiple: float = 2.0     # take-profit in R

    # --- risk management ---
    risk_per_trade: float = float(os.environ.get("DELTA_RISK_PER_TRADE", "0.005"))  # 0.5% of equity
    max_leverage: float = float(os.environ.get("DELTA_MAX_LEVERAGE", "3"))
    daily_loss_limit: float = float(os.environ.get("DELTA_DAILY_LOSS_LIMIT", "0.02"))  # stop for the day at -2%
    max_consecutive_losses: int = int(os.environ.get("DELTA_MAX_CONSEC_LOSSES", "5"))
    max_open_positions: int = 1

    # --- costs (used for filters and paper fills) ---
    taker_fee: float = 0.0005
    maker_fee: float = 0.0002
    slippage: float = 0.0002

    # --- ops ---
    poll_seconds: int = 20
    paper_start_equity: float = float(os.environ.get("DELTA_PAPER_EQUITY", "1000"))
    state_file: str = os.environ.get("DELTA_STATE_FILE", "scalper_state.json")
    log_file: str = os.environ.get("DELTA_LOG_FILE", "scalper.log")

    @property
    def round_trip_cost(self) -> float:
        # maker entry + taker exit + slippage both ways (conservative)
        return self.maker_fee + self.taker_fee + 2 * self.slippage

    def validate(self):
        if self.live and (not self.api_key or not self.api_secret):
            raise SystemExit(
                "DELTA_LIVE=1 but DELTA_API_KEY / DELTA_API_SECRET are not set."
            )
        if self.risk_per_trade > 0.02:
            raise SystemExit("risk_per_trade > 2% is not allowed by this agent.")

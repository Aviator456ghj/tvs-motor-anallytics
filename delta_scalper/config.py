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
    # "pullback"  (default): trend-pullback baseline
    # "structure":           confirmed liquidity sweep + order-block entry
    #                        (best per-trade quality; very selective)
    # "fib":                 0.618-retracement / 1.618-extension with trend
    #                        filter (bigger sample; BTC-validated)
    # "choch":               1h trend-change (CHoCH) swing + fib discount
    #                        entry, 2.618 target (BTC-only validated)
    # "riley":               BOS + failed-retest reversal with an FVG
    #                        ("unhealthy move") filter, 15m, swing-trailed
    #                        exit — validated on both BTC and ETH
    # "orderblock":          displaced structure break -> retest of the
    #                        order-block candle -> ride exit, 1h
    # "liqfakeout":          liquidity sweep + same-candle fakeout reversal,
    #                        volume-confirmed, fixed 1R target, 1h ONLY —
    #                        validated cross-asset on BTC/ETH/SOL/XRP
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
    # best on a 5m trading timeframe (set DELTA_TIMEFRAME_MIN=5)
    ms_htf_minutes: int = 60       # higher timeframe holding the liquidity levels
    ms_swing_k: int = 3            # fractal half-width for HTF swings
    ms_micro_bars: int = 3         # lookback for the CHoCH trigger level
    ms_confirm_bars: int = 6       # bars allowed between sweep and confirmation
    ms_r_multiple: float = 2.0     # take-profit in R
    ms_wick_frac: float = 0.5      # fakeout filter: wick beyond level >= 50% of bar range
    ms_wait_bars: int = 12         # cancel the order-block limit if unfilled
    # failure-derived filters (see reports/market_structure_report.md §failure
    # analysis): losing trades clustered in low-volume sweeps and too-tight
    # structures; both filters validated in-sample AND out-of-sample
    ms_vol_ratio: float = 1.0      # sweep bar volume >= this x 20-bar average
    ms_min_stop_pct: float = 0.0045  # skip structures tighter than 0.45% (noise-stopped)

    # --- fib strategy parameters (DELTA_STRATEGY=fib, 5m timeframe) ---
    # walk-forward selected; note 1.618 beat 2.618 as the extension target
    fib_swing_k: int = 24          # fractal half-width (24 x 5m = 2h swings)
    fib_entry_r: float = 0.618     # limit entry at this retracement of A->B
    fib_stop_r: float = 1.0        # stop just beyond A (full retracement = invalid)
    fib_ext_r: float = 1.618       # take-profit extension from the fill
    fib_wait_bars: int = 200       # cancel the unfilled retracement limit
    # failure filter (validated in+out of sample): a pullback that crashes
    # into the zone within an hour is impulsive, not corrective — fills in
    # the first 12 bars had a 23% win rate vs 36-43% for slower pullbacks
    fib_min_pull_bars: int = 12

    # --- choch strategy parameters (DELTA_STRATEGY=choch, 1h timeframe) ---
    choch_swing_k: int = 5         # fractal half-width on 1h
    choch_entry_r: float = 0.5     # golden zone near edge (0.5 retracement)
    choch_zone_far_r: float = 0.618  # golden zone far edge
    choch_ext_r: float = 2.618     # target: A + 2.618*(B-A) — reversals run far
    choch_wait_bars: int = 120     # setup validity window (~5 days)
    choch_disrespect_r: float = 0.786  # a CLOSE past this level voids the setup
    # buffer stop: extra room beyond A so wick-hunts under the swing don't
    # clip the trade — validated: OOS profit factor 1.47 -> 1.71, win rate
    # 34.8% -> 39.1% with a 5%-of-swing buffer
    choch_stop_buffer: float = 0.05  # as a fraction of the A->B swing
    # engulfing confirmation: the confirming candle must close beyond the
    # counter candle's OPEN (true engulf). Post-mortem: engulfed entries won
    # 60% vs 34.6% for weak confirmations; validated out-of-sample (50% wr,
    # PF 1.82). Cuts trade frequency roughly in half.
    choch_require_engulf: bool = os.environ.get("DELTA_CHOCH_ENGULF", "1") == "1"
    # exit mode: "trend" = ride until the OPPOSITE change of character
    #            (close through the confirmed swing trail) — validated best
    #            total growth; "target" = fixed 2.618 extension take-profit
    choch_exit_mode: str = os.environ.get("DELTA_CHOCH_EXIT", "trend")
    choch_max_hold_bars: int = 2000  # trend rides run for days; don't time-cut them
    # displacement filter: the CHoCH breaking candle must travel >= this
    # many ATRs past the broken swing — a decisive break, not a drift.
    # Validated on the ride exit: wr +3pts both phases, PF 2.04->2.45 in /
    # 3.66->4.24 out, max drawdown -41% -> -30%
    choch_min_break_atr: float = 1.0
    # entry mode: "candle" = golden-zone candle-color confirmation (a candle
    # touching the zone closes against the trade direction, the next candle
    # closes with it -> market entry); "limit" = blind limit at the 0.5 level
    choch_entry_mode: str = os.environ.get("DELTA_CHOCH_ENTRY", "candle")

    # --- riley strategy parameters (DELTA_STRATEGY=riley, 15m timeframe) ---
    # walk-forward validated (both BTC and ETH, k=3 and k=5): FVG filter is
    # essential — without it, at least one symbol/phase cell goes negative
    riley_swing_k: int = 5          # fractal half-width
    riley_fvg_mult: float = 0.5     # required FVG size, in ATRs, in the impulse leg
    riley_retest_window: int = 12   # bars allowed for the failed-retest bounce
    riley_fill_window: int = 12     # bars allowed for the breakout entry to trigger
    riley_exit_mode: str = "trail"  # "trail" (validated best) or "target"
    riley_r_mult: float = 2.0       # take-profit R-multiple if exit_mode="target"
    # "Part 2" failure-analysis filter (see pine/riley_checklist_v2.pine for
    # the derivation: both rules found on 321 pooled BTC+ETH v1 trades,
    # p<0.01, validated to raise PF on both symbols): the entry must fill
    # within riley_max_fill_delay bars of the failed retest, and the BOS
    # candle must have volume >= riley_min_vol_ratio x its 20-bar average.
    riley_use_p2: bool = os.environ.get("DELTA_RILEY_P2", "") == "1"
    riley_max_fill_delay: int = 3
    riley_min_vol_ratio: float = 1.3

    # --- order block strategy parameters (DELTA_STRATEGY=orderblock, 1h) ---
    # Same CHoCH structure detection as the choch strategy, but the entry is
    # a retest of the "order block" (last opposite-colour candle before the
    # displaced break) with a confirming candle, not a fib level. Stop
    # beyond the OB zone + ATR buffer; ride exit via the swing trail. See
    # pine/order_block_retest.pine for backtest numbers.
    ob_swing_k: int = 4             # fractal half-width
    ob_min_break_atr: float = 1.0   # displacement filter on the break candle
    ob_wait_bars: int = 120         # max bars to wait for the OB retest
    ob_buf_atr: float = 0.9         # stop buffer beyond the OB zone (x ATR)

    # --- liquidity fakeout strategy (DELTA_STRATEGY=liqfakeout, 1h ONLY) ---
    # a confirmed k-bar swing is where resting stop-loss/breakout liquidity
    # clusters; a SWEEP pierces >= liq_wick_atr ATRs beyond it; a FAKEOUT is
    # the sweeping candle itself failing to hold beyond the level (closes
    # back inside) -- traded only when that candle's volume is
    # >= liq_vol_mult x its 20-bar average (the filter that separates a
    # real stop-hunt from a random wick: PF 0.85 without it, 1.06-1.90
    # with it, walk-forward, across BTC/ETH/SOL/XRP). Exit: fixed R target,
    # not a ride -- a fakeout is a quick snap-back, not a trend.
    # VALIDATED ON 1H ONLY: fails on 15m (PF 0.63-0.99), marginal on 30m
    # (PF 0.81-1.14). Do not run this strategy at any other timeframe.
    liq_swing_k: int = 3
    liq_wick_atr: float = 0.1        # min sweep depth beyond the level (x ATR)
    liq_reject_frac: float = 0.0     # how far back inside the level the close must reach
    liq_vol_mult: float = 1.5        # min sweep-candle volume (x 20-bar avg)
    liq_r_mult: float = 1.0          # fixed take-profit, in R
    liq_buf_atr: float = 0.15        # stop buffer beyond the sweep extreme (x ATR)

    # --- trend-following BB+EMA breakout (DELTA_STRATEGY=tfbreakout, 1h) ---
    # Replicated from a Claude+Jesse-MCP autonomous strategy-development
    # video: Bollinger Band breakout filtered by an EMA trend, two exit
    # modes sharing this one entry rule. See
    # reports/tf_breakout_jesse_replication_report.md for the full
    # validation on real Delta Exchange India data (~2.3 years BTC/ETH/SOL,
    # entry-rule significance test, hyperparameter grid search, Monte
    # Carlo). HONEST RESULT: neither exit mode cleared the video's own
    # Sharpe>1 target out-of-sample (trail: -0.35, fixed: 0.90) even though
    # both passed the significance test and Monte Carlo on the full period
    # — a real demonstration of why walk-forward matters. Paper-only;
    # watch the live journal, don't trust the full-period backtest number.
    tf_bb_period: int = 20
    tf_bb_dev: float = 2.5
    tf_ema_period: int = 150         # 200 for the trail variant, 100 for fixed (set per-preset)
    tf_stop_mult: float = 1.5        # initial stop distance (x ATR)
    tf_exit_mult: float = 2.0        # target_mult (fixed mode) / trail_mult (trail mode), x ATR
    tf_exit_mode: str = "fixed"      # "fixed" (ATR stop+target) | "trail" (ATR ratchet, ride exit)
    tf_max_hold_bars: int = 720      # 30 days at 1h -- trend trades can run long

    # --- position sizing mode ---
    # "risk" (default): risk_per_trade% of equity, sized off the stop distance
    # "compound":       stake the FULL balance x compound_leverage every trade
    #                   (the $1 -> grow experiment; a stop-loss bites the pot)
    sizing: str = os.environ.get("DELTA_SIZING", "risk")
    compound_leverage: float = float(os.environ.get("DELTA_COMPOUND_LEV", "1"))

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

    def __post_init__(self):
        # structure/fib validated on 5m, choch on 1h; honor explicit override
        if "DELTA_TIMEFRAME_MIN" not in os.environ:
            if self.strategy in ("structure", "fib"):
                self.timeframe_minutes = 5
            elif self.strategy in ("choch", "orderblock", "liqfakeout"):
                self.timeframe_minutes = 60
            elif self.strategy == "riley":
                self.timeframe_minutes = 15
        # engulf helps the fixed-target exit but hurts the trend-ride exit
        # (fewer entries starve the compounding); pair defaults accordingly
        if "DELTA_CHOCH_ENGULF" not in os.environ:
            self.choch_require_engulf = self.choch_exit_mode == "target"
        # in compound mode a single stop-loss can exceed a 2% daily limit;
        # relax the default so one loss doesn't halt the experiment for a day
        if self.sizing == "compound" and "DELTA_DAILY_LOSS_LIMIT" not in os.environ:
            self.daily_loss_limit = 0.25

    @property
    def round_trip_cost(self) -> float:
        # maker entry + taker exit + slippage both ways (conservative)
        return self.maker_fee + self.taker_fee + 2 * self.slippage

    def validate(self):
        if self.live and (not self.api_key or not self.api_secret):
            raise SystemExit(
                "DELTA_LIVE=1 but DELTA_API_KEY / DELTA_API_SECRET are not set."
            )
        if self.live and self.sizing == "risk" and self.risk_per_trade > 0.02:
            # The cap is LIVE-only on purpose: paper mode may replay the
            # high-risk research presets (agents/run_agent.py) to watch how
            # they behave in real time, but this agent will never place real
            # orders sized above 2% risk per trade. The backtested presets
            # at 15-100% risk produced -55% to -90% max drawdowns — that is
            # account-ruin territory, not a validated edge.
            raise SystemExit(
                "risk_per_trade > 2% is not allowed for LIVE trading by this "
                "agent (the high-risk presets are paper-only by design)."
            )
        if self.compound_leverage > 3:
            raise SystemExit("compound_leverage > 3 is not allowed: at full-"
                             "balance staking, higher leverage risks ruin — "
                             "25x+ was liquidated on trade #2 in backtest "
                             "(see reports/leverage_sweep.png).")

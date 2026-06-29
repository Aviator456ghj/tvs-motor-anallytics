"""Position sizing and stop/target math derived from market structure."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TradePlan:
    side: str            # "buy" | "sell"
    size: int            # number of contracts
    entry: float
    stop: float
    take_profit: float
    risk_amount: float   # settle-asset units risked if stop hit
    notional: float


def round_to_tick(price: float, tick: float) -> float:
    if tick <= 0:
        return price
    return round(round(price / tick) * tick, 10)


def build_plan(
    *,
    side: str,
    entry: float,
    stop: float,
    equity: float,
    risk_pct: float,
    tp_r_multiple: float,
    contract_value: float,   # BTC per contract, e.g. 0.001
    tick_size: float,
    max_leverage: float,
    stop_pad_ticks: int = 2,
) -> TradePlan | None:
    """
    Size so that hitting the stop loses `risk_pct`% of equity.

    For a USDT-settled contract, P&L per contract for a price move dP is
    `contract_value * dP`. So:
        risk_per_contract = stop_distance * contract_value
        size              = floor(risk_amount / risk_per_contract)
    """
    # Pad the stop a couple ticks beyond the wick so we are not the exact stop level.
    pad = stop_pad_ticks * tick_size
    if side == "buy":
        stop = stop - pad
        stop_distance = entry - stop
    else:
        stop = stop + pad
        stop_distance = stop - entry

    if stop_distance <= 0:
        return None

    risk_amount = equity * (risk_pct / 100.0)
    risk_per_contract = stop_distance * contract_value
    if risk_per_contract <= 0:
        return None

    size = int(risk_amount // risk_per_contract)
    if size < 1:
        return None

    # Leverage cap: notional must not exceed equity * max_leverage.
    notional = size * contract_value * entry
    max_notional = equity * max_leverage
    if notional > max_notional:
        size = int(max_notional // (contract_value * entry))
        if size < 1:
            return None
        notional = size * contract_value * entry

    if side == "buy":
        take_profit = entry + stop_distance * tp_r_multiple
    else:
        take_profit = entry - stop_distance * tp_r_multiple

    return TradePlan(
        side=side,
        size=size,
        entry=entry,
        stop=round_to_tick(stop, tick_size),
        take_profit=round_to_tick(take_profit, tick_size),
        risk_amount=size * risk_per_contract,
        notional=notional,
    )

"""Order-flow / market-condition analysis: "big money" moves, order book
pressure, and volatility/trend regime — all from real Delta Exchange India
public data (no news, no LLM; that layer lives in agents/market_intel_agent.py).

Every function here returns plain numbers and short strings, not verdicts —
this module observes and measures, it does not decide. That separation
matters: everything below is deterministic and inspectable (you can log it,
reason about it, disagree with it), unlike the LLM synthesis step in
market_intel_agent.py, which is not.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class WhaleTrade:
    price: float
    size: int
    notional_usd: float
    side: str  # "buy" (aggressive buyer) or "sell" (aggressive seller)
    timestamp: int


@dataclass
class OrderFlowSnapshot:
    symbol: str
    mark_price: float
    spread: float
    spread_bps: float
    book_imbalance: float          # (bid_depth - ask_depth) / (bid_depth + ask_depth) over N levels, [-1, 1]
    bid_depth_usd: float
    ask_depth_usd: float
    biggest_bid_wall: dict         # {"price":..., "size":..., "usd":...} the single largest resting bid level
    biggest_ask_wall: dict
    taker_buy_ratio: float         # fraction of recent trade VOLUME that was aggressive buying, [0, 1]
    whale_trades: list             # WhaleTrade list, largest-size trades in the recent window
    oi_change_usd_6h: float
    funding_rate: float
    volatility_regime: str         # "low" / "normal" / "high" (ATR percentile of recent history)
    trend_regime: str              # "trending" / "ranging" (ADX-style directional strength)
    trend_direction: str           # "up" / "down" / "flat"


def analyze_orderbook(ob: dict, contract_value: float, levels: int = 20) -> dict:
    buy = ob.get("buy", [])[:levels]
    sell = ob.get("sell", [])[:levels]
    best_bid = float(buy[0]["price"]) if buy else float("nan")
    best_ask = float(sell[0]["price"]) if sell else float("nan")
    mid = (best_bid + best_ask) / 2 if buy and sell else float("nan")
    spread = best_ask - best_bid if buy and sell else float("nan")
    bid_depth = sum(int(x["size"]) for x in buy) * contract_value * mid
    ask_depth = sum(int(x["size"]) for x in sell) * contract_value * mid
    total = bid_depth + ask_depth
    imbalance = (bid_depth - ask_depth) / total if total > 0 else 0.0

    def biggest_wall(levels_, mid_):
        if not levels_:
            return {"price": None, "size": 0, "usd": 0.0}
        top = max(levels_, key=lambda x: int(x["size"]))
        usd = int(top["size"]) * contract_value * mid_
        return {"price": float(top["price"]), "size": int(top["size"]), "usd": usd}

    return dict(
        best_bid=best_bid, best_ask=best_ask, mid=mid,
        spread=spread, spread_bps=(spread / mid * 1e4) if mid else float("nan"),
        book_imbalance=imbalance, bid_depth_usd=bid_depth, ask_depth_usd=ask_depth,
        biggest_bid_wall=biggest_wall(buy, mid), biggest_ask_wall=biggest_wall(sell, mid),
    )


def analyze_trades(trades: list, contract_value: float, mark_price: float,
                    whale_pctile: float = 99.0, top_n: int = 5) -> dict:
    """taker_buy_ratio (order-flow/CVD-style pressure) + the largest
    individual prints in the sample ("big man" trades)."""
    if not trades:
        return dict(taker_buy_ratio=0.5, whale_trades=[])
    sizes = np.array([int(t["size"]) for t in trades])
    threshold = np.percentile(sizes, whale_pctile) if len(sizes) >= 20 else sizes.max()
    buy_vol = sum(int(t["size"]) for t in trades if t["buyer_role"] == "taker")
    sell_vol = sum(int(t["size"]) for t in trades if t["seller_role"] == "taker")
    total_vol = buy_vol + sell_vol
    ratio = buy_vol / total_vol if total_vol > 0 else 0.5

    whales = []
    for t in trades:
        size = int(t["size"])
        if size >= threshold and size > 0:
            side = "buy" if t["buyer_role"] == "taker" else "sell"
            whales.append(WhaleTrade(
                price=float(t["price"]), size=size,
                notional_usd=size * contract_value * float(t["price"]),
                side=side, timestamp=int(t["timestamp"]),
            ))
    whales.sort(key=lambda w: w.notional_usd, reverse=True)
    return dict(taker_buy_ratio=ratio, whale_trades=whales[:top_n])


def market_regime(candles: pd.DataFrame, atr_window: int = 14, lookback: int = 200) -> dict:
    """Volatility regime = current ATR's percentile rank within its own
    recent history (self-relative, works across any symbol's price scale).
    Trend regime = simplified directional-movement strength (ADX-style):
    high + consistent directional movement = trending, else ranging."""
    h, l, c = candles.high.values, candles.low.values, candles.close.values
    n = len(candles)
    tr = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    atr = pd.Series(tr).ewm(alpha=1 / atr_window, adjust=False).mean().values
    recent = atr[-lookback:] if n > lookback else atr
    cur_atr = atr[-1] if len(atr) else float("nan")
    pctile = float((recent < cur_atr).mean() * 100) if len(recent) else 50.0
    vol_regime = "high" if pctile >= 75 else ("low" if pctile <= 25 else "normal")

    up_move = np.maximum(h[1:] - h[:-1], 0)
    dn_move = np.maximum(l[:-1] - l[1:], 0)
    up_move = np.where(up_move > dn_move, up_move, 0)
    dn_move = np.where(dn_move > up_move, dn_move, 0)
    # atr[i] and up_move[i]/dn_move[i] are both aligned to original bar i+1
    atr_safe = np.where(atr > 0, atr, np.nan)
    plus_di = 100 * pd.Series(up_move).ewm(alpha=1 / atr_window, adjust=False).mean().values / atr_safe
    minus_di = 100 * pd.Series(dn_move).ewm(alpha=1 / atr_window, adjust=False).mean().values / atr_safe
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)
    adx = pd.Series(dx).ewm(alpha=1 / atr_window, adjust=False).mean().values
    cur_adx = adx[-1] if len(adx) else 0.0
    trend_regime = "trending" if cur_adx >= 25 else "ranging"
    direction = "flat"
    if len(plus_di) and len(minus_di):
        if plus_di[-1] > minus_di[-1] * 1.1:
            direction = "up"
        elif minus_di[-1] > plus_di[-1] * 1.1:
            direction = "down"

    return dict(volatility_regime=vol_regime, volatility_percentile=pctile,
                trend_regime=trend_regime, trend_direction=direction, adx=float(cur_adx))


def build_snapshot(symbol: str, ticker: dict, ob: dict, trades: list,
                   candles: pd.DataFrame, contract_value: float) -> OrderFlowSnapshot:
    mark = float(ticker.get("mark_price", 0) or 0)
    ob_a = analyze_orderbook(ob, contract_value)
    tr_a = analyze_trades(trades, contract_value, mark)
    reg = market_regime(candles)
    return OrderFlowSnapshot(
        symbol=symbol, mark_price=mark, spread=ob_a["spread"], spread_bps=ob_a["spread_bps"],
        book_imbalance=ob_a["book_imbalance"], bid_depth_usd=ob_a["bid_depth_usd"],
        ask_depth_usd=ob_a["ask_depth_usd"], biggest_bid_wall=ob_a["biggest_bid_wall"],
        biggest_ask_wall=ob_a["biggest_ask_wall"], taker_buy_ratio=tr_a["taker_buy_ratio"],
        whale_trades=tr_a["whale_trades"], oi_change_usd_6h=float(ticker.get("oi_change_usd_6h", 0) or 0),
        funding_rate=float(ticker.get("funding_rate", 0) or 0),
        volatility_regime=reg["volatility_regime"], trend_regime=reg["trend_regime"],
        trend_direction=reg["trend_direction"],
    )

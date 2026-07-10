"""Shared helpers for the three run_*_screenshot_backtest.py scripts.

These three scripts reproduce three specific Strategy Test Bench console
runs (screenshots the user tested by hand), NOT the repo's validated
defaults — see each script's module docstring for the exact settings and
the honesty warning that goes with them. Kept separate from the validated
backtests/run_*_backtest.py scripts on purpose, so the validated defaults
in delta_scalper/config.py are never touched by these high-risk configs.
"""
import numpy as np
import pandas as pd

TAKER = 0.0005
SLIP = 0.0002

# Real Delta Exchange India perpetual futures specs (BTCUSD).
BTCUSD_CONTRACT_VALUE = 0.001
BTCUSD_DEFAULT_LEVERAGE = 200


def atr_arr(df: pd.DataFrame, n: int = 14) -> np.ndarray:
    tr = pd.concat([
        df.high - df.low,
        (df.high - df.close.shift()).abs(),
        (df.low - df.close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean().values


def swing_trail(df: pd.DataFrame, k: int):
    """Most recent confirmed k-bar swing low/high as of each bar (no
    lookahead) — a trailing stop that only ever tightens, never loosens."""
    h, l = df.high.values, df.low.values
    n = len(df)
    lo = np.full(n, np.nan)
    hi = np.full(n, np.nan)
    cur_lo = cur_hi = np.nan
    for t in range(n):
        j = t - k
        if j >= k:
            if l[j] == l[j - k: j + k + 1].min():
                cur_lo = l[j]
            if h[j] == h[j - k: j + k + 1].max():
                cur_hi = h[j]
        lo[t], hi[t] = cur_lo, cur_hi
    return lo, hi


def size_lots(equity: float, entry: float, stop_d: float, risk_pct: float,
              leverage: float, contract_value: float):
    """Whole-lot position sizing — matches delta_scalper/bot.py's live
    order sizing exactly: size = max(1, floor(notional / (contract_value *
    entry))). Small accounts can end up risking MORE than the requested
    risk_pct once rounded up to the minimum 1 lot — that's a real exchange
    constraint, not a backtest artifact."""
    ideal_notional = min(equity * risk_pct / (stop_d / entry), equity * leverage)
    lots = max(1, int(np.floor(ideal_notional / (contract_value * entry))))
    notional = lots * contract_value * entry
    return notional, lots


def stats(trades: pd.DataFrame, eq0: float) -> dict:
    if trades.empty:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "ret": 0.0, "maxDD": 0.0, "finalEq": eq0}
    wins = trades[trades.pnl > 0]
    losses = trades[trades.pnl <= 0]
    gross_win = wins.pnl.sum()
    gross_loss = -losses.pnl.sum()
    pf = gross_win / gross_loss if gross_loss > 0 else float("inf")
    wr = 100 * len(wins) / len(trades)
    final_eq = trades.equity.iloc[-1]
    ret = 100 * (final_eq - eq0) / eq0
    peak, max_dd = eq0, 0.0
    for eq in trades.equity:
        if eq > peak:
            peak = eq
        dd = 100 * (peak - eq) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    return {"n": len(trades), "wr": wr, "pf": pf, "ret": ret, "maxDD": max_dd, "finalEq": final_eq}


def print_report(label: str, st: dict):
    print(f"{label}")
    print(f"  trades={st['n']}  win_rate={st['wr']:.1f}%  profit_factor={st['pf']:.2f}  "
          f"total_return={st['ret']:+.2f}%  max_drawdown=-{st['maxDD']:.1f}%  "
          f"final_equity=${st['finalEq']:.2f}")


def fetch_candles(client, symbol: str, timeframe: str, days: int) -> pd.DataFrame:
    import time
    bar_seconds = {"15m": 900, "1h": 3600}[timeframe]
    end = int(time.time())
    start = end - days * 86400
    frames, cursor = [], end
    while cursor > start:
        chunk = max(start, cursor - 2000 * bar_seconds)
        data = client.get_candles(symbol, timeframe, chunk, cursor)
        if not data:
            break
        frames.append(pd.DataFrame(data))
        cursor = min(c["time"] for c in data) - bar_seconds
        time.sleep(0.25)
    df = pd.concat(frames).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df

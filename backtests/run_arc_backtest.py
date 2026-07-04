"""ARC method (Area-Range-Candle) — mechanical implementation.

A: box high/low = previous UTC day's high/low (wicks included);
   swing high = most recent daily high above the box high (scan back);
   swing low  = most recent daily low  below the box low.
B: buy only at/near box low or swing low; sell only at/near box high or
   swing high; never trade the middle.
R: range R = boxH - boxL. Target = tgt_frac * R from entry (50%..100%).
C: rejection candle at the level (wick through/touching, closes back
   inside, wick >= wick_frac of candle range), then the NEXT candle takes
   out its high (long) -> enter at that candle's close.
   Stop under the rejection candle's extreme (small buffer).

Timeframe: 15m (also 5m on the shorter dataset). Costs: taker + slippage.
"""
import numpy as np
import pandas as pd

TAKER, SLIP = 0.0005, 0.0002
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def daily_levels(df):
    """Per intraday bar: previous day's box H/L and swing H/L (no lookahead)."""
    d = df.copy()
    d["day"] = (d["time"] // 86400).astype(int)
    daily = d.groupby("day").agg(hi=("high", "max"), lo=("low", "min"))
    days = daily.index.values
    his, los = daily.hi.values, daily.lo.values
    box_h = {}; box_l = {}; sw_h = {}; sw_l = {}
    for i in range(1, len(days)):
        bh, bl = his[i - 1], los[i - 1]
        sh = np.nan
        for j in range(i - 2, max(-1, i - 60), -1):
            if his[j] > bh:
                sh = his[j]
                break
        sl = np.nan
        for j in range(i - 2, max(-1, i - 60), -1):
            if los[j] < bl:
                sl = los[j]
                break
        box_h[days[i]], box_l[days[i]] = bh, bl
        sw_h[days[i]], sw_l[days[i]] = sh, sl
    day_arr = d["day"].values
    return (np.array([box_h.get(x, np.nan) for x in day_arr]),
            np.array([box_l.get(x, np.nan) for x in day_arr]),
            np.array([sw_h.get(x, np.nan) for x in day_arr]),
            np.array([sw_l.get(x, np.nan) for x in day_arr]))


def run_arc(df, tgt_frac=0.5, near_frac=0.02, wick_frac=0.4, buf_frac=0.05,
            max_hold=96, use_swing=True, risk=0.005, eq0=1000.0):
    o, h, l, c = df.open.values, df.high.values, df.low.values, df.close.values
    bh, bl, sh, sl = daily_levels(df)
    n = len(df)
    cost = 2 * (TAKER + SLIP)
    equity, trades, used_until = eq0, [], 0
    i = 1
    while i < n - 2:
        if i < used_until or np.isnan(bh[i]) or np.isnan(bl[i]):
            i += 1
            continue
        R = bh[i] - bl[i]
        if R <= 0:
            i += 1
            continue
        near = near_frac * R
        # candidate levels for this bar
        longs = [bl[i]] + ([sl[i]] if use_swing and not np.isnan(sl[i]) else [])
        shorts = [bh[i]] + ([sh[i]] if use_swing and not np.isnan(sh[i]) else [])
        sig = 0
        level = extreme = None
        rng_i = h[i] - l[i]
        for lv in longs:
            # rejection candle at the level: low touches/pierces, closes above
            if l[i] <= lv + near and c[i] > lv and rng_i > 0 and \
                    (min(o[i], c[i]) - l[i]) / rng_i >= wick_frac:
                sig, level, extreme = 1, lv, l[i]
                break
        if sig == 0:
            for lv in shorts:
                if h[i] >= lv - near and c[i] < lv and rng_i > 0 and \
                        (h[i] - max(o[i], c[i])) / rng_i >= wick_frac:
                    sig, level, extreme = -1, lv, h[i]
                    break
        if sig == 0:
            i += 1
            continue
        # next candle must take out the rejection candle's high (long)
        j = i + 1
        took_out = h[j] > h[i] if sig == 1 else l[j] < l[i]
        if not took_out:
            i += 1
            continue
        entry = c[j] * (1 + SLIP * sig)
        stop = extreme - sig * buf_frac * R
        tp = entry + sig * tgt_frac * R
        stop_d = abs(entry - stop)
        if stop_d <= 0 or stop_d / entry < 3 * cost or sig * (tp - entry) <= 0:
            i += 1
            continue
        notional = min(equity * risk / (stop_d / entry), equity * 10)
        exit_px, k = None, j + 1
        for k in range(j + 1, min(j + max_hold, n)):
            if sig == 1:
                if l[k] <= stop: exit_px = stop; break
                if h[k] >= tp: exit_px = tp; break
            else:
                if h[k] >= stop: exit_px = stop; break
                if l[k] <= tp: exit_px = tp; break
        if exit_px is None:
            k = min(j + max_hold, n - 1)
            exit_px = c[k]
        ret = sig * (exit_px - entry) / entry - cost
        pnl = notional * ret
        equity += pnl
        trades.append({"entry_time": int(df.time.iloc[j]), "pnl": pnl,
                       "equity": equity, "r_outcome": ret / (stop_d / entry)})
        used_until = k + 1
        i = k + 1
    return pd.DataFrame(trades)


def stats(t, eq0=1000.0):
    if len(t) < 5:
        return None
    eq = pd.concat([pd.Series([eq0]), t.equity])
    w = t[t.pnl > 0]
    return {"n": len(t), "wr": round(100 * (t.pnl > 0).mean(), 1),
            "pf": round(w.pnl.sum() / max(1e-9, -t[t.pnl <= 0].pnl.sum()), 2),
            "ret%": round((eq.iloc[-1] / eq0 - 1) * 100, 2),
            "avgR": round(t.r_outcome.mean(), 2)}


if __name__ == "__main__":
    import time as _t
    from delta_scalper.config import Config
    from delta_scalper.delta_client import DeltaClient
    client = DeltaClient(Config().base_url)
    print("fetching BTCUSD 15m x 540d ...")
    end = int(_t.time()); start = end - 540 * 86400
    frames, cursor = [], end
    while cursor > start:
        chunk = max(start, cursor - 2000 * 900)
        data = client.get_candles("BTCUSD", "15m", chunk, cursor)
        if not data:
            break
        frames.append(pd.DataFrame(data))
        cursor = min(x["time"] for x in data) - 900
        _t.sleep(0.25)
    d15 = pd.concat(frames).drop_duplicates("time").sort_values("time").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume"]:
        d15[col] = d15[col].astype(float)
    t0 = d15.time.min()
    split = t0 + 360 * 86400
    d_in = d15[d15.time < split].reset_index(drop=True)
    d_out = d15[d15.time >= split].reset_index(drop=True)
    rows = []
    for name, kw in {
        "ARC 50% target":        dict(tgt_frac=0.5),
        "ARC 75% target":        dict(tgt_frac=0.75),
        "ARC 100% target":       dict(tgt_frac=1.0),
        "ARC 50%, box only":     dict(tgt_frac=0.5, use_swing=False),
        "ARC 50%, strict wick":  dict(tgt_frac=0.5, wick_frac=0.6),
        "ARC 50%, loose wick":   dict(tgt_frac=0.5, wick_frac=0.25),
    }.items():
        for ph, dd in [("in", d_in), ("out", d_out)]:
            st = stats(run_arc(dd, **kw))
            if st:
                rows.append({"variant": name, "phase": ph, **st})
    r = pd.DataFrame(rows)
    pd.set_option("display.width", 240)
    print("BTCUSD 15m, 540 days, walk-forward 360/180:")
    print(r.pivot_table(index="variant", columns="phase",
                        values=["n", "wr", "pf", "ret%", "avgR"],
                        aggfunc="first").round(2).to_string())

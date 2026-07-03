"""Quantum Wave Matrix (QWM) — mechanical implementation & test.

De-jargoned rules:
  entry  : after a vertical spike ("vector angle" >= 70deg) fade it —
           short the pump / long the dump
  angle  : arctan(dPrice/dTime) is unit-dependent, so we normalize:
           theta = arctan( (C[t] - C[t-w]) / (w * ATR) ).  tan(70deg)=2.75
           => the move must average >= 2.75 ATR per bar over the window.
  phase  : two versions tested —
           faithful : Phi(t) = sin(w*t + phi) anchored to a 4h cycle
                      (depends ONLY on clock time, not price)
           charitable: position in rolling 24h range >= 99.5% (short) /
                      <= 0.5% (long) — "price at the extreme of the wave"
  mass   : charitable integral = 20-bar volume z-score >= 1.0
  gates  : London 3:00-6:30 NY, New York 8:30-11:30 NY (approx UTC-4)
  chop   : |theta| < 45deg -> no trade (implicit: entry needs 70deg)
  SL     : extreme wick +/- 0.5 * sigma(20 closes)
  BE     : stop to entry after +1.5R
  TP     : midpoint of the rolling 24h (macro wave) range
  size   : risk 1% of equity per trade (their spec), costs: taker both ways
"""
import numpy as np
import pandas as pd

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
TAKER, SLIP = 0.0005, 0.0002
COST = 2 * (TAKER + SLIP)


def prep(df):
    df = df.copy()
    tr = pd.concat([df.high - df.low, (df.high - df.close.shift()).abs(),
                    (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    df["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    df["sigma20"] = df.close.rolling(20).std()
    df["hh"] = df.high.rolling(288).max()      # 24h wave range
    df["ll"] = df.low.rolling(288).min()
    df["mid"] = (df.hh + df.ll) / 2
    df["rangepos"] = (df.close - df.ll) / (df.hh - df.ll).replace(0, np.nan)
    df["volz"] = (df.volume - df.volume.rolling(20).mean()) / \
                 df.volume.rolling(20).std().replace(0, np.nan)
    # NY-time hour (approx UTC-4)
    ny = pd.to_datetime(df.time, unit="s", utc=True) - pd.Timedelta(hours=4)
    df["ny_minutes"] = ny.dt.hour * 60 + ny.dt.minute
    # faithful pi-phase: sine anchored to a 4h angular frequency
    omega = 2 * np.pi / (4 * 3600)
    df["phi_time"] = np.sin(omega * df.time.values)
    return df


def in_gate(m):
    return (180 <= m <= 390) or (510 <= m <= 690)  # 3:00-6:30, 8:30-11:30 NY


def run_qwm(df, angle_deg=70, window=3, phase="charitable", use_mass=True,
            use_gates=True, be_at_r=1.5, risk=0.01, eq0=1000.0, max_hold=288):
    d = prep(df)
    o, h, l, c = d.open.values, d.high.values, d.low.values, d.close.values
    atr, sig, mid = d.atr.values, d.sigma20.values, d.mid.values
    rp, vz, phit = d.rangepos.values, d.volz.values, d.phi_time.values
    nym = d.ny_minutes.values
    slope_thr = np.tan(np.radians(angle_deg))
    n = len(d)
    equity, trades, i = eq0, [], 300
    while i < n - 2:
        if use_gates and not in_gate(nym[i]):
            i += 1
            continue
        if np.isnan(atr[i]) or atr[i] <= 0 or np.isnan(mid[i]):
            i += 1
            continue
        vel = (c[i] - c[i - window]) / (window * atr[i])
        s = 0
        if vel >= slope_thr:
            s = -1  # fade the pump
        elif vel <= -slope_thr:
            s = 1   # fade the dump
        if s == 0:
            i += 1
            continue
        if phase == "faithful":
            ok = phit[i] >= 0.995 if s == -1 else phit[i] <= -0.995
        else:
            ok = rp[i] >= 0.995 if s == -1 else rp[i] <= 0.005
        if not ok or (use_mass and (np.isnan(vz[i]) or vz[i] < 1.0)):
            i += 1
            continue
        wick = h[i] if s == -1 else l[i]
        entry = o[i + 1] * (1 + SLIP * s)
        sl = wick - s * 0.5 * sig[i]
        tp = mid[i]
        stop_d = abs(entry - sl)
        if stop_d <= 0 or s * (tp - entry) <= 0:
            i += 1
            continue
        notional = min(equity * risk / (stop_d / entry), equity * 10)
        be_level = entry + s * be_at_r * stop_d
        cur_sl = sl
        exit_px, j = None, i + 1
        for j in range(i + 1, min(i + max_hold, n)):
            if s == 1:
                if l[j] <= cur_sl: exit_px = cur_sl; break
                if h[j] >= tp: exit_px = tp; break
                if h[j] >= be_level: cur_sl = max(cur_sl, entry)
            else:
                if h[j] >= cur_sl: exit_px = cur_sl; break
                if l[j] <= tp: exit_px = tp; break
                if l[j] <= be_level: cur_sl = min(cur_sl, entry)
        if exit_px is None:
            j = min(i + max_hold, n - 1)
            exit_px = c[j]
        ret = s * (exit_px - entry) / entry - COST
        pnl = notional * ret
        equity += pnl
        trades.append({"entry_time": int(d.time.iloc[i + 1]), "pnl": pnl,
                       "equity": equity, "rr_planned": abs(tp - entry) / stop_d,
                       "r_outcome": ret / (stop_d / entry)})
        i = j + 1
    return pd.DataFrame(trades)


def stats(t, eq0, days):
    if len(t) < 3:
        return {"trades": len(t)}
    eq = pd.concat([pd.Series([eq0]), t.equity])
    w = t[t.pnl > 0]
    return {"trades": len(t), "per_month": round(len(t) / days * 30, 1),
            "wr": round(100 * (t.pnl > 0).mean(), 1),
            "pf": round(w.pnl.sum() / max(1e-9, -t[t.pnl <= 0].pnl.sum()), 2),
            "ret%": round((eq.iloc[-1] / eq0 - 1) * 100, 2),
            "dd%": round(((eq / eq.cummax() - 1).min()) * 100, 2),
            "planned_RR": round(t.rr_planned.median(), 1)}


if __name__ == "__main__":
    rows = []
    from delta_scalper.config import Config
    from delta_scalper.delta_client import DeltaClient
    from run_backtest import fetch
    client = DeltaClient(Config().base_url)
    for sym in ["BTCUSD", "ETHUSD"]:
        print(f"fetching {sym} 5m x 180d ...")
        raw = fetch(client, sym, 5, 180)
        t0 = raw.time.min()
        split = t0 + 120 * 86400
        d_in = raw[raw.time < split].reset_index(drop=True)
        d_out = raw[raw.time >= split].reset_index(drop=True)
        variants = {
            "faithful (sine-of-time phase)": dict(phase="faithful"),
            "charitable (range-extreme)":    dict(phase="charitable"),
            "charitable, 60deg":             dict(phase="charitable", angle_deg=60),
            "charitable, 60deg, w=6":        dict(phase="charitable", angle_deg=60, window=6),
            "charitable, no gates":          dict(phase="charitable", angle_deg=60, use_gates=False),
            "charitable, no mass":           dict(phase="charitable", angle_deg=60, use_mass=False),
        }
        for name, kw in variants.items():
            for ph, d, days in [("in", d_in, 120), ("out", d_out, 60)]:
                t = run_qwm(d, **kw)
                st = stats(t, 1000.0, days)
                rows.append({"sym": sym, "variant": name, "phase": ph, **st})
    r = pd.DataFrame(rows)
    pd.set_option("display.width", 260)
    print(r.pivot_table(index="variant", columns=["sym", "phase"],
                        values=["trades", "wr", "pf", "ret%"],
                        aggfunc="first").round(2).to_string())

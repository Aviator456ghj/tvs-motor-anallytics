"""
Long-window (2-year) CVD-divergence backtest using a volume-delta PROXY,
since true buy/sell-tagged trade data isn't available that far back.

Proxy delta per daily candle (a standard substitute when real order flow
isn't available): assumes volume executed near the candle's close was more
buy-side if the candle closed in the upper part of its range, and more
sell-side if it closed in the lower part.

  delta = volume * [(close - low) - (high - close)] / (high - low)

This is clearly an approximation, not real CVD - reported separately from
the true 5-minute trade-tagged backtest for that reason.
"""
import csv
from measured_swing_backtest import load_data
from cvd_divergence_backtest import run_cvd_backtest, summarize

SRC = "data/btc_usd_daily.csv"
OUT = "data/btc_usd_daily_proxy_cvd.csv"


def build_proxy_cvd():
    bars = load_data(SRC)
    with open(SRC) as f:
        volumes = [float(r["volume"]) for r in csv.DictReader(f)]

    cvd = 0.0
    rows = []
    for b, vol in zip(bars, volumes):
        rng = b["high"] - b["low"]
        if rng > 0:
            delta = vol * ((b["close"] - b["low"]) - (b["high"] - b["close"])) / rng
        else:
            delta = 0.0
        cvd += delta
        rows.append({**b, "cvd": cvd})

    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "open", "high", "low", "close", "cvd"])
        for r in rows:
            w.writerow([r["date"], r["open"], r["high"], r["low"], r["close"], f"{r['cvd']:.6f}"])
    return rows


def main():
    proxy_bars = build_proxy_cvd()
    daily_bars = load_data(SRC)
    trades, fine_dates = run_cvd_backtest(daily_bars, proxy_bars, k=2, label="proxy")
    report = summarize(trades, fine_dates, proxy_bars, "PROXY DELTA, 2-YEAR DAILY (2024-07-07 -> 2026-06-27)")
    print(report)
    with open("results_cvd_proxy_2yr.txt", "w") as f:
        f.write(report + "\n")


if __name__ == "__main__":
    main()

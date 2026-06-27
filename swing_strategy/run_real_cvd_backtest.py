"""
Real CVD-divergence backtest: true buyer/seller-tagged trade data from
Kraken (see fetch_recent_trades.py), aggregated into 5-minute bars, over
the most recent ~30 days. Swing legs/zones still come from the full
2-year daily zig-zag so the comparison to the original Fibonacci backtest
stays apples-to-apples - only the entry trigger and stop placement change.
"""
from measured_swing_backtest import load_data
from cvd_divergence_backtest import load_bars_with_delta, run_cvd_backtest, summarize

DAILY_SRC = "data/btc_usd_daily.csv"
FINE_SRC = "data/btc_usd_5min_cvd.csv"


def main():
    daily_bars = load_data(DAILY_SRC)
    fine_bars = load_bars_with_delta(FINE_SRC)
    trades, fine_dates = run_cvd_backtest(daily_bars, fine_bars, k=3, label="real")
    window = f"{fine_bars[0]['date']} -> {fine_bars[-1]['date']}"
    report = summarize(trades, fine_dates, fine_bars, f"REAL 5-MIN TRADE-TAGGED CVD ({window})")
    print(report)
    with open("results_cvd_real_30d.txt", "w") as f:
        f.write(report + "\n")


if __name__ == "__main__":
    main()

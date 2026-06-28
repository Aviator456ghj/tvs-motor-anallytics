"""
Build aligned 1-minute / 15-minute / 4-hour BTCUSD OHLCV+order-flow bars from
the raw trade-by-trade dump already fetched for the 5-min CVD variant
(fetch_recent_trades.py's RAW_CHECKPOINT, 30 days, ~1.93M trades).

Kraken's public OHLC endpoint only ever serves the most recent 720 candles
per interval - for 1-minute that's 12 hours, nowhere near enough history
for a multi-timeframe backtest. Trades, by contrast, are paginated by ID
and were already pulled back 30 days. Aggregating that same raw trade feed
into three timeframes at once guarantees the 1m/15m/4h bars are exactly
consistent with each other (same source ticks), which matters for a
strategy that reasons about the same market across three timeframes
simultaneously.

Each bar also carries buy_vol/sell_vol/delta/cvd, built from Kraken's real
buyer/seller aggressor tag on every trade (not a price-uptick proxy) - this
is what lets a strategy reason about genuine order flow (absorption,
delta divergence) rather than price action alone.
"""
import csv
import time

RAW_CHECKPOINT = "/tmp/claude-0/-home-user-tvs-motor-anallytics/c7303aa4-a232-5e4d-b35a-e5cd7eac0bea/scratchpad/trades_raw.csv"

TIMEFRAMES = {
    "1min": (60, "data/btc_usd_1min.csv"),
    "15min": (900, "data/btc_usd_15min.csv"),
    "4h": (14400, "data/btc_usd_4h.csv"),
}


def aggregate():
    buckets = {name: {} for name in TIMEFRAMES}
    with open(RAW_CHECKPOINT) as f:
        reader = csv.reader(f)
        next(reader)
        for price, volume, t, side in reader:
            price, volume, t = float(price), float(volume), float(t)
            for name, (secs, _) in TIMEFRAMES.items():
                bucket_ts = int(t // secs) * secs
                b = buckets[name].setdefault(bucket_ts, {"o": None, "h": -1.0, "l": 1e18, "c": None,
                                                           "buy_vol": 0.0, "sell_vol": 0.0})
                if b["o"] is None:
                    b["o"] = price
                b["h"] = max(b["h"], price)
                b["l"] = min(b["l"], price)
                b["c"] = price
                if side == "b":
                    b["buy_vol"] += volume
                else:
                    b["sell_vol"] += volume

    for name, (secs, path) in TIMEFRAMES.items():
        rows = sorted(buckets[name].items())
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "datetime", "open", "high", "low", "close",
                        "volume", "buy_vol", "sell_vol", "delta", "cvd"])
            cvd = 0.0
            for ts, b in rows:
                dt = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts))
                vol = b["buy_vol"] + b["sell_vol"]
                delta = b["buy_vol"] - b["sell_vol"]
                cvd += delta
                w.writerow([ts, dt, b["o"], b["h"], b["l"], b["c"], round(vol, 8),
                            round(b["buy_vol"], 8), round(b["sell_vol"], 8),
                            round(delta, 8), round(cvd, 8)])
        print(f"{name}: {len(rows)} bars -> {path} "
              f"({rows[0][0] and time.strftime('%Y-%m-%d %H:%M', time.gmtime(rows[0][0]))} -> "
              f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime(rows[-1][0]))})")


if __name__ == "__main__":
    aggregate()

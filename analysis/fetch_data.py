"""Fetch historical 15m OHLCV candles from Crypto.com's public REST API.

The MCP tool only returns the most recent 50 candles; this paginates the
underlying public endpoint with `end_ts` to build a deeper local history
for backtesting.
"""
import csv
import time
from pathlib import Path

import requests

BASE_URL = "https://api.crypto.com/exchange/v1/public/get-candlestick"
DATA_DIR = Path(__file__).parent / "data"


def fetch_history(instrument: str, timeframe: str = "15m", days_back: int = 180) -> list[dict]:
    candles = {}
    end_ts = None
    window_ms = 300 * 15 * 60 * 1000  # 300 candles * 15min
    target_span_ms = days_back * 24 * 60 * 60 * 1000
    fetched_span = 0

    while fetched_span < target_span_ms:
        params = {"instrument_name": instrument, "timeframe": timeframe, "count": 300}
        if end_ts is not None:
            params["end_ts"] = end_ts
        resp = requests.get(BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("result", {}).get("data", [])
        if not data:
            break

        new_count = 0
        for c in data:
            if c["t"] not in candles:
                candles[c["t"]] = c
                new_count += 1
        if new_count == 0:
            break  # hit start of available history, API repeating oldest page

        oldest_ts = min(c["t"] for c in data)
        end_ts = oldest_ts - 1
        fetched_span = max(candles) - min(candles)
        time.sleep(0.15)

    return sorted(candles.values(), key=lambda c: c["t"])


def save_csv(instrument: str, candles: list[dict], timeframe: str = "15m") -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / f"{instrument}_{timeframe}.csv"
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_ms", "open", "high", "low", "close", "volume"])
        for c in candles:
            writer.writerow([c["t"], c["o"], c["h"], c["l"], c["c"], c["v"]])
    return path


if __name__ == "__main__":
    for instrument in ["BTC_USDT", "ETH_USDT", "SOL_USDT"]:
        print(f"Fetching {instrument} 15m history...")
        candles = fetch_history(instrument, days_back=365)
        path = save_csv(instrument, candles)
        print(f"  {len(candles)} candles -> {path}")

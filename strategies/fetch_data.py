"""
Fetch OHLCV candle history from Delta Exchange India's public REST API.
No auth required — public market data endpoint.

Usage:
    python3 fetch_data.py BTCUSD 30m 75 btcusd_30m_history.json
    python3 fetch_data.py BTCUSD 5m 75 btcusd_5m_history.json
"""

import sys
import json
import time
import urllib.request

BASE = "https://api.india.delta.exchange/v2"

RESOLUTION_SECONDS = {
    "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "2h": 7200, "4h": 14400, "6h": 21600, "1d": 86400,
}


def pub_get(path, params):
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(f"{BASE}{path}?{qs}", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def fetch_history(symbol, resolution, days_back):
    bar_seconds = RESOLUTION_SECONDS[resolution]
    end = int(time.time())
    full_start = end - days_back * 86400
    all_candles = {}
    cur_end = end
    chunk_seconds = 2000 * bar_seconds
    while cur_end > full_start:
        cur_start = max(full_start, cur_end - chunk_seconds)
        data = pub_get("/history/candles", {
            "symbol": symbol, "resolution": resolution, "start": cur_start, "end": cur_end,
        })
        result = data.get("result", [])
        for c in result:
            all_candles[c["time"]] = c
        if not result:
            break
        cur_end = cur_start - bar_seconds
        time.sleep(0.2)
    return sorted(all_candles.values(), key=lambda c: c["time"])


if __name__ == "__main__":
    symbol, resolution, days_back, outfile = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    candles = fetch_history(symbol, resolution, days_back)
    with open(outfile, "w") as f:
        json.dump(candles, f)
    if candles:
        print(f"{symbol} {resolution}: {len(candles)} candles, "
              f"{time.strftime('%Y-%m-%d', time.gmtime(candles[0]['time']))} to "
              f"{time.strftime('%Y-%m-%d', time.gmtime(candles[-1]['time']))} -> {outfile}")
    else:
        print(f"{symbol} {resolution}: NO DATA")

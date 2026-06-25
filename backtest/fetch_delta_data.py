"""Fetch historical OHLCV candles from Delta Exchange's public REST API.

Delta Exchange caps each /v2/history/candles call to a few thousand
candles, so we page backward in fixed-size time windows and concatenate.
No API key is required for public market data.
"""
import time
import urllib.request
import json
import pandas as pd

BASE_URL = "https://api.delta.exchange/v2/history/candles"


def fetch_candles(symbol: str, resolution: str, start: int, end: int,
                   chunk_seconds: int = 3 * 86400, pause: float = 0.2) -> pd.DataFrame:
    rows = []
    chunk_end = end
    while chunk_end > start:
        chunk_start = max(start, chunk_end - chunk_seconds)
        url = f"{BASE_URL}?resolution={resolution}&symbol={symbol}&start={chunk_start}&end={chunk_end}"
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read())
        if not data.get("success"):
            raise RuntimeError(f"Delta API error: {data}")
        rows.extend(data["result"])
        chunk_end = chunk_start
        time.sleep(pause)

    df = pd.DataFrame(rows).drop_duplicates(subset="time").sort_values("time")
    df["datetime"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.set_index("datetime")[["open", "high", "low", "close", "volume"]].astype(float)
    return df


if __name__ == "__main__":
    end = int(time.time())
    start = end - 30 * 86400
    df = fetch_candles("BTCUSDT", "5m", start, end)
    df.to_csv("/home/user/tvs-motor-anallytics/backtest/btcusdt_5m.csv")
    print(f"Fetched {len(df)} candles, {df.index.min()} -> {df.index.max()}")

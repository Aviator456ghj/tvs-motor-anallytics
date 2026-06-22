"""Fetch historical 15m OHLCV candles for gold and forex pairs from Yahoo
Finance's public chart API (no API key needed). Used to extend the
pressure-formula backtest beyond crypto.

Yahoo only serves 15m bars for the trailing ~60 days, so this is a
shorter window than the ~1 year of crypto data, but covers a fully
independent, non-crypto market (futures-quoted gold + major FX pairs).
"""
import csv
import time
from pathlib import Path

import requests

BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
DATA_DIR = Path(__file__).parent / "data"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

# (Yahoo symbol, local instrument name)
SYMBOLS = [
    ("GC=F", "XAUUSD"),      # COMEX gold futures, used as a gold-price proxy
    ("EURUSD=X", "EURUSD"),
    ("GBPUSD=X", "GBPUSD"),
    ("USDJPY=X", "USDJPY"),
]


def fetch_history(symbol: str, interval: str = "15m", range_: str = "60d") -> list[dict]:
    resp = requests.get(
        BASE_URL.format(symbol=symbol),
        params={"interval": interval, "range": range_},
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    result = resp.json()["chart"]["result"][0]
    ts = result["timestamp"]
    quote = result["indicators"]["quote"][0]

    candles = []
    for i, t in enumerate(ts):
        o, h, l, c = quote["open"][i], quote["high"][i], quote["low"][i], quote["close"][i]
        if None in (o, h, l, c):
            continue  # gaps from market-closed bars
        v = quote["volume"][i] or 0
        candles.append({"t": t * 1000, "o": o, "h": h, "l": l, "c": c, "v": v})
    return candles


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
    for symbol, instrument in SYMBOLS:
        print(f"Fetching {instrument} ({symbol}) 15m history...")
        candles = fetch_history(symbol)
        path = save_csv(instrument, candles)
        print(f"  {len(candles)} candles -> {path}")
        time.sleep(0.3)

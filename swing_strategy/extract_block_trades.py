"""
Extract individual large ("block") trades from the raw 30-day trade dump.

Order-book depth (resting bids/asks, walls) would be the most direct way to
see a big player's footprint, but Kraken's public Depth endpoint only ever
returns the *current* live book - the `since` parameter is silently
ignored, and there is no historical depth data anywhere in the public API.
That data was never captured and can't be reconstructed retroactively, so
it can only ever support a live monitor, not a backtest.

A single outsized trade print is the closest thing to a real institutional
footprint that *is* present in this historical dataset: Kraken tags every
trade with its real aggressor side ('b'/'s'), so a trade at or above
BLOCK_SIZE_THRESHOLD BTC is one large market order hitting the book in one
shot - much closer to "a big player just traded" than a bar-level volume
ratio computed over many small trades.

Output is a small CSV (price, volume, timestamp, side) sorted by time, so
the backtest can bisect into it cheaply instead of re-scanning all 1.93M
raw trades per leg evaluated.
"""
import csv

RAW_CHECKPOINT = "/tmp/claude-0/-home-user-tvs-motor-anallytics/c7303aa4-a232-5e4d-b35a-e5cd7eac0bea/scratchpad/trades_raw.csv"
OUT_PATH = "data/block_trades.csv"
BLOCK_SIZE_THRESHOLD = 2.0  # BTC


def extract(threshold=BLOCK_SIZE_THRESHOLD, out_path=OUT_PATH):
    rows = []
    with open(RAW_CHECKPOINT) as f:
        reader = csv.reader(f)
        next(reader)
        for price, volume, t, side in reader:
            v = float(volume)
            if v >= threshold:
                rows.append((float(t), float(price), v, side))
    rows.sort()
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "price", "volume", "side"])
        for t, price, v, side in rows:
            w.writerow([t, price, round(v, 8), side])
    print(f"{len(rows)} block trades (>= {threshold} BTC) -> {out_path}")


if __name__ == "__main__":
    extract()

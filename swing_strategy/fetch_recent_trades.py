"""
Pull real trade-by-trade data (with Kraken's buyer/seller aggressor tag)
for XBTUSD over the last LOOKBACK_DAYS and aggregate into 5-minute bars
with true Cumulative Volume Delta (CVD).

Kraken's public Trades endpoint already classifies every trade as
buyer-initiated ('b') or seller-initiated ('s') - this is real order-flow
data, not an approximation. We paginate with the 'since' cursor (nanosecond
trade id) and checkpoint progress so the run is resumable.
"""
import json
import time
import urllib.request
import urllib.error
import csv
import os

PAIR = "XBTUSD"
LOOKBACK_DAYS = 30
BAR_SECONDS = 5 * 60
RAW_CHECKPOINT = "/tmp/claude-0/-home-user-tvs-motor-anallytics/c7303aa4-a232-5e4d-b35a-e5cd7eac0bea/scratchpad/trades_raw.csv"
OUT_BARS = "data/btc_usd_5min_cvd.csv"
SLEEP_BETWEEN_CALLS = 0.3


def fetch_page(since):
    url = f"https://api.kraken.com/0/public/Trades?pair={PAIR}&since={since}&count=1000"
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = json.loads(resp.read())
            if data.get("error"):
                raise RuntimeError(str(data["error"]))
            key = [k for k in data["result"] if k != "last"][0]
            return data["result"][key], data["result"]["last"]
        except Exception as e:
            wait = 2 ** attempt
            print(f"  retry {attempt} after error: {e} (sleep {wait}s)")
            time.sleep(wait)
    raise RuntimeError("failed after retries")


def main():
    now_ns = int(time.time() * 1e9)
    start_ns = now_ns - LOOKBACK_DAYS * 86400 * 10**9

    since = start_ns
    if os.path.exists(RAW_CHECKPOINT):
        with open(RAW_CHECKPOINT) as f:
            lines = f.readlines()
        if len(lines) > 1:
            last_line = lines[-1]
            since = int(float(last_line.split(",")[2]) * 1e9)
            print(f"Resuming from checkpoint, since={since}")
            write_mode = "a"
        else:
            write_mode = "w"
    else:
        write_mode = "w"

    total = 0
    calls = 0
    with open(RAW_CHECKPOINT, write_mode, newline="") as f:
        w = csv.writer(f)
        if write_mode == "w":
            w.writerow(["price", "volume", "time", "side"])
        while since < now_ns:
            rows, last = fetch_page(since)
            if not rows:
                break
            for r in rows:
                w.writerow([r[0], r[1], r[2], r[3]])
            total += len(rows)
            calls += 1
            new_since = int(last)
            if new_since <= since:
                break
            since = new_since
            if calls % 50 == 0:
                f.flush()
                last_t = float(rows[-1][2])
                pct = min(100.0, (last_t * 1e9 - start_ns) / (now_ns - start_ns) * 100)
                print(f"  calls={calls} trades={total} progress~{pct:.1f}%")
            time.sleep(SLEEP_BETWEEN_CALLS)

    print(f"Done fetching: {calls} calls, {total} trades")
    aggregate_to_bars()


def aggregate_to_bars():
    buckets = {}
    with open(RAW_CHECKPOINT) as f:
        reader = csv.reader(f)
        next(reader)
        for price, volume, t, side in reader:
            price, volume, t = float(price), float(volume), float(t)
            bucket = int(t // BAR_SECONDS) * BAR_SECONDS
            b = buckets.setdefault(bucket, {"o": None, "h": -1, "l": 1e18, "c": None,
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

    os.makedirs(os.path.dirname(OUT_BARS), exist_ok=True)
    cvd = 0.0
    with open(OUT_BARS, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "datetime", "open", "high", "low", "close",
                    "buy_vol", "sell_vol", "delta", "cvd"])
        for bucket in sorted(buckets):
            b = buckets[bucket]
            delta = b["buy_vol"] - b["sell_vol"]
            cvd += delta
            import datetime as dt
            dts = dt.datetime.utcfromtimestamp(bucket).strftime("%Y-%m-%d %H:%M:%S")
            w.writerow([bucket, dts, b["o"], b["h"], b["l"], b["c"],
                        f"{b['buy_vol']:.6f}", f"{b['sell_vol']:.6f}", f"{delta:.6f}", f"{cvd:.6f}"])
    print(f"Wrote {len(buckets)} 5-min bars to {OUT_BARS}")


if __name__ == "__main__":
    main()

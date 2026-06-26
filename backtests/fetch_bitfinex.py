import urllib.request, json, time, sys, csv

def fetch(symbol, timeframe, start_ms, end_ms, out_path):
    rows = []
    cursor = start_ms
    url_base = f"https://api-pub.bitfinex.com/v2/candles/trade:{timeframe}:{symbol}/hist"
    while cursor < end_ms:
        url = f"{url_base}?start={cursor}&end={end_ms}&limit=10000&sort=1"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8.5.0", "Accept": "*/*"})
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.loads(r.read())
                break
            except Exception as e:
                print("retry", attempt, e, file=sys.stderr)
                time.sleep(2)
        else:
            raise RuntimeError("failed to fetch " + url)
        if not data:
            break
        rows.extend(data)
        last_ts = data[-1][0]
        if last_ts <= cursor:
            break
        cursor = last_ts + 1
        print(f"  fetched {len(data)} candles, up to {time.strftime('%Y-%m-%d', time.gmtime(last_ts/1000))}", file=sys.stderr)
        time.sleep(0.3)
    rows.sort(key=lambda x: x[0])
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts_ms", "open", "close", "high", "low", "volume"])
        for row in rows:
            w.writerow(row)
    print(f"Saved {len(rows)} rows to {out_path}")

if __name__ == "__main__":
    symbol = sys.argv[1]
    timeframe = sys.argv[2]
    start_ms = int(sys.argv[3])
    end_ms = int(sys.argv[4])
    out_path = sys.argv[5]
    fetch(symbol, timeframe, start_ms, end_ms, out_path)

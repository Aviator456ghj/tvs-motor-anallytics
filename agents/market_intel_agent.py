#!/usr/bin/env python3
"""Market Intelligence Agent — whale/order-flow tracking, market regime,
news, and an optional LLM reasoning layer, built on request.

⚠️ READ THIS BEFORE RUNNING: this agent is fundamentally different from
every strategy preset in this repo. Those are mechanical rules, walk-forward
backtested on years of candles with a measured win rate and profit factor.
THIS agent is a real-time MONITOR that surfaces what is actually happening
right now (whale trades, order book pressure, open interest, funding,
volatility/trend regime, news headlines) and — only with --reason — adds
an LLM's plain-English read of that snapshot. That reasoning step CANNOT
be backtested the way a candle rule can (an LLM call is not a
deterministic, cheaply-replayable function over history), so it carries NO
win rate, NO profit factor, and NO validation claim. Treat its output as a
second opinion to think about, not a signal to size into. It does NOT
place any orders — it only prints/logs/writes alerts. Wiring an LLM's
judgment directly into order placement is a materially bigger, riskier
step this script deliberately does not take; ask explicitly if you want
that.

COST: the deterministic monitor above (whale trades, order book, regime,
news) is 100% free, no LLM needed, no API key, ever. The --reason step has
TWO backends: 'ollama' (default) runs a free, open-source model on your
own machine via Ollama (https://ollama.com) — no account, no API key, no
cost, unlimited use, just weaker reasoning than Claude. 'anthropic' calls
Claude with your own ANTHROPIC_API_KEY — better quality, but real API
pricing applies past the small one-time free trial credit new accounts
get. If you can't pay for API access, use the default (ollama) — everyone
gets the full whale/order-book/regime/news monitor either way.

What it actually watches (all real data, no news/LLM needed for this part):
  - Order book: bid/ask depth imbalance, the single largest resting "wall"
    on each side (a visible large limit order — one real meaning of "big
    money" on an order book)
  - Recent trades: aggressive taker buy/sell volume ratio (order-flow
    pressure), and individual "whale" prints (trades in the top percentile
    of recent size)
  - Open interest change (6h) and funding rate — futures-specific
    positioning signals: rising OI + one-sided funding often means new
    money piling into one side, not just existing positions changing hands
  - Volatility regime (current ATR vs its own recent history) and trend
    regime (ADX-style directional strength) — "market conditions"
  - Recent crypto headlines (CoinDesk public RSS, no API key needed) —
    keyword-flagged for anything regulation/macro/hack/ETF related, since
    those are the categories that most reliably move crypto independent of
    chart structure

Usage:
    python agents/market_intel_agent.py --symbol BTCUSD
    python agents/market_intel_agent.py --symbol ETHUSD --interval 300
    # free LLM synthesis (needs Ollama installed + a model pulled, both free):
    python agents/market_intel_agent.py --symbol BTCUSD --reason
    # paid, higher-quality alternative, needs your own key:
    ANTHROPIC_API_KEY=sk-... python agents/market_intel_agent.py --symbol BTCUSD --reason --llm-backend anthropic

Writes each snapshot (and, with --reason, the LLM synthesis) to
agents/logs/market_intel_<symbol>.json, which the dashboard reads.
"""
import argparse
import json
import logging
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd  # noqa: E402

from delta_scalper.config import Config  # noqa: E402
from delta_scalper.delta_client import DeltaClient  # noqa: E402
from delta_scalper import orderflow  # noqa: E402

log = logging.getLogger("market_intel")
AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(AGENTS_DIR, "logs")

NEWS_RSS = "https://www.coindesk.com/arc/outboundfeeds/rss/"
NEWS_KEYWORDS = [
    "sec ", "regulat", "etf", "hack", "exploit", "rate cut", "rate hike",
    "fed ", "federal reserve", "inflation", "cpi", "ban ", "lawsuit",
    "liquidat", "outage", "halt", "delist",
]

CONTRACT_VALUE = {"BTCUSD": 0.001, "ETHUSD": 0.01, "SOLUSD": 1, "XRPUSD": 1}


def fetch_news(limit=8, timeout=15):
    """Public RSS, no key required. Returns [] on any failure — a dead
    news feed should never take the rest of the agent down with it."""
    try:
        req = urllib.request.Request(NEWS_RSS, headers={"User-Agent": "market-intel-agent/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            root = ET.fromstring(r.read())
        items = []
        for item in root.iter("item"):
            title = item.findtext("title", "").strip()
            if not title:
                continue
            flagged = [kw.strip() for kw in NEWS_KEYWORDS if kw in title.lower()]
            items.append({"title": title, "flagged": bool(flagged), "matched": flagged})
            if len(items) >= limit:
                break
        return items
    except Exception as e:
        log.warning("news fetch failed: %s", e)
        return []


def gather_snapshot(client, symbol, timeframe="15m", candle_bars=300):
    ticker = client.get_ticker(symbol)
    ob = client.get_orderbook(symbol)
    trades = client.get_recent_trades(symbol, page_size=200)
    tf_sec = {"15m": 900, "1h": 3600}[timeframe]
    now = int(time.time())
    raw = client.get_candles(symbol, timeframe, now - candle_bars * tf_sec, now)
    candles = pd.DataFrame(raw)
    for col in ["open", "high", "low", "close", "volume"]:
        candles[col] = candles[col].astype(float)
    candles = candles.sort_values("time").reset_index(drop=True)
    snap = orderflow.build_snapshot(symbol, ticker, ob, trades, candles,
                                    CONTRACT_VALUE.get(symbol, 1))
    return snap


def snapshot_to_dict(snap, news):
    return {
        "symbol": snap.symbol, "timestamp": int(time.time()), "mark_price": snap.mark_price,
        "spread_bps": round(snap.spread_bps, 2), "book_imbalance": round(snap.book_imbalance, 3),
        "bid_depth_usd": round(snap.bid_depth_usd), "ask_depth_usd": round(snap.ask_depth_usd),
        "biggest_bid_wall": snap.biggest_bid_wall, "biggest_ask_wall": snap.biggest_ask_wall,
        "taker_buy_ratio": round(snap.taker_buy_ratio, 3),
        "whale_trades": [{"price": w.price, "size": w.size, "notional_usd": round(w.notional_usd),
                         "side": w.side} for w in snap.whale_trades],
        "oi_change_usd_6h": snap.oi_change_usd_6h, "funding_rate": snap.funding_rate,
        "volatility_regime": snap.volatility_regime, "trend_regime": snap.trend_regime,
        "trend_direction": snap.trend_direction, "news": news,
    }


def rule_based_alerts(d):
    """Deterministic pre-alerts — no LLM needed, always on. Thresholds are
    intentionally conservative (fewer, more meaningful alerts, not noise)."""
    alerts = []
    if abs(d["book_imbalance"]) >= 0.4:
        side = "bids" if d["book_imbalance"] > 0 else "asks"
        alerts.append(f"Order book skewed toward {side} ({d['book_imbalance']:+.0%} imbalance)")
    if d["whale_trades"]:
        biggest = max(d["whale_trades"], key=lambda w: w["notional_usd"])
        if biggest["notional_usd"] >= 50_000:
            alerts.append(f"Whale {biggest['side']} print: ${biggest['notional_usd']:,.0f} "
                          f"@ {biggest['price']}")
    if abs(d["oi_change_usd_6h"]) >= 5_000_000:
        direction = "opening" if d["oi_change_usd_6h"] > 0 else "closing"
        alerts.append(f"Large open-interest {direction}: ${abs(d['oi_change_usd_6h']):,.0f} over 6h")
    if abs(d["funding_rate"]) >= 0.05:
        alerts.append(f"Extreme funding rate: {d['funding_rate']:+.3%} "
                      f"(crowded {'longs' if d['funding_rate'] > 0 else 'shorts'})")
    if d["volatility_regime"] == "high":
        alerts.append("Volatility regime: HIGH (top quartile of recent ATR)")
    if d["trend_regime"] == "trending":
        alerts.append(f"Trend regime: TRENDING {d['trend_direction'].upper()} (ADX-confirmed)")
    for n in d["news"]:
        if n["flagged"]:
            alerts.append(f"News flag [{'/'.join(n['matched'])}]: {n['title']}")
    return alerts


def _reasoning_prompt(d, alerts):
    return f"""You are a market-microstructure analyst. Below is a real,
live snapshot of {d['symbol']} on Delta Exchange India. Reason about it
plainly. You are NOT placing trades or giving financial advice — you are
summarizing what the data shows and flagging genuine uncertainty. If the
signals conflict or are weak, say so explicitly rather than forcing a
narrative.

SNAPSHOT:
{json.dumps(d, indent=2, default=str)}

RULE-BASED ALERTS ALREADY TRIGGERED:
{json.dumps(alerts, indent=2)}

Respond with ONLY a compact JSON object, no other text, no markdown fences:
{{"read": "<2-4 sentence plain-English synthesis>",
  "bias": "bullish" | "bearish" | "neutral" | "conflicting",
  "confidence": "low" | "medium" | "high",
  "worth_a_look": true | false,
  "caveats": "<what would make you wrong>"}}"""


def _parse_llm_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)  # tolerate a stray sentence around the JSON
    return json.loads(m.group(0) if m else text)


def llm_reasoning_anthropic(d, alerts):
    """Paid: Anthropic's API, the user's OWN ANTHROPIC_API_KEY (never
    embed one). Returns None (not an error) if no key is set, so the rest
    of the agent works identically with or without this layer. A new
    Anthropic account gets a small one-time free credit (~$5 as of this
    writing) — enough to try this, not enough to run it 24/7. For
    genuinely free, unlimited reasoning, use --llm-backend ollama below."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
    except ImportError:
        log.warning("`pip install anthropic` to enable --llm-backend anthropic")
        return None
    client = anthropic.Anthropic(api_key=api_key)
    try:
        resp = client.messages.create(
            model="claude-sonnet-5", max_tokens=500,
            messages=[{"role": "user", "content": _reasoning_prompt(d, alerts)}],
        )
        return _parse_llm_json(resp.content[0].text)
    except Exception as e:
        log.warning("Anthropic reasoning call failed: %s", e)
        return {"read": f"(Anthropic call failed: {e})", "bias": "unknown",
                "confidence": "low", "worth_a_look": False, "caveats": ""}


def llm_reasoning_ollama(d, alerts, model="llama3.2", host="http://localhost:11434"):
    """FREE, unlimited, runs entirely on your own machine via Ollama
    (https://ollama.com — free, open-source, no account, no API key).
    Install once, pull a model once (both free), then this costs nothing
    per call, ever — no rate limit, no credit card. Quality is well below
    Claude (these are much smaller models), so treat it as a rougher first
    pass, and double-check anything it flags as significant. Returns None
    (not an error) if Ollama isn't running, so the rest of the agent works
    identically without it."""
    import urllib.request as _u
    payload = json.dumps({
        "model": model, "stream": False, "format": "json",
        "messages": [{"role": "user", "content": _reasoning_prompt(d, alerts)}],
    }).encode()
    try:
        req = _u.Request(f"{host}/api/chat", data=payload,
                         headers={"Content-Type": "application/json"})
        with _u.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
        return _parse_llm_json(resp["message"]["content"])
    except Exception as e:
        log.warning("Ollama reasoning call failed (is `ollama serve` running? "
                    "did you `ollama pull %s`?): %s", model, e)
        return {"read": f"(Ollama call failed: {e})", "bias": "unknown",
                "confidence": "low", "worth_a_look": False, "caveats": ""}


def llm_reasoning(d, alerts, backend="anthropic", model=None):
    if backend == "ollama":
        return llm_reasoning_ollama(d, alerts, model=model or "llama3.2")
    return llm_reasoning_anthropic(d, alerts)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", default="BTCUSD", choices=list(CONTRACT_VALUE))
    ap.add_argument("--timeframe", default="15m", choices=["15m", "1h"])
    ap.add_argument("--interval", type=int, default=120, help="seconds between snapshots")
    ap.add_argument("--reason", action="store_true",
                    help="also get an LLM synthesized read (see --llm-backend)")
    ap.add_argument("--llm-backend", default="ollama", choices=["ollama", "anthropic"],
                    help="'ollama' (default): free, local, unlimited, needs Ollama installed. "
                         "'anthropic': needs your own ANTHROPIC_API_KEY, better quality, costs money "
                         "past the small one-time free trial credit.")
    ap.add_argument("--llm-model", default=None,
                    help="model name for the chosen backend (default: llama3.2 for ollama, "
                         "claude-sonnet-5 for anthropic)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    os.makedirs(LOGS, exist_ok=True)
    out_path = os.path.join(LOGS, f"market_intel_{args.symbol}.json")

    cfg = Config()
    client = DeltaClient(cfg.base_url)
    log.info("Market Intelligence Agent starting: %s %s interval=%ss reason=%s backend=%s",
             args.symbol, args.timeframe, args.interval, args.reason, args.llm_backend)
    if not args.reason:
        log.info("Running rule-based only (pass --reason for an LLM synthesis on top; "
                 "default backend is Ollama, free and local)")

    news_cache, news_fetched_at = [], 0
    while True:
        try:
            if time.time() - news_fetched_at > 900:  # refresh news every 15 min, not every loop
                news_cache = fetch_news()
                news_fetched_at = time.time()
            snap = gather_snapshot(client, args.symbol, args.timeframe)
            d = snapshot_to_dict(snap, news_cache)
            alerts = rule_based_alerts(d)
            d["alerts"] = alerts
            if alerts:
                for a in alerts:
                    log.info("PRE-ALERT [%s]: %s", args.symbol, a)
            else:
                log.info("[%s] no threshold trips this cycle (price=%.2f)", args.symbol, snap.mark_price)
            if args.reason:
                d["llm"] = llm_reasoning(d, alerts, backend=args.llm_backend, model=args.llm_model)
                if d["llm"]:
                    log.info("LLM read: %s", d["llm"].get("read"))
            with open(out_path, "w") as f:
                json.dump(d, f, indent=2, default=str)
        except KeyboardInterrupt:
            log.info("stopped by user")
            return
        except Exception:
            log.exception("loop error — continuing")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()

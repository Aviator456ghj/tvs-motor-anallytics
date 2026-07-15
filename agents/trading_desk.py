#!/usr/bin/env python3
"""AI Trading Desk — free, local, standalone. Not a Claude Code config.

You uploaded a reference project ("ai-trading-desk-claude") built as a
Claude Code configuration: markdown subagents + slash commands, no
standalone code anywhere. That architecture cannot be "wired to Ollama"
— there's no LLM API call in it to redirect; the "agents" ARE Claude
Code's own subagent mechanism, which only runs on a paid Claude plan or
API credits. This file is the actual, literal alternative: a real Python
program that replicates the same six-stage pipeline, but with genuine
code making genuine (and swappable) LLM calls — Ollama (free, local) by
default, Anthropic optional — against real Delta Exchange India data.

Pipeline (mirrors the reference project's stages):
  1. Data Acquisition   — Delta Exchange India public candles/orderbook/
                           trades (multi-timeframe) + CoinDesk RSS news +
                           your testnet wallet balance if connected
                           (read-only — same file intel_dashboard.py's
                           testnet panel writes to).
  2. Regime/Feature Engine — trend/volatility regime (delta_scalper.
                           orderflow), RSI/MACD/EMA-structure/ATR per
                           timeframe, support/resistance, order-book
                           imbalance, whale prints, funding/OI. Computed
                           in code, not asked of an LLM — this repo's
                           standing preference: deterministic first, the
                           LLM only ever adds judgment on top, never the
                           numbers themselves (a small local model is not
                           reliable at consistent arithmetic).
  3. Multi-Agent Reasoning — 5 real LLM calls, one per role (technical/
                           sentiment/macro/quant-regime/portfolio),
                           each returns stance + conviction + evidence +
                           main risk as parsed JSON.
  4. Risk review         — a 6th LLM call (risk-manager) reviews a
                           deterministically-computed ATR-based candidate
                           entry/stop/target, not invent one.
  5. CIO synthesis        — a 7th LLM call weighs the panel, writes the
                           thesis and scenario A/B/C, but the composite
                           score and BUY/SELL/HOLD band are computed in
                           Python from the panel's own numbers, not left
                           to the LLM to add up.
  6. Trade plan + HTML report — self-contained, saved to
                           reports/trading_desk/.

Never places an order — there is no order-placement call anywhere in
this file. Educational/research only, same disclaimer as the reference
project and every other LLM-touching piece of this repo.
"""
import argparse
import hashlib
import hmac
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd  # noqa: E402

from delta_scalper.config import Config              # noqa: E402
from delta_scalper.delta_client import DeltaClient   # noqa: E402
from delta_scalper.paper import PaperBroker          # noqa: E402
from delta_scalper import orderflow                  # noqa: E402
from delta_scalper.indicators import ema, rsi, atr, macd  # noqa: E402

log = logging.getLogger("trading_desk")
AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(AGENTS_DIR)
REPORTS_DIR = os.path.join(REPO, "reports", "trading_desk")

NEWS_RSS = "https://www.coindesk.com/arc/outboundfeeds/rss/"
CONTRACT_VALUE = {"BTCUSD": 0.001, "ETHUSD": 0.01, "SOLUSD": 1, "XRPUSD": 1}
TIMEFRAMES = ["15m", "1h", "4h", "1d"]
PRIMARY_TF = "1h"

TESTNET_BASE = "https://cdn-ind.testnet.deltaex.org"
TESTNET_KEYS_FILE = os.path.join(AGENTS_DIR, ".delta_testnet_keys.json")  # shared file with intel_dashboard.py


# ═══════════════════════════ 1. data acquisition ═══════════════════════════

def fetch_candles(client, symbol, resolution, bars=300):
    tf_sec = {"15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}[resolution]
    now = int(time.time())
    raw = client.get_candles(symbol, resolution, now - bars * tf_sec, now)
    df = pd.DataFrame(raw)
    if df.empty:
        return df
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    return df.sort_values("time").reset_index(drop=True)


def fetch_news(limit=8, timeout=15):
    """Public RSS, no key required. Returns [] on any failure."""
    try:
        req = urllib.request.Request(NEWS_RSS, headers={"User-Agent": "trading-desk/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            root = ET.fromstring(r.read())
        items = []
        for item in root.iter("item"):
            title = item.findtext("title", "").strip()
            if title:
                items.append(title)
            if len(items) >= limit:
                break
        return items
    except Exception as e:
        log.warning("news fetch failed: %s", e)
        return []


def load_testnet_keys():
    try:
        with open(TESTNET_KEYS_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def testnet_wallet_balance():
    """Read-only practice-money balance, if you've connected testnet keys
    via intel_dashboard.py's Broker panel (same file). Used only to size
    the SUGGESTED trade plan against a real number instead of a guess —
    never to place an order; there is no order-placement code here."""
    keys = load_testnet_keys()
    if not keys.get("api_key"):
        return None
    ts = str(int(time.time()))
    path = "/v2/wallet/balances"
    msg = "GET" + ts + path
    sig = hmac.new(keys["api_secret"].encode(), msg.encode(), hashlib.sha256).hexdigest()
    req = urllib.request.Request(TESTNET_BASE + path, headers={
        "api-key": keys["api_key"], "timestamp": ts, "signature": sig,
        "User-Agent": "trading-desk/1.0", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            res = json.load(r)
        if isinstance(res, dict) and res.get("success"):
            for b in res.get("result", []):
                if b.get("asset_symbol") in ("USD", "USDT") and float(b.get("balance", 0) or 0) > 0:
                    return float(b["balance"])
        return None
    except Exception as e:
        log.warning("testnet balance check failed: %s", e)
        return None


# ═══════════════════════════ 2. regime / feature engine ═══════════════════════════

def support_resistance(df, k=5, lookback=150):
    """Nearest confirmed k-bar swing high/low above/below the current
    price, from the recent window."""
    if len(df) < 2 * k + 10:
        return {"support": None, "resistance": None}
    sub = df.iloc[-lookback:].reset_index(drop=True)
    h, l, c = sub.high.values, sub.low.values, sub.close.values
    price = float(c[-1])
    highs, lows = [], []
    for j in range(k, len(sub) - k):
        if h[j] == h[j - k:j + k + 1].max():
            highs.append(float(h[j]))
        if l[j] == l[j - k:j + k + 1].min():
            lows.append(float(l[j]))
    resistance = min((x for x in highs if x > price), default=None)
    support = max((x for x in lows if x < price), default=None)
    return {"support": support, "resistance": resistance}


def build_features(client, symbol):
    """Stages 1+2: deterministic data acquisition and regime/feature
    engineering — no LLM involved, so it's free, fast, and reliable
    regardless of which LLM backend (or none) is available."""
    dfs = {tf: fetch_candles(client, symbol, tf) for tf in TIMEFRAMES}
    ticker = client.get_ticker(symbol)
    ob = client.get_orderbook(symbol)
    trades = client.get_recent_trades(symbol, page_size=200)
    mark = float(ticker.get("mark_price", 0) or 0)

    regimes = {}
    for tf, df in dfs.items():
        if len(df) < 60:
            continue
        reg = orderflow.market_regime(df)
        r = rsi(df.close, 14)
        _, _, m_hist = macd(df.close)
        e20, e50, e100 = ema(df.close, 20), ema(df.close, 50), ema(df.close, 100)
        a = atr(df, 14)
        if e20.iloc[-1] > e50.iloc[-1] > e100.iloc[-1]:
            alignment = "bullish"
        elif e20.iloc[-1] < e50.iloc[-1] < e100.iloc[-1]:
            alignment = "bearish"
        else:
            alignment = "mixed"
        regimes[tf] = dict(
            trend_regime=reg["trend_regime"], trend_direction=reg["trend_direction"],
            volatility_regime=reg["volatility_regime"], adx=round(float(reg["adx"]), 1),
            rsi=round(float(r.iloc[-1]), 1) if pd.notna(r.iloc[-1]) else None,
            macd_hist=round(float(m_hist.iloc[-1]), 4) if pd.notna(m_hist.iloc[-1]) else None,
            ema_alignment=alignment,
            atr_pct=round(float(a.iloc[-1]) / mark * 100, 3) if mark and pd.notna(a.iloc[-1]) else None,
        )

    primary_df = dfs.get(PRIMARY_TF, next(iter(dfs.values())))
    sr = support_resistance(primary_df)
    ob_a = orderflow.analyze_orderbook(ob, CONTRACT_VALUE.get(symbol, 1))
    tr_a = orderflow.analyze_trades(trades, CONTRACT_VALUE.get(symbol, 1), mark)

    conflicts = []
    trend_dirs = {tf: r["trend_direction"] for tf, r in regimes.items() if r["trend_regime"] == "trending"}
    if len(set(trend_dirs.values())) > 1:
        conflicts.append(f"Trending timeframes disagree on direction: {trend_dirs}")

    return dict(
        symbol=symbol, timestamp=int(time.time()), mark_price=mark,
        regimes=regimes, timeframe_conflicts=conflicts,
        support=sr["support"], resistance=sr["resistance"],
        book_imbalance=round(ob_a["book_imbalance"], 3),
        biggest_bid_wall=ob_a["biggest_bid_wall"], biggest_ask_wall=ob_a["biggest_ask_wall"],
        taker_buy_ratio=round(tr_a["taker_buy_ratio"], 3),
        whale_trades=[{"price": w.price, "notional_usd": round(w.notional_usd), "side": w.side}
                      for w in tr_a["whale_trades"]],
        funding_rate=float(ticker.get("funding_rate", 0) or 0),
        oi_change_usd_6h=float(ticker.get("oi_change_usd_6h", 0) or 0),
        news=fetch_news(),
        atr_1h=float(atr(dfs[PRIMARY_TF], 14).iloc[-1]) if PRIMARY_TF in dfs and len(dfs[PRIMARY_TF]) > 20 else None,
    )


# ═══════════════════════════ LLM dispatch (swappable backend) ═══════════════════════════

def _call_ollama(prompt, model="llama3.2", host="http://localhost:11434", timeout=90):
    payload = json.dumps({
        "model": model, "stream": False, "format": "json",
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(f"{host}/api/chat", data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read())
    return resp["message"]["content"]


def _call_anthropic(prompt, model=None, timeout=90):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("no ANTHROPIC_API_KEY set")
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model or "claude-sonnet-5", max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def _parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    return json.loads(m.group(0) if m else text)


def call_llm(prompt, backend="ollama", model=None):
    """Returns a parsed dict, or None on any failure — never raises, so
    one flaky agent call doesn't take the whole panel down."""
    try:
        raw = _call_ollama(prompt, model=model or "llama3.2") if backend == "ollama" \
            else _call_anthropic(prompt, model=model)
        return _parse_json(raw)
    except Exception as e:
        log.warning("LLM call failed (%s backend, %s): %s", backend,
                    model or ("llama3.2" if backend == "ollama" else "claude-sonnet-5"), e)
        return None


# ═══════════════════════════ 3. multi-agent reasoning panel ═══════════════════════════

# Each role's instructions, adapted from the reference project's own
# .claude/agents/*.md — same lens, same judgment, real LLM call instead
# of a Claude Code subagent.
ROLE_INSTRUCTIONS = {
    "technical-analyst":
        "You are a senior technical analyst. Using the per-timeframe regime/feature data below "
        "(trend, RSI, MACD histogram, EMA alignment, ATR%, support/resistance), assess trend and "
        "structure, momentum, moving-average alignment, and identify the key support/resistance "
        "level whose break would flip your read. If timeframes disagree, say which one you weight "
        "and why.",
    "sentiment-analyst":
        "You are a sentiment analyst. Using the news headlines below (if any), assess overall tone, "
        "whether sentiment looks stretched (contrarian risk), and whether it confirms or contradicts "
        "the technical picture. Never state rumor as fact. If there are no relevant headlines, say so "
        "plainly instead of inventing a narrative.",
    "macro-analyst":
        "You are a macro/positioning analyst. This system has ONLY crypto-specific positioning data "
        "(funding rate, 6h open-interest change) — no broader macro feeds (rates, DXY, COT). Say that "
        "limitation explicitly, then reason only from what's actually provided: funding rate, OI "
        "change, and the cross-timeframe trend regime as a rough risk-on/off proxy. Judge whether "
        "this is a tailwind, headwind, or neutral for the trade.",
    "quant-regime-analyst":
        "You are a quantitative regime analyst. The regime/feature computation below was already "
        "done deterministically in code, NOT by you — your job is to NARRATE it in plain English: "
        "summarize the regime per timeframe, flag any conflicts explicitly, and state which "
        "timeframe's regime should carry the most weight for a trade on the primary (1h) timeframe.",
    "portfolio-manager":
        "You are a portfolio manager. No existing portfolio or open positions are available in this "
        "system — state general guidance only: a sensible max allocation for a single-symbol crypto "
        "trade, and the main portfolio-level risk (concentration, correlation with a typical crypto "
        "book) of taking this position.",
}

JSON_SCHEMA_NOTE = (
    'Respond with ONLY a compact JSON object, no other text, no markdown fences: '
    '{"stance": "bullish"|"bearish"|"neutral", "conviction": <0-100 integer>, '
    '"evidence": ["<concrete point 1>", "<concrete point 2>", "<concrete point 3>"], '
    '"main_risk": "<the main risk to this view>"}'
)


def run_agent(role, features, backend, model):
    prompt = (
        f"{ROLE_INSTRUCTIONS[role]}\n\n"
        f"DATA (real, live, from Delta Exchange India, {features['symbol']}, "
        f"mark price {features['mark_price']}):\n{json.dumps(features, indent=2, default=str)}\n\n"
        f"{JSON_SCHEMA_NOTE}"
    )
    result = call_llm(prompt, backend=backend, model=model)
    if not result or "stance" not in result:
        return {"stance": "neutral", "conviction": 0, "evidence": [], "main_risk": "unavailable",
                "note": f"({role} LLM call failed or returned unusable output — treated as neutral/0)"}
    result.setdefault("evidence", [])
    result.setdefault("main_risk", "")
    result["conviction"] = max(0, min(100, int(result.get("conviction", 0) or 0)))
    if result["stance"] not in ("bullish", "bearish", "neutral"):
        result["stance"] = "neutral"
    return result


PANEL_ROLES = ["technical-analyst", "sentiment-analyst", "macro-analyst", "quant-regime-analyst"]
CATEGORY_WEIGHT = {"technical-analyst": 30, "quant-regime-analyst": 20,
                   "sentiment-analyst": 15, "macro-analyst": 15}


def run_panel(features, backend, model):
    panel = {}
    for role in PANEL_ROLES:
        log.info("running %s...", role)
        panel[role] = run_agent(role, features, backend, model)
    return panel


# ═══════════════════════════ 4. deterministic candidate plan + risk review ═══════════════════════════

STANCE_SIGN = {"bullish": 1, "bearish": -1, "neutral": 0}


def consensus_direction(panel):
    score = sum(STANCE_SIGN[a["stance"]] * a["conviction"] for a in panel.values())
    return 1 if score > 0 else (-1 if score < 0 else 0)


def candidate_plan(features, direction, stop_atr_mult=1.5, target_r_mult=2.0):
    """ATR-based candidate entry/stop/target, computed in code (not asked
    of the LLM) — the same formula used throughout this repo's other
    strategies. direction: 1 long / -1 short / 0 no clear direction."""
    a = features.get("atr_1h")
    mark = features["mark_price"]
    if not a or a <= 0 or direction == 0 or not mark:
        return None
    stop_dist = stop_atr_mult * a
    entry = mark
    stop = entry - direction * stop_dist
    target = entry + direction * stop_dist * target_r_mult
    return dict(side="long" if direction == 1 else "short", entry=round(entry, 4),
                stop=round(stop, 4), target=round(target, 4),
                r_r=round(target_r_mult, 2), stop_dist=stop_dist)


def run_risk_review(features, plan, backend, model):
    if plan is None:
        return {"stance": "neutral", "conviction": 0, "evidence": [],
                "main_risk": "no clear directional consensus", "recommended_size_pct": 0.0}
    prompt = (
        "You are a risk manager — capital preservation first. A candidate ATR-based trade has "
        "already been computed deterministically in code (NOT by you): "
        f"{json.dumps(plan, indent=2)}\n\n"
        f"Context: mark price {features['mark_price']}, 1h ATR {features.get('atr_1h')}, "
        f"support {features.get('support')}, resistance {features.get('resistance')}.\n\n"
        "Review it: is the stop technically justified, is the R:R acceptable (reject/downgrade if "
        "< 1.5), and what position size (as a % of account equity, 1-2% risk per trade is the "
        "default budget) would you recommend. Respond with ONLY a compact JSON object: "
        '{"stance": "trade"|"no_trade", "conviction": <0-100>, '
        '"evidence": ["...", "..."], "main_risk": "...", "recommended_size_pct": <number, e.g. 1.5>}'
    )
    result = call_llm(prompt, backend=backend, model=model)
    if not result:
        return {"stance": "neutral", "conviction": 0, "evidence": [],
                "main_risk": "risk-manager LLM call failed", "recommended_size_pct": 1.0}
    result.setdefault("recommended_size_pct", 1.0)
    result.setdefault("evidence", [])
    return result


def run_portfolio_review(features, backend, model):
    return run_agent("portfolio-manager", features, backend, model)


# ═══════════════════════════ 5. composite score + CIO synthesis ═══════════════════════════

def composite_score(panel, risk_review):
    direction = consensus_direction(panel)
    total = 0.0
    for role, weight in CATEGORY_WEIGHT.items():
        a = panel[role]
        agree = STANCE_SIGN[a["stance"]] * direction
        conv = a["conviction"] / 100.0
        if agree > 0:
            total += weight * conv
        elif agree < 0:
            total += weight * (1 - conv)
        else:
            total += weight * 0.5 * conv
    rr_component = risk_review.get("conviction", 0) / 100.0
    total += 20 * rr_component
    return round(max(0.0, min(100.0, total)), 1)


def run_cio(features, panel, risk_review, portfolio_review, plan, score, backend, model):
    direction = consensus_direction(panel)
    band = "action" if score >= 70 else ("lean" if score >= 45 else "hold")
    prompt = (
        "You are the Chief Investment Officer, the decision engine sitting above a specialist panel. "
        "You do NOT recompute the composite score or pick the direction — both were already computed "
        "deterministically in code: consensus direction is "
        f"{'LONG/bullish' if direction == 1 else ('SHORT/bearish' if direction == -1 else 'no clear consensus')}, "
        f"the Composite Signal Score is {score}/100 (band: {band} — >=70 favors action, 45-69 "
        f"lean/scale-in or wait for trigger, <45 hold/stand aside).\n\n"
        f"PANEL OUTPUTS:\n{json.dumps(panel, indent=2)}\n\n"
        f"RISK MANAGER REVIEW:\n{json.dumps(risk_review, indent=2)}\n\n"
        f"PORTFOLIO MANAGER REVIEW:\n{json.dumps(portfolio_review, indent=2)}\n\n"
        f"CANDIDATE TRADE PLAN:\n{json.dumps(plan, indent=2)}\n\n"
        "Your job: weigh the strongest arguments (not the loudest), reconcile disagreement, and write "
        "the synthesis. Respond with ONLY a compact JSON object: "
        '{"thesis": "<one paragraph>", "strongest_bull_point": "...", "strongest_bear_point": "...", '
        '"confidence_gauge": <0-100>, "reasoning_quality_gauge": <0-100>, "risk_gauge": <0-100>, '
        '"scenario_a_base": {"trigger": "...", "path": "...", "outcome": "...", "probability_pct": <num>}, '
        '"scenario_b_alternate": {"trigger": "...", "path": "...", "outcome": "...", "probability_pct": <num>}, '
        '"scenario_c_invalidation": {"trigger": "...", "path": "...", "outcome": "...", "probability_pct": <num>}, '
        '"what_would_change_my_mind": "..."} '
        "(the three scenario probabilities should sum to roughly 100)."
    )
    result = call_llm(prompt, backend=backend, model=model)
    if not result:
        result = {"thesis": "(CIO LLM call failed — no synthesis available; deterministic score/"
                            "direction/plan below are still real.)",
                  "strongest_bull_point": "", "strongest_bear_point": "",
                  "confidence_gauge": 0, "reasoning_quality_gauge": 0, "risk_gauge": 100,
                  "scenario_a_base": {}, "scenario_b_alternate": {}, "scenario_c_invalidation": {},
                  "what_would_change_my_mind": ""}
    decision = "HOLD"
    if band in ("action", "lean") and direction != 0:
        decision = "BUY" if direction == 1 else "SELL"
    result["decision"] = decision
    result["band"] = band
    result["direction"] = direction
    result["composite_score"] = score
    return result


# ═══════════════════════════ 6. trade plan + HTML report ═══════════════════════════

def build_final_plan(plan, risk_review, cio, equity):
    if plan is None or cio["decision"] == "HOLD":
        return None
    size_pct = max(0.1, min(5.0, float(risk_review.get("recommended_size_pct", 1.0) or 1.0))) / 100.0
    if cio["band"] == "lean":
        size_pct /= 2  # "45-69: lean/scale-in" -- half size vs. a full >=70 action signal
    notional = equity * size_pct / (plan["stop_dist"] / plan["entry"]) if plan["stop_dist"] else 0.0
    return dict(**plan, size_pct=round(size_pct * 100, 2), notional=round(notional, 2),
                equity_basis=equity, invalidation=plan["stop"], horizon="hours to a few days (1h setup)")


def render_html(symbol, features, panel, risk_review, portfolio_review, cio, final_plan, path):
    def esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    decision_color = {"BUY": "#3fb950", "SELL": "#f85149", "HOLD": "#8b949e"}[cio["decision"]]
    regime_rows = "".join(
        f"<tr><td>{tf}</td><td>{r['trend_regime']} {r['trend_direction']}</td>"
        f"<td>{r['volatility_regime']}</td><td>{r['rsi']}</td><td>{r['macd_hist']}</td>"
        f"<td>{r['ema_alignment']}</td><td>{r['atr_pct']}%</td></tr>"
        for tf, r in features["regimes"].items()
    )
    agent_cards = "".join(
        f'<div class="card"><h3>{role}</h3>'
        f'<div class="stance b-{a["stance"]}">{a["stance"].upper()} · {a["conviction"]}/100</div>'
        f'<ul>{"".join(f"<li>{esc(e)}</li>" for e in a.get("evidence", []))}</ul>'
        f'<div class="risk">Main risk: {esc(a.get("main_risk", ""))}</div></div>'
        for role, a in list(panel.items()) + [("risk-manager", risk_review), ("portfolio-manager", portfolio_review)]
    )
    scenarios = "".join(
        f'<div class="card"><h3>{label}</h3>'
        f'<div class="prob">{s.get("probability_pct", "?")}%</div>'
        f'<p><b>Trigger:</b> {esc(s.get("trigger", ""))}</p>'
        f'<p><b>Path:</b> {esc(s.get("path", ""))}</p>'
        f'<p><b>Outcome:</b> {esc(s.get("outcome", ""))}</p></div>'
        for label, s in [("A — Base", cio.get("scenario_a_base", {})),
                         ("B — Alternate", cio.get("scenario_b_alternate", {})),
                         ("C — Invalidation", cio.get("scenario_c_invalidation", {}))]
    )
    plan_html = (
        f'<table><tr><th>Side</th><th>Entry</th><th>Stop</th><th>Target</th><th>R:R</th>'
        f'<th>Size</th><th>Notional</th><th>Invalidation</th></tr>'
        f'<tr><td>{final_plan["side"]}</td><td>{final_plan["entry"]}</td><td>{final_plan["stop"]}</td>'
        f'<td>{final_plan["target"]}</td><td>{final_plan["r_r"]}</td><td>{final_plan["size_pct"]}%</td>'
        f'<td>${final_plan["notional"]}</td><td>{final_plan["invalidation"]}</td></tr></table>'
    ) if final_plan else '<p class="mut">No trade plan — decision is HOLD.</p>'

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>AI Trading Desk — {esc(symbol)}</title>
<style>
:root{{--bg:#0a0d12;--card:#12161d;--line:#232a35;--ink:#e6edf3;--mut:#8b949e;
--up:#3fb950;--dn:#f85149;--accent:#7aa2ff}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font:14px/1.6 -apple-system,'Segoe UI',Roboto,sans-serif;
padding:24px;max-width:1200px;margin:0 auto}}
h1{{font-size:22px}} h2{{font-size:16px;color:var(--accent);margin:24px 0 10px}}
h3{{font-size:13px;margin-bottom:6px}}
.sub{{color:var(--mut);font-size:12px;margin-bottom:16px}}
.warn{{background:#1a2230;border:1px solid #2d3f6e;border-radius:8px;padding:12px;font-size:12.5px;
color:#a9c1f0;margin-bottom:20px}}
.badge{{display:inline-block;padding:6px 18px;border-radius:8px;font-weight:700;font-size:16px;
color:#04140a;background:{decision_color}}}
.gauges{{display:flex;gap:16px;margin:14px 0;flex-wrap:wrap}}
.gauge{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 16px;min-width:120px}}
.gauge .n{{font-size:22px;font-weight:700}} .gauge .l{{font-size:11px;color:var(--mut)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px;margin-bottom:10px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}}
.stance{{font-weight:700;font-size:13px;margin-bottom:8px}}
.b-bullish{{color:var(--up)}} .b-bearish{{color:var(--dn)}} .b-neutral{{color:var(--mut)}}
ul{{margin-left:18px;margin-bottom:8px;font-size:12.5px}}
.risk{{color:var(--mut);font-size:11.5px}}
.prob{{font-size:20px;font-weight:700;color:var(--accent)}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{color:var(--mut);text-align:left;padding:6px 10px;border-bottom:1px solid var(--line)}}
td{{padding:6px 10px;border-bottom:1px solid #21262d}}
.mut{{color:var(--mut)}}
.thesis{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:10px 0}}
footer{{margin-top:30px;padding-top:16px;border-top:1px solid var(--line);color:var(--mut);font-size:11.5px}}
</style></head><body>
<h1>AI Trading Desk — {esc(symbol)}</h1>
<div class="sub">{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(features['timestamp']))} ·
mark price ${features['mark_price']}</div>
<div class="warn"><b>Educational / research only — NOT financial advice.</b> This never executes trades or
moves money; it only analyzes and recommends. Do your own due diligence.</div>

<div class="badge">{cio['decision']}</div>
<div class="gauges">
<div class="gauge"><div class="n">{cio['composite_score']}</div><div class="l">Composite Score</div></div>
<div class="gauge"><div class="n">{cio.get('confidence_gauge', '?')}</div><div class="l">Confidence</div></div>
<div class="gauge"><div class="n">{cio.get('reasoning_quality_gauge', '?')}</div><div class="l">Reasoning Quality</div></div>
<div class="gauge"><div class="n">{cio.get('risk_gauge', '?')}</div><div class="l">Risk</div></div>
</div>
<div class="thesis"><b>Thesis:</b> {esc(cio.get('thesis', ''))}<br><br>
<b>Strongest bull point:</b> {esc(cio.get('strongest_bull_point', ''))}<br>
<b>Strongest bear point:</b> {esc(cio.get('strongest_bear_point', ''))}<br>
<b>What would change this:</b> {esc(cio.get('what_would_change_my_mind', ''))}</div>

<h2>Regime by timeframe</h2>
<table><tr><th>TF</th><th>Trend</th><th>Volatility</th><th>RSI</th><th>MACD hist</th><th>EMA align</th><th>ATR%</th></tr>
{regime_rows}</table>
{f'<p class="risk" style="margin-top:8px">{esc("; ".join(features["timeframe_conflicts"]))}</p>' if features['timeframe_conflicts'] else ''}

<h2>Agent panel</h2>
<div class="grid">{agent_cards}</div>

<h2>Scenarios</h2>
<div class="grid">{scenarios}</div>

<h2>Trade plan</h2>
{plan_html}

<footer>AI Trading Desk — free/local build (Ollama by default) replicating the six-stage architecture of
the uploaded reference project. Real Delta Exchange India data; LLM reasoning quality depends entirely on
the backend/model used — treat as a rougher first pass with a local model, and always verify independently.
Never places an order.</footer>
</body></html>"""

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(html)


# ═══════════════════════════ orchestration ═══════════════════════════

def run(symbol, backend="ollama", model=None, equity_override=None):
    cfg = Config()
    client = DeltaClient(cfg.base_url)

    log.info("stage 1-2: data acquisition + regime/feature engine...")
    features = build_features(client, symbol)

    log.info("stage 3: multi-agent reasoning panel (%s backend)...", backend)
    panel = run_panel(features, backend, model)

    direction = consensus_direction(panel)
    plan = candidate_plan(features, direction)

    log.info("stage 4: risk + portfolio review...")
    risk_review = run_risk_review(features, plan, backend, model)
    portfolio_review = run_portfolio_review(features, backend, model)

    score = composite_score(panel, risk_review)

    log.info("stage 5: CIO synthesis...")
    cio = run_cio(features, panel, risk_review, portfolio_review, plan, score, backend, model)

    equity = equity_override if equity_override is not None else (testnet_wallet_balance() or 10000.0)
    final_plan = build_final_plan(plan, risk_review, cio, equity)

    ts = int(time.time())
    report_path = os.path.join(REPORTS_DIR, f"{symbol}_{ts}.html")
    render_html(symbol, features, panel, risk_review, portfolio_review, cio, final_plan, report_path)

    return dict(features=features, panel=panel, risk_review=risk_review,
                portfolio_review=portfolio_review, cio=cio, final_plan=final_plan,
                report_path=report_path)


# ═══════════════════════════ the "body" — paper execution (--loop) ═══════════════════════════
# A single run() call is the brain only: it thinks and writes a report, nothing more. --loop
# gives it paper hands: when the CIO's decision is BUY/SELL, it actually opens a simulated
# position at the exact plan (entry/stop/target/size) and manages it against live prices, same
# safety tier as market_intel_agent.py's --demo-trade. This NEVER places a real order — no live-
# broker or order-placement call exists anywhere in this file. Trades land in the shared
# trade_journal.csv (strategy="trading_desk") the same way every other paper-traded strategy in
# this repo does, so they're inspectable with the same tools.

def desk_broker(symbol, start_equity=None):
    cfg = Config()
    cfg.symbols = (symbol,)
    cfg.strategy = "trading_desk"
    cfg.state_file = f"scalper_state_trading_desk_{symbol}.json"
    if start_equity is not None:
        cfg.paper_start_equity = start_equity
    return PaperBroker(cfg)


def desk_trade_step(broker, symbol, mark_price, final_plan):
    """Manage any open paper position against the live price; if flat and
    a final_plan exists (CIO decision != HOLD), open it at the exact
    entry/stop/target/size the desk computed. Returns True if a new
    position was opened this call."""
    broker.check_pending(mark_price)
    pnl = broker.check_exit(mark_price)
    if pnl is not None:
        log.info("[DESK] %s position closed, pnl=%.4f, equity=%.2f", symbol, pnl, broker.equity)
    if broker.position is not None or broker.account.pending is not None:
        return False
    if final_plan is None:
        return False
    d = 1 if final_plan["side"] == "long" else -1
    stop_pct = abs(final_plan["entry"] - final_plan["stop"]) / final_plan["entry"] * 100
    broker.open_position(
        symbol, "buy" if d == 1 else "sell", final_plan["notional"],
        final_plan["entry"], final_plan["stop"], final_plan["target"],
        max_hold_seconds=7 * 86400,
        context={"setup": "trading_desk", "level": None, "wick_ratio": None,
                 "sweep_depth_atr": None, "vol_ratio": None, "trend_align": d,
                 "stop_pct": round(stop_pct, 3)},
    )
    log.info("[DESK] opened %s %s @ %.2f (composite score %.1f, size %.2f%%)",
             symbol, final_plan["side"].upper(), final_plan["entry"],
             final_plan.get("_composite_score", 0), final_plan["size_pct"])
    return True


def run_loop(symbol, backend, model, equity_override, interval, poll_seconds=30):
    """The body's main loop: cheap price polling every poll_seconds to
    manage any open position, and the full (expensive, LLM-driven)
    analysis pipeline every interval seconds while flat, to decide
    whether to open a new one."""
    broker = desk_broker(symbol, start_equity=equity_override)
    client = DeltaClient(Config().base_url)
    log.info("[DESK] paper trading ON for %s — starts at $%.2f, state file "
             "scalper_state_trading_desk_%s_paper.json. This NEVER touches real money.",
             symbol, broker.equity, symbol)
    last_pipeline_run = 0.0
    while True:
        try:
            ticker = client.get_ticker(symbol)
            mark = float(ticker.get("mark_price", 0) or 0)
            if mark:
                desk_trade_step(broker, symbol, mark, None)
            now = time.time()
            flat = broker.position is None and broker.account.pending is None
            if flat and now - last_pipeline_run >= interval:
                log.info("[DESK] running full analysis pipeline...")
                result = run(symbol, backend=backend, model=model, equity_override=broker.equity)
                last_pipeline_run = time.time()
                plan = result["final_plan"]
                if plan:
                    plan["_composite_score"] = result["cio"]["composite_score"]
                desk_trade_step(broker, symbol, result["features"]["mark_price"], plan)
        except KeyboardInterrupt:
            log.info("[DESK] stopped by user")
            return
        except Exception:
            log.exception("[DESK] loop error — continuing")
        time.sleep(poll_seconds)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", default="BTCUSD", choices=list(CONTRACT_VALUE))
    ap.add_argument("--llm-backend", default="ollama", choices=["ollama", "anthropic"],
                    help="'ollama' (default): free, local, unlimited. 'anthropic': needs your own "
                         "ANTHROPIC_API_KEY, better quality, costs money past a small free trial.")
    ap.add_argument("--llm-model", default=None,
                    help="model name for the chosen backend (default: llama3.2 for ollama, "
                         "claude-sonnet-5 for anthropic)")
    ap.add_argument("--equity", type=float, default=None,
                    help="starting/account equity for position sizing (default: your connected "
                         "testnet balance if available, else $10,000)")
    ap.add_argument("--loop", action="store_true",
                    help="give the desk a (paper) body: run forever, actually opening/managing "
                         "simulated positions from the CIO's decision — real behavior, zero real "
                         "money. Without this flag, it's brain-only: one analysis, one report, exit.")
    ap.add_argument("--interval", type=int, default=1800,
                    help="[--loop only] seconds between full analysis pipeline runs while flat "
                         "(default 1800 = 30min; a single run already takes a few minutes with a "
                         "local model, don't set this too low)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log.info("AI Trading Desk: %s backend=%s model=%s mode=%s", args.symbol, args.llm_backend,
             args.llm_model or "(default)", "loop/paper-trading" if args.loop else "single-shot")
    if args.llm_backend == "ollama":
        log.info("Free/local: make sure `ollama serve` is running and you've `ollama pull llama3.2` "
                 "(or pass --llm-model). This makes 6 LLM calls — expect it to take a few minutes on "
                 "a typical machine.")

    if args.loop:
        run_loop(args.symbol, args.llm_backend, args.llm_model, args.equity, args.interval)
        return

    result = run(args.symbol, backend=args.llm_backend, model=args.llm_model, equity_override=args.equity)

    cio = result["cio"]
    print(f"\n{'='*60}\nDECISION: {cio['decision']}  (composite score {cio['composite_score']}/100)")
    print(f"Confidence {cio.get('confidence_gauge')}  Reasoning {cio.get('reasoning_quality_gauge')}  "
          f"Risk {cio.get('risk_gauge')}")
    print(f"\nThesis: {cio.get('thesis')}")
    if result["final_plan"]:
        p = result["final_plan"]
        print(f"\nPlan: {p['side'].upper()} entry={p['entry']} stop={p['stop']} target={p['target']} "
              f"R:R={p['r_r']} size={p['size_pct']}% (${p['notional']} notional on ${p['equity_basis']:,.0f} equity)")
    else:
        print("\nNo trade plan — HOLD.")
    print(f"\nFull report: {result['report_path']}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

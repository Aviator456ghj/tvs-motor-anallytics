#!/usr/bin/env python3
"""Web interface for the 24/7 trading agent — stdlib only, no extra installs.

Start it:
    python agents/dashboard.py                              # http://localhost:8080
    python agents/dashboard.py --password mysecret          # require a login
    python agents/dashboard.py --host 0.0.0.0 --password s3 # reachable on your LAN

What you get in the browser:
  - start/stop buttons for every preset (scalper presets AND the new
    pattern presets from the July 2026 backtest study)
  - live paper equity, open position, and trade count per preset
  - the shared trade journal, filtered per preset
  - live log tail per preset
  - an embedded TradingView chart (free public widget, view-only)
  - a "Broker: Delta Exchange" panel — save API key/secret, test the
    connection, and see your live wallet balance
  - a "Market Intelligence" panel per symbol — whale trades, order-book
    imbalance, open interest/funding, volatility/trend regime, and news
    (agents/market_intel_agent.py). This is a MONITOR, not a backtested
    strategy — no win rate, no auto-execution.

About TradingView logins: the agent does NOT log into TradingView, on
purpose. TradingView has no public order API — orders execute at Delta
Exchange. For an in-TradingView view of these agents, load the Chrome
extension in extension/ — it slides a signals sidebar into tradingview.com
that reads this dashboard's API.

Security: with --password, access requires HTTP Basic auth. API keys are
stored in agents/.delta_keys.json (chmod 600) and never sent to any host
except api.india.delta.exchange. Never port-forward this to the internet.
"""
import argparse
import base64
import csv
import hashlib
import hmac
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(AGENTS_DIR)
LOGS = os.path.join(AGENTS_DIR, "logs")
KEYS_FILE = os.path.join(AGENTS_DIR, ".delta_keys.json")
DELTA_BASE = "https://api.india.delta.exchange"
sys.path.insert(0, AGENTS_DIR)
sys.path.insert(0, REPO)

from run_agent import PRESETS as SCALPER_PRESETS      # noqa: E402
from pattern_agent import PRESETS as PATTERN_PRESETS  # noqa: E402

PRESETS = {**SCALPER_PRESETS, **PATTERN_PRESETS}
RUNNER = {name: "run_agent.py" for name in SCALPER_PRESETS}
RUNNER.update({name: "pattern_agent.py" for name in PATTERN_PRESETS})

# Market Intelligence Agent — a real-time whale/order-flow/regime/news
# MONITOR, not a backtested strategy (see agents/market_intel_agent.py's
# module docstring). Runs alongside the trading presets, writes alerts
# to agents/logs/market_intel_<symbol>.json, never places orders.
INTEL_SYMBOLS = ["BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD"]
INTEL_PRESETS = {f"intel-{sym}": sym for sym in INTEL_SYMBOLS}

PRESET_META = {
    name: {"strategy": p["strategy"], "symbol": p["symbols"][0]}
    for name, p in PRESETS.items()
}
TV_SYMBOL = {"BTCUSD": "BINANCE:BTCUSDT", "ETHUSD": "BINANCE:ETHUSDT"}

PASSWORD = None  # set from --password


# ───────────────────────── process management ─────────────────────────

def pid_file(preset):
    return os.path.join(LOGS, f"{preset}.pid")


def log_file(preset):
    return os.path.join(LOGS, f"{preset}.log")


def _pid_alive(pid, preset):
    """Cross-platform liveness check. NEVER os.kill(pid,0) on Windows."""
    if os.name == "nt":
        try:
            out = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10).stdout
        except (OSError, subprocess.TimeoutExpired):
            return False
        return f'"{pid}"' in out and "python" in out.lower()
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            cmd = f.read().decode(errors="replace")
        return preset in cmd and ("run_agent" in cmd or "pattern_agent" in cmd
                                  or "market_intel_agent" in cmd)
    except FileNotFoundError:
        return True


def agent_pid(preset):
    try:
        with open(pid_file(preset)) as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return None
    marker = INTEL_PRESETS[preset] if preset in INTEL_PRESETS else preset
    return pid if _pid_alive(pid, marker) else None


def _agent_argv(preset, opts=None):
    opts = opts or {}
    if preset in INTEL_PRESETS:
        argv = [sys.executable, os.path.join(AGENTS_DIR, "market_intel_agent.py"),
                "--symbol", INTEL_PRESETS[preset]]
        if opts.get("reason"):
            argv.append("--reason")
        if opts.get("demo_trade"):
            argv.append("--demo-trade")  # implies --reason inside the script itself too
        return argv
    return [sys.executable, os.path.join(AGENTS_DIR, RUNNER[preset]), preset]


def start_agent(preset, opts=None):
    if agent_pid(preset):
        return {"ok": False, "error": "already running"}
    os.makedirs(LOGS, exist_ok=True)
    out = open(log_file(preset), "a")
    out.write(f"\n===== dashboard start {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n")
    out.flush()
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = (subprocess.DETACHED_PROCESS |
                                   subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        kwargs["start_new_session"] = True
    p = subprocess.Popen(
        _agent_argv(preset, opts),
        stdout=out, stderr=subprocess.STDOUT, cwd=REPO, **kwargs,
    )
    with open(pid_file(preset), "w") as f:
        f.write(str(p.pid))
    return {"ok": True, "pid": p.pid}


def stop_agent(preset):
    pid = agent_pid(preset)
    if not pid:
        return {"ok": False, "error": "not running"}
    os.kill(pid, signal.SIGTERM)
    try:
        os.remove(pid_file(preset))
    except OSError:
        pass
    return {"ok": True}


# ───────────────────────── broker: Delta Exchange ─────────────────────────

def load_keys():
    try:
        with open(KEYS_FILE) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_keys(api_key, api_secret):
    with open(KEYS_FILE, "w") as f:
        json.dump({"api_key": api_key, "api_secret": api_secret}, f)
    try:
        os.chmod(KEYS_FILE, 0o600)
    except OSError:
        pass


def delta_signed_get(path, query=""):
    """Signed GET against Delta Exchange India.
    signature = hex(HMAC_SHA256(secret, method + timestamp + path + query + body))"""
    keys = load_keys()
    if not keys.get("api_key"):
        return {"error": "no keys saved"}
    ts = str(int(time.time()))
    msg = "GET" + ts + path + (("?" + query) if query else "") + ""
    sig = hmac.new(keys["api_secret"].encode(), msg.encode(), hashlib.sha256).hexdigest()
    url = DELTA_BASE + path + (("?" + query) if query else "")
    req = urllib.request.Request(url, headers={
        "api-key": keys["api_key"], "timestamp": ts, "signature": sig,
        "User-Agent": "agent-dashboard/1.0", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return {"error": f"HTTP {e.code}", "detail": json.loads(e.read().decode())}
        except Exception:
            return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)}


def broker_status():
    keys = load_keys()
    out = {"connected": False, "keys_saved": bool(keys.get("api_key")),
           "key_hint": (keys.get("api_key", "")[:6] + "…") if keys.get("api_key") else None}
    if not out["keys_saved"]:
        return out
    res = delta_signed_get("/v2/wallet/balances")
    if isinstance(res, dict) and res.get("success"):
        bals = [{"asset": b.get("asset_symbol"),
                 "balance": b.get("balance"),
                 "available": b.get("available_balance")}
                for b in res.get("result", [])
                if float(b.get("balance", 0) or 0) != 0]
        out["connected"] = True
        out["balances"] = bals or [{"asset": "—", "balance": "0", "available": "0"}]
    else:
        out["error"] = res.get("error") or "authentication failed"
        out["detail"] = res.get("detail")
    return out


# ───────────────────────── data readers ─────────────────────────

def paper_state(preset):
    path = os.path.join(REPO, f"scalper_state_{preset}_paper.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            d = json.load(f)
        return {
            "equity": round(d.get("equity", 0), 2),
            "position": d.get("position"),
            "pending": d.get("pending"),
            "closed_trades": len(d.get("trades", [])),
        }
    except (json.JSONDecodeError, OSError):
        return None


def journal_rows(preset, limit=50):
    path = os.path.join(REPO, "trade_journal.csv")
    meta = PRESET_META[preset]
    rows = []
    if os.path.exists(path):
        with open(path) as f:
            for r in csv.DictReader(f):
                if r.get("strategy") == meta["strategy"] and r.get("symbol") == meta["symbol"]:
                    rows.append({k: r.get(k, "") for k in
                                 ("closed_at", "symbol", "side", "entry", "exit",
                                  "notional", "pnl", "r_outcome", "exit_reason")})
    return rows[-limit:]


def log_tail(preset, lines=60):
    path = log_file(preset)
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - 64 * 1024))
        text = f.read().decode(errors="replace")
    return "\n".join(text.splitlines()[-lines:])


def intel_data(symbol):
    """Latest Market Intelligence snapshot for a symbol, or None if that
    agent hasn't produced one yet (never started, or first cycle pending)."""
    path = os.path.join(LOGS, f"market_intel_{symbol}.json")
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def signals_summary():
    """Compact status for the TradingView sidebar extension."""
    out = []
    for name in PRESETS:
        st = paper_state(name)
        pos = st.get("position") if st else None
        out.append({
            "preset": name, "symbol": PRESET_META[name]["symbol"],
            "strategy": PRESET_META[name]["strategy"],
            "running": agent_pid(name) is not None,
            "equity": st["equity"] if st else None,
            "closed_trades": st["closed_trades"] if st else 0,
            "position": ({"side": pos.get("side"), "entry": pos.get("entry_price"),
                          "stop": pos.get("stop"), "target": pos.get("target"),
                          "pattern": pos.get("pattern"), "confirm": pos.get("confirm")}
                         if pos else None),
        })
    return out


# ───────────────────────── http server ─────────────────────────

class Handler(BaseHTTPRequestHandler):
    server_version = "AgentDash/2.0"

    def _authed(self):
        if PASSWORD is None:
            return True
        h = self.headers.get("Authorization", "")
        if h.startswith("Basic "):
            try:
                creds = base64.b64decode(h[6:]).decode()
                return creds.split(":", 1)[-1] == PASSWORD
            except Exception:
                return False
        return False

    def _deny(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Trading Agent Dashboard"')
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"login required")

    def _cors(self):
        # lets the TradingView sidebar extension (content script on
        # tradingview.com) read the API on localhost
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization,Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _html(self, body):
        body = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if not self._authed():
            return self._deny()
        u = urlparse(self.path)
        q = parse_qs(u.query)
        preset = (q.get("preset") or [None])[0]
        if u.path == "/":
            return self._html(PAGE)
        if u.path == "/api/status":
            out = {}
            for name in PRESETS:
                out[name] = {
                    "desc": PRESETS[name]["_desc"],
                    "running": agent_pid(name) is not None,
                    "state": paper_state(name),
                    "meta": PRESET_META[name],
                    "tv": TV_SYMBOL.get(PRESET_META[name]["symbol"], "BINANCE:BTCUSDT"),
                }
            return self._json(out)
        if u.path == "/api/signals":
            return self._json(signals_summary())
        if u.path == "/api/broker":
            return self._json(broker_status())
        if u.path == "/api/journal" and preset in PRESETS:
            return self._json(journal_rows(preset))
        if u.path == "/api/log" and preset in PRESETS:
            return self._json({"log": log_tail(preset)})
        if u.path == "/api/intel":
            out = {}
            for name, sym in INTEL_PRESETS.items():
                out[name] = {"symbol": sym, "running": agent_pid(name) is not None,
                            "data": intel_data(sym)}
            return self._json(out)
        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        if not self._authed():
            return self._deny()
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/api/broker/save":
            try:
                n = int(self.headers.get("Content-Length", 0))
                d = json.loads(self.rfile.read(n).decode())
                key, sec = d.get("api_key", "").strip(), d.get("api_secret", "").strip()
                if not key or not sec:
                    return self._json({"ok": False, "error": "key and secret required"}, 400)
                save_keys(key, sec)
                return self._json({"ok": True, **broker_status()})
            except Exception as e:
                return self._json({"ok": False, "error": str(e)}, 400)
        if u.path == "/api/broker/forget":
            try:
                os.remove(KEYS_FILE)
            except OSError:
                pass
            return self._json({"ok": True})
        preset = (q.get("preset") or [None])[0]
        if preset not in PRESETS and preset not in INTEL_PRESETS:
            return self._json({"error": "unknown preset"}, 400)
        if u.path == "/api/start":
            opts = {"reason": (q.get("reason") or ["0"])[0] == "1",
                    "demo_trade": (q.get("demo_trade") or ["0"])[0] == "1"}
            return self._json(start_agent(preset, opts))
        if u.path == "/api/stop":
            return self._json(stop_agent(preset))
        return self._json({"error": "not found"}, 404)


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trading Agent Dashboard</title>
<style>
:root{--bg:#0a0d12;--bg2:#0d1117;--card:#151b23;--card2:#1a212b;--line:#26303c;--line2:#323d4a;
--ink:#eef2f6;--mut:#8b98a8;--mut2:#5f6b7a;
--up:#3fb950;--up-dim:#1a4530;--dn:#f85149;--dn-dim:#4a1e1c;--amber:#e3a008;--accent:#4c8dff;
--shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px -8px rgba(0,0,0,.5);
--radius:12px}
*{box-sizing:border-box;margin:0;padding:0}
body{background:radial-gradient(1200px 600px at 15% -10%,#111a26 0%,var(--bg) 55%);color:var(--ink);
font:14px/1.55 -apple-system,'Segoe UI',Roboto,Inter,sans-serif;padding:0 0 40px;max-width:1240px;margin:0 auto;
-webkit-font-smoothing:antialiased}
.topbar{display:flex;align-items:center;gap:12px;padding:20px 20px 18px;position:sticky;top:0;z-index:10;
background:linear-gradient(180deg,var(--bg) 60%,rgba(10,13,18,0));backdrop-filter:blur(6px)}
.logo{width:34px;height:34px;border-radius:9px;background:linear-gradient(135deg,#4c8dff,#7c5cff);
display:flex;align-items:center;justify-content:center;font-weight:800;font-size:15px;color:#fff;
box-shadow:0 2px 12px -2px rgba(76,141,255,.5);flex-shrink:0}
.topbar-text{flex:1;min-width:0}
h1{font-size:19px;font-weight:700;letter-spacing:-.01em}
.sub{color:var(--mut);font-size:12px;margin-top:2px}
.main{padding:0 20px}
.warn{background:linear-gradient(135deg,#241014,#1a1013);border:1px solid #5a2226;border-radius:var(--radius);
padding:12px 14px;font-size:12.5px;color:#f4b3ae;margin-bottom:18px;box-shadow:var(--shadow)}
.warn b{color:#ff9d95}
.sectionhead{display:flex;align-items:baseline;gap:8px;margin:26px 0 12px}
.sectionhead h2{font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--ink)}
.sectionhead .tag{font-size:10.5px;color:var(--mut2);border:1px solid var(--line);border-radius:20px;padding:2px 9px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px;margin-bottom:8px}
.card{background:linear-gradient(180deg,var(--card2),var(--card));border:1px solid var(--line);
border-radius:var(--radius);padding:16px;box-shadow:var(--shadow);transition:border-color .15s,transform .15s}
.card:hover{border-color:var(--line2)}
.card h3{font-size:14.5px;font-weight:650;margin-bottom:5px;display:flex;align-items:center}
.desc{color:var(--mut);font-size:11.5px;margin-bottom:12px;min-height:40px;line-height:1.5}
.row{display:flex;justify-content:space-between;align-items:center;margin:5px 0;font-size:12.5px}
.mut{color:var(--mut)} .eq{font-size:18px;font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:-.01em}
.dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:7px;flex-shrink:0}
.on{background:var(--up);box-shadow:0 0 0 3px var(--up-dim)}
.off{background:var(--mut2)}
button{border:0;border-radius:8px;padding:8px 15px;font-weight:650;cursor:pointer;font-size:12.5px;
transition:filter .15s,transform .1s;letter-spacing:.01em}
button:hover{filter:brightness(1.12)} button:active{transform:scale(.97)}
.start{background:linear-gradient(135deg,#3fb950,#2ea043);color:#04220d}
.stop{background:linear-gradient(135deg,#f85149,#da3633);color:#2d0605}
.ghost{background:var(--card2);color:var(--ink);border:1px solid var(--line2)}
.btns{display:flex;gap:8px;margin-top:12px}
.panel{background:linear-gradient(180deg,var(--card2),var(--card));border:1px solid var(--line);
border-radius:var(--radius);padding:18px;margin-bottom:18px;box-shadow:var(--shadow)}
.panel h2{font-size:13.5px;font-weight:700;margin-bottom:12px;color:var(--ink);display:flex;align-items:center;gap:8px}
.panel h2::before{content:'';width:3px;height:14px;background:var(--accent);border-radius:2px;display:inline-block}
table{width:100%;border-collapse:collapse;font-size:12px}
th{color:var(--mut2);text-align:left;font-weight:600;text-transform:uppercase;letter-spacing:.04em;
font-size:10.5px;padding:6px 8px;border-bottom:1px solid var(--line)}
td{padding:7px 8px;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums}
tr:hover td{background:rgba(255,255,255,.015)}
.pos{color:var(--up)} .neg{color:var(--dn)}
pre{background:#060809;border:1px solid var(--line);border-radius:10px;padding:12px;font-size:11px;
font-family:'SF Mono',Consolas,Monaco,monospace;overflow-x:auto;white-space:pre-wrap;max-height:280px;
overflow-y:auto;color:#9da7b3;line-height:1.6}
#tvwrap{height:440px;border-radius:10px;overflow:hidden;border:1px solid var(--line)}
select,input{background:var(--card2);color:var(--ink);border:1px solid var(--line2);border-radius:7px;
padding:7px 10px;font-size:12.5px;transition:border-color .15s}
select:focus,input:focus{outline:none;border-color:var(--accent)}
input{width:100%;margin:4px 0}
.flex{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.badge{font-size:10.5px;border-radius:20px;padding:3px 10px;font-weight:650;letter-spacing:.02em}
.bok{background:var(--up-dim);color:#5fd975} .bno{background:var(--dn-dim);color:#ff8a83}
.brokergrid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
input[type=checkbox]{width:auto;accent-color:var(--accent);cursor:pointer}
::-webkit-scrollbar{width:9px;height:9px} ::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--line2);border-radius:6px}
@media(max-width:640px){#tvwrap{height:320px}.brokergrid{grid-template-columns:1fr}.main{padding:0 14px}}
</style></head><body>
<div class="topbar">
  <div class="logo">Δ</div>
  <div class="topbar-text">
    <h1>Trading Agent Dashboard</h1>
    <div class="sub">delta scalping + pattern research + market intelligence &middot; paper trading by default &middot; agents keep running even if you close this page</div>
  </div>
</div>
<div class="main">
<div class="warn"><b>Risk reminder:</b> scalper presets reproduced backtests with -55% to -90% max drawdowns; the
pattern presets are research-grade backtests (no fees/slippage modelled). Paper mode is where they all belong.</div>

<div class="panel"><div class="flex"><h2 style="margin:0">Broker — Delta Exchange India</h2>
<span id="bstat" class="badge bno">checking…</span></div>
<div class="brokergrid">
<div>
  <div class="mut" style="font-size:12px;margin-bottom:6px">Create an API key at
  Delta Exchange &rarr; Account &rarr; API keys (read + trade, IP-whitelist this machine).
  Keys are stored only in <code>agents/.delta_keys.json</code> on this computer.</div>
  <input id="bkey" placeholder="API key" autocomplete="off">
  <input id="bsec" placeholder="API secret" type="password" autocomplete="off">
  <div class="btns">
    <button class="start" onclick="brokerSave()">Save &amp; connect</button>
    <button class="ghost" onclick="brokerForget()">Forget keys</button>
  </div>
</div>
<div>
  <div class="mut" style="font-size:12px;margin-bottom:6px">Wallet</div>
  <table id="btab"><thead><tr><th>asset</th><th>balance</th><th>available</th></tr></thead><tbody></tbody></table>
  <div class="mut" id="bmsg" style="font-size:12px;padding-top:6px">not connected</div>
</div>
</div></div>

<div class="sectionhead"><h2>Market Intelligence</h2><span class="tag">monitor · no win rate · never trades live</span></div>
<div class="panel" style="padding-top:12px">
<div class="mut" style="font-size:11.5px;margin-bottom:4px">Whale trades, order-book imbalance, open interest/funding,
volatility/trend regime, and crypto news — 100% free, always on, no key needed. Check <b>Reason</b> per card for an LLM
synthesis on top (free via Ollama by default — install from ollama.com and <code>ollama pull llama3.2</code> — or your
own Anthropic key). Check <b>Demo trade</b> to let it paper-trade its own bias so you can watch a track record build;
it NEVER places a real order.</div>
<div class="grid" id="intelcards" style="margin-top:14px"></div></div>

<div class="sectionhead"><h2>Trading Presets</h2><span class="tag">mechanical rules · backtested</span></div>
<div class="grid" id="cards"></div>

<div class="panel"><div class="flex"><h2 style="margin:0">Chart</h2>
<select id="tvsym"><option value="BINANCE:BTCUSDT">BTCUSD</option><option value="BINANCE:ETHUSDT">ETHUSD</option></select></div>
<div id="tvwrap"><div id="tv_chart" style="height:100%"></div></div>
<div class="mut" style="font-size:11.5px;margin-top:8px">TradingView's free public widget — view-only, no login. Tip: load the extension in <code>extension/</code> for this agent's signals as a sidebar inside tradingview.com itself.</div></div>

<div class="panel"><div class="flex"><h2 style="margin:0">Trade Journal</h2>
<select id="jsel"></select></div>
<table id="jtab"><thead><tr><th>closed</th><th>side</th><th>entry</th><th>exit</th><th>notional</th><th>pnl</th><th>R</th><th>reason</th></tr></thead><tbody></tbody></table>
<div class="mut" id="jempty" style="padding:10px 4px;font-size:12px">no trades yet — signals fire a few times per week; leave it running</div></div>

<div class="panel"><div class="flex"><h2 style="margin:0">Agent Log</h2>
<select id="lsel"></select></div><pre id="logbox">select a preset…</pre></div>
</div>

<script src="https://s3.tradingview.com/tv.js"></script>
<script>
const $=id=>document.getElementById(id);
let presets=[];
function tv(sym){
  try{
    if(typeof TradingView==='undefined') throw new Error('script did not load');
    $('tv_chart').innerHTML='';
    new TradingView.widget({symbol:sym,interval:'60',theme:'dark',autosize:true,
      container_id:'tv_chart',hide_side_toolbar:true,allow_symbol_change:true});
  }catch(e){
    $('tv_chart').innerHTML='<div class="mut" style="padding:16px;font-size:12.5px">'+
      'Chart widget failed to load (offline, or s3.tradingview.com blocked) — everything else on this page still works.</div>';
  }
}
$('tvsym').onchange=e=>tv(e.target.value);
async function act(p,verb){ await fetch(`/api/${verb}?preset=${p}`,{method:'POST'}); refresh(); }
function fmt(x){ return x==null?'—':(+x).toLocaleString(undefined,{maximumFractionDigits:2}); }
async function refresh(){
  const st=await (await fetch('/api/status')).json();
  presets=Object.keys(st);
  $('cards').innerHTML=presets.map(p=>{const s=st[p],ps=s.state;
    const pos=ps&&ps.position?`${ps.position.side==='buy'?'LONG':'SHORT'} @ ${fmt(ps.position.entry_price)}`:'flat';
    return `<div class="card"><h3><span class="dot ${s.running?'on':'off'}"></span>${p}</h3>
    <div class="desc">${s.desc}</div>
    <div class="row"><span class="mut">paper equity</span><span class="eq">$${ps?fmt(ps.equity):'1,000.00'}</span></div>
    <div class="row"><span class="mut">position</span><span>${pos}</span></div>
    <div class="row"><span class="mut">closed trades</span><span>${ps?ps.closed_trades:0}</span></div>
    <div class="btns">${s.running
      ?`<button class="stop" onclick="act('${p}','stop')">Stop</button>`
      :`<button class="start" onclick="act('${p}','start')">Start</button>`}
    <button class="ghost" onclick="$('lsel').value='${p}';loadLog();$('jsel').value='${p}';loadJournal()">Inspect</button>
    </div></div>`;}).join('');
  for(const sel of ['jsel','lsel']) if(!$(sel).options.length)
    $(sel).innerHTML=presets.map(p=>`<option>${p}</option>`).join('');
}
function timeAgo(ts){ if(!ts) return '—'; const s=Math.floor(Date.now()/1000-ts);
  return s<90?`${s}s ago`:s<5400?`${Math.floor(s/60)}m ago`:`${Math.floor(s/3600)}h ago`; }
async function intelStart(p){
  const reason=$('reason-'+p).checked?1:0, demo=$('demo-'+p).checked?1:0;
  await fetch(`/api/start?preset=${p}&reason=${reason}&demo_trade=${demo}`,{method:'POST'});
  setTimeout(intelRefresh,300);
}
async function intelStop(p){ await fetch(`/api/stop?preset=${p}`,{method:'POST'}); setTimeout(intelRefresh,300); }
async function intelRefresh(){
  const st=await (await fetch('/api/intel')).json();
  $('intelcards').innerHTML=Object.keys(st).map(p=>{
    const s=st[p], d=s.data;
    const toggles=`<div class="row" style="gap:14px;margin-top:8px">
      <label style="font-size:11.5px;display:flex;align-items:center;gap:4px;cursor:pointer">
        <input type="checkbox" id="reason-${p}" ${s.running?'disabled':''}${d&&d.llm?'checked':''}> Reason (free/Ollama)</label>
      <label style="font-size:11.5px;display:flex;align-items:center;gap:4px;cursor:pointer">
        <input type="checkbox" id="demo-${p}" ${s.running?'disabled':''}${d&&d.demo_equity!=null?'checked':''}> Demo trade (paper)</label>
      </div>`;
    const btns=`<div class="btns">${s.running
      ?`<button class="stop" onclick="intelStop('${p}')">Stop</button>`
      :`<button class="start" onclick="intelStart('${p}')">Start</button>`}</div>`;
    if(!d){
      return `<div class="card"><h3><span class="dot ${s.running?'on':'off'}"></span>${s.symbol}</h3>
      <div class="desc">no snapshot yet${s.running?' — first cycle pending':''}</div>${toggles}${btns}</div>`;
    }
    const alerts=(d.alerts||[]).slice(0,4).map(a=>`<div class="row" style="color:#d29922">⚠ ${a}</div>`).join('')
      || `<div class="row mut">no threshold trips this cycle</div>`;
    const llm=d.llm?`<div class="row" style="margin-top:6px;padding-top:6px;border-top:1px solid #2d333b">
      <span class="mut">LLM read (${d.llm.confidence||'?'} confidence, ${d.llm.bias||'?'})</span></div>
      <div class="row" style="font-size:11.5px;color:#c3c2b7">${d.llm.read||''}</div>`:'';
    const demo=d.demo_equity!=null?`<div class="row" style="margin-top:6px;padding-top:6px;border-top:1px solid #2d333b">
      <span class="mut">demo paper equity</span><span class="eq">$${fmt(d.demo_equity)}</span></div>
      <div class="row"><span class="mut">demo position</span><span>${d.demo_position
        ?`${d.demo_position.side==='buy'?'LONG':'SHORT'} @ ${fmt(d.demo_position.entry_price)}`:'flat'}</span></div>`:'';
    return `<div class="card"><h3><span class="dot ${s.running?'on':'off'}"></span>${s.symbol}
      <span class="mut" style="font-weight:400;font-size:11px"> · ${timeAgo(d.timestamp)}</span></h3>
      <div class="row"><span class="mut">mark price</span><span>$${fmt(d.mark_price)}</span></div>
      <div class="row"><span class="mut">book imbalance</span><span>${(d.book_imbalance*100).toFixed(1)}%</span></div>
      <div class="row"><span class="mut">taker buy ratio</span><span>${(d.taker_buy_ratio*100).toFixed(0)}%</span></div>
      <div class="row"><span class="mut">regime</span><span>${d.volatility_regime} vol / ${d.trend_regime} ${d.trend_direction}</span></div>
      <div class="row"><span class="mut">funding</span><span>${(d.funding_rate*100).toFixed(3)}%</span></div>
      ${alerts}${llm}${demo}${toggles}${btns}</div>`;
  }).join('');
}
async function brokerRefresh(){
  const b=await (await fetch('/api/broker')).json();
  const s=$('bstat');
  if(b.connected){ s.textContent='connected'; s.className='badge bok';
    $('bmsg').textContent=`key ${b.key_hint} — live balance from Delta Exchange India`;
    $('btab').tBodies[0].innerHTML=(b.balances||[]).map(x=>
      `<tr><td>${x.asset}</td><td>${fmt(x.balance)}</td><td>${fmt(x.available)}</td></tr>`).join('');
  } else if(b.keys_saved){ s.textContent='auth failed'; s.className='badge bno';
    $('bmsg').textContent=`saved key ${b.key_hint} rejected: ${b.error||''}`;
  } else { s.textContent='not connected'; s.className='badge bno';
    $('bmsg').textContent='no API keys saved yet'; }
}
async function brokerSave(){
  const r=await fetch('/api/broker/save',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({api_key:$('bkey').value,api_secret:$('bsec').value})});
  await r.json(); $('bkey').value='';$('bsec').value=''; brokerRefresh();
}
async function brokerForget(){ await fetch('/api/broker/forget',{method:'POST'}); brokerRefresh(); }
async function loadJournal(){ const p=$('jsel').value; if(!p)return;
  const rows=await (await fetch(`/api/journal?preset=${p}`)).json();
  $('jempty').style.display=rows.length?'none':'block';
  $('jtab').tBodies[0].innerHTML=rows.reverse().map(r=>{
    const d=new Date(+r.closed_at*1000).toLocaleString();
    const cls=+r.pnl>=0?'pos':'neg';
    return `<tr><td>${d}</td><td>${r.side}</td><td>${fmt(r.entry)}</td><td>${fmt(r.exit)}</td>
    <td>${fmt(r.notional)}</td><td class="${cls}">${fmt(r.pnl)}</td><td class="${cls}">${r.r_outcome}</td><td>${r.exit_reason}</td></tr>`;}).join('');
}
async function loadLog(){ const p=$('lsel').value; if(!p)return;
  const d=await (await fetch(`/api/log?preset=${p}`)).json();
  $('logbox').textContent=d.log||'(no log yet — start the agent)'; }
$('jsel').onchange=loadJournal; $('lsel').onchange=loadLog;
// each independent so one failing (e.g. offline, TradingView blocked) never blocks the rest
for(const fn of [refresh, ()=>tv('BINANCE:BTCUSDT'), brokerRefresh, intelRefresh])
  try{ fn(); }catch(e){ console.error(e); }
setInterval(refresh,5000); setInterval(loadLog,7000); setInterval(loadJournal,15000);
setInterval(brokerRefresh,30000); setInterval(intelRefresh,10000);
</script></body></html>
"""


def main():
    global PASSWORD
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--password", default=None)
    args = ap.parse_args()
    PASSWORD = args.password
    if args.host != "127.0.0.1" and not PASSWORD:
        print("refusing to bind beyond localhost without --password")
        sys.exit(1)
    os.makedirs(LOGS, exist_ok=True)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    where = f"http://{'localhost' if args.host == '127.0.0.1' else args.host}:{args.port}"
    print(f"Trading Agent Dashboard running -> {where}"
          + ("  (login required)" if PASSWORD else ""))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\ndashboard stopped (agents keep running)")


if __name__ == "__main__":
    main()

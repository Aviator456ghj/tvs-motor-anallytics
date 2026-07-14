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

# Exceptions that just mean "the browser closed/canceled the request before
# we finished writing the response" — a tab refresh, navigation, or an
# overlapping poll. Harmless and extremely common; not worth a traceback.
CLIENT_GONE = (ConnectionAbortedError, ConnectionResetError, BrokenPipeError, TimeoutError)
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
        return preset in cmd and ("run_agent" in cmd or "pattern_agent" in cmd)
    except FileNotFoundError:
        return True


def agent_pid(preset):
    try:
        with open(pid_file(preset)) as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return None
    return pid if _pid_alive(pid, preset) else None


def start_agent(preset):
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
        [sys.executable, os.path.join(AGENTS_DIR, RUNNER[preset]), preset],
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
        if preset not in PRESETS:
            return self._json({"error": "unknown preset"}, 400)
        if u.path == "/api/start":
            return self._json(start_agent(preset))
        if u.path == "/api/stop":
            return self._json(stop_agent(preset))
        return self._json({"error": "not found"}, 404)


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trading Agent Dashboard</title>
<style>
:root{--bg:#0d1117;--card:#161b22;--line:#2d333b;--ink:#e6edf3;--mut:#8b949e;
--up:#3fb950;--dn:#f85149;--amber:#d29922;--accent:#eda100}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,'Segoe UI',Roboto,sans-serif;padding:16px;max-width:1200px;margin:0 auto}
h1{font-size:19px;margin-bottom:2px} .sub{color:var(--mut);font-size:12px;margin-bottom:16px}
.warn{background:#2d1a1a;border:1px solid #6e2c2c;border-radius:8px;padding:10px 12px;font-size:12.5px;color:#f0b0ae;margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:12px;margin-bottom:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.card h3{font-size:14px;margin-bottom:4px}
.desc{color:var(--mut);font-size:11.5px;margin-bottom:10px;min-height:44px}
.row{display:flex;justify-content:space-between;align-items:center;margin:4px 0;font-size:13px}
.mut{color:var(--mut)} .eq{font-size:17px;font-weight:600}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.on{background:var(--up)} .off{background:#484f58}
button{border:0;border-radius:7px;padding:7px 14px;font-weight:600;cursor:pointer;font-size:12.5px}
.start{background:var(--up);color:#04260f} .stop{background:var(--dn);color:#2d0605}
.ghost{background:#21262d;color:var(--ink);border:1px solid var(--line)}
.btns{display:flex;gap:8px;margin-top:10px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:16px}
.panel h2{font-size:14px;margin-bottom:10px;color:var(--accent)}
table{width:100%;border-collapse:collapse;font-size:12px}
th{color:var(--mut);text-align:left;font-weight:500;padding:4px 8px;border-bottom:1px solid var(--line)}
td{padding:4px 8px;border-bottom:1px solid #21262d;font-variant-numeric:tabular-nums}
.pos{color:var(--up)} .neg{color:var(--dn)}
pre{background:#0a0d12;border:1px solid var(--line);border-radius:8px;padding:10px;font-size:11px;overflow-x:auto;white-space:pre-wrap;max-height:280px;overflow-y:auto;color:#9da7b3}
#tvwrap{height:440px;border-radius:10px;overflow:hidden;border:1px solid var(--line)}
select,input{background:#21262d;color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:5px 8px}
input{width:100%;margin:4px 0;font-size:12.5px}
.flex{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.badge{font-size:11px;border-radius:5px;padding:2px 7px;font-weight:600}
.bok{background:#12351f;color:var(--up)} .bno{background:#3a1416;color:var(--dn)}
.brokergrid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:640px){#tvwrap{height:320px}.brokergrid{grid-template-columns:1fr}}
</style></head><body>
<h1>Trading Agent Dashboard</h1>
<div class="sub">delta scalping + pattern research &mdash; paper trading by default &middot; agents keep running even if you close this page</div>
<div class="warn"><b>Risk reminder:</b> scalper presets reproduced backtests with -55% to -90% max drawdowns; the
pattern presets are research-grade backtests (no fees/slippage modelled). Paper mode is where they all belong.</div>

<div class="panel"><div class="flex"><h2 style="margin:0">Broker &mdash; Delta Exchange India</h2>
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

<div class="grid" id="cards"></div>

<div class="panel"><div class="flex"><h2 style="margin:0">Chart (TradingView free widget &mdash; view-only, no login)</h2>
<select id="tvsym"><option value="BINANCE:BTCUSDT">BTCUSD</option><option value="BINANCE:ETHUSDT">ETHUSD</option></select></div>
<div id="tvwrap"><div id="tv_chart" style="height:100%"></div></div>
<div class="mut" style="font-size:11.5px;margin-top:6px">Tip: install the extension in <code>extension/</code> to get this agent's signals as a sidebar inside tradingview.com itself.</div></div>

<div class="panel"><div class="flex"><h2 style="margin:0">Trade journal</h2>
<select id="jsel"></select></div>
<table id="jtab"><thead><tr><th>closed</th><th>side</th><th>entry</th><th>exit</th><th>notional</th><th>pnl</th><th>R</th><th>reason</th></tr></thead><tbody></tbody></table>
<div class="mut" id="jempty" style="padding:8px;font-size:12px">no trades yet — signals fire a few times per week; leave it running</div></div>

<div class="panel"><div class="flex"><h2 style="margin:0">Agent log</h2>
<select id="lsel"></select></div><pre id="logbox">select a preset…</pre></div>

<script src="https://s3.tradingview.com/tv.js"></script>
<script>
const $=id=>document.getElementById(id);
let presets=[];
function tv(sym){ $('tv_chart').innerHTML='';
  new TradingView.widget({symbol:sym,interval:'60',theme:'dark',autosize:true,
    container_id:'tv_chart',hide_side_toolbar:true,allow_symbol_change:true}); }
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
refresh(); tv('BINANCE:BTCUSDT'); brokerRefresh();
setInterval(refresh,5000); setInterval(loadLog,7000); setInterval(loadJournal,15000);
setInterval(brokerRefresh,30000);
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

    class Server(ThreadingHTTPServer):
        def handle_error(self, request, client_address):
            if sys.exc_info()[0] in CLIENT_GONE:
                return  # client disconnected mid-response; nothing to act on
            super().handle_error(request, client_address)

    srv = Server((args.host, args.port), Handler)
    where = f"http://{'localhost' if args.host == '127.0.0.1' else args.host}:{args.port}"
    print(f"Trading Agent Dashboard running -> {where}"
          + ("  (login required)" if PASSWORD else ""))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\ndashboard stopped (agents keep running)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Web interface for the 24/7 trading agent — stdlib only, no extra installs.

Start it:
    python agents/dashboard.py                              # http://localhost:8080
    python agents/dashboard.py --password mysecret          # require a login
    python agents/dashboard.py --host 0.0.0.0 --password s3 # reachable on your LAN
                                                            # (phone browser etc.)

What you get in the browser:
  - start/stop buttons for every preset (each runs as its own background
    process that keeps running even if you close the dashboard)
  - live paper equity, open position, and trade count per preset
  - the shared trade journal, filtered per preset
  - live log tail per preset
  - an embedded TradingView chart (TradingView's free public widget — no
    TradingView account or login needed; it's view-only market data)

About TradingView logins: the agent does NOT log into TradingView, on
purpose. A TradingView login adds no trading ability (TradingView has no
public order API — orders execute at a broker, and Delta Exchange India is
not a TradingView broker), and automating a login against their site
violates their terms of service and breaks at the first captcha. The chart
below is TradingView's official free embed; execution happens directly on
Delta Exchange via the agent processes.

Security note: with --password, access requires HTTP Basic auth (the
browser shows a login box). Only expose beyond localhost (--host 0.0.0.0)
on a network you trust — this is a hobby dashboard, not a hardened web
app. Never port-forward it to the open internet.
"""
import argparse
import base64
import csv
import json
import os
import signal
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(AGENTS_DIR)
LOGS = os.path.join(AGENTS_DIR, "logs")
sys.path.insert(0, AGENTS_DIR)
sys.path.insert(0, REPO)

from run_agent import PRESETS  # noqa: E402

# preset -> (strategy, symbol) for journal filtering / chart symbol
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


def agent_pid(preset):
    """Return the live pid for a preset, or None. Guards against pid reuse
    by checking the process cmdline actually mentions the preset."""
    try:
        with open(pid_file(preset)) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)  # raises if dead
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            cmd = f.read().decode(errors="replace")
        if preset in cmd and "run_agent" in cmd:
            return pid
    except (OSError, ValueError, FileNotFoundError):
        pass
    return None


def start_agent(preset):
    if agent_pid(preset):
        return {"ok": False, "error": "already running"}
    os.makedirs(LOGS, exist_ok=True)
    out = open(log_file(preset), "a")
    out.write(f"\n===== dashboard start {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n")
    out.flush()
    p = subprocess.Popen(
        [sys.executable, os.path.join(AGENTS_DIR, "run_agent.py"), preset],
        stdout=out, stderr=subprocess.STDOUT, cwd=REPO,
        start_new_session=True,  # survives the dashboard being closed
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


# ───────────────────────── data readers ─────────────────────────

def paper_state(preset):
    """Equity / open position from the preset's paper-broker state file."""
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


# ───────────────────────── http server ─────────────────────────

class Handler(BaseHTTPRequestHandler):
    server_version = "AgentDash/1.0"

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

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, body):
        body = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # quieter console
        pass

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
select{background:#21262d;color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:5px 8px}
.flex{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
@media(max-width:640px){#tvwrap{height:320px}}
</style></head><body>
<h1>Trading Agent Dashboard</h1>
<div class="sub">delta scalping research &mdash; paper trading by default &middot; agents keep running even if you close this page</div>
<div class="warn"><b>Risk reminder:</b> these presets reproduced backtests with -55% to -90% max drawdowns.
Paper mode is where they belong. Live trading is capped at 2% risk/trade by the bot itself.</div>

<div class="grid" id="cards"></div>

<div class="panel"><div class="flex"><h2 style="margin:0">Chart (TradingView free widget &mdash; view-only, no login)</h2>
<select id="tvsym"><option value="BINANCE:BTCUSDT">BTCUSD</option><option value="BINANCE:ETHUSDT">ETHUSD</option></select></div>
<div id="tvwrap"><div id="tv_chart" style="height:100%"></div></div></div>

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
refresh(); tv('BINANCE:BTCUSDT');
setInterval(refresh,5000); setInterval(loadLog,7000); setInterval(loadJournal,15000);
</script></body></html>
"""


def main():
    global PASSWORD
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1",
                    help="bind address (default localhost only; 0.0.0.0 = whole LAN)")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--password", default=None,
                    help="require this password to open the dashboard (browser login box)")
    args = ap.parse_args()
    PASSWORD = args.password
    if args.host != "127.0.0.1" and not PASSWORD:
        print("refusing to bind beyond localhost without --password "
              "(anyone on your network could start/stop trading agents).")
        sys.exit(1)
    os.makedirs(LOGS, exist_ok=True)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    where = f"http://{'localhost' if args.host == '127.0.0.1' else args.host}:{args.port}"
    print(f"Trading Agent Dashboard running -> {where}"
          + ("  (login required)" if PASSWORD else ""))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\ndashboard stopped (agents keep running; use the buttons or "
              "kill their pids in agents/logs/*.pid to stop them)")


if __name__ == "__main__":
    main()

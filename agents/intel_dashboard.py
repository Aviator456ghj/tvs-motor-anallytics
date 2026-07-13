#!/usr/bin/env python3
"""Standalone web UI for the Market Intelligence Agent — a completely
separate app from agents/dashboard.py, on purpose. That dashboard is for
the mechanical scalper/pattern presets (backtested rules, fixed risk).
This one is for the "second brain": a continuous, self-thinking monitor
per asset — order book, whale trades, OI/funding, volatility/trend
regime, news, and an optional LLM read — with its own timeline, not just
a single latest snapshot.

Start it:
    python agents/intel_dashboard.py                       # http://localhost:8090
    python agents/intel_dashboard.py --password mysecret    # require a login
    python agents/intel_dashboard.py --host 0.0.0.0 --password s3

Different port (8090), different pid/log file naming (intel_<symbol>.*),
different password from agents/dashboard.py (8080) — the two run side by
side without touching each other's files or processes. Starting/stopping
a symbol here launches/kills agents/market_intel_agent.py directly; it
keeps running even if you close the browser or stop this UI.

This UI only ever reads market_intel_agent.py's output files and starts/
stops that one script. It never places a real order — see that module's
docstring for the paper-only boundary, which is structural, not a flag
here.
"""
import argparse
import base64
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
sys.path.insert(0, AGENTS_DIR)
sys.path.insert(0, REPO)

from market_intel_agent import CONTRACT_VALUE, LOGS  # noqa: E402

SYMBOLS = list(CONTRACT_VALUE)
PASSWORD = None  # set from --password


# ───────────────────────── process management ─────────────────────────

def pid_file(symbol):
    return os.path.join(LOGS, f"intel_{symbol}.pid")


def log_file(symbol):
    return os.path.join(LOGS, f"intel_{symbol}.log")


def snapshot_file(symbol):
    return os.path.join(LOGS, f"market_intel_{symbol}.json")


def history_file(symbol):
    return os.path.join(LOGS, f"market_intel_{symbol}_history.jsonl")


def _pid_alive(pid, symbol):
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
        return "market_intel_agent" in cmd and symbol in cmd
    except FileNotFoundError:
        return True


def agent_pid(symbol):
    try:
        with open(pid_file(symbol)) as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return None
    return pid if _pid_alive(pid, symbol) else None


def start_agent(symbol, reason, demo, backend, model, timeframe, interval):
    if agent_pid(symbol):
        return {"ok": False, "error": "already running"}
    os.makedirs(LOGS, exist_ok=True)
    out = open(log_file(symbol), "a")
    out.write(f"\n===== intel-dashboard start {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n")
    out.flush()
    cmd = [sys.executable, os.path.join(AGENTS_DIR, "market_intel_agent.py"),
           "--symbol", symbol, "--timeframe", timeframe, "--interval", str(interval)]
    if demo:
        cmd.append("--demo-trade")
    elif reason:
        cmd.append("--reason")
    if backend:
        cmd += ["--llm-backend", backend]
    if model:
        cmd += ["--llm-model", model]
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = (subprocess.DETACHED_PROCESS |
                                   subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        kwargs["start_new_session"] = True
    p = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, cwd=REPO, **kwargs)
    with open(pid_file(symbol), "w") as f:
        f.write(str(p.pid))
    return {"ok": True, "pid": p.pid}


def stop_agent(symbol):
    pid = agent_pid(symbol)
    if not pid:
        return {"ok": False, "error": "not running"}
    os.kill(pid, signal.SIGTERM)
    try:
        os.remove(pid_file(symbol))
    except OSError:
        pass
    return {"ok": True}


# ───────────────────────── data readers ─────────────────────────

def latest_snapshot(symbol):
    try:
        with open(snapshot_file(symbol)) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def read_history(symbol, limit=400):
    path = history_file(symbol)
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as f:
        lines = f.readlines()[-limit:]
    for line in lines:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def alert_history(symbol, limit=80):
    """Newest-first log of cycles that actually raised an alert (skips the
    many quiet cycles in between) — this is the 'watch everything, all the
    time' timeline the snapshot card alone can't show."""
    out = [h for h in read_history(symbol, limit=2000) if h.get("alerts")]
    return list(reversed(out))[:limit]


def log_tail(symbol, lines=60):
    path = log_file(symbol)
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
    server_version = "IntelDash/1.0"

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
        self.send_header("WWW-Authenticate", 'Basic realm="Market Intelligence"')
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"login required")

    def _json(self, obj, code=200):
        body = json.dumps(obj, default=str).encode()
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

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if not self._authed():
            return self._deny()
        u = urlparse(self.path)
        q = parse_qs(u.query)
        symbol = (q.get("symbol") or [None])[0]
        if u.path == "/":
            return self._html(PAGE)
        if u.path == "/api/status":
            out = {}
            for s in SYMBOLS:
                snap = latest_snapshot(s)
                out[s] = {
                    "running": agent_pid(s) is not None,
                    "snapshot": snap,
                }
            return self._json(out)
        if u.path == "/api/history" and symbol in SYMBOLS:
            limit = int((q.get("limit") or [400])[0])
            return self._json(read_history(symbol, limit=limit))
        if u.path == "/api/alerts" and symbol in SYMBOLS:
            return self._json(alert_history(symbol))
        if u.path == "/api/log" and symbol in SYMBOLS:
            return self._json({"log": log_tail(symbol)})
        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        if not self._authed():
            return self._deny()
        u = urlparse(self.path)
        q = parse_qs(u.query)
        symbol = (q.get("symbol") or [None])[0]
        if symbol not in SYMBOLS:
            return self._json({"error": "unknown symbol"}, 400)
        if u.path == "/api/start":
            try:
                n = int(self.headers.get("Content-Length", 0))
                d = json.loads(self.rfile.read(n).decode()) if n else {}
            except Exception:
                d = {}
            res = start_agent(
                symbol,
                reason=bool(d.get("reason")),
                demo=bool(d.get("demo")),
                backend=d.get("backend") or "ollama",
                model=(d.get("model") or "").strip() or None,
                timeframe=d.get("timeframe") or "15m",
                interval=int(d.get("interval") or 120),
            )
            return self._json(res)
        if u.path == "/api/stop":
            return self._json(stop_agent(symbol))
        return self._json({"error": "not found"}, 404)


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Market Intelligence — Second Brain</title>
<style>
:root{--bg:#0a0d12;--card:#12161d;--line:#232a35;--ink:#e6edf3;--mut:#8b949e;
--up:#3fb950;--dn:#f85149;--amber:#d29922;--accent:#7aa2ff;--purp:#c297ff}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,'Segoe UI',Roboto,sans-serif;padding:16px;max-width:1300px;margin:0 auto}
h1{font-size:19px;margin-bottom:2px} .sub{color:var(--mut);font-size:12px;margin-bottom:16px}
.warn{background:#1a2230;border:1px solid #2d3f6e;border-radius:8px;padding:10px 12px;font-size:12.5px;color:#a9c1f0;margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.card h3{font-size:15px;margin-bottom:2px;display:flex;align-items:center;gap:6px}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%}
.on{background:var(--up)} .off{background:#484f58}
.price{font-size:20px;font-weight:700;margin:6px 0}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px;font-size:12.5px;margin-bottom:8px}
.row{display:flex;justify-content:space-between} .mut{color:var(--mut)}
.badge{font-size:10.5px;border-radius:5px;padding:1px 6px;font-weight:600;display:inline-block}
.b-high{background:#3a1416;color:var(--dn)} .b-normal{background:#25304a;color:var(--accent)} .b-low{background:#12351f;color:var(--up)}
.b-trending{background:#3a2a10;color:var(--amber)} .b-ranging{background:#232a35;color:var(--mut)}
.b-bull{background:#12351f;color:var(--up)} .b-bear{background:#3a1416;color:var(--dn)} .b-neutral{background:#232a35;color:var(--mut)} .b-conflicting{background:#3a2a10;color:var(--amber)}
.alerts{background:#1a1610;border:1px solid #4a3a10;border-radius:6px;padding:6px 8px;font-size:11.5px;color:#e0c785;margin:6px 0;max-height:70px;overflow-y:auto}
.llm{background:#161425;border:1px solid #322a55;border-radius:6px;padding:8px;font-size:12px;color:#cfc7f5;margin:6px 0}
.llm .caveat{color:var(--mut);font-size:11px;margin-top:4px}
svg{width:100%;height:60px;display:block;background:#0a0d12;border-radius:6px;border:1px solid var(--line)}
.btns{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}
button{border:0;border-radius:7px;padding:7px 12px;font-weight:600;cursor:pointer;font-size:12px}
.start{background:var(--up);color:#04260f} .stop{background:var(--dn);color:#2d0605}
.ghost{background:#21262d;color:var(--ink);border:1px solid var(--line)}
.opts{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0;font-size:11.5px}
select,input[type=text]{background:#21262d;color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:4px 6px;font-size:11.5px}
label{display:flex;align-items:center;gap:4px;color:var(--mut)}
.panel{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin-top:16px}
.panel h2{font-size:14px;margin-bottom:10px;color:var(--accent)}
pre{background:#0a0d12;border:1px solid var(--line);border-radius:8px;padding:10px;font-size:11px;overflow-x:auto;white-space:pre-wrap;max-height:260px;overflow-y:auto;color:#9da7b3}
select#detailsel{margin-bottom:8px}
.alertlog{font-size:11.5px;border-bottom:1px solid #21262d;padding:6px 0}
.alertlog .t{color:var(--mut);font-size:10.5px}
</style></head><body>
<h1>Market Intelligence — Second Brain</h1>
<div class="sub">continuous per-asset monitor: order book, whale trades, OI/funding, volatility &amp; trend regime, news, optional LLM read &mdash; a separate app from the scalper dashboard on purpose</div>
<div class="warn"><b>Not a signal source:</b> everything here is read-only observation plus an optional LLM opinion with no win rate. Demo trading (if enabled) is 100% simulated — this never places a real order. See <code>agents/market_intel_agent.py</code> docstring.</div>

<div class="grid" id="cards"></div>

<div class="panel"><div style="display:flex;justify-content:space-between;align-items:center">
<h2 style="margin:0">Detail &amp; alert timeline</h2>
<select id="detailsel"></select></div>
<div id="alertlog"></div></div>

<div class="panel"><div style="display:flex;justify-content:space-between;align-items:center">
<h2 style="margin:0">Process log</h2>
<select id="logsel"></select></div><pre id="logbox">select a symbol…</pre></div>

<script>
const $=id=>document.getElementById(id);
const SYMBOLS=__SYMBOLS__;
function fmt(x,d=2){ return x==null||x==='—'?'—':(+x).toLocaleString(undefined,{maximumFractionDigits:d}); }
function pct(x){ return x==null?'—':((+x)*100).toFixed(1)+'%'; }
function regimeBadge(v){ return `<span class="badge b-${v}">${v}</span>`; }
function sparkline(vals){
  if(!vals||vals.length<2) return '<svg viewBox="0 0 100 30" preserveAspectRatio="none"></svg>';
  const nums=vals.map(Number).filter(v=>!isNaN(v));
  const lo=Math.min(...nums), hi=Math.max(...nums), span=(hi-lo)||1;
  const pts=nums.map((v,i)=>`${(i/(nums.length-1)*100).toFixed(2)},${(28-((v-lo)/span*26)).toFixed(2)}`).join(' ');
  const up=nums[nums.length-1]>=nums[0];
  return `<svg viewBox="0 0 100 30" preserveAspectRatio="none"><polyline points="${pts}" fill="none" stroke="${up?'#3fb950':'#f85149'}" stroke-width="1.2" vector-effect="non-scaling-stroke"/></svg>`;
}
async function act(symbol,verb,opts){
  const body=opts?JSON.stringify(opts):undefined;
  await fetch(`/api/${verb}?symbol=${symbol}`,{method:'POST',headers:{'Content-Type':'application/json'},body});
  refresh();
}
function startOpts(symbol){
  const reason=$('r_'+symbol).checked, demo=$('d_'+symbol).checked;
  const backend=$('b_'+symbol).value, model=$('m_'+symbol).value;
  const tf=$('tf_'+symbol).value;
  act(symbol,'start',{reason,demo,backend,model,timeframe:tf,interval:120});
}
let histCache={};
async function refresh(){
  const st=await (await fetch('/api/status')).json();
  const rows=await Promise.all(SYMBOLS.map(s=>fetch(`/api/history?symbol=${s}&limit=200`).then(r=>r.json())));
  SYMBOLS.forEach((s,i)=>histCache[s]=rows[i]);
  $('cards').innerHTML=SYMBOLS.map(s=>{
    const running=st[s].running, snap=st[s].snapshot, hist=histCache[s]||[];
    const prices=hist.map(h=>h.mark_price), eq=hist.map(h=>h.demo_equity).filter(v=>v!=null);
    const llm=snap&&snap.llm;
    const alerts=(snap&&snap.alerts)||[];
    return `<div class="card"><h3><span class="dot ${running?'on':'off'}"></span>${s}
      ${snap?`<span class="price" style="margin-left:auto">$${fmt(snap.mark_price)}</span>`:''}</h3>
    ${prices.length>1?sparkline(prices):'<div class="mut" style="font-size:11.5px;padding:8px 0">no history yet — start the agent</div>'}
    ${snap?`
    <div class="grid2">
      <div class="row"><span class="mut">book imbalance</span><span>${pct(snap.book_imbalance)}</span></div>
      <div class="row"><span class="mut">taker buy ratio</span><span>${pct(snap.taker_buy_ratio)}</span></div>
      <div class="row"><span class="mut">volatility</span><span>${regimeBadge(snap.volatility_regime)}</span></div>
      <div class="row"><span class="mut">trend</span><span>${regimeBadge(snap.trend_regime)} ${snap.trend_direction||''}</span></div>
      <div class="row"><span class="mut">funding rate</span><span>${pct(snap.funding_rate)}</span></div>
      <div class="row"><span class="mut">OI change 6h</span><span>$${fmt(snap.oi_change_usd_6h,0)}</span></div>
      <div class="row"><span class="mut">whale trades</span><span>${(snap.whale_trades||[]).length}</span></div>
      <div class="row"><span class="mut">demo equity</span><span>${snap.demo_equity!=null?'$'+fmt(snap.demo_equity):'—'}</span></div>
    </div>
    ${eq.length>1?`<div class="mut" style="font-size:10.5px;margin-bottom:2px">demo equity</div>${sparkline(eq)}`:''}
    ${alerts.length?`<div class="alerts">${alerts.map(a=>'⚠ '+a).join('<br>')}</div>`:''}
    ${llm?`<div class="llm"><b>${(llm.bias||'unknown').toUpperCase()}</b>
      <span class="badge b-${llm.bias||'neutral'}">${llm.confidence||'—'} confidence</span>
      <div style="margin-top:4px">${llm.read||''}</div>
      ${llm.caveats?`<div class="caveat">caveat: ${llm.caveats}</div>`:''}</div>`:''}
    `:'<div class="mut" style="font-size:12px;padding:8px 0">not started yet</div>'}
    <div class="opts">
      <label><input type="checkbox" id="r_${s}" ${running?'disabled':''}> reason (LLM)</label>
      <label><input type="checkbox" id="d_${s}" ${running?'disabled':''}> demo-trade</label>
      <select id="b_${s}" ${running?'disabled':''}><option value="ollama">ollama (free)</option><option value="anthropic">anthropic</option></select>
      <input type="text" id="m_${s}" placeholder="model (optional)" style="width:110px" ${running?'disabled':''}>
      <select id="tf_${s}" ${running?'disabled':''}><option value="15m">15m</option><option value="1h">1h</option></select>
    </div>
    <div class="btns">${running
      ?`<button class="stop" onclick="act('${s}','stop')">Stop</button>`
      :`<button class="start" onclick="startOpts('${s}')">Start</button>`}
    <button class="ghost" onclick="$('detailsel').value='${s}';loadAlerts();$('logsel').value='${s}';loadLog()">Inspect</button>
    </div></div>`;
  }).join('');
  for(const sel of ['detailsel','logsel']) if(!$(sel).options.length)
    $(sel).innerHTML=SYMBOLS.map(s=>`<option>${s}</option>`).join('');
}
async function loadAlerts(){
  const s=$('detailsel').value; if(!s) return;
  const rows=await (await fetch(`/api/alerts?symbol=${s}`)).json();
  $('alertlog').innerHTML=rows.length?rows.map(r=>{
    const d=new Date(r.timestamp*1000).toLocaleString();
    return `<div class="alertlog"><div class="t">${d} &mdash; $${fmt(r.mark_price)} &mdash; bias:${r.llm_bias||'—'}</div>${(r.alerts||[]).map(a=>'⚠ '+a).join('<br>')}</div>`;
  }).join(''):'<div class="mut" style="font-size:12px;padding:8px">no alerts recorded yet for this symbol</div>';
}
async function loadLog(){
  const s=$('logsel').value; if(!s) return;
  const d=await (await fetch(`/api/log?symbol=${s}`)).json();
  $('logbox').textContent=d.log||'(no log yet — start the agent)';
}
$('detailsel').onchange=loadAlerts; $('logsel').onchange=loadLog;
refresh(); setTimeout(()=>{loadAlerts();loadLog();},600);
setInterval(refresh,8000); setInterval(loadAlerts,15000); setInterval(loadLog,10000);
</script></body></html>
""".replace("__SYMBOLS__", json.dumps(SYMBOLS))


def main():
    global PASSWORD
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--password", default=None)
    args = ap.parse_args()
    PASSWORD = args.password
    if args.host != "127.0.0.1" and not PASSWORD:
        print("refusing to bind beyond localhost without --password")
        sys.exit(1)
    os.makedirs(LOGS, exist_ok=True)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    where = f"http://{'localhost' if args.host == '127.0.0.1' else args.host}:{args.port}"
    print(f"Market Intelligence dashboard running -> {where}"
          + ("  (login required)" if PASSWORD else ""))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nintel dashboard stopped (running agents keep running)")


if __name__ == "__main__":
    main()

"""
Tiny web dashboard for the liquidity bot.

Serves an auto-refreshing status page that reads the snapshot the bot writes
to ``status_file`` every loop. No build step, no JS framework.

Run:  python -m bot.dashboard      (listens on DASHBOARD_PORT, default 8080)
"""

from __future__ import annotations

import json

from flask import Flask, Response

from .config import Config

cfg = Config()
app = Flask(__name__)

PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Liquidity Bot</title>
<style>
  :root{color-scheme:dark}
  body{margin:0;font:15px/1.5 system-ui,sans-serif;background:#0d1117;color:#e6edf3}
  .wrap{max-width:640px;margin:6vh auto;padding:0 16px}
  .card{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:24px;margin-bottom:16px}
  h1{font-size:18px;margin:0 0 4px}
  .sym{font-size:34px;font-weight:700;letter-spacing:.5px}
  .px{font-size:46px;font-weight:800;margin:6px 0}
  .badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:700}
  .dry{background:#1f6f3f33;color:#3fb950;border:1px solid #2ea04366}
  .live{background:#8b232333;color:#ff7b72;border:1px solid #da363366}
  .row{display:flex;justify-content:space-between;padding:6px 0;border-top:1px solid #21262d}
  .k{color:#8b949e}.v{font-weight:600}
  .bar{position:relative;height:12px;background:#21262d;border-radius:999px;margin:14px 0 6px}
  .fill{position:absolute;top:0;bottom:0;width:3px;background:#58a6ff;border-radius:3px;transform:translateX(-50%)}
  .ends{display:flex;justify-content:space-between;color:#8b949e;font-size:12px}
  .evt{font-size:13px;color:#c9d1d9;white-space:pre-wrap}
  .muted{color:#6e7681;font-size:12px;margin-top:10px}
  .side-buy{color:#3fb950}.side-sell{color:#ff7b72}
</style></head><body><div class="wrap">
  <div class="card">
    <h1>Liquidity-Sweep Bot <span id="mode" class="badge dry">—</span></h1>
    <div class="sym" id="sym">—</div>
    <div class="px" id="px">—</div>
    <div class="bar"><div class="fill" id="fill" style="left:50%"></div></div>
    <div class="ends"><span id="lo">—</span><span id="hi">—</span></div>
    <div class="row"><span class="k">Trend</span><span class="v" id="trend">—</span></div>
    <div class="row"><span class="k">Range mid</span><span class="v" id="mid">—</span></div>
    <div class="muted" id="ts">waiting for data…</div>
  </div>
  <div class="card">
    <h1>Last signal</h1>
    <div class="evt" id="evt">No signal yet — watching for a sweep / flip.</div>
  </div>
</div>
<script>
async function tick(){
  try{
    const r = await fetch('/api/status',{cache:'no-store'}); const d = await r.json();
    if(d.error){document.getElementById('ts').textContent=d.error;return;}
    sym.textContent=d.symbol; px.textContent=Number(d.price).toLocaleString();
    trend.textContent=d.trend; mid.textContent=Number(d.mid).toLocaleString();
    lo.textContent=Number(d.range_low).toLocaleString();
    hi.textContent=Number(d.range_high).toLocaleString();
    const span=d.range_high-d.range_low;
    let pct=span>0?((d.price-d.range_low)/span)*100:50; pct=Math.max(0,Math.min(100,pct));
    fill.style.left=pct+'%';
    const m=document.getElementById('mode');
    m.textContent=d.mode; m.className='badge '+(d.mode==='LIVE'?'live':'dry');
    ts.textContent='updated '+d.ts;
    const e=d.last_event;
    evt.innerHTML = e ? (
      '<span class="side-'+e.side+'">'+e.side.toUpperCase()+' '+e.kind+'</span>  size '+e.size+
      '\\nentry '+e.entry+'  stop '+e.stop+'  tp '+e.take_profit+
      '\\n'+e.reason+'\\n('+e.mode+' · '+e.ts+')'
    ) : 'No signal yet — watching for a sweep / flip.';
  }catch(err){ document.getElementById('ts').textContent='dashboard unreachable'; }
}
tick(); setInterval(tick, 3000);
</script></body></html>"""


@app.route("/")
def index() -> str:
    return PAGE


@app.route("/api/status")
def api_status() -> Response:
    try:
        with open(cfg.status_file) as f:
            return Response(f.read(), mimetype="application/json")
    except OSError:
        return Response('{"error":"no status yet — is the bot running?"}',
                        mimetype="application/json")


def main() -> None:
    app.run(host="0.0.0.0", port=cfg.dashboard_port)


if __name__ == "__main__":
    main()

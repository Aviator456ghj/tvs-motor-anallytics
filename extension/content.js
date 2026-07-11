// Delta Pattern Agent — TradingView sidebar
// Reads your LOCAL dashboard (python agents/dashboard.py) at localhost:8080.
// If the dashboard runs with --password, set it here:
const DASH = "http://localhost:8080";
const PASSWORD = ""; // e.g. "mysecret" if you started dashboard with --password

(function () {
  if (document.getElementById("dpa-toggle")) return;

  const btn = document.createElement("button");
  btn.id = "dpa-toggle";
  btn.textContent = "AGENT";
  document.body.appendChild(btn);

  const panel = document.createElement("div");
  panel.id = "dpa-panel";
  panel.innerHTML = `<button id="dpa-close">×</button>
    <h2>Pattern Agent</h2>
    <div class="dpa-sub">live from your local dashboard — paper trading</div>
    <div id="dpa-body">connecting…</div>`;
  document.body.appendChild(panel);

  btn.onclick = () => { panel.classList.toggle("open"); load(); };
  panel.querySelector("#dpa-close").onclick = () => panel.classList.remove("open");

  const fmt = x => x == null ? "—" : (+x).toLocaleString(undefined, { maximumFractionDigits: 2 });
  const headers = PASSWORD ? { "Authorization": "Basic " + btoa("user:" + PASSWORD) } : {};

  async function load() {
    const body = document.getElementById("dpa-body");
    try {
      const r = await fetch(DASH + "/api/signals", { headers });
      const sigs = await r.json();
      body.innerHTML = sigs.map(s => {
        const pos = s.position;
        const posHtml = pos
          ? `<div class="dpa-row"><span class="m">signal</span>
               <span class="${pos.side === "buy" ? "dpa-long" : "dpa-short"}">
               ${pos.side === "buy" ? "LONG" : "SHORT"} ${pos.pattern || ""}${pos.confirm ? "+" + pos.confirm : ""}</span></div>
             <div class="dpa-row"><span class="m">entry</span><span>${fmt(pos.entry)}</span></div>
             <div class="dpa-row"><span class="m">stop / target</span><span>${fmt(pos.stop)} / ${fmt(pos.target)}</span></div>`
          : `<div class="dpa-row"><span class="m">signal</span><span>flat — waiting</span></div>`;
        return `<div class="dpa-card">
          <h3><span class="dpa-dot ${s.running ? "dpa-on" : "dpa-off"}"></span>${s.preset}
              <span style="color:#8b949e;font-weight:400">· ${s.symbol}</span></h3>
          ${posHtml}
          <div class="dpa-row"><span class="m">paper equity</span><span>$${fmt(s.equity ?? 1000)}</span></div>
          <div class="dpa-row"><span class="m">closed trades</span><span>${s.closed_trades}</span></div>
        </div>`;
      }).join("") || "<div class='dpa-err'>no presets found</div>";
    } catch (e) {
      body.innerHTML = `<div class="dpa-err">Can't reach the dashboard at ${DASH}.<br>
        Start it with:<br><code>python agents/dashboard.py</code><br>
        (If it uses --password, set PASSWORD at the top of content.js.)</div>`;
    }
  }
  setInterval(() => { if (panel.classList.contains("open")) load(); }, 7000);
})();

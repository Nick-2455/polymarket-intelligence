"""FastAPI dashboard endpoints."""

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

from storage.logger import SignalLogger
from paper_trading.portfolio import Portfolio, PORTFOLIO_FILE

BACKTEST_REPORT_FILE = Path("backtest_report.json")

router = APIRouter()
logger = SignalLogger()

# ── Shared CSS + layout injected into every page ──────────────────────────

_BASE_STYLE = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
  --bg:       #0f1117;
  --surface:  #1a1d27;
  --surface2: #21253a;
  --border:   #2a2d3e;
  --accent:   #6c63ff;
  --accent2:  #5a52e0;
  --green:    #00c896;
  --red:      #ff4d6d;
  --yellow:   #f5a623;
  --text:     #e2e4f0;
  --muted:    #7b7f9e;
  --radius:   12px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  font-family: 'Inter', sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  font-size: 14px;
  line-height: 1.5;
}

/* ── Navbar ── */
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 56px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 100;
}
.navbar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 15px;
  color: var(--text);
  text-decoration: none;
}
.navbar-brand .dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 8px var(--accent);
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.navbar-tabs {
  display: flex;
  gap: 4px;
}
.nav-tab {
  padding: 6px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  color: var(--muted);
  transition: all 0.15s;
}
.nav-tab:hover { color: var(--text); background: var(--surface2); }
.nav-tab.active { color: var(--text); background: var(--surface2); font-weight: 600; }
.navbar-right { color: var(--muted); font-size: 12px; }

/* ── Layout ── */
.page { max-width: 1200px; margin: 0 auto; padding: 28px 24px 48px; }
.page-header { margin-bottom: 28px; }
.page-title { font-size: 22px; font-weight: 700; color: var(--text); margin-bottom: 4px; }
.page-subtitle { color: var(--muted); font-size: 13px; }

/* ── KPI Cards ── */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 14px;
  margin-bottom: 28px;
}
.kpi-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px 20px;
  transition: transform 0.15s, box-shadow 0.15s;
  cursor: default;
}
.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}
.kpi-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
  margin-bottom: 10px;
}
.kpi-value {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.5px;
  line-height: 1;
}
.kpi-sub { font-size: 12px; color: var(--muted); margin-top: 4px; }
.c-green  { color: var(--green); }
.c-red    { color: var(--red); }
.c-yellow { color: var(--yellow); }
.c-accent { color: var(--accent); }
.c-muted  { color: var(--muted); }
.c-text   { color: var(--text); }

/* ── Cards ── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  margin-bottom: 20px;
  overflow: hidden;
}
.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.card-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 20px;
  background: var(--surface2);
  color: var(--muted);
}

/* ── Table ── */
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
thead th {
  padding: 12px 20px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
tbody tr {
  border-bottom: 1px solid rgba(42,45,62,0.5);
  transition: background 0.12s;
}
tbody tr:nth-child(even) { background: rgba(255,255,255,0.015); }
tbody tr:hover { background: var(--surface2); }
tbody td {
  padding: 12px 20px;
  font-size: 13px;
  vertical-align: middle;
}
.td-q {
  max-width: 340px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
  color: var(--text);
}
.td-muted { color: var(--muted); font-size: 12px; }

/* ── Badges ── */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
}
.badge-buy    { background: rgba(0,200,150,0.15); color: var(--green); }
.badge-sell   { background: rgba(255,77,109,0.15); color: var(--red); }
.badge-watch  { background: rgba(245,166,35,0.15); color: var(--yellow); }
.badge-ignore { background: rgba(123,127,158,0.1); color: var(--muted); }
.badge-yes    { background: rgba(0,200,150,0.15); color: var(--green); }
.badge-no     { background: rgba(255,77,109,0.15); color: var(--red); }
.badge-won    { background: rgba(0,200,150,0.15); color: var(--green); }
.badge-lost   { background: rgba(255,77,109,0.15); color: var(--red); }
.badge-open   { background: rgba(245,166,35,0.12); color: var(--yellow); }

/* ── Chart ── */
.chart-wrap {
  padding: 20px;
  height: 220px;
}

/* ── Empty state ── */
.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: var(--muted);
  font-size: 13px;
}
.empty-state .icon { font-size: 32px; margin-bottom: 12px; opacity: 0.4; }

/* ── Responsive ── */
@media (max-width: 640px) {
  .navbar { padding: 0 16px; }
  .page { padding: 20px 16px 40px; }
  .kpi-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .kpi-value { font-size: 22px; }
  .page-title { font-size: 18px; }
  thead th, tbody td { padding: 10px 12px; }
}
</style>
"""

_NAVBAR = """
<nav class="navbar">
  <a class="navbar-brand" href="/">
    <span class="dot"></span>
    Polymarket Intelligence
  </a>
  <div class="navbar-tabs">
    <a class="nav-tab {signals_active}" href="/">Signals</a>
    <a class="nav-tab {paper_active}" href="/paper">Paper Trading</a>
    <a class="nav-tab {backtest_active}" href="/backtest">Backtest</a>
    <a class="nav-tab {guide_active}" href="/guide">Guide</a>
  </div>
  <div class="navbar-right" id="clock"></div>
</nav>
<script>
(function() {
  function tick() {
    var el = document.getElementById('clock');
    if (el) el.textContent = new Date().toLocaleTimeString();
  }
  tick();
  setInterval(tick, 1000);
})();
</script>
"""


def _navbar(active: str) -> str:
    return (
        _NAVBAR
        .replace("{signals_active}", "active" if active == "signals" else "")
        .replace("{paper_active}", "active" if active == "paper" else "")
        .replace("{backtest_active}", "active" if active == "backtest" else "")
        .replace("{guide_active}", "active" if active == "guide" else "")
    )


# ── Dashboard: Signals ─────────────────────────────────────────────────────

DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Signals — Polymarket Intelligence</title>
""" + _BASE_STYLE + """
</head>
<body>
""" + _navbar("signals") + """
<div class="page">
  <div class="page-header">
    <div class="page-title">Live Signals</div>
    <div class="page-subtitle">5 AI trader archetypes scanning top markets every 60s</div>
  </div>

  <div class="kpi-grid" id="kpis">
    <div class="kpi-card"><div class="kpi-label">Total Signals</div><div class="kpi-value c-accent" id="kpi-total">—</div></div>
    <div class="kpi-card"><div class="kpi-label">Strong Buy</div><div class="kpi-value c-green" id="kpi-buy">—</div></div>
    <div class="kpi-card"><div class="kpi-label">Strong Sell</div><div class="kpi-value c-red" id="kpi-sell">—</div></div>
    <div class="kpi-card"><div class="kpi-label">Watch</div><div class="kpi-value c-yellow" id="kpi-watch">—</div></div>
    <div class="kpi-card"><div class="kpi-label">Last Scan</div><div class="kpi-value c-muted" style="font-size:16px;font-weight:600" id="kpi-last">—</div></div>
  </div>

  <div class="card">
    <div class="card-header">
      <span class="card-title">Recent Signals</span>
      <span class="card-badge" id="refresh-label">Auto-refresh 60s</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Signal</th>
            <th>Question</th>
            <th>Edge %</th>
            <th>Consensus</th>
            <th>Volume</th>
            <th>Time</th>
          </tr>
        </thead>
        <tbody id="signals-body">
          <tr><td colspan="6" class="empty-state"><div class="icon">⏳</div>Waiting for first scan…</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<script>
function badgeSignal(s) {
  const map = {
    STRONG_BUY: ['badge-buy', 'Strong Buy'],
    STRONG_SELL: ['badge-sell', 'Strong Sell'],
    WATCH: ['badge-watch', 'Watch'],
    IGNORE: ['badge-ignore', 'Ignore'],
  };
  const [cls, label] = map[s] || ['badge-ignore', s];
  return `<span class="badge ${cls}">${label}</span>`;
}
function fmtConsensus(v) {
  const sign = v > 0 ? '+' : '';
  const cls = v > 2 ? 'c-green' : v < -2 ? 'c-red' : 'c-muted';
  return `<span class="${cls}" style="font-weight:600">${sign}${v.toFixed(2)}</span>`;
}
function fmtVol(v) {
  if (v >= 1e6) return '$' + (v/1e6).toFixed(1) + 'M';
  if (v >= 1e3) return '$' + (v/1e3).toFixed(0) + 'K';
  return '$' + v.toFixed(0);
}
function timeAgo(iso) {
  const m = Math.floor((Date.now() - new Date(iso)) / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return m + 'm ago';
  return Math.floor(m/60) + 'h ago';
}

async function loadSignals() {
  try {
    const data = await fetch('/api/signals').then(r => r.json());
    const rev = [...data].reverse();

    // KPIs
    document.getElementById('kpi-total').textContent = data.length;
    document.getElementById('kpi-buy').textContent   = data.filter(s => s.signal === 'STRONG_BUY').length;
    document.getElementById('kpi-sell').textContent  = data.filter(s => s.signal === 'STRONG_SELL').length;
    document.getElementById('kpi-watch').textContent = data.filter(s => s.signal === 'WATCH').length;
    if (data.length) {
      document.getElementById('kpi-last').textContent = timeAgo(data[data.length-1].timestamp);
    }

    const tbody = document.getElementById('signals-body');
    if (!rev.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-state"><div class="icon">📡</div>No signals yet. Waiting for first scan…</td></tr>';
      return;
    }
    tbody.innerHTML = rev.map(s => `
      <tr>
        <td>${badgeSignal(s.signal)}</td>
        <td class="td-q" title="${s.question}">${s.question}</td>
        <td><span class="c-accent" style="font-weight:600">${s.edge.toFixed(1)}%</span></td>
        <td>${fmtConsensus(s.consensus_score)}</td>
        <td class="td-muted">${fmtVol(s.volume)}</td>
        <td class="td-muted">${timeAgo(s.timestamp)}</td>
      </tr>`).join('');
  } catch(e) { console.error(e); }
}

loadSignals();
setInterval(loadSignals, 60000);
</script>
</body>
</html>
"""


# ── Paper Trading page ─────────────────────────────────────────────────────

PAPER_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Paper Trading — Polymarket Intelligence</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
""" + _BASE_STYLE + """
</head>
<body>
""" + _navbar("paper") + """
<div class="page">
  <div class="page-header">
    <div class="page-title">Paper Trading</div>
    <div class="page-subtitle">Simulated portfolio · $5,000 starting balance · 2% stake per signal</div>
  </div>

  <div class="kpi-grid" id="kpis"></div>

  <div class="card">
    <div class="card-header">
      <span class="card-title">Equity Over Time</span>
    </div>
    <div class="chart-wrap"><canvas id="balanceChart"></canvas></div>
  </div>

  <div class="card">
    <div class="card-header">
      <span class="card-title">Open Positions</span>
      <span class="card-badge" id="open-count">0</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>Direction</th><th>Question</th><th>Stake</th><th>Entry</th><th>Potential</th><th>Edge%</th><th>Opened</th></tr>
        </thead>
        <tbody id="open-body">
          <tr><td colspan="7" class="empty-state"><div class="icon">💼</div>No open positions</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <span class="card-title">Trade History</span>
      <span class="card-badge" id="history-count">0 trades</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>Result</th><th>Dir</th><th>Question</th><th>Stake</th><th>P&amp;L</th><th>ROI</th><th>Closed</th></tr>
        </thead>
        <tbody id="history-body">
          <tr><td colspan="7" class="empty-state"><div class="icon">📋</div>No closed trades yet</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<script>
let chartInst = null;

function fmt$(v) {
  const sign = v >= 0 ? '+' : '-';
  return sign + '$' + Math.abs(v).toFixed(2);
}
function timeAgo(iso) {
  const m = Math.floor((Date.now() - new Date(iso)) / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return m + 'm ago';
  const h = Math.floor(m/60);
  if (h < 24) return h + 'h ago';
  return Math.floor(h/24) + 'd ago';
}
function clsNum(v) { return v >= 0 ? 'c-green' : 'c-red'; }
function badgeDir(d) {
  return `<span class="badge ${d === 'YES' ? 'badge-yes' : 'badge-no'}">${d}</span>`;
}
function badgeResult(r) {
  const cls = r === 'WON' ? 'badge-won' : r === 'LOST' ? 'badge-lost' : 'badge-open';
  return `<span class="badge ${cls}">${r}</span>`;
}

async function load() {
  const resp = await fetch('/api/paper/portfolio');
  if (!resp.ok) return;
  const p = await resp.json();
  const s = p.stats;

  // KPIs
  const retCls = s.total_return_pct >= 0 ? 'c-green' : 'c-red';
  const pnlCls = s.realized_pnl >= 0 ? 'c-green' : 'c-red';
  const wrCls  = s.win_rate >= 55 ? 'c-green' : s.win_rate <= 45 ? 'c-red' : 'c-yellow';
  document.getElementById('kpis').innerHTML = `
    <div class="kpi-card">
      <div class="kpi-label">Balance</div>
      <div class="kpi-value c-accent">$${s.balance.toFixed(0)}</div>
      <div class="kpi-sub">available</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Total Equity</div>
      <div class="kpi-value c-text">$${s.total_equity.toFixed(0)}</div>
      <div class="kpi-sub">incl. staked</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Return</div>
      <div class="kpi-value ${retCls}">${s.total_return_pct >= 0 ? '+' : ''}${s.total_return_pct}%</div>
      <div class="kpi-sub">vs $${s.initial_balance.toFixed(0)} start</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Realized P&L</div>
      <div class="kpi-value ${pnlCls}">${fmt$(s.realized_pnl)}</div>
      <div class="kpi-sub">${s.total_trades} closed trades</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Win Rate</div>
      <div class="kpi-value ${wrCls}">${s.win_rate}%</div>
      <div class="kpi-sub">${s.total_trades} trades</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Open</div>
      <div class="kpi-value c-yellow">${s.open_positions}</div>
      <div class="kpi-sub">positions</div>
    </div>
  `;

  // Chart
  const hist = (p.balance_history || []);
  if (hist.length > 1) {
    const labels = hist.map(h => new Date(h.timestamp).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}));
    const data   = hist.map(h => h.balance);
    const last   = data[data.length - 1];
    const color  = last >= 5000 ? '#00c896' : '#ff4d6d';
    const fill   = last >= 5000 ? 'rgba(0,200,150,0.08)' : 'rgba(255,77,109,0.08)';
    if (chartInst) chartInst.destroy();
    chartInst = new Chart(document.getElementById('balanceChart'), {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Equity ($)',
          data,
          borderColor: color,
          backgroundColor: fill,
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
        scales: {
          x: { ticks: { color: '#7b7f9e', maxTicksLimit: 6, font: { family: 'Inter', size: 11 } }, grid: { color: 'rgba(42,45,62,0.6)' } },
          y: { ticks: { color: '#7b7f9e', font: { family: 'Inter', size: 11 } }, grid: { color: 'rgba(42,45,62,0.6)' } }
        }
      }
    });
  }

  // Open positions
  const openPos = (p.positions || []).filter(x => x.status === 'OPEN');
  document.getElementById('open-count').textContent = openPos.length;
  const obody = document.getElementById('open-body');
  obody.innerHTML = openPos.length ? openPos.map(pos => `
    <tr>
      <td>${badgeDir(pos.direction)}</td>
      <td class="td-q" title="${pos.question}">${pos.question}</td>
      <td style="font-weight:600">$${pos.stake.toFixed(2)}</td>
      <td class="td-muted">${pos.entry_price.toFixed(3)}</td>
      <td class="c-green" style="font-weight:600">$${pos.potential_payout.toFixed(2)}</td>
      <td class="c-accent" style="font-weight:600">${pos.edge_at_entry.toFixed(1)}%</td>
      <td class="td-muted">${timeAgo(pos.opened_at)}</td>
    </tr>`).join('')
    : '<tr><td colspan="7" class="empty-state"><div class="icon">💼</div>No open positions</td></tr>';

  // History
  const history = [...(p.trade_history || [])].reverse();
  document.getElementById('history-count').textContent = history.length + ' trades';
  const hbody = document.getElementById('history-body');
  hbody.innerHTML = history.length ? history.map(t => `
    <tr>
      <td>${badgeResult(t.result)}</td>
      <td>${badgeDir(t.direction)}</td>
      <td class="td-q" title="${t.question}">${t.question}</td>
      <td style="font-weight:600">$${t.stake.toFixed(2)}</td>
      <td class="${clsNum(t.pnl)}" style="font-weight:600">${fmt$(t.pnl)}</td>
      <td class="${clsNum(t.roi_pct)}" style="font-weight:600">${t.roi_pct >= 0 ? '+' : ''}${t.roi_pct.toFixed(1)}%</td>
      <td class="td-muted">${new Date(t.closed_at).toLocaleDateString()} ${new Date(t.closed_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</td>
    </tr>`).join('')
    : '<tr><td colspan="7" class="empty-state"><div class="icon">📋</div>No closed trades yet</td></tr>';
}

load();
setInterval(load, 30000);
</script>
</body>
</html>
"""


# ── Backtest page ──────────────────────────────────────────────────────────

BACKTEST_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Backtest — Polymarket Intelligence</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
""" + _BASE_STYLE + """
</head>
<body>
""" + _navbar("backtest") + """
<div class="page">
  <div class="page-header">
    <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">
      <div>
        <div class="page-title">Backtest Report</div>
        <div class="page-subtitle" id="subtitle">Validate signal performance against resolved markets</div>
      </div>
      <button id="run-btn" onclick="runBacktest()" style="
        background:var(--accent);color:#fff;border:none;border-radius:8px;
        padding:10px 20px;font-size:13px;font-weight:600;font-family:'Inter',sans-serif;
        cursor:pointer;transition:background 0.15s;white-space:nowrap
      ">Run Backtest</button>
    </div>
  </div>
  <div id="run-status" style="display:none;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px 18px;margin-bottom:20px;font-size:13px;color:var(--muted)"></div>

  <div id="warning" style="display:none;background:rgba(245,166,35,0.08);border:1px solid rgba(245,166,35,0.25);border-radius:var(--radius);padding:14px 18px;margin-bottom:20px;color:var(--yellow);font-size:13px">
    ⚠ Insufficient data — need at least 10 resolved signals for statistical conclusions
  </div>

  <div class="kpi-grid" id="kpis">
    <div class="kpi-card"><div class="kpi-label">Loading</div><div class="kpi-value c-muted">—</div></div>
  </div>

  <div class="card">
    <div class="card-header"><span class="card-title">Cumulative P&amp;L</span></div>
    <div class="chart-wrap"><canvas id="roiChart"></canvas></div>
  </div>

  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;margin-bottom:20px" id="insight-grid"></div>

  <div class="card">
    <div class="card-header">
      <span class="card-title">Resolved Trades</span>
      <span class="card-badge" id="trades-count">0</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>Signal</th><th>Question</th><th>Edge%</th><th>Consensus</th><th>Resolution</th><th>ROI</th><th>P&amp;L</th></tr>
        </thead>
        <tbody id="trades-body">
          <tr><td colspan="7" class="empty-state"><div class="icon">📊</div>No backtest data yet</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<script>
function badgeSignal(s) {
  const map = { STRONG_BUY: ['badge-buy','Strong Buy'], STRONG_SELL: ['badge-sell','Strong Sell'] };
  const [cls, label] = map[s] || ['badge-ignore', s];
  return `<span class="badge ${cls}">${label}</span>`;
}

async function runBacktest() {
  const btn = document.getElementById('run-btn');
  const status = document.getElementById('run-status');
  btn.disabled = true;
  btn.textContent = 'Running…';
  btn.style.background = 'var(--surface2)';
  status.style.display = 'block';
  status.textContent = '⏳ Running backtest — querying Polymarket for resolved markets…';
  try {
    const resp = await fetch('/api/backtest/run', { method: 'POST' });
    const data = await resp.json();
    if (resp.ok) {
      status.style.color = 'var(--green)';
      status.textContent = '✓ ' + (data.message || 'Backtest complete');
      await loadReport();
    } else {
      status.style.color = 'var(--red)';
      status.textContent = '✗ ' + (data.error || 'Backtest failed');
    }
  } catch(e) {
    status.style.color = 'var(--red)';
    status.textContent = '✗ Network error: ' + e.message;
  }
  btn.disabled = false;
  btn.textContent = 'Run Backtest';
  btn.style.background = 'var(--accent)';
}

async function loadReport() {
  const resp = await fetch('/api/backtest');
  if (!resp.ok) return;
  const r = await resp.json();
  const s = r.summary;

  document.getElementById('subtitle').textContent =
    `Period: ${r.period_start} → ${r.period_end}  ·  Generated: ${new Date(r.generated_at).toLocaleString()}`;
  if (s.insufficient_data) document.getElementById('warning').style.display = 'block';

  const wrCls  = s.win_rate >= 55 ? 'c-green' : s.win_rate <= 45 ? 'c-red' : 'c-yellow';
  const roiCls = s.avg_roi >= 0 ? 'c-green' : 'c-red';
  const pnlCls = s.total_pnl_usd >= 0 ? 'c-green' : 'c-red';
  document.getElementById('kpis').innerHTML = `
    <div class="kpi-card"><div class="kpi-label">Win Rate</div><div class="kpi-value ${wrCls}">${s.win_rate}%</div><div class="kpi-sub">${s.resolved} resolved</div></div>
    <div class="kpi-card"><div class="kpi-label">Avg ROI</div><div class="kpi-value ${roiCls}">${s.avg_roi >= 0 ? '+' : ''}${s.avg_roi}%</div></div>
    <div class="kpi-card"><div class="kpi-label">Sim P&L</div><div class="kpi-value ${pnlCls}">${s.total_pnl_usd >= 0 ? '+' : ''}$${s.total_pnl_usd}</div><div class="kpi-sub">$10/trade</div></div>
    <div class="kpi-card"><div class="kpi-label">Signals</div><div class="kpi-value c-accent">${s.total_signals}</div><div class="kpi-sub">${s.open} open</div></div>
    <div class="kpi-card"><div class="kpi-label">Strong Buy</div><div class="kpi-value c-green">${s.strong_buy}</div></div>
    <div class="kpi-card"><div class="kpi-label">Strong Sell</div><div class="kpi-value c-red">${s.strong_sell}</div></div>
  `;

  // Chart
  const trades = r.trades || [];
  if (trades.length > 0) {
    const sorted = [...trades].sort((a,b) => a.signal_timestamp.localeCompare(b.signal_timestamp));
    let cum = 0;
    const labels = [], data = [];
    sorted.forEach(t => {
      cum += t.pnl || 0;
      labels.push(new Date(t.signal_timestamp).toLocaleDateString());
      data.push(+cum.toFixed(2));
    });
    const last  = data[data.length-1] || 0;
    const color = last >= 0 ? '#00c896' : '#ff4d6d';
    const fill  = last >= 0 ? 'rgba(0,200,150,0.08)' : 'rgba(255,77,109,0.08)';
    new Chart(document.getElementById('roiChart'), {
      type: 'line',
      data: { labels, datasets: [{ data, borderColor: color, backgroundColor: fill, fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
        scales: {
          x: { ticks: { color: '#7b7f9e', maxTicksLimit: 8, font: { family: 'Inter', size: 11 } }, grid: { color: 'rgba(42,45,62,0.6)' } },
          y: { ticks: { color: '#7b7f9e', font: { family: 'Inter', size: 11 } }, grid: { color: 'rgba(42,45,62,0.6)' } }
        }
      }
    });
  }

  // Insight cards
  function insightCard(title, rows) {
    const noData = '<div style="color:var(--muted);padding:10px 0;font-size:12px">Insufficient data</div>';
    const html = rows.length ? rows.map(r => `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);font-size:13px">
        <span style="color:var(--muted)">${r.label}</span>
        <span style="font-weight:600;color:${r.wr>=55?'var(--green)':r.wr<=45?'var(--red)':'var(--yellow)'}">${r.wr}% <span style="color:var(--muted);font-weight:400;font-size:11px">n=${r.n}</span></span>
      </div>`).join('') : noData;
    return `<div class="card" style="margin:0"><div class="card-header"><span class="card-title">${title}</span></div><div style="padding:8px 20px 16px">${html}</div></div>`;
  }
  const archRows = (r.by_archetype||[]).map(a => ({label:a.archetype, wr:a.win_rate, n:a.trades}));
  const edgeRows = (r.by_edge||[]).map(b => ({label:b.bucket, wr:b.win_rate, n:b.trades}));
  document.getElementById('insight-grid').innerHTML =
    insightCard('By Archetype (conviction ≥ 7)', archRows) +
    insightCard('By Edge', edgeRows);

  // Trades table
  document.getElementById('trades-count').textContent = trades.length + ' trades';
  const tbody = document.getElementById('trades-body');
  tbody.innerHTML = trades.length ? trades.map(t => `
    <tr>
      <td>${badgeSignal(t.signal_type)}</td>
      <td class="td-q" title="${t.question}">${t.question}</td>
      <td class="c-accent" style="font-weight:600">${t.edge_at_entry.toFixed(1)}%</td>
      <td style="color:${t.consensus_at_entry>0?'var(--green)':'var(--red)'};font-weight:600">${t.consensus_at_entry>0?'+':''}${t.consensus_at_entry.toFixed(1)}</td>
      <td><span style="font-weight:600;color:${t.resolution==='YES'?'var(--green)':'var(--red)'}">${t.resolution}</span></td>
      <td style="font-weight:600;color:${t.roi>=0?'var(--green)':'var(--red)'}">${t.roi>=0?'+':''}${t.roi.toFixed(1)}%</td>
      <td style="font-weight:600;color:${t.pnl>=0?'var(--green)':'var(--red)'}">${t.pnl>=0?'+':''}$${t.pnl.toFixed(2)}</td>
    </tr>`).join('')
    : '<tr><td colspan="7" class="empty-state"><div class="icon">📊</div>No resolved trades yet</td></tr>';
}

loadReport();
</script>
</body>
</html>
"""


# ── User Guide page ───────────────────────────────────────────────────────

GUIDE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Guide — Polymarket Intelligence</title>
""" + _BASE_STYLE + """
<style>
.guide { max-width: 760px; margin: 0 auto; padding: 32px 24px 64px; }
.guide h2 { font-size: 18px; font-weight: 700; color: var(--text); margin: 36px 0 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
.guide h3 { font-size: 14px; font-weight: 600; color: var(--accent); margin: 20px 0 8px; }
.guide p  { color: var(--muted); line-height: 1.75; margin-bottom: 12px; font-size: 14px; }
.guide ul, .guide ol { color: var(--muted); padding-left: 20px; margin-bottom: 12px; }
.guide li { line-height: 1.8; font-size: 14px; }
.guide strong { color: var(--text); font-weight: 600; }
.guide code {
  background: var(--surface2); color: var(--accent);
  padding: 2px 7px; border-radius: 4px; font-size: 12px;
  font-family: 'SF Mono','Fira Code',monospace;
}
.guide a { color: var(--accent); text-decoration: none; }
.guide a:hover { text-decoration: underline; }
.guide .hero {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 28px 32px;
  margin-bottom: 8px;
}
.guide .hero-title { font-size: 26px; font-weight: 800; color: var(--text); margin-bottom: 8px; }
.guide .hero-sub { color: var(--muted); font-size: 14px; line-height: 1.7; }
.flow {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin: 16px 0 24px;
}
.flow-step {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  text-align: center;
}
.flow-step .num {
  width: 28px; height: 28px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  font-size: 12px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 10px;
}
.flow-step .label { font-size: 12px; font-weight: 600; color: var(--text); }
.flow-step .desc  { font-size: 11px; color: var(--muted); margin-top: 4px; }
.signal-table { width: 100%; border-collapse: collapse; margin: 12px 0 20px; }
.signal-table th { text-align: left; padding: 8px 14px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); border-bottom: 1px solid var(--border); }
.signal-table td { padding: 10px 14px; font-size: 13px; border-bottom: 1px solid rgba(42,45,62,0.5); vertical-align: top; }
.signal-table tr:last-child td { border-bottom: none; }
.archetype-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin: 12px 0 20px; }
.archetype-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 16px;
}
.archetype-card .name { font-size: 12px; font-weight: 700; color: var(--accent); margin-bottom: 4px; }
.archetype-card .desc { font-size: 12px; color: var(--muted); line-height: 1.6; }
.tip {
  background: rgba(108,99,255,0.08);
  border-left: 3px solid var(--accent);
  border-radius: 0 8px 8px 0;
  padding: 12px 16px;
  margin: 12px 0;
  font-size: 13px;
  color: var(--muted);
}
.tip strong { color: var(--text); }
@media (max-width: 640px) {
  .guide { padding: 20px 16px 48px; }
  .guide .hero { padding: 20px; }
  .guide .hero-title { font-size: 20px; }
}
</style>
</head>
<body>
""" + _navbar("guide") + """
<div class="guide">

  <div class="hero">
    <div class="hero-title">Polymarket Intelligence — User Guide</div>
    <div class="hero-sub">
      An AI system that scans Polymarket prediction markets every 60 seconds,
      simulates how 5 different trader archetypes would react, and generates
      actionable trading signals. This guide explains everything you need to know.
    </div>
  </div>

  <h2>How it works</h2>
  <p>Every 60 seconds the system runs a full scan cycle:</p>
  <div class="flow">
    <div class="flow-step"><div class="num">1</div><div class="label">Fetch</div><div class="desc">Top 5 markets by volume from Polymarket</div></div>
    <div class="flow-step"><div class="num">2</div><div class="label">Analyze</div><div class="desc">5 Claude AI archetypes give their opinion</div></div>
    <div class="flow-step"><div class="num">3</div><div class="label">Score</div><div class="desc">Consensus score calculated from all agents</div></div>
    <div class="flow-step"><div class="num">4</div><div class="label">Signal</div><div class="desc">STRONG BUY / SELL / WATCH / IGNORE</div></div>
    <div class="flow-step"><div class="num">5</div><div class="label">Trade</div><div class="desc">Paper portfolio bets automatically</div></div>
  </div>

  <h2>Signal Types</h2>
  <table class="signal-table">
    <thead><tr><th>Signal</th><th>Condition</th><th>Meaning</th><th>Action</th></tr></thead>
    <tbody>
      <tr>
        <td><span class="badge badge-buy">Strong Buy</span></td>
        <td><code>edge &gt; 2%</code> and <code>consensus &gt; +4</code></td>
        <td>Strong bullish agreement — most agents want YES</td>
        <td>Paper portfolio bets YES automatically</td>
      </tr>
      <tr>
        <td><span class="badge badge-sell">Strong Sell</span></td>
        <td><code>edge &gt; 2%</code> and <code>consensus &lt; -4</code></td>
        <td>Strong bearish agreement — most agents want NO</td>
        <td>Paper portfolio bets NO automatically</td>
      </tr>
      <tr>
        <td><span class="badge badge-watch">Watch</span></td>
        <td><code>edge &gt; 1%</code> and <code>|consensus| &gt; 6</code></td>
        <td>Interesting market but edge not strong enough yet</td>
        <td>Monitor — no bet placed</td>
      </tr>
      <tr>
        <td><span class="badge badge-ignore">Ignore</span></td>
        <td>Everything else</td>
        <td>No clear opportunity</td>
        <td>Skipped</td>
      </tr>
    </tbody>
  </table>

  <h2>The 5 Trader Archetypes</h2>
  <p>Each market is analyzed by 5 Claude AI agents simultaneously. Each has a distinct personality and decision logic:</p>
  <div class="archetype-grid">
    <div class="archetype-card"><div class="name">RETAIL</div><div class="desc">Emotional, FOMO-driven. Follows headlines and social sentiment. Tends to buy when everyone else is buying.</div></div>
    <div class="archetype-card"><div class="name">INSTITUTION</div><div class="desc">Analytical and conservative. Fades extreme momentum. Waits for data confirmation before acting.</div></div>
    <div class="archetype-card"><div class="name">DEGEN</div><div class="desc">High risk tolerance. Hunts asymmetric bets and extreme odds. Rarely skips — loves volatile markets.</div></div>
    <div class="archetype-card"><div class="name">WHALE</div><div class="desc">Only acts with overwhelming conviction. Aware their size moves the market. SKIPs most opportunities.</div></div>
    <div class="archetype-card"><div class="name">QUANT</div><div class="desc">Pure statistics. Ignores narrative entirely. Compares implied probability vs historical base rates.</div></div>
  </div>

  <h2>Reading the Numbers</h2>

  <h3>Edge %</h3>
  <p>
    Measures how far the YES price deviates from 50/50 — a proxy for market conviction.
    <br><code>edge = |yes_price − 0.5| × 200</code>
    <br>A market at 0.5 (50%) has edge 0%. A market at 0.99 has edge 98%.
    High edge means the crowd has strong conviction, which creates potential for mispricing.
  </p>

  <h3>Consensus Score (−10 to +10)</h3>
  <p>
    Weighted average of all non-SKIP agents:<br>
    <code>YES agents contribute +conviction</code> &nbsp;·&nbsp; <code>NO agents contribute −conviction</code>
  </p>
  <ul>
    <li><strong>+8 to +10</strong> — near-unanimous bullish. Very strong signal.</li>
    <li><strong>+4 to +7</strong> — moderate bullish lean.</li>
    <li><strong>0</strong> — agents split. No clear direction.</li>
    <li><strong>−4 to −7</strong> — moderate bearish lean.</li>
    <li><strong>−8 to −10</strong> — near-unanimous bearish. Very strong signal.</li>
  </ul>

  <h2>Paper Trading</h2>
  <p>
    The paper trading module simulates real bets with <strong>$5,000 fake USDC</strong>.
    Every STRONG BUY or STRONG SELL automatically opens a position.
  </p>
  <ul>
    <li><strong>Stake per trade:</strong> 2% of current balance (dynamic — grows with wins, shrinks with losses)</li>
    <li><strong>STRONG BUY</strong> → bets YES at current yes_price</li>
    <li><strong>STRONG SELL</strong> → bets NO at current no_price</li>
    <li><strong>No duplicates:</strong> only one open position per market at a time</li>
    <li><strong>Payout formula:</strong> <code>payout = stake / entry_price</code> if won</li>
    <li><strong>Bust protection:</strong> if balance drops below $50 with no open positions, resets to $5,000</li>
  </ul>

  <div class="tip">
    <strong>Example:</strong> Balance $5,000 → stake = $100. YES price = 0.25.
    If market resolves YES → payout = $100 / 0.25 = $400 → profit $300 (+300% ROI).
    If resolves NO → lose $100 (−100%).
  </div>

  <h2>Backtest</h2>
  <p>
    The backtest checks <strong>past signals against real market resolutions</strong> to measure
    if the system is actually making good predictions.
  </p>
  <ul>
    <li>Click <strong>Run Backtest</strong> on the Backtest page at any time</li>
    <li>Only STRONG BUY and STRONG SELL signals are evaluated</li>
    <li>Markets that haven't resolved yet show as <em>open</em> — they're excluded from win rate</li>
    <li>Results are cached — resolved markets aren't re-queried</li>
  </ul>
  <p><strong>How to interpret results:</strong></p>
  <ul>
    <li>Win rate <strong>&gt; 55%</strong> with n &gt; 20 signals → system has real predictive value</li>
    <li>Win rate <strong>&lt; 50%</strong> → signals are noisy, thresholds need tuning</li>
    <li>If <strong>QUANT</strong> has the highest win rate → its statistical approach is most reliable for this market</li>
  </ul>

  <h2>Pages at a Glance</h2>
  <ul>
    <li><strong><a href="/">Signals</a></strong> — live feed of all signals from recent scans, auto-refreshes every 60s</li>
    <li><strong><a href="/paper">Paper Trading</a></strong> — portfolio balance, open positions, closed trade history, equity chart</li>
    <li><strong><a href="/backtest">Backtest</a></strong> — run historical validation on-demand, see win rate by archetype and edge bucket</li>
    <li><strong><a href="/health">/health</a></strong> — JSON status endpoint, useful to verify the scanner is running</li>
  </ul>

  <h2>Cost &amp; Rate Limits</h2>
  <ul>
    <li>Each scan: 5 markets × 5 agents × ~$0.0008 ≈ <strong>$0.02</strong></li>
    <li>Running 24/7 at 60s interval: ~1,440 scans/day ≈ <strong>$28/day</strong></li>
    <li>Model used: <code>claude-haiku-4-5-20251001</code> (fastest &amp; cheapest)</li>
    <li>Scan interval is configurable via <code>SCAN_INTERVAL_SECONDS</code> env var</li>
  </ul>

  <div class="tip">
    <strong>Tip:</strong> Set <code>SCAN_INTERVAL_SECONDS=300</code> in Railway env vars to scan every 5 minutes
    and reduce costs to ~$5.76/day with minimal loss of signal quality.
  </div>

</div>
</body>
</html>
"""


# ── Route handlers ─────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML


@router.get("/api/signals")
async def get_signals():
    return JSONResponse(content=logger.read_last(50))


@router.get("/api/signals/strong")
async def get_strong_signals():
    return JSONResponse(content=logger.read_strong(50))


@router.get("/health")
async def health():
    signals = logger.read_last(1)
    last_scan = signals[-1]["timestamp"] if signals else None
    return {
        "status": "ok",
        "last_scan": last_scan,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/api/backtest/run")
async def run_backtest_endpoint():
    from backtester.run import run_backtest
    try:
        report = await run_backtest()
        if report is None:
            return JSONResponse(
                content={"error": "No actionable signals found in log"},
                status_code=400,
            )
        s = report["summary"]
        return JSONResponse(content={
            "message": f"Done — {s['resolved']} resolved signals, win rate {s['win_rate']}%",
            "summary": s,
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@router.get("/api/backtest")
async def get_backtest():
    if not BACKTEST_REPORT_FILE.exists():
        return JSONResponse(
            content={"error": "No backtest report found. Run: python -m backtester.run"},
            status_code=404,
        )
    try:
        return JSONResponse(content=json.loads(BACKTEST_REPORT_FILE.read_text()))
    except json.JSONDecodeError:
        return JSONResponse(content={"error": "Corrupted report file"}, status_code=500)


@router.get("/backtest", response_class=HTMLResponse)
async def backtest_page():
    return BACKTEST_HTML


@router.get("/guide", response_class=HTMLResponse)
async def guide_page():
    return GUIDE_HTML


@router.get("/paper", response_class=HTMLResponse)
async def paper_page():
    return PAPER_HTML


@router.get("/api/paper/portfolio")
async def get_portfolio():
    p = Portfolio.load()
    data = p.model_dump()
    data["stats"] = p.get_stats()
    return JSONResponse(content=data)


@router.get("/api/paper/positions")
async def get_positions():
    p = Portfolio.load()
    return JSONResponse(content=[pos.model_dump() for pos in p.positions if pos.status == "OPEN"])


@router.get("/api/paper/history")
async def get_history():
    p = Portfolio.load()
    return JSONResponse(content=[t.model_dump() for t in reversed(p.trade_history)])

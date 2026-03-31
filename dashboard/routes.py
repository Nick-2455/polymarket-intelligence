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

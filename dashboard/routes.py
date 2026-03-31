"""FastAPI dashboard endpoints."""

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

from storage.logger import SignalLogger

BACKTEST_REPORT_FILE = Path("backtest_report.json")

router = APIRouter()
logger = SignalLogger()

DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Polymarket Intelligence</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    background: #0d1117; color: #c9d1d9;
    padding: 24px; min-height: 100vh;
  }
  h1 { color: #58a6ff; margin-bottom: 8px; font-size: 1.6rem; }
  .subtitle { color: #8b949e; margin-bottom: 24px; font-size: 0.85rem; }
  table { width: 100%; border-collapse: collapse; }
  th {
    text-align: left; padding: 12px 16px;
    background: #161b22; color: #8b949e;
    font-size: 0.75rem; text-transform: uppercase;
    letter-spacing: 0.05em; border-bottom: 1px solid #21262d;
  }
  td {
    padding: 12px 16px; border-bottom: 1px solid #21262d;
    font-size: 0.85rem;
  }
  tr:hover { background: #161b22; }
  .badge {
    display: inline-block; padding: 3px 10px;
    border-radius: 12px; font-size: 0.72rem;
    font-weight: 700; text-transform: uppercase;
  }
  .STRONG_BUY { background: #0d4429; color: #3fb950; border: 1px solid #238636; }
  .STRONG_SELL { background: #491c1c; color: #f85149; border: 1px solid #da3633; }
  .WATCH { background: #3d2e00; color: #d29922; border: 1px solid #9e6a03; }
  .IGNORE { background: #21262d; color: #8b949e; border: 1px solid #30363d; }
  .edge { color: #58a6ff; font-weight: 600; }
  .consensus-pos { color: #3fb950; }
  .consensus-neg { color: #f85149; }
  .consensus-neutral { color: #8b949e; }
  .question { max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .timestamp { color: #8b949e; font-size: 0.75rem; }
  .empty { text-align: center; padding: 48px; color: #8b949e; }
  .refresh-note { color: #484f58; font-size: 0.7rem; margin-top: 16px; text-align: right; }
</style>
</head>
<body>
<h1>Polymarket Intelligence System</h1>
<p class="subtitle">AI-powered prediction market analysis with 5 trader archetypes</p>
<table>
  <thead>
    <tr>
      <th>Signal</th>
      <th>Question</th>
      <th>Edge %</th>
      <th>Consensus</th>
      <th>Volume</th>
      <th>Timestamp</th>
    </tr>
  </thead>
  <tbody id="signals-body">
    <tr><td colspan="6" class="empty">Loading signals...</td></tr>
  </tbody>
</table>
<p class="refresh-note">Auto-refresh every 60s</p>
<script>
function formatConsensus(val) {
  const sign = val > 0 ? '+' : '';
  const cls = val > 0 ? 'consensus-pos' : val < 0 ? 'consensus-neg' : 'consensus-neutral';
  return `<span class="${cls}">${sign}${val.toFixed(2)}</span>`;
}

function formatVolume(v) {
  if (v >= 1e6) return '$' + (v / 1e6).toFixed(1) + 'M';
  if (v >= 1e3) return '$' + (v / 1e3).toFixed(0) + 'K';
  return '$' + v.toFixed(0);
}

async function loadSignals() {
  try {
    const resp = await fetch('/api/signals');
    const data = await resp.json();
    const tbody = document.getElementById('signals-body');
    if (!data.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty">No signals yet. Waiting for first scan...</td></tr>';
      return;
    }
    tbody.innerHTML = data.reverse().map(s => `
      <tr>
        <td><span class="badge ${s.signal}">${s.signal.replace('_', ' ')}</span></td>
        <td class="question" title="${s.question}">${s.question}</td>
        <td class="edge">${s.edge.toFixed(2)}%</td>
        <td>${formatConsensus(s.consensus_score)}</td>
        <td>${formatVolume(s.volume)}</td>
        <td class="timestamp">${new Date(s.timestamp).toLocaleString()}</td>
      </tr>
    `).join('');
  } catch (e) {
    console.error('Failed to load signals:', e);
  }
}

loadSignals();
setInterval(loadSignals, 60000);
</script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML


@router.get("/api/signals")
async def get_signals():
    signals = logger.read_last(50)
    return JSONResponse(content=signals)


@router.get("/api/signals/strong")
async def get_strong_signals():
    signals = logger.read_strong(50)
    return JSONResponse(content=signals)


@router.get("/health")
async def health():
    signals = logger.read_last(1)
    last_scan = signals[-1]["timestamp"] if signals else None
    return {
        "status": "ok",
        "last_scan": last_scan,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/api/backtest")
async def get_backtest():
    if not BACKTEST_REPORT_FILE.exists():
        return JSONResponse(
            content={"error": "No backtest report found. Run: python -m backtester.run"},
            status_code=404,
        )
    try:
        data = json.loads(BACKTEST_REPORT_FILE.read_text())
        return JSONResponse(content=data)
    except json.JSONDecodeError:
        return JSONResponse(content={"error": "Corrupted report file"}, status_code=500)


BACKTEST_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Backtest — Polymarket Intelligence</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    background: #0d1117; color: #c9d1d9;
    padding: 24px; min-height: 100vh;
  }
  h1 { color: #58a6ff; margin-bottom: 4px; font-size: 1.6rem; }
  h2 { color: #8b949e; margin: 24px 0 12px; font-size: 1rem; text-transform: uppercase; letter-spacing: 0.05em; }
  .nav { margin-bottom: 24px; }
  .nav a { color: #58a6ff; text-decoration: none; font-size: 0.8rem; }
  .nav a:hover { text-decoration: underline; }
  .subtitle { color: #8b949e; margin-bottom: 24px; font-size: 0.85rem; }

  .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 32px; }
  .kpi {
    background: #161b22; border: 1px solid #21262d;
    border-radius: 8px; padding: 16px;
  }
  .kpi-label { color: #8b949e; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
  .kpi-value { font-size: 2rem; font-weight: 700; }
  .kpi-value.green { color: #3fb950; }
  .kpi-value.red { color: #f85149; }
  .kpi-value.yellow { color: #d29922; }
  .kpi-value.blue { color: #58a6ff; }
  .kpi-value.neutral { color: #c9d1d9; }

  .warning {
    background: #3d2e00; border: 1px solid #9e6a03;
    color: #d29922; padding: 12px 16px; border-radius: 6px;
    margin-bottom: 24px; font-size: 0.85rem;
  }

  .chart-wrap { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 20px; margin-bottom: 32px; height: 260px; }

  .insights { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 32px; }
  .insight-card {
    background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 16px;
  }
  .insight-card h3 { color: #8b949e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; }
  .insight-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #21262d; font-size: 0.82rem; }
  .insight-row:last-child { border-bottom: none; }
  .insight-wr { font-weight: 700; }

  table { width: 100%; border-collapse: collapse; }
  th {
    text-align: left; padding: 10px 14px;
    background: #161b22; color: #8b949e;
    font-size: 0.72rem; text-transform: uppercase;
    letter-spacing: 0.05em; border-bottom: 1px solid #21262d;
  }
  td { padding: 10px 14px; border-bottom: 1px solid #21262d; font-size: 0.82rem; }
  tr:hover { background: #161b22; }
  .badge {
    display: inline-block; padding: 2px 8px;
    border-radius: 10px; font-size: 0.68rem; font-weight: 700;
  }
  .STRONG_BUY { background: #0d4429; color: #3fb950; border: 1px solid #238636; }
  .STRONG_SELL { background: #491c1c; color: #f85149; border: 1px solid #da3633; }
  .YES { color: #3fb950; font-weight: 600; }
  .NO { color: #f85149; font-weight: 600; }
  .roi-pos { color: #3fb950; font-weight: 600; }
  .roi-neg { color: #f85149; font-weight: 600; }
  .empty { text-align: center; padding: 48px; color: #8b949e; }
  #loading { text-align: center; padding: 80px; color: #8b949e; }
</style>
</head>
<body>
<div class="nav"><a href="/">← Back to dashboard</a></div>
<h1>Backtest Report</h1>
<p class="subtitle" id="subtitle">Loading...</p>
<div id="loading">Loading report...</div>
<div id="content" style="display:none">
  <div id="warning" class="warning" style="display:none">
    ⚠ Datos insuficientes para conclusiones estadísticas (menos de 10 señales resueltas)
  </div>
  <div class="kpi-grid" id="kpis"></div>
  <h2>ROI Acumulado</h2>
  <div class="chart-wrap"><canvas id="roiChart"></canvas></div>
  <div class="insights">
    <div class="insight-card">
      <h3>Por Arquetipo (conviction ≥ 7)</h3>
      <div id="archetype-rows"></div>
    </div>
    <div class="insight-card">
      <h3>Por Edge</h3>
      <div id="edge-rows"></div>
    </div>
    <div class="insight-card">
      <h3>Mejores Condiciones</h3>
      <div id="top3-rows"></div>
    </div>
  </div>
  <h2>Trades Resueltos</h2>
  <table>
    <thead>
      <tr><th>Señal</th><th>Pregunta</th><th>Edge%</th><th>Consensus</th><th>Resolución</th><th>ROI</th><th>P&L</th></tr>
    </thead>
    <tbody id="trades-body"></tbody>
  </table>
</div>
<script>
function wrColor(wr) {
  if (wr >= 55) return 'green';
  if (wr <= 45) return 'red';
  return 'yellow';
}

async function loadReport() {
  const resp = await fetch('/api/backtest');
  if (!resp.ok) {
    document.getElementById('loading').innerHTML =
      'No backtest report found.<br><br>Run: <code>python -m backtester.run</code>';
    return;
  }
  const r = await resp.json();
  const s = r.summary;

  document.getElementById('loading').style.display = 'none';
  document.getElementById('content').style.display = 'block';
  document.getElementById('subtitle').textContent =
    `Período: ${r.period_start} → ${r.period_end}  |  Generado: ${new Date(r.generated_at).toLocaleString()}`;

  if (s.insufficient_data) {
    document.getElementById('warning').style.display = 'block';
  }

  // KPIs
  const wrCls = wrColor(s.win_rate);
  const roiCls = s.avg_roi >= 0 ? 'green' : 'red';
  const pnlCls = s.total_pnl_usd >= 0 ? 'green' : 'red';
  document.getElementById('kpis').innerHTML = `
    <div class="kpi"><div class="kpi-label">Win Rate</div><div class="kpi-value ${wrCls}">${s.win_rate}%</div></div>
    <div class="kpi"><div class="kpi-label">ROI Promedio</div><div class="kpi-value ${roiCls}">${s.avg_roi > 0 ? '+' : ''}${s.avg_roi}%</div></div>
    <div class="kpi"><div class="kpi-label">P&L Simulado</div><div class="kpi-value ${pnlCls}">${s.total_pnl_usd >= 0 ? '+' : ''}$${s.total_pnl_usd}</div></div>
    <div class="kpi"><div class="kpi-label">Señales</div><div class="kpi-value neutral">${s.total_signals}</div></div>
    <div class="kpi"><div class="kpi-label">Resueltas</div><div class="kpi-value blue">${s.resolved}</div></div>
    <div class="kpi"><div class="kpi-label">Abiertas</div><div class="kpi-value neutral">${s.open}</div></div>
  `;

  // Chart: cumulative ROI
  const trades = r.trades || [];
  if (trades.length > 0) {
    const sorted = [...trades].sort((a, b) => a.signal_timestamp.localeCompare(b.signal_timestamp));
    let cum = 0;
    const labels = [];
    const data = [];
    sorted.forEach(t => {
      cum += t.pnl || 0;
      labels.push(new Date(t.signal_timestamp).toLocaleDateString());
      data.push(+cum.toFixed(2));
    });
    new Chart(document.getElementById('roiChart'), {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'P&L acumulado ($)',
          data,
          borderColor: cum >= 0 ? '#3fb950' : '#f85149',
          backgroundColor: 'transparent',
          tension: 0.3,
          pointRadius: 3,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#8b949e', maxTicksLimit: 8 }, grid: { color: '#21262d' } },
          y: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } }
        }
      }
    });
  }

  // Archetype stats
  const archRows = (r.by_archetype || []).map(a => `
    <div class="insight-row">
      <span>${a.archetype}</span>
      <span class="insight-wr" style="color:${a.win_rate>=55?'#3fb950':a.win_rate<=45?'#f85149':'#d29922'}">${a.win_rate}% <small style="color:#8b949e">(n=${a.trades})</small></span>
    </div>`).join('') || '<div style="color:#8b949e;padding:8px 0;font-size:0.8rem">Sin datos suficientes</div>';
  document.getElementById('archetype-rows').innerHTML = archRows;

  // Edge stats
  const edgeRows = (r.by_edge || []).map(b => `
    <div class="insight-row">
      <span>${b.bucket}</span>
      <span class="insight-wr" style="color:${b.win_rate>=55?'#3fb950':b.win_rate<=45?'#f85149':'#d29922'}">${b.win_rate}% <small style="color:#8b949e">(n=${b.trades})</small></span>
    </div>`).join('') || '<div style="color:#8b949e;padding:8px 0;font-size:0.8rem">Sin datos suficientes</div>';
  document.getElementById('edge-rows').innerHTML = edgeRows;

  // Top 3 conditions
  const all = [...(r.by_archetype || []), ...(r.by_edge || [])].filter(x => x.trades >= 3);
  all.sort((a, b) => b.win_rate - a.win_rate);
  const top3 = all.slice(0, 3).map(x => `
    <div class="insight-row">
      <span>${x.archetype || x.bucket}</span>
      <span class="insight-wr" style="color:#3fb950">${x.win_rate}%</span>
    </div>`).join('') || '<div style="color:#8b949e;padding:8px 0;font-size:0.8rem">Sin datos suficientes</div>';
  document.getElementById('top3-rows').innerHTML = top3;

  // Trades table
  const tbody = document.getElementById('trades-body');
  if (!trades.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="empty">No hay trades resueltos aún</td></tr>';
    return;
  }
  tbody.innerHTML = trades.map(t => `
    <tr>
      <td><span class="badge ${t.signal_type}">${t.signal_type.replace('_', ' ')}</span></td>
      <td style="max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${t.question}">${t.question}</td>
      <td style="color:#58a6ff">${t.edge_at_entry.toFixed(1)}%</td>
      <td style="color:${t.consensus_at_entry>0?'#3fb950':'#f85149'}">${t.consensus_at_entry > 0 ? '+' : ''}${t.consensus_at_entry.toFixed(1)}</td>
      <td class="${t.resolution}">${t.resolution}</td>
      <td class="${t.roi >= 0 ? 'roi-pos' : 'roi-neg'}">${t.roi >= 0 ? '+' : ''}${t.roi.toFixed(1)}%</td>
      <td class="${t.pnl >= 0 ? 'roi-pos' : 'roi-neg'}">${t.pnl >= 0 ? '+' : ''}$${t.pnl.toFixed(2)}</td>
    </tr>
  `).join('');
}

loadReport();
</script>
</body>
</html>
"""


@router.get("/backtest", response_class=HTMLResponse)
async def backtest_page():
    return BACKTEST_HTML

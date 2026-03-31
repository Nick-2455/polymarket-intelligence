# Polymarket Intelligence System

AI-powered prediction market analysis using Claude API to simulate 5 trader archetypes and generate actionable trading signals.

## Architecture

```
main.py (FastAPI + APScheduler)
  ├── scanner/         Polymarket API client + edge calculation
  ├── agents/          5 Claude-powered trader archetypes + signal logic
  ├── storage/         Thread-safe JSONL signal logger
  └── dashboard/       Web dashboard + REST API
```

**Flow:** Fetch markets → Calculate edge → Filter top 5 → Simulate 5 archetypes in parallel → Classify signal → Log to JSONL → Display on dashboard

## Running

```bash
pip install -r requirements.txt
cp .env.example .env  # Add your ANTHROPIC_API_KEY
python main.py
```

Dashboard at `http://localhost:8000`. API at `/api/signals`, `/api/signals/strong`, `/health`.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | (required) | Claude API key |
| `EDGE_THRESHOLD` | `1.0` | Minimum edge % to analyze a market |
| `MAX_MARKETS_PER_SCAN` | `5` | Markets per scan cycle |
| `SCAN_INTERVAL_SECONDS` | `60` | Seconds between scans |
| `PORT` | `8000` | Dashboard port |

## Trader Archetypes

| Archetype | Behavior |
|---|---|
| RETAIL | Emotional, FOMO-driven, follows headlines |
| INSTITUTION | Analytical, conservative, fades momentum |
| DEGEN | High risk, hunts extreme odds, rarely skips |
| WHALE | Ultra-high conviction only, usually SKIPs |
| QUANT | Pure statistics, ignores narrative |

### Adding a New Archetype

Add a new `Archetype` entry in `agents/archetypes.py`. No other files need changes — the simulator auto-iterates over `ARCHETYPES`.

## Signal Classification

| Signal | Condition |
|---|---|
| `STRONG_BUY` | edge > 2% AND consensus > +4.0 |
| `STRONG_SELL` | edge > 2% AND consensus < -4.0 |
| `WATCH` | edge > 1% AND |consensus| > 6.0 |
| `IGNORE` | Everything else |

**Consensus score** ranges from -10 (all agents bearish) to +10 (all agents bullish). Calculated as weighted average of conviction * direction for non-SKIP agents.

## signals_log.jsonl Schema

Each line:
```json
{
  "timestamp": "ISO8601",
  "market_id": "string",
  "question": "string",
  "yes_price": 0.0,
  "no_price": 0.0,
  "volume": 0.0,
  "edge": 0.0,
  "consensus_score": 0.0,
  "signal": "STRONG_BUY | STRONG_SELL | WATCH | IGNORE",
  "agents": {
    "RETAIL": {"position": "YES", "conviction": 8, "reasoning": "..."},
    ...
  }
}
```

## Cost Estimate

- Per scan: 5 markets x 5 agents x ~$0.0008 = **~$0.02**
- Per day (24/7 at 60s interval): ~1,440 scans = **~$28/day**
- Model: `claude-haiku-4-5-20251001` (cheapest, fastest)

## Backtester

Correr manualmente (el scanner no necesita estar corriendo):

```bash
python -m backtester.run                     # backtest completo
python -m backtester.run --days 7            # últimos 7 días
python -m backtester.run --signal STRONG_BUY # solo un tipo
python -m backtester.run --min-edge 2.0      # filtrar por edge mínimo
```

Reporte en consola + guardado en `backtest_report.json`.
Ver reporte visual en: `http://localhost:8000/backtest`

**Interpretación:**
- Win rate > 55% con n > 20 señales = sistema útil
- Win rate < 50% = ajustar thresholds de edge/consensus en `agents/signal.py`
- Si QUANT tiene win rate >> otros = subir peso de QUANT en `signal.py`
- `backtest_cache.json` cachea markets ya resueltos para no re-consultarlos

## Deploy to Railway

1. Push to GitHub
2. Connect repo in Railway
3. Set `ANTHROPIC_API_KEY` env var in Railway dashboard
4. `railway.toml` handles the rest — auto-deploys on push

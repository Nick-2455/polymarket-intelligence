"""Entry point del backtester. Uso: python -m backtester.run [opciones]"""

import argparse
import asyncio
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from .resolver import resolve_markets
from .calculator import build_trades
from .report import generate_report

LOG_FILE = Path("signals_log.jsonl")


def _load_signals(
    days: int | None,
    signal_type: str | None,
    min_edge: float,
) -> list[dict]:
    if not LOG_FILE.exists():
        print("[ERROR] signals_log.jsonl not found. Run the main scanner first.")
        return []

    signals = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                signals.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    # Filter by days
    if days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        signals = [
            s for s in signals
            if datetime.fromisoformat(s["timestamp"]) >= cutoff
        ]

    # Filter by signal type
    if signal_type:
        signals = [s for s in signals if s["signal"] == signal_type]
    else:
        # Only backtest actionable signals
        signals = [s for s in signals if s["signal"] in ("STRONG_BUY", "STRONG_SELL")]

    # Filter by edge
    if min_edge > 0:
        signals = [s for s in signals if s["edge"] >= min_edge]

    # Deduplicate: keep latest signal per market_id
    seen: dict[str, dict] = {}
    for s in signals:
        mid = s["market_id"]
        if mid not in seen or s["timestamp"] > seen[mid]["timestamp"]:
            seen[mid] = s
    signals = list(seen.values())

    return signals


async def run_backtest(
    days: int | None = None,
    signal_type: str | None = None,
    min_edge: float = 0.0,
) -> dict | None:
    print("Loading signals from signals_log.jsonl...")
    signals = _load_signals(days, signal_type, min_edge)

    if not signals:
        print("No actionable signals found matching filters.")
        return None

    print(f"Found {len(signals)} unique markets to resolve...")

    market_ids = list({s["market_id"] for s in signals})
    market_results = await resolve_markets(market_ids)

    resolved_count = sum(1 for r in market_results.values() if r.resolved)
    print(f"Resolved: {resolved_count}/{len(market_ids)} markets")

    trades = build_trades(signals, market_results)

    timestamps = [s["timestamp"] for s in signals]
    period_start = min(timestamps)[:10] if timestamps else "N/A"
    period_end = max(timestamps)[:10] if timestamps else "N/A"

    return generate_report(trades, period_start, period_end)


def main():
    parser = argparse.ArgumentParser(
        description="Polymarket Intelligence — Backtester"
    )
    parser.add_argument(
        "--days", type=int, default=None,
        help="Analizar últimos N días (default: todos)"
    )
    parser.add_argument(
        "--signal", type=str, default=None,
        choices=["STRONG_BUY", "STRONG_SELL"],
        help="Filtrar por tipo de señal"
    )
    parser.add_argument(
        "--min-edge", type=float, default=0.0,
        help="Edge mínimo para incluir en análisis (default: 0)"
    )
    args = parser.parse_args()

    asyncio.run(run_backtest(
        days=args.days,
        signal_type=args.signal,
        min_edge=args.min_edge,
    ))


if __name__ == "__main__":
    main()

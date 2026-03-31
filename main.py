"""Entry point: FastAPI + APScheduler for Polymarket Intelligence System."""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from scanner.client import PolymarketClient
from scanner.edge import calculate_edge, filter_by_edge
from agents.simulator import simulate
from storage.logger import SignalLogger
from dashboard.routes import router

load_dotenv()

EDGE_THRESHOLD = float(os.getenv("EDGE_THRESHOLD", "0"))
MAX_MARKETS = int(os.getenv("MAX_MARKETS_PER_SCAN", "5"))
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL_SECONDS", "60"))
PORT = int(os.getenv("PORT", "8000"))

signal_logger = SignalLogger()
poly_client = PolymarketClient()


def _print_result(result):
    print(f"\n  [{result.signal}] \"{result.market.question}\"")
    print(f"    Edge: {result.edge:.1f}% | Consensus: {result.consensus_score:+.1f}")
    for name, resp in result.agent_responses.items():
        pos = resp.position.ljust(4)
        conv = str(resp.conviction).rjust(2)
        print(f"    {name.ljust(12)} {pos}({conv}) — \"{resp.reasoning}\"")


async def run_scan():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*50}")
    print(f"=== POLYMARKET SCAN [{now}] ===")
    print(f"{'='*50}")

    try:
        markets = await poly_client.fetch_markets()
    except ConnectionError as e:
        print(f"  [ERROR] Failed to fetch markets: {e}")
        return

    filtered = filter_by_edge(markets, threshold=EDGE_THRESHOLD)
    filtered.sort(key=lambda m: m.volume, reverse=True)
    top_markets = filtered[:MAX_MARKETS]

    if not top_markets:
        print(f"  No markets found. Skipping.")
        return

    print(f"  Markets fetched: {len(markets)} | Analyzing: {len(top_markets)}")

    signal_count = 0
    for market in top_markets:
        try:
            result = await simulate(market)
            signal_logger.log(result)
            if result.signal != "IGNORE":
                signal_count += 1
            _print_result(result)
        except Exception as e:
            print(f"\n  [ERROR] Simulation failed for \"{market.question}\": {e}")

    print(f"\n  Signals generated: {signal_count}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: scheduler runs inside uvicorn's event loop
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_scan,
        "interval",
        seconds=SCAN_INTERVAL,
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.start()
    print(f"  Scheduler started — scan every {SCAN_INTERVAL}s")
    yield
    # Shutdown
    scheduler.shutdown(wait=False)
    await poly_client.close()


app = FastAPI(title="Polymarket Intelligence System", lifespan=lifespan)
app.include_router(router)


def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[FATAL] ANTHROPIC_API_KEY not set. Add it to .env")
        return

    print("=" * 50)
    print("  POLYMARKET INTELLIGENCE SYSTEM")
    print("=" * 50)
    print(f"  Edge threshold:  {EDGE_THRESHOLD}%")
    print(f"  Max markets:     {MAX_MARKETS}")
    print(f"  Scan interval:   {SCAN_INTERVAL}s")
    print(f"  Dashboard:       http://0.0.0.0:{PORT}")
    print(f"  API key:         ...{api_key[-8:]}")
    print("=" * 50)

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))


if __name__ == "__main__":
    main()

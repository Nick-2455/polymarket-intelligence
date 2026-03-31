"""Consulta el resultado final de cada market en Polymarket."""

import json
from pathlib import Path

import httpx
from pydantic import BaseModel

GAMMA_API = "https://gamma-api.polymarket.com/markets"
CACHE_FILE = Path("backtest_cache.json")


class MarketResult(BaseModel):
    market_id: str
    question: str
    resolved: bool
    resolution: str | None  # "YES", "NO", o None
    final_yes_price: float
    final_no_price: float


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_FILE.write_text(json.dumps(cache, indent=2))


def _parse_prices(item: dict) -> tuple[float, float]:
    outcomes_prices = item.get("outcomePrices", "")
    try:
        if isinstance(outcomes_prices, str) and outcomes_prices:
            prices = json.loads(outcomes_prices)
            yes = float(prices[0]) if len(prices) > 0 else 0.5
            no = float(prices[1]) if len(prices) > 1 else 0.5
        elif isinstance(outcomes_prices, list) and len(outcomes_prices) >= 2:
            yes = float(outcomes_prices[0])
            no = float(outcomes_prices[1])
        else:
            yes, no = 0.5, 0.5
    except (ValueError, IndexError):
        yes, no = 0.5, 0.5
    return max(0.0, min(1.0, yes)), max(0.0, min(1.0, no))


def _detect_resolution(item: dict) -> tuple[bool, str | None]:
    if item.get("closed") or item.get("resolved"):
        # Check winning outcome
        winning = item.get("winner", item.get("winning_outcome", ""))
        if isinstance(winning, str):
            upper = winning.upper()
            if "YES" in upper or upper == "1":
                return True, "YES"
            if "NO" in upper or upper == "0":
                return True, "NO"

        # Infer from prices: resolved markets have price ~0 or ~1
        yes, no = _parse_prices(item)
        if yes >= 0.99:
            return True, "YES"
        if no >= 0.99:
            return True, "NO"
        if yes <= 0.01:
            return True, "NO"
        if no <= 0.01:
            return True, "YES"

        return True, None  # resolved but ambiguous

    return False, None


async def resolve_markets(market_ids: list[str]) -> dict[str, MarketResult]:
    cache = _load_cache()
    results: dict[str, MarketResult] = {}
    to_fetch = []

    for mid in market_ids:
        if mid in cache:
            results[mid] = MarketResult.model_validate(cache[mid])
        else:
            to_fetch.append(mid)

    if not to_fetch:
        return results

    async with httpx.AsyncClient(timeout=20.0) as client:
        for mid in to_fetch:
            try:
                resp = await client.get(f"{GAMMA_API}/{mid}")
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                item = resp.json()

                resolved, resolution = _detect_resolution(item)
                yes, no = _parse_prices(item)

                mr = MarketResult(
                    market_id=mid,
                    question=item.get("question", "Unknown"),
                    resolved=resolved,
                    resolution=resolution,
                    final_yes_price=yes,
                    final_no_price=no,
                )
                results[mid] = mr

                # Only cache resolved markets
                if resolved:
                    cache[mid] = mr.model_dump()

            except (httpx.HTTPError, httpx.TimeoutException):
                continue

    _save_cache(cache)
    return results

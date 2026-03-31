"""HTTP client for Polymarket gamma API."""

import httpx
from pydantic import BaseModel, Field


class Market(BaseModel):
    id: str
    question: str
    yes_price: float = Field(ge=0, le=1)
    no_price: float = Field(ge=0, le=1)
    volume: float
    end_date: str
    description: str = ""


GAMMA_API_URL = "https://gamma-api.polymarket.com/markets"

MAX_RETRIES = 3
BACKOFF_BASE = 1.0


class PolymarketClient:
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0)

    async def fetch_markets(self, limit: int = 100) -> list[Market]:
        params = {
            "limit": limit,
            "active": "true",
            "closed": "false",
            "order": "volume",
            "ascending": "false",
        }

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = await self._client.get(GAMMA_API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                return self._parse_markets(data)
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    import asyncio
                    wait = BACKOFF_BASE * (2 ** attempt)
                    await asyncio.sleep(wait)

        raise ConnectionError(
            f"Failed to fetch markets after {MAX_RETRIES} attempts: {last_error}"
        )

    def _parse_markets(self, data: list[dict]) -> list[Market]:
        markets = []
        for item in data:
            try:
                outcomes_prices = item.get("outcomePrices", "")
                if isinstance(outcomes_prices, str) and outcomes_prices:
                    import json
                    prices = json.loads(outcomes_prices)
                    yes_price = float(prices[0]) if len(prices) > 0 else 0.5
                    no_price = float(prices[1]) if len(prices) > 1 else 0.5
                elif isinstance(outcomes_prices, list) and len(outcomes_prices) >= 2:
                    yes_price = float(outcomes_prices[0])
                    no_price = float(outcomes_prices[1])
                else:
                    yes_price = 0.5
                    no_price = 0.5

                yes_price = max(0.0, min(1.0, yes_price))
                no_price = max(0.0, min(1.0, no_price))

                market = Market(
                    id=str(item.get("id", "")),
                    question=item.get("question", "Unknown"),
                    yes_price=yes_price,
                    no_price=no_price,
                    volume=float(item.get("volume", 0)),
                    end_date=item.get("endDate", item.get("end_date", "")),
                    description=item.get("description", ""),
                )
                markets.append(market)
            except (ValueError, KeyError, IndexError):
                continue
        return markets

    async def close(self):
        await self._client.aclose()

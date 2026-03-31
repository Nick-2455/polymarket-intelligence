"""Checks open positions against Polymarket API to detect resolutions."""

import json
from pathlib import Path

import httpx

from .portfolio import Portfolio

GAMMA_API = "https://gamma-api.polymarket.com/markets"
CACHE_FILE = Path("backtest_cache.json")


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


def _detect_resolution(item: dict) -> tuple[bool, str | None, float]:
    """Returns (resolved, resolution, exit_price)."""
    yes, no = _parse_prices(item)

    if item.get("closed") or item.get("resolved"):
        winning = item.get("winner", item.get("winning_outcome", ""))
        if isinstance(winning, str):
            upper = winning.upper()
            if "YES" in upper or upper == "1":
                return True, "YES", 1.0
            if "NO" in upper or upper == "0":
                return True, "NO", 1.0

        if yes >= 0.99:
            return True, "YES", yes
        if no >= 0.99:
            return True, "NO", no
        if yes <= 0.01:
            return True, "NO", no
        if no <= 0.01:
            return True, "YES", yes

    return False, None, 0.0


async def check_open_positions(portfolio: Portfolio) -> None:
    open_positions = [p for p in portfolio.positions if p.status == "OPEN"]
    if not open_positions:
        return

    cache = _load_cache()
    cache_updated = False

    async with httpx.AsyncClient(timeout=20.0) as client:
        for pos in open_positions:
            mid = pos.market_id

            # Use cache for already-resolved markets
            if mid in cache and cache[mid].get("resolved"):
                cached = cache[mid]
                resolution = cached.get("resolution")
                if resolution in ("YES", "NO"):
                    won = pos.direction == resolution
                    trade = portfolio.close_position(pos.position_id, won=won, exit_price=1.0)
                    if trade:
                        _log_close(trade)
                continue

            try:
                resp = await client.get(f"{GAMMA_API}/{mid}")
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                item = resp.json()
            except (httpx.HTTPError, httpx.TimeoutException):
                continue

            resolved, resolution, exit_price = _detect_resolution(item)

            if not resolved or resolution is None:
                continue

            # Cache the resolved result
            yes, no = _parse_prices(item)
            cache[mid] = {
                "market_id": mid,
                "question": item.get("question", pos.question),
                "resolved": True,
                "resolution": resolution,
                "final_yes_price": yes,
                "final_no_price": no,
            }
            cache_updated = True

            won = pos.direction == resolution
            trade = portfolio.close_position(pos.position_id, won=won, exit_price=exit_price)
            if trade:
                _log_close(trade)

    if cache_updated:
        _save_cache(cache)

    portfolio.check_bust()


def _log_close(trade) -> None:
    result_label = "WON" if trade.result == "WON" else "LOST"
    sign = "+" if trade.pnl >= 0 else ""
    print(
        f"  [PAPER] {result_label} | {sign}${trade.pnl:.2f} ({sign}{trade.roi_pct:.1f}%)"
        f" | \"{trade.question[:50]}\""
    )

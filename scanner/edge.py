"""Edge calculation and market filtering.

Polymarket normalizes prices so YES + NO = 1.0 (no vig spread).
Edge is measured as "price conviction" — how far the YES price deviates
from the fair-coin 0.5. Markets at extremes (near 0 or 1) represent
strong crowd conviction and potential mispricing opportunity.

  edge = |yes_price - 0.5| * 200   → range 0–100%
  - 0%   = perfectly uncertain (YES=0.50)
  - 100% = fully resolved     (YES=0.00 or 1.00)
"""

from datetime import datetime, timezone, timedelta

from .client import Market

MIN_VOLUME = 2_000_000.0
MIN_DAYS_TO_EXPIRY = 30


def calculate_edge(market: Market) -> float:
    edge = abs(market.yes_price - 0.5) * 200
    return round(edge, 4)


def implied_probabilities(market: Market) -> tuple[float, float]:
    total = market.yes_price + market.no_price
    if total == 0:
        return 0.5, 0.5
    implied_yes = market.yes_price / total
    implied_no = market.no_price / total
    return round(implied_yes, 4), round(implied_no, 4)


def filter_by_edge(markets: list[Market], threshold: float = 1.0) -> list[Market]:
    return [m for m in markets if calculate_edge(m) > threshold]


def filter_by_volume(markets: list[Market], min_volume: float = MIN_VOLUME) -> list[Market]:
    """Reject markets with volume below min_volume (default $2,000,000)."""
    filtered = [m for m in markets if m.volume >= min_volume]
    skipped = len(markets) - len(filtered)
    if skipped:
        print(f"  [FILTER] Volume: removed {skipped} markets below ${min_volume:,.0f} volume")
    return filtered


def filter_by_expiration(markets: list[Market], min_days: int = MIN_DAYS_TO_EXPIRY) -> list[Market]:
    """Reject markets expiring in less than min_days days (default 30)."""
    cutoff = datetime.now(timezone.utc) + timedelta(days=min_days)
    filtered = []
    skipped = 0
    for m in markets:
        if not m.end_date:
            skipped += 1
            continue
        try:
            end = datetime.fromisoformat(m.end_date.replace("Z", "+00:00"))
            if end >= cutoff:
                filtered.append(m)
            else:
                skipped += 1
        except (ValueError, AttributeError):
            skipped += 1
    if skipped:
        print(f"  [FILTER] Expiry: removed {skipped} markets expiring within {min_days} days")
    return filtered

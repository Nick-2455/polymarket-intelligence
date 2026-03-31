"""Edge calculation and market filtering.

Polymarket normalizes prices so YES + NO = 1.0 (no vig spread).
Edge is measured as "price conviction" — how far the YES price deviates
from the fair-coin 0.5. Markets at extremes (near 0 or 1) represent
strong crowd conviction and potential mispricing opportunity.

  edge = |yes_price - 0.5| * 200   → range 0–100%
  - 0%   = perfectly uncertain (YES=0.50)
  - 100% = fully resolved     (YES=0.00 or 1.00)
"""

from .client import Market


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

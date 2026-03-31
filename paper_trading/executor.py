"""Executes paper trades based on simulation results."""

from agents.simulator import SimulationResult
from .portfolio import Portfolio, Position, MIN_BALANCE


async def execute_signals(
    results: list[SimulationResult],
    portfolio: Portfolio,
) -> list[Position]:
    new_positions = []

    for result in results:
        if result.signal not in ("STRONG_BUY", "STRONG_SELL"):
            continue

        if portfolio.balance < MIN_BALANCE:
            print(f"  [PAPER] Skipping — balance below minimum (${portfolio.balance:.2f})")
            break

        signal_data = {
            "market_id": result.market.id,
            "question": result.market.question,
            "signal": result.signal,
            "yes_price": result.market.yes_price,
            "no_price": result.market.no_price,
            "edge": result.edge,
            "consensus_score": result.consensus_score,
        }

        pos = portfolio.open_position(signal_data)
        if pos is None:
            continue

        direction_label = "YES" if result.signal == "STRONG_BUY" else "NO"
        print(
            f"  [PAPER] OPENED {direction_label} | ${pos.stake:.2f} @ {pos.entry_price:.3f}"
            f" | payout ${pos.potential_payout:.2f}"
            f" | \"{result.market.question[:50]}\""
        )
        new_positions.append(pos)

    return new_positions

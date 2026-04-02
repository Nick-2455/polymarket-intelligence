"""Executes paper trades based on simulation results."""

from agents.simulator import SimulationResult
from .portfolio import Portfolio, Position, MIN_BALANCE

MAX_OPEN_POSITIONS = 5
MIN_CONSENSUS_ABS = 5.0
LOW_PROB_THRESHOLD = 0.10  # Don't bet YES if implied probability < 10%


async def execute_signals(
    results: list[SimulationResult],
    portfolio: Portfolio,
) -> list[Position]:
    new_positions = []

    # Problem 3: Enforce max open positions limit
    open_count = len([p for p in portfolio.positions if p.status == "OPEN"])
    if open_count >= MAX_OPEN_POSITIONS:
        print(f"  [PAPER] Skipping all — {open_count} positions open (max {MAX_OPEN_POSITIONS})")
        return new_positions

    for result in results:
        if result.signal not in ("STRONG_BUY", "STRONG_SELL"):
            continue

        if portfolio.balance < MIN_BALANCE:
            print(f"  [PAPER] Skipping — balance below minimum (${portfolio.balance:.2f})")
            break

        # Problem 4: Require absolute consensus > 5
        if abs(result.consensus_score) < MIN_CONSENSUS_ABS:
            print(f"  [PAPER] Skipping — consensus {result.consensus_score:+.1f} too divided (need |consensus| > {MIN_CONSENSUS_ABS})")
            continue

        # Problem 1: No YES bet when implied probability < 10%
        if result.signal == "STRONG_BUY" and result.market.yes_price < LOW_PROB_THRESHOLD:
            print(f"  [PAPER] Skipping — YES price {result.market.yes_price:.3f} < {LOW_PROB_THRESHOLD} (low probability, only NO allowed)")
            continue

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

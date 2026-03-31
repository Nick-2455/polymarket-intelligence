"""Orchestrates parallel Claude API calls for each archetype."""

import asyncio
import json
import os
from datetime import datetime, timezone

import anthropic
from pydantic import BaseModel

from scanner.client import Market
from scanner.edge import calculate_edge, implied_probabilities
from .archetypes import ARCHETYPES, Archetype
from .signal import classify_signal


class AgentResponse(BaseModel):
    position: str  # YES | NO | SKIP
    conviction: int  # 1-10
    reasoning: str


class SimulationResult(BaseModel):
    market: Market
    edge: float
    consensus_score: float
    agent_responses: dict[str, AgentResponse]
    signal: str
    timestamp: str


def _build_user_prompt(market: Market, edge: float) -> str:
    implied_yes, implied_no = implied_probabilities(market)
    return (
        f"Prediction market analysis:\n"
        f"Question: {market.question}\n"
        f"YES price: {market.yes_price:.4f} (implied prob: {implied_yes:.2%})\n"
        f"NO price: {market.no_price:.4f} (implied prob: {implied_no:.2%})\n"
        f"Volume: ${market.volume:,.0f}\n"
        f"End date: {market.end_date}\n"
        f"Edge (spread): {edge:.2f}%\n"
        f"Description: {market.description[:500] if market.description else 'N/A'}\n\n"
        f"Should you take a position? Respond with ONLY the JSON."
    )


async def _call_agent(
    client: anthropic.AsyncAnthropic,
    archetype: Archetype,
    user_prompt: str,
) -> AgentResponse:
    try:
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            system=archetype.system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = message.content[0].text.strip()
        # Extract JSON from response in case of extra text
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON found in response")

        data = json.loads(raw[start:end])
        position = data.get("position", "SKIP").upper()
        if position not in ("YES", "NO", "SKIP"):
            position = "SKIP"

        conviction = int(data.get("conviction", 0))
        conviction = max(0, min(10, conviction))

        reasoning = str(data.get("reasoning", ""))[:100]

        return AgentResponse(
            position=position,
            conviction=conviction,
            reasoning=reasoning,
        )
    except Exception:
        return AgentResponse(
            position="SKIP",
            conviction=0,
            reasoning="parse error",
        )


def calculate_consensus(responses: dict[str, AgentResponse]) -> float:
    total = 0.0
    active_agents = 0
    for r in responses.values():
        if r.position == "SKIP":
            continue
        direction = 1 if r.position == "YES" else -1
        total += r.conviction * direction
        active_agents += 1
    if active_agents == 0:
        return 0.0
    return round(total / active_agents, 2)


async def simulate(market: Market) -> SimulationResult:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.AsyncAnthropic(api_key=api_key)
    edge = calculate_edge(market)
    user_prompt = _build_user_prompt(market, edge)

    tasks = [
        _call_agent(client, archetype, user_prompt)
        for archetype in ARCHETYPES
    ]
    results = await asyncio.gather(*tasks)

    agent_responses = {
        archetype.name: response
        for archetype, response in zip(ARCHETYPES, results)
    }

    consensus = calculate_consensus(agent_responses)
    signal = classify_signal(edge, consensus)

    return SimulationResult(
        market=market,
        edge=edge,
        consensus_score=consensus,
        agent_responses=agent_responses,
        signal=signal,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

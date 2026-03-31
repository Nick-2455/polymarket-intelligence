"""Thread-safe JSONL logger for signals."""

import json
import threading
from pathlib import Path

from agents.simulator import SimulationResult


LOG_FILE = Path("signals_log.jsonl")


class SignalLogger:
    def __init__(self, path: Path = LOG_FILE):
        self._path = path
        self._lock = threading.Lock()

    def log(self, result: SimulationResult) -> None:
        entry = {
            "timestamp": result.timestamp,
            "market_id": result.market.id,
            "question": result.market.question,
            "yes_price": result.market.yes_price,
            "no_price": result.market.no_price,
            "volume": result.market.volume,
            "edge": result.edge,
            "consensus_score": result.consensus_score,
            "signal": result.signal,
            "agents": {
                name: resp.model_dump()
                for name, resp in result.agent_responses.items()
            },
        }
        line = json.dumps(entry, ensure_ascii=False) + "\n"
        with self._lock:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(line)

    def read_last(self, n: int = 50) -> list[dict]:
        if not self._path.exists():
            return []
        with self._lock:
            with open(self._path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        entries = []
        for line in lines[-n:]:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries

    def read_strong(self, n: int = 50) -> list[dict]:
        all_signals = self.read_last(n * 3)
        strong = [
            s for s in all_signals
            if s.get("signal") in ("STRONG_BUY", "STRONG_SELL")
        ]
        return strong[-n:]

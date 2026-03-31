"""Portfolio state — balance, positions, trade history. Persisted to paper_portfolio.json."""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

PORTFOLIO_FILE = Path("paper_portfolio.json")
MIN_BALANCE = 50.0
INITIAL_BALANCE = 5000.0


class Position(BaseModel):
    position_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    market_id: str
    question: str
    direction: str          # "YES" | "NO"
    stake: float
    entry_price: float
    potential_payout: float
    edge_at_entry: float
    consensus_at_entry: float
    opened_at: str
    status: str = "OPEN"    # "OPEN" | "WON" | "LOST"


class Trade(BaseModel):
    position_id: str
    market_id: str
    question: str
    direction: str
    stake: float
    entry_price: float
    exit_price: float | None = None
    pnl: float | None = None
    roi_pct: float | None = None
    opened_at: str
    closed_at: str | None = None
    result: str             # "WON" | "LOST" | "OPEN"


class Portfolio(BaseModel):
    balance: float = INITIAL_BALANCE
    initial_balance: float = INITIAL_BALANCE
    total_staked: float = 0.0
    realized_pnl: float = 0.0
    positions: list[Position] = []
    trade_history: list[Trade] = []
    balance_history: list[dict] = []  # [{timestamp, balance}] for chart

    # Not persisted — runtime lock
    class Config:
        arbitrary_types_allowed = True

    def open_position(self, signal_data: dict) -> "Position | None":
        stake = round(self.balance * 0.02, 2)
        if self.balance < MIN_BALANCE:
            return None
        stake = min(stake, self.balance - MIN_BALANCE)
        if stake <= 0:
            return None

        # No duplicate market positions
        open_ids = {p.market_id for p in self.positions if p.status == "OPEN"}
        if signal_data["market_id"] in open_ids:
            return None

        is_buy = signal_data["signal"] == "STRONG_BUY"
        direction = "YES" if is_buy else "NO"
        entry_price = signal_data["yes_price"] if is_buy else signal_data["no_price"]

        if entry_price <= 0:
            return None

        potential_payout = round(stake / entry_price, 2)

        pos = Position(
            market_id=signal_data["market_id"],
            question=signal_data["question"],
            direction=direction,
            stake=stake,
            entry_price=entry_price,
            potential_payout=potential_payout,
            edge_at_entry=signal_data["edge"],
            consensus_at_entry=signal_data["consensus_score"],
            opened_at=datetime.now(timezone.utc).isoformat(),
        )

        self.positions.append(pos)
        self.balance = round(self.balance - stake, 2)
        self.total_staked = round(self.total_staked + stake, 2)
        self._record_balance()
        return pos

    def close_position(self, position_id: str, won: bool, exit_price: float = 0.0) -> "Trade | None":
        pos = next((p for p in self.positions if p.position_id == position_id), None)
        if pos is None or pos.status != "OPEN":
            return None

        now = datetime.now(timezone.utc).isoformat()

        if won:
            payout = round(pos.stake / pos.entry_price, 2)
            pnl = round(payout - pos.stake, 2)
            roi_pct = round((pnl / pos.stake) * 100, 2)
            self.balance = round(self.balance + payout, 2)
            pos.status = "WON"
        else:
            payout = 0.0
            pnl = round(-pos.stake, 2)
            roi_pct = -100.0
            pos.status = "LOST"

        self.total_staked = round(self.total_staked - pos.stake, 2)
        self.realized_pnl = round(self.realized_pnl + pnl, 2)

        trade = Trade(
            position_id=pos.position_id,
            market_id=pos.market_id,
            question=pos.question,
            direction=pos.direction,
            stake=pos.stake,
            entry_price=pos.entry_price,
            exit_price=exit_price if exit_price else (1.0 if won else 0.0),
            pnl=pnl,
            roi_pct=roi_pct,
            opened_at=pos.opened_at,
            closed_at=now,
            result="WON" if won else "LOST",
        )
        self.trade_history.append(trade)
        self._record_balance()
        return trade

    def check_bust(self) -> bool:
        open_positions = [p for p in self.positions if p.status == "OPEN"]
        if self.balance < MIN_BALANCE and not open_positions:
            print("\n  [PAPER] ⚠ PORTFOLIO BUSTED — resetting to $5,000")
            self.balance = INITIAL_BALANCE
            self.total_staked = 0.0
            self.realized_pnl = 0.0
            self.positions = []
            self._record_balance()
            return True
        return False

    def get_stats(self) -> dict:
        closed = [t for t in self.trade_history if t.result in ("WON", "LOST")]
        wins = [t for t in closed if t.result == "WON"]
        open_positions = [p for p in self.positions if p.status == "OPEN"]

        unrealized_pnl = sum(
            p.potential_payout - p.stake for p in open_positions
        )

        win_rate = round(len(wins) / len(closed) * 100, 1) if closed else 0.0
        avg_roi = round(
            sum(t.roi_pct for t in closed) / len(closed), 1
        ) if closed else 0.0

        best = max(closed, key=lambda t: t.roi_pct, default=None)
        worst = min(closed, key=lambda t: t.roi_pct, default=None)

        total_equity = round(self.balance + self.total_staked, 2)
        total_return_pct = round(
            (total_equity - self.initial_balance) / self.initial_balance * 100, 2
        )

        return {
            "balance": self.balance,
            "initial_balance": self.initial_balance,
            "total_staked": self.total_staked,
            "total_equity": total_equity,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_return_pct": total_return_pct,
            "total_trades": len(closed),
            "open_positions": len(open_positions),
            "win_rate": win_rate,
            "avg_roi": avg_roi,
            "best_trade": {"question": best.question, "roi_pct": best.roi_pct} if best else None,
            "worst_trade": {"question": worst.question, "roi_pct": worst.roi_pct} if worst else None,
        }

    def _record_balance(self):
        self.balance_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "balance": round(self.balance + self.total_staked, 2),
        })
        # Keep last 500 points
        if len(self.balance_history) > 500:
            self.balance_history = self.balance_history[-500:]

    def save(self, lock: threading.Lock):
        with lock:
            PORTFOLIO_FILE.write_text(
                self.model_dump_json(indent=2), encoding="utf-8"
            )

    @classmethod
    def load(cls) -> "Portfolio":
        if PORTFOLIO_FILE.exists():
            try:
                data = json.loads(PORTFOLIO_FILE.read_text(encoding="utf-8"))
                return cls.model_validate(data)
            except Exception:
                pass
        return cls()

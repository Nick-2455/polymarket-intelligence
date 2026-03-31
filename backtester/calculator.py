"""Calcula P&L por señal comparando entry price vs resolución."""

from pydantic import BaseModel

from .resolver import MarketResult

STAKE = 10.0  # USD simulado por trade


class TradeResult(BaseModel):
    signal_timestamp: str
    market_id: str
    question: str
    signal_type: str        # STRONG_BUY | STRONG_SELL
    entry_yes_price: float
    entry_no_price: float
    edge_at_entry: float
    consensus_at_entry: float
    agents_at_entry: dict   # raw agent responses
    resolution: str         # YES | NO | OPEN
    roi: float | None       # None si OPEN
    pnl: float | None       # None si OPEN
    profitable: bool | None # None si OPEN


def calculate_roi(signal: dict, result: MarketResult | None) -> TradeResult:
    signal_type = signal["signal"]
    entry_yes = signal["yes_price"]
    entry_no = signal["no_price"]

    if result is None or not result.resolved or result.resolution is None:
        return TradeResult(
            signal_timestamp=signal["timestamp"],
            market_id=signal["market_id"],
            question=signal["question"],
            signal_type=signal_type,
            entry_yes_price=entry_yes,
            entry_no_price=entry_no,
            edge_at_entry=signal["edge"],
            consensus_at_entry=signal["consensus_score"],
            agents_at_entry=signal.get("agents", {}),
            resolution="OPEN",
            roi=None,
            pnl=None,
            profitable=None,
        )

    resolution = result.resolution  # "YES" or "NO"

    if signal_type == "STRONG_BUY":
        # Apostamos YES al precio de entrada
        if resolution == "YES":
            roi = (1.0 - entry_yes) / entry_yes if entry_yes > 0 else 0.0
        else:
            roi = -1.0
    else:  # STRONG_SELL
        # Apostamos NO al precio de entrada
        if resolution == "NO":
            roi = (1.0 - entry_no) / entry_no if entry_no > 0 else 0.0
        else:
            roi = -1.0

    pnl = round(STAKE * roi, 2)
    roi = round(roi * 100, 2)  # como porcentaje

    return TradeResult(
        signal_timestamp=signal["timestamp"],
        market_id=signal["market_id"],
        question=signal["question"],
        signal_type=signal_type,
        entry_yes_price=entry_yes,
        entry_no_price=entry_no,
        edge_at_entry=signal["edge"],
        consensus_at_entry=signal["consensus_score"],
        agents_at_entry=signal.get("agents", {}),
        resolution=resolution,
        roi=roi,
        pnl=pnl,
        profitable=roi > 0,
    )


def build_trades(signals: list[dict], market_results: dict[str, MarketResult]) -> list[TradeResult]:
    trades = []
    for sig in signals:
        if sig["signal"] not in ("STRONG_BUY", "STRONG_SELL"):
            continue
        result = market_results.get(sig["market_id"])
        trades.append(calculate_roi(sig, result))
    return trades

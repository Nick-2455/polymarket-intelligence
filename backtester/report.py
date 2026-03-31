"""Genera reporte de performance del backtester."""

import json
from datetime import datetime, timezone
from pathlib import Path

from .calculator import TradeResult

REPORT_FILE = Path("backtest_report.json")
ARCHETYPE_NAMES = ["RETAIL", "INSTITUTION", "DEGEN", "WHALE", "QUANT"]


def _win_rate(trades: list[TradeResult]) -> float:
    resolved = [t for t in trades if t.profitable is not None]
    if not resolved:
        return 0.0
    return round(len([t for t in resolved if t.profitable]) / len(resolved) * 100, 1)


def _archetype_stats(trades: list[TradeResult]) -> list[dict]:
    stats = []
    for name in ARCHETYPE_NAMES:
        matching = []
        for t in trades:
            if t.profitable is None:
                continue
            agent = t.agents_at_entry.get(name, {})
            conviction = agent.get("conviction", 0)
            position = agent.get("position", "SKIP")
            # High conviction = conviction >= 7 and agrees with signal
            if conviction >= 7 and position != "SKIP":
                signal_direction = "YES" if t.signal_type == "STRONG_BUY" else "NO"
                if position == signal_direction:
                    matching.append(t)

        if len(matching) < 3:
            continue

        wr = _win_rate(matching)
        stats.append({
            "archetype": name,
            "trades": len(matching),
            "win_rate": wr,
        })

    stats.sort(key=lambda x: x["win_rate"], reverse=True)
    return stats


def _edge_bucket_stats(trades: list[TradeResult]) -> list[dict]:
    buckets = [
        ("edge > 50%", lambda e: e > 50),
        ("edge 20-50%", lambda e: 20 < e <= 50),
        ("edge 10-20%", lambda e: 10 < e <= 20),
        ("edge 5-10%", lambda e: 5 < e <= 10),
        ("edge 2-5%", lambda e: 2 < e <= 5),
        ("edge 1-2%", lambda e: 1 < e <= 2),
    ]
    result = []
    resolved = [t for t in trades if t.profitable is not None]
    for label, fn in buckets:
        group = [t for t in resolved if fn(t.edge_at_entry)]
        if len(group) < 2:
            continue
        result.append({
            "bucket": label,
            "trades": len(group),
            "win_rate": _win_rate(group),
            "avg_roi": round(sum(t.roi for t in group) / len(group), 1),
        })
    return result


def generate_report(
    trades: list[TradeResult],
    period_start: str,
    period_end: str,
) -> dict:
    resolved = [t for t in trades if t.profitable is not None]
    open_trades = [t for t in trades if t.profitable is None]
    winners = [t for t in resolved if t.profitable]
    losers = [t for t in resolved if not t.profitable]

    strong_buy = [t for t in trades if t.signal_type == "STRONG_BUY"]
    strong_sell = [t for t in trades if t.signal_type == "STRONG_SELL"]

    rois = [t.roi for t in resolved]
    avg_roi = round(sum(rois) / len(rois), 1) if rois else 0.0
    med_roi = round(sorted(rois)[len(rois) // 2], 1) if rois else 0.0
    total_pnl = round(sum(t.pnl for t in resolved), 2)

    best = max(resolved, key=lambda t: t.roi, default=None)
    worst = min(resolved, key=lambda t: t.roi, default=None)

    insufficient = len(resolved) < 10
    win_rate = _win_rate(resolved)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_start": period_start,
        "period_end": period_end,
        "summary": {
            "total_signals": len(trades),
            "strong_buy": len(strong_buy),
            "strong_sell": len(strong_sell),
            "resolved": len(resolved),
            "open": len(open_trades),
            "winners": len(winners),
            "losers": len(losers),
            "win_rate": win_rate,
            "avg_roi": avg_roi,
            "median_roi": med_roi,
            "total_pnl_usd": total_pnl,
            "stake_per_trade_usd": 10.0,
            "insufficient_data": insufficient,
        },
        "best_trade": {
            "question": best.question,
            "roi": best.roi,
            "signal": best.signal_type,
        } if best else None,
        "worst_trade": {
            "question": worst.question,
            "roi": worst.roi,
            "signal": worst.signal_type,
        } if worst else None,
        "by_archetype": _archetype_stats(trades),
        "by_edge": _edge_bucket_stats(trades),
        "trades": [t.model_dump() for t in sorted(resolved, key=lambda x: x.roi, reverse=True)],
        "open_trades": [t.model_dump() for t in open_trades],
    }

    REPORT_FILE.write_text(json.dumps(report, indent=2))
    _print_report(report)
    return report


def _print_report(r: dict) -> None:
    s = r["summary"]
    print("\n" + "=" * 50)
    print("=== BACKTEST REPORT ===")
    print("=" * 50)
    print(f"Período: {r['period_start']} → {r['period_end']}")
    print(f"Señales analizadas: {s['total_signals']}")
    print(f"  STRONG_BUY:  {s['strong_buy']}")
    print(f"  STRONG_SELL: {s['strong_sell']}")
    print(f"  Abiertas:    {s['open']}")

    if s["insufficient_data"]:
        print("\n  ⚠ Datos insuficientes para conclusiones estadísticas (<10 señales resueltas)")

    print(f"\nPerformance ({s['resolved']} señales resueltas):")
    print(f"  Win Rate:        {s['win_rate']}%")
    print(f"  ROI Promedio:    {s['avg_roi']:+.1f}%")
    print(f"  ROI Mediano:     {s['median_roi']:+.1f}%")
    if r["best_trade"]:
        print(f"  Mejor trade:     {r['best_trade']['roi']:+.1f}% — \"{r['best_trade']['question'][:50]}\"")
    if r["worst_trade"]:
        print(f"  Peor trade:      {r['worst_trade']['roi']:+.1f}% — \"{r['worst_trade']['question'][:50]}\"")
    print(f"  P&L simulado ($10/trade): ${s['total_pnl_usd']:+.2f}")

    if r["by_archetype"]:
        print("\nPor arquetipo (conviction >= 7, alineado con señal):")
        for a in r["by_archetype"]:
            print(f"  {a['archetype'].ljust(12)} Win rate {a['win_rate']}%  (n={a['trades']})")

    if r["by_edge"]:
        print("\nPor edge:")
        for b in r["by_edge"]:
            print(f"  {b['bucket'].ljust(14)} Win rate {b['win_rate']}%  avg ROI {b['avg_roi']:+.1f}%  (n={b['trades']})")

    print(f"\nReporte guardado en: backtest_report.json")
    print("=" * 50)

"""Run read-only shared-cash research on validated daily CSV datasets.

Usage: ``python -m backtesting.portfolio_research --help``.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

from app.ai.features import FEATURE_VERSION
from app.strategy.strategy_v1 import TrendFollowingV1
from backtesting.portfolio_engine import (
    PortfolioBacktestEngine, ResearchPortfolioLimits, summarize_portfolio,
)
from backtesting.research import COST_SCENARIOS, PERIODS_PER_YEAR, _utc_date, load_dataset


def run_portfolio_research(
    dataset_paths: list[Path], *, trade_start: str, trade_end: str,
    limits: ResearchPortfolioLimits | None = None,
    buy_priority: str = "alphabetical", scenarios: tuple[str, ...] = ("optimistic", "base", "pessimistic"),
) -> dict[str, object]:
    """Validate manifests, then score one continuously funded portfolio."""
    if not dataset_paths:
        raise ValueError("At least one dataset path is required")
    if not scenarios or any(name not in COST_SCENARIOS for name in scenarios):
        raise ValueError("scenarios must name one or more known cost cases")
    if _utc_date(trade_start) >= _utc_date(trade_end):
        raise ValueError("trade_start must precede trade_end")
    datasets = {}
    manifests = {}
    paths_by_symbol = {}
    for path in dataset_paths:
        bars, manifest = load_dataset(path)
        symbol = str(manifest["symbol"])
        if symbol in datasets:
            raise ValueError(f"Duplicate dataset for {symbol}")
        if manifest["timeframe"] != "1Day":
            raise ValueError(f"{symbol}: this portfolio runner currently supports only validated 1Day bars")
        if not (manifest["start_utc"] <= trade_start < trade_end <= manifest["end_exclusive_utc"]):
            raise ValueError(f"{symbol}: trading window is outside the dataset range")
        datasets[symbol] = bars
        manifests[symbol] = manifest
        paths_by_symbol[symbol] = path
    conventions = {
        (manifest["start_utc"], manifest["end_exclusive_utc"], manifest["feed"], manifest["adjustment"])
        for manifest in manifests.values()
    }
    if len(conventions) != 1:
        raise ValueError("All portfolio datasets must have the same range, feed, and adjustment")

    limits = limits or ResearchPortfolioLimits()
    results = {}
    for name in scenarios:
        costs = replace(COST_SCENARIOS[name], periods_per_year=PERIODS_PER_YEAR["1Day"])
        result = PortfolioBacktestEngine(
            TrendFollowingV1(), costs=costs, limits=limits, buy_priority=buy_priority
        ).run(datasets, trade_start=_utc_date(trade_start), trade_end=_utc_date(trade_end))
        results[name] = {
            "costs": asdict(costs),
            "metrics": summarize_portfolio(result),
            "fills": [
                {
                    "timestamp": fill.timestamp.isoformat(), "symbol": fill.symbol,
                    "side": fill.side.value, "quantity": fill.quantity,
                    "reference_open": fill.reference_open, "fill_price": fill.fill_price,
                    "commission": fill.commission,
                    "signal_timestamp": fill.signal_timestamp.isoformat(),
                    "signal_reason": fill.signal_reason,
                }
                for fill in result.fills
            ],
            "equity_curve": [
                {
                    "timestamp": point.timestamp.isoformat(), "cash": point.cash,
                    "equity": point.equity, "gross_exposure": point.gross_exposure,
                    "position_count": point.position_count, "drawdown": point.drawdown,
                }
                for point in result.equity_curve
            ],
            "events": list(result.events),
        }
    return {
        "method": "shared_cash_daily_next_session_open",
        "symbols": sorted(datasets),
        "datasets": {
            symbol: {
                "path": str(paths_by_symbol[symbol]), "sha256": manifests[symbol]["sha256"],
                "row_count": manifests[symbol]["row_count"],
                "validation_warnings": manifests[symbol]["validation_warnings"],
            }
            for symbol in sorted(datasets)
        },
        "timeframe": "1Day", "feed": next(iter(manifests.values()))["feed"],
        "adjustment": next(iter(manifests.values()))["adjustment"],
        "strategy": TrendFollowingV1.name, "feature_version": FEATURE_VERSION,
        "trade_start_utc": trade_start, "trade_end_exclusive_utc": trade_end,
        "order_sizing": "Plan a maximum whole-share BUY quantity from the completed signal close; reduce or skip at the next open to honor shared cash and entry limits; never increase the planned quantity after an opening gap.",
        "buy_priority": buy_priority, "research_limits": asdict(limits),
        "policy_gaps": [
            "No stop order or per-trade stop-risk cap; exits require a later trend-rule signal.",
            "No historical snapshot/signal freshness, sector, or volatility gate.",
            "A daily-loss or drawdown breach halts new entries but does not force liquidation.",
            "Adjusted daily OHLC and spread/slippage scenarios are proxies, not broker fill and cash-dividend records.",
            "Fixed present-day symbols do not remove survivorship or historical-universe selection bias.",
        ],
        "cost_scenarios": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", nargs="+", type=Path, required=True)
    parser.add_argument("--trade-start", required=True, help="YYYY-MM-DD UTC inclusive")
    parser.add_argument("--trade-end", required=True, help="YYYY-MM-DD UTC exclusive")
    parser.add_argument("--buy-priority", choices=["alphabetical", "reverse"], default="alphabetical")
    parser.add_argument("--scenarios", nargs="+", choices=list(COST_SCENARIOS), default=list(COST_SCENARIOS))
    parser.add_argument("--max-portfolio-exposure", type=float, default=0.70)
    parser.add_argument("--max-single-position", type=float, default=0.10)
    parser.add_argument("--max-positions", type=int, default=7)
    parser.add_argument("--max-daily-loss", type=float, default=0.03)
    parser.add_argument("--max-drawdown", type=float, default=0.10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Report already exists; choose a fresh output path")
    report = run_portfolio_research(
        args.datasets, trade_start=args.trade_start, trade_end=args.trade_end,
        limits=ResearchPortfolioLimits(
            max_portfolio_exposure=args.max_portfolio_exposure,
            max_single_position=args.max_single_position,
            max_positions=args.max_positions,
            max_daily_loss=args.max_daily_loss,
            max_drawdown=args.max_drawdown,
        ),
        buy_priority=args.buy_priority, scenarios=tuple(args.scenarios),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": str(args.output), "symbols": report["symbols"],
        "summary": {name: data["metrics"] for name, data in report["cost_scenarios"].items()},
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

"""Explain the simulated entries, exits, and holding times in one backtest.

This is an offline research command. It reads a validated local dataset and
never constructs a broker client or submits an order.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path
from statistics import mean, median
from zoneinfo import ZoneInfo

import pandas as pd

from app.strategy.base import SignalAction
from app.strategy.strategy_v1 import TrendFollowingV1
from backtesting.engine import SimulatedFill, BacktestEngine
from backtesting.research import COST_SCENARIOS, PERIODS_PER_YEAR, _utc_date, load_dataset


def _fill_details(fill: SimulatedFill) -> dict[str, object]:
    return {
        "signal_bar_start_utc": fill.signal_timestamp.isoformat(),
        "signal_reason": fill.signal_reason,
        "fill_utc": fill.timestamp.isoformat(),
        "reference_open": fill.reference_open,
        "fill_price": fill.fill_price,
        "shares": fill.quantity,
        "commission": fill.commission,
    }


def audit_trades(
    dataset_path: Path, *, trade_start: str, trade_end: str,
    cost_scenario: str = "base",
) -> dict[str, object]:
    """Return each completed round trip and a holding-time summary.

    Durations are elapsed calendar hours between simulated fills, so nights,
    weekends, and holidays count. A signal timestamp denotes the *start* of
    its 15-minute bar; the decision is made only after that bar closes, and
    the simulated fill uses the next observed bar's open.
    """
    if cost_scenario not in COST_SCENARIOS:
        raise ValueError(f"cost_scenario must be one of {', '.join(COST_SCENARIOS)}")
    bars, manifest = load_dataset(dataset_path)
    if not (manifest["start_utc"] <= trade_start < trade_end <= manifest["end_exclusive_utc"]):
        raise ValueError("Trade window must lie inside the downloaded dataset range")
    timeframe = str(manifest["timeframe"])
    if timeframe not in PERIODS_PER_YEAR:
        raise ValueError(f"Unsupported dataset timeframe: {timeframe}")
    config = replace(COST_SCENARIOS[cost_scenario], periods_per_year=PERIODS_PER_YEAR[timeframe])
    run = BacktestEngine(TrendFollowingV1(), config=config).run(
        bars, trade_start=pd.Timestamp(_utc_date(trade_start)),
        trade_end=pd.Timestamp(_utc_date(trade_end)),
    )

    open_buy: SimulatedFill | None = None
    trades: list[dict[str, object]] = []
    eastern = ZoneInfo("America/New_York")
    for fill in run.fills:
        if fill.side == SignalAction.BUY:
            if open_buy is not None:
                raise ValueError("A second BUY fill occurred before the first position was closed")
            open_buy = fill
        elif fill.side == SignalAction.SELL:
            if open_buy is None or fill.quantity != open_buy.quantity:
                raise ValueError("A SELL fill does not match the open BUY fill")
            duration_hours = (fill.timestamp - open_buy.timestamp).total_seconds() / 3600
            trades.append({
                "buy": _fill_details(open_buy),
                "sell": _fill_details(fill),
                "elapsed_calendar_hours": duration_hours,
                "held_overnight": (
                    open_buy.timestamp.tz_convert(eastern).date()
                    != fill.timestamp.tz_convert(eastern).date()
                ),
                "net_profit_dollars": (
                    fill.quantity * (fill.fill_price - open_buy.fill_price)
                    - open_buy.commission - fill.commission
                ),
            })
            open_buy = None

    durations = [float(trade["elapsed_calendar_hours"]) for trade in trades]
    summary = {
        "closed_trades": len(trades),
        "median_calendar_hours": median(durations) if durations else None,
        "mean_calendar_hours": mean(durations) if durations else None,
        "min_calendar_hours": min(durations) if durations else None,
        "max_calendar_hours": max(durations) if durations else None,
        "held_overnight_count": sum(bool(trade["held_overnight"]) for trade in trades),
        "open_position_at_window_end": open_buy is not None,
        "unclosed_buy": _fill_details(open_buy) if open_buy is not None else None,
    }
    return {
        "dataset": str(dataset_path),
        "dataset_sha256": manifest["sha256"],
        "symbol": manifest["symbol"],
        "timeframe": timeframe,
        "trade_start_utc": trade_start,
        "trade_end_exclusive_utc": trade_end,
        "cost_scenario": cost_scenario,
        "assumptions": asdict(config),
        "timestamp_note": "Signal timestamp is bar start; decision occurs after bar close; fill uses next observed bar open.",
        "summary": summary,
        "trades": trades,
        "events": list(run.events),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--trade-start", required=True, help="YYYY-MM-DD UTC; inclusive")
    parser.add_argument("--trade-end", required=True, help="YYYY-MM-DD UTC; exclusive")
    parser.add_argument("--cost-scenario", choices=COST_SCENARIOS, default="base")
    parser.add_argument("--output", type=Path, help="Optional JSON audit path")
    arguments = parser.parse_args()
    if arguments.output and arguments.output.exists():
        raise FileExistsError("Audit already exists; choose a fresh output path")
    report = audit_trades(
        arguments.dataset, trade_start=arguments.trade_start,
        trade_end=arguments.trade_end, cost_scenario=arguments.cost_scenario,
    )
    rendered = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
        print(json.dumps({"output": str(arguments.output), "summary": report["summary"]}, indent=2))
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()

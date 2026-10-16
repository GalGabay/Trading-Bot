"""Expanding-window calibration and yearly out-of-sample case studies.

Run with ``python -m backtesting.walk_forward --help``. This research module
reads a previously downloaded single-symbol dataset and never places orders.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

import pandas as pd

from app.ai.features import FEATURE_VERSION
from app.strategy.strategy_v1 import TrendFollowingV1, TrendFollowingV1Config
from backtesting.engine import BacktestEngine
from backtesting.metrics import calculate_metrics
from backtesting.research import COST_SCENARIOS, PERIODS_PER_YEAR, _utc_date, load_dataset


# Define this grid before looking at a test fold. Changing it after inspecting
# test results creates selection bias; a later experiment needs a new report.
CANDIDATES: tuple[tuple[str, TrendFollowingV1Config], ...] = (
    ("baseline", TrendFollowingV1Config()),
    ("narrow", TrendFollowingV1Config(rsi_minimum=52, rsi_maximum=68, minimum_volume_ratio=1.1)),
    ("broad", TrendFollowingV1Config(rsi_minimum=45, rsi_maximum=75, minimum_volume_ratio=0.8)),
)


@dataclass(frozen=True)
class WalkForwardConfig:
    """Full-year, expanding training windows followed by one unseen year."""

    min_train_years: int = 3
    min_train_trades: int = 20
    first_test_year: int | None = None
    last_test_year: int | None = None

    def __post_init__(self) -> None:
        if self.min_train_years < 1:
            raise ValueError("min_train_years must be at least 1")
        if self.min_train_trades < 1:
            raise ValueError("min_train_trades must be at least 1")


def _full_year_range(manifest: dict[str, object], config: WalkForwardConfig) -> tuple[int, int, int]:
    """Require full calendar years so a partial year cannot masquerade as one."""
    dataset_start = _utc_date(str(manifest["start_utc"]))
    dataset_end = _utc_date(str(manifest["end_exclusive_utc"]))
    if (dataset_start.month, dataset_start.day) != (1, 1) or (dataset_end.month, dataset_end.day) != (1, 1):
        raise ValueError("Walk-forward datasets must start and end on January 1 UTC")
    first = config.first_test_year or dataset_start.year + config.min_train_years
    last = config.last_test_year or dataset_end.year - 1
    if first < dataset_start.year + config.min_train_years:
        raise ValueError("The first test year needs the requested number of earlier training years")
    if first > last or last >= dataset_end.year:
        raise ValueError("No complete test years fit in the dataset; download more full years")
    return dataset_start.year, first, last


def _periods(manifest: dict[str, object]) -> int:
    timeframe = str(manifest["timeframe"])
    if timeframe not in PERIODS_PER_YEAR:
        raise ValueError(f"Unsupported timeframe in dataset manifest: {timeframe}")
    return PERIODS_PER_YEAR[timeframe]


def run_walk_forward(
    dataset_path: Path, *, config: WalkForwardConfig | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    """Select parameters on past years only, then score each following year.

    Training uses the base cost assumptions. The fixed selection score is net
    total return plus maximum drawdown (which is non-positive), subject to a
    minimum number of completed training trades. Ties keep the earlier grid
    candidate. Test results never enter that year's parameter selection.
    """
    config = config or WalkForwardConfig()
    bars, manifest = load_dataset(dataset_path)
    train_begin, first_test, last_test = _full_year_range(manifest, config)
    periods_per_year = _periods(manifest)
    timestamp = bars["timestamp"]
    folds: list[dict[str, object]] = []

    for test_year in range(first_test, last_test + 1):
        if progress is not None:
            progress(f"Selecting settings using {train_begin}–{test_year - 1}; testing {test_year}.")
        train_start = pd.Timestamp(datetime(train_begin, 1, 1, tzinfo=UTC))
        test_start = pd.Timestamp(datetime(test_year, 1, 1, tzinfo=UTC))
        test_end = pd.Timestamp(datetime(test_year + 1, 1, 1, tzinfo=UTC))
        train_history = bars.loc[timestamp < test_start]
        test_history = bars.loc[timestamp < test_end]
        if not (timestamp.ge(train_start) & timestamp.lt(test_start)).any():
            raise ValueError(f"No training bars precede {test_year}")
        if not (timestamp.ge(test_start) & timestamp.lt(test_end)).any():
            raise ValueError(f"No test bars exist for {test_year}")

        candidates: list[dict[str, object]] = []
        selected: tuple[str, TrendFollowingV1Config, float] | None = None
        for name, strategy_config in CANDIDATES:
            base_costs = replace(COST_SCENARIOS["base"], periods_per_year=periods_per_year)
            training = BacktestEngine(
                TrendFollowingV1(config=strategy_config), config=base_costs
            ).run(train_history, trade_start=train_start, trade_end=test_start)
            metrics = calculate_metrics(training, periods_per_year=periods_per_year)
            eligible = metrics.number_of_trades >= config.min_train_trades
            score = metrics.total_return + metrics.max_drawdown if eligible else None
            candidates.append({
                "name": name, "strategy_config": asdict(strategy_config),
                "eligible": eligible, "selection_score": score,
                "train_metrics": asdict(metrics),
            })
            if score is not None and (selected is None or score > selected[2]):
                selected = (name, strategy_config, score)
        if selected is None:
            raise ValueError(
                f"No candidate reached {config.min_train_trades} completed training trades before {test_year}"
            )
        if progress is not None:
            progress(f"Selected {selected[0]} for {test_year}; evaluating cost scenarios.")

        test_scenarios: dict[str, object] = {}
        for scenario_name, costs in COST_SCENARIOS.items():
            scenario_config = replace(costs, periods_per_year=periods_per_year)
            evaluation = BacktestEngine(
                TrendFollowingV1(config=selected[1]), config=scenario_config
            ).run(test_history, trade_start=test_start, trade_end=test_end)
            test_scenarios[scenario_name] = {
                "assumptions": asdict(scenario_config),
                "metrics": asdict(calculate_metrics(evaluation, periods_per_year=periods_per_year)),
                "signal_count": len(evaluation.signals),
                "fill_count": len(evaluation.fills),
                "final_equity": evaluation.final_equity,
                "events": list(evaluation.events),
            }
        folds.append({
            "train_start_utc": train_start.date().isoformat(),
            "train_end_exclusive_utc": test_start.date().isoformat(),
            "test_start_utc": test_start.date().isoformat(),
            "test_end_exclusive_utc": test_end.date().isoformat(),
            "training_candidates": candidates,
            "selected_candidate": selected[0],
            "selected_strategy_config": asdict(selected[1]),
            "test_scenarios": test_scenarios,
        })

    base_returns = [float(fold["test_scenarios"]["base"]["metrics"]["total_return"]) for fold in folds]
    return {
        "method": "expanding_yearly_walk_forward",
        "dataset": str(dataset_path), "dataset_sha256": manifest["sha256"],
        "symbol": manifest["symbol"], "timeframe": manifest["timeframe"],
        "feed": manifest["feed"], "adjustment": manifest["adjustment"],
        "strategy": TrendFollowingV1.name, "feature_version": FEATURE_VERSION,
        "scope": manifest["universe_scope"],
        "selection_rule": "base-cost training total_return + max_drawdown; minimum closed-trade count; grid-order tie break",
        "walk_forward_config": asdict(config),
        "candidate_grid": [{"name": name, "strategy_config": asdict(choice)} for name, choice in CANDIDATES],
        "folds": folds,
        "summary": {
            "fold_count": len(folds),
            "base_mean_fold_return": sum(base_returns) / len(base_returns),
            "base_worst_fold_return": min(base_returns),
            "base_profitable_fold_count": sum(value > 0 for value in base_returns),
        },
        "limitations": [
            "Single current-symbol case study; survivorship and universe-selection bias remain unresolved.",
            "Each test year starts with fresh cash; open positions at year-end are marked to market, then discarded between folds.",
            "Adjusted historical bars are a research proxy, not point-in-time executable prices or cash dividend accounting.",
            "The reported test years are no longer untouched holdouts after this report is inspected.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--first-test-year", type=int)
    parser.add_argument("--last-test-year", type=int)
    parser.add_argument("--min-train-years", type=int, default=3)
    parser.add_argument("--min-train-trades", type=int, default=20)
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    arguments = parser.parse_args()
    if arguments.output and arguments.output.exists():
        raise FileExistsError("Report already exists; choose a fresh output path")
    report = run_walk_forward(
        arguments.dataset,
        config=WalkForwardConfig(
            min_train_years=arguments.min_train_years,
            min_train_trades=arguments.min_train_trades,
            first_test_year=arguments.first_test_year,
            last_test_year=arguments.last_test_year,
        ),
        progress=lambda message: print(message, file=sys.stderr, flush=True),
    )
    rendered = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
        print(json.dumps({"report": str(arguments.output), "summary": report["summary"]}, indent=2))
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()

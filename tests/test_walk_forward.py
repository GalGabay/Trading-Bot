from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import pandas as pd

from backtesting.walk_forward import WalkForwardConfig, _full_year_range, run_walk_forward


def manifest() -> dict[str, object]:
    return {
        "start_utc": "2019-01-01",
        "end_exclusive_utc": "2024-01-01",
        "sha256": "example-checksum",
        "symbol": "AAPL",
        "timeframe": "15Min",
        "feed": "sip",
        "adjustment": "all",
        "universe_scope": "single_symbol_case_study",
    }


def yearly_bars() -> pd.DataFrame:
    dates = [f"{year}-{day}T15:00:00Z" for year in range(2019, 2024) for day in ("01-02", "12-30")]
    return pd.DataFrame({"timestamp": pd.to_datetime(dates, utc=True)})


@dataclass(frozen=True)
class FakeMetrics:
    total_return: float
    max_drawdown: float
    number_of_trades: int


class WalkForwardTests(TestCase):
    def test_full_year_boundaries_and_training_history_are_required(self) -> None:
        self.assertEqual(_full_year_range(manifest(), WalkForwardConfig()), (2019, 2022, 2023))
        with self.assertRaisesRegex(ValueError, "January 1"):
            _full_year_range({**manifest(), "start_utc": "2019-02-01"}, WalkForwardConfig())
        with self.assertRaisesRegex(ValueError, "earlier training years"):
            _full_year_range(manifest(), WalkForwardConfig(first_test_year=2021))
        with self.assertRaisesRegex(ValueError, "complete test years"):
            _full_year_range(manifest(), WalkForwardConfig(last_test_year=2024))
        with self.assertRaisesRegex(ValueError, "min_train_trades"):
            WalkForwardConfig(min_train_trades=0)

    def test_each_fold_selects_from_earlier_years_only_and_records_scenarios(self) -> None:
        calls: list[dict[str, object]] = []
        training_returns = {
            2022: {50: 0.02, 52: 0.05, 45: 0.03},
            2023: {50: 0.04, 52: 0.03, 45: 0.06},
        }

        class FakeEngine:
            def __init__(self, strategy, *, config):
                self.strategy = strategy
                self.config = config

            def run(self, candles, *, trade_start, trade_end):
                # The engine must never receive a later candle for training or testing.
                self_outer.assertTrue((candles["timestamp"] < trade_end).all())
                call = {
                    "candidate": self.strategy.config.rsi_minimum,
                    "start": trade_start.year,
                    "end": trade_end.year,
                    "last_bar_year": candles["timestamp"].max().year,
                    "costs": self.config.slippage_bps,
                    "periods_per_year": self.config.periods_per_year,
                }
                calls.append(call)
                return SimpleNamespace(**call, signals=(), fills=(), events=(), final_equity=100_000)

        def fake_metrics(result, *, periods_per_year):
            self.assertEqual(periods_per_year, 252 * 26)
            if result.start == 2019:
                return FakeMetrics(training_returns[result.end][result.candidate], -0.01, 30)
            return FakeMetrics({0: 0.1, 5: 0.05, 20: -0.02}[result.costs], -0.02, 5)

        self_outer = self
        with (
            patch("backtesting.walk_forward.load_dataset", return_value=(yearly_bars(), manifest())),
            patch("backtesting.walk_forward.BacktestEngine", FakeEngine),
            patch("backtesting.walk_forward.calculate_metrics", side_effect=fake_metrics),
        ):
            report = run_walk_forward(Path("unused.csv"))

        self.assertEqual([fold["selected_candidate"] for fold in report["folds"]], ["narrow", "broad"])
        self.assertEqual([fold["train_end_exclusive_utc"] for fold in report["folds"]], ["2022-01-01", "2023-01-01"])
        self.assertEqual([fold["test_end_exclusive_utc"] for fold in report["folds"]], ["2023-01-01", "2024-01-01"])
        self.assertEqual([call["last_bar_year"] for call in calls if call["start"] == 2019], [2021] * 3 + [2022] * 3)
        self.assertEqual([call["candidate"] for call in calls if call["start"] == 2022], [52] * 3)
        self.assertEqual([call["candidate"] for call in calls if call["start"] == 2023], [45] * 3)
        self.assertTrue(all(call["periods_per_year"] == 252 * 26 for call in calls))
        self.assertEqual(set(report["folds"][0]["test_scenarios"]), {"optimistic", "base", "pessimistic"})
        self.assertEqual(report["summary"]["fold_count"], 2)
        self.assertEqual(report["summary"]["base_mean_fold_return"], 0.05)
        self.assertEqual(report["dataset_sha256"], "example-checksum")
        self.assertEqual(report["scope"], "single_symbol_case_study")

    def test_rejects_missing_test_year_before_any_simulation(self) -> None:
        bars = yearly_bars().loc[lambda frame: frame["timestamp"].dt.year != 2022]
        with (
            patch("backtesting.walk_forward.load_dataset", return_value=(bars, manifest())),
            patch("backtesting.walk_forward.BacktestEngine") as engine,
        ):
            with self.assertRaisesRegex(ValueError, "No test bars exist for 2022"):
                run_walk_forward(Path("unused.csv"))
        engine.assert_not_called()

    def test_rejects_candidates_with_too_few_completed_training_trades(self) -> None:
        class FakeEngine:
            def __init__(self, strategy, *, config):
                pass

            def run(self, candles, *, trade_start, trade_end):
                return object()

        with (
            patch("backtesting.walk_forward.load_dataset", return_value=(yearly_bars(), manifest())),
            patch("backtesting.walk_forward.BacktestEngine", FakeEngine),
            patch("backtesting.walk_forward.calculate_metrics", return_value=FakeMetrics(0.1, -0.01, 2)),
        ):
            with self.assertRaisesRegex(ValueError, "No candidate reached 20"):
                run_walk_forward(Path("unused.csv"))

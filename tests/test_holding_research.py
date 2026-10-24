"""Reporting and refusal checks for the finite holding-period study."""

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import pandas as pd

from app.strategy.base import SignalAction
from backtesting.holding_research import capacity_summary, holding_summary, load_history, run_study


class HoldingResearchTests(TestCase):
    def fills(self, *, late=False):
        dates = list(pd.bdate_range("2022-01-03", periods=9, tz="UTC"))
        exit_index = 7 if late else 2
        replacement = 8 if late else 2
        fills = [SimpleNamespace(timestamp=dates[0], symbol="AAPL", side=SignalAction.BUY, signal_reason="entry"),
                 SimpleNamespace(timestamp=dates[exit_index], symbol="AAPL", side=SignalAction.SELL, signal_reason="HOLDING_REVIEW_FAILED"),
                 SimpleNamespace(timestamp=dates[replacement], symbol="MSFT", side=SignalAction.BUY, signal_reason="entry")]
        if not late:
            fills.append(SimpleNamespace(timestamp=dates[6], symbol="MSFT", side=SignalAction.SELL, signal_reason="natural exit"))
        return SimpleNamespace(fills=fills, equity_curve=[SimpleNamespace(timestamp=day) for day in dates], holding_reviews=[])

    def test_replacement_and_completed_holding_lengths_are_reported(self):
        report = holding_summary(self.fills())
        self.assertEqual(report["completed_holding_sessions_mean"], 3)
        self.assertEqual(report["completed_holding_sessions_max"], 4)
        self.assertEqual(report["exit_kinds"], {"holding_time": 1, "natural": 1})
        self.assertEqual(report["time_exit_with_different_buy_same_open"], 1)
        self.assertEqual(report["time_exit_with_different_buy_within_five_sessions"], 1)

    def test_incomplete_five_session_followup_is_right_censored(self):
        report = holding_summary(self.fills(late=True))
        self.assertEqual(report["complete_five_session_followups"], 0)
        self.assertEqual(report["right_censored_five_session_followups"], 1)
        self.assertEqual(report["time_exit_with_different_buy_within_five_sessions"], 0)
        self.assertEqual(report["open_position_ages"], {"MSFT": 1})

    def test_capacity_counts_separate_planning_from_open_rejections(self):
        result = SimpleNamespace(buy_decisions=[
            {"phase": "open", "status": "blocked", "blockers": ["position_count"], "held_ages": {"AAPL": 50}, "cash": 5000},
            {"phase": "open", "status": "filled", "blockers": [], "held_ages": {}, "cash": 6000},
            {"phase": "close", "status": "blocked", "blockers": ["missing_volatility"], "held_ages": {}, "cash": 6000}],
            equity_curve=[SimpleNamespace(position_count=7), SimpleNamespace(position_count=1)])
        report = capacity_summary(result)
        self.assertEqual(report["open_attempts"], 2)
        self.assertEqual(report["blocked_open_attempts"], 1)
        self.assertEqual(report["position_count_blocks_with_positive_cash"], 1)
        self.assertEqual(report["planning_blockers"], {"missing_volatility": 1})
        self.assertEqual(report["sessions_at_seven_position_limit"], 1)

    def test_existing_output_is_not_overwritten_or_scored(self):
        with TemporaryDirectory() as temp, patch("backtesting.holding_research.simulate_policy") as simulate:
            with self.assertRaises(FileExistsError):
                run_study(Path(temp))
            simulate.assert_not_called()

    def test_reference_chain_mutation_refuses_loading_prices(self):
        with patch("backtesting.holding_research.digest", return_value="changed"), patch("backtesting.holding_research.load_dataset") as load:
            with self.assertRaisesRegex(ValueError, "reference chain"):
                load_history(Path("unused"), {"reference_sha256": {"original.json": "expected"}})
            load.assert_not_called()

    def test_calendar_mutation_refuses_loading_prices(self):
        with patch("backtesting.holding_research.digest", return_value="changed"), patch("backtesting.holding_research.load_dataset") as load:
            with self.assertRaisesRegex(ValueError, "calendar"):
                load_history(Path("unused"), {"reference_sha256": {}, "calendar_sha256": "expected"})
            load.assert_not_called()

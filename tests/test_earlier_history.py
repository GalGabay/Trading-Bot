"""Offline coverage, provenance, and retained-halt checks for Study C-R4."""

import hashlib
import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import pandas as pd

from backtesting.allocation_research import ARMS, simulate_policy
from backtesting.daily_research import SYMBOLS
from backtesting.daily_strategies import DailyRuleConfig
from backtesting.earlier_history import (
    PROTOCOL, SnapshotCalendar, _pack_window, _validate_range, join_history,
    load_extension, run_study,
)
from backtesting.engine import BacktestConfig
from tests.test_portfolio_backtesting import daily_candles


class EarlierHistoryTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # Deliberately small declared calendar: Dec 31, New Year holiday, Jan 2.
        self.calendar_path = self.root / "calendar.json"
        self.calendar_raw = {
            "start": "2016-01-01", "end": "2023-12-31",
            "sessions": [
                {"opens_at": "2018-12-31T14:30:00Z", "closes_at": "2018-12-31T21:00:00Z"},
                {"opens_at": "2019-01-02T14:30:00Z", "closes_at": "2019-01-02T21:00:00Z"},
            ],
        }
        self.write_calendar()

    def write_calendar(self):
        self.calendar_path.write_text(json.dumps(self.calendar_raw), encoding="utf-8")
        return SnapshotCalendar(self.calendar_path)

    def frame(self, symbol="AAPL", dates=None):
        dates = dates or ["2018-12-31T05:00:00Z", "2019-01-02T05:00:00Z"]
        return daily_candles(symbol, dates, [100] * len(dates), [100] * len(dates))

    def extension(self):
        path = self.root / "AAPL.csv"
        frame = self.frame(dates=["2018-12-31T05:00:00Z"])
        frame.to_csv(path, index=False)
        manifest = {"symbol": "AAPL", "timeframe": "1Day", "feed": "sip", "adjustment": "all",
                    "start_utc": "2016-01-01", "end_exclusive_utc": "2019-01-01", "row_count": 1,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "universe_scope": "single_symbol_case_study"}
        path.with_suffix(".manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return path, manifest

    def test_calendar_bounds_and_holiday_gap_are_respected(self):
        calendar = self.write_calendar()
        report = _validate_range(self.frame(), "2018-12-31", "2019-01-03", calendar)
        self.assertEqual(report.time_gaps, 0)
        self.assertEqual(len(calendar.sessions(date(2019, 1, 1), date(2019, 1, 2))), 1)
        with self.assertRaisesRegex(ValueError, "coverage"):
            calendar.sessions(date(2015, 1, 1), date(2019, 1, 1))

    def test_calendar_rejects_duplicates_and_reversed_order(self):
        original = self.calendar_raw["sessions"].copy()
        for rows in ([original[0]] * 2, original[::-1]):
            with self.subTest(rows=rows):
                self.calendar_raw["sessions"] = rows
                with self.assertRaisesRegex(ValueError, "unique ordered"):
                    self.write_calendar()

    def test_calendar_rejects_naive_and_out_of_bounds_session(self):
        self.calendar_raw["sessions"][0]["opens_at"] = "2018-12-31T14:30:00"
        with self.assertRaisesRegex(ValueError, "timezone"):
            self.write_calendar()
        self.calendar_raw["sessions"][0]["opens_at"] += "Z"
        self.calendar_raw["start"] = "2019-01-01"
        with self.assertRaisesRegex(ValueError, "bounds"):
            self.write_calendar()

    def test_actual_missing_session_is_rejected_without_mutation(self):
        frame = self.frame().iloc[:1].copy()
        original = frame.copy(deep=True)
        with self.assertRaisesRegex(ValueError, "No bar was observed"):
            _validate_range(frame, "2018-12-31", "2019-01-03", self.write_calendar())
        pd.testing.assert_frame_equal(frame, original)

    def test_exclusive_end_rejects_out_of_scope_bar(self):
        with self.assertRaisesRegex(ValueError, "exclusive date range"):
            _validate_range(self.frame(), "2018-12-31", "2019-01-02", self.write_calendar())

    def test_extension_revalidates_checksum_and_conventions(self):
        path, manifest = self.extension()
        bars, provenance = load_extension(path, "AAPL", "2016-01-01", self.write_calendar())
        self.assertEqual(len(bars), 1)
        self.assertEqual(provenance["sha256"], manifest["sha256"])
        manifest["feed"] = "iex"
        path.with_suffix(".manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "conventions"):
            load_extension(path, "AAPL", "2016-01-01", self.write_calendar())

    def test_extension_rejects_changed_csv(self):
        path, _ = self.extension()
        path.write_text(path.read_text() + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "checksum"):
            load_extension(path, "AAPL", "2016-01-01", self.write_calendar())

    def history(self):
        return ({symbol: self.frame(symbol).iloc[:1].copy() for symbol in SYMBOLS},
                {symbol: self.frame(symbol).iloc[1:].copy() for symbol in SYMBOLS})

    def test_join_preserves_real_holiday_gap_and_all_symbols(self):
        earlier, later = self.history()
        joined = join_history(earlier, later, "2016-01-01", self.write_calendar())
        self.assertEqual(set(joined), set(SYMBOLS))
        self.assertTrue(all(len(frame) == 2 for frame in joined.values()))

    def test_join_rejects_dropped_symbol(self):
        earlier, later = self.history()
        del later["JNJ"]
        with self.assertRaisesRegex(ValueError, "all twelve"):
            join_history(earlier, later, "2016-01-01", self.write_calendar())

    def test_join_rejects_overlap_and_missing_real_session(self):
        for broken in (self.frame(), self.frame().iloc[:0]):
            earlier, later = self.history()
            later["AAPL"] = broken
            with self.assertRaises(ValueError):
                join_history(earlier, later, "2016-01-01", self.write_calendar())

    def test_incomplete_coverage_never_scores(self):
        coverage = self.root / "coverage.json"
        coverage.write_text(json.dumps({"protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
                                        "coverage_complete": False, "selected_mode": None}), encoding="utf-8")
        with patch("backtesting.earlier_history.simulate_policy") as simulate:
            report = run_study(self.root, coverage, self.root / "results", self.root / "absent_reference.json")
        simulate.assert_not_called()
        self.assertFalse(report["paper_authorized"])
        self.assertEqual(report["status"], "incomplete_coverage_no_basket_scored")

    def test_protocol_and_calendar_mutation_fail_before_scoring(self):
        coverage = self.root / "coverage.json"
        coverage.write_text(json.dumps({"protocol_sha256": "changed"}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "protocol hashes"):
            run_study(self.root, coverage, self.root / "out1", self.root / "none")
        coverage.write_text(json.dumps({"protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
                                        "coverage_complete": True, "selected_mode": "primary", "calendar_sha256": "changed"}), encoding="utf-8")
        from backtesting.earlier_history import CALENDAR_NAME
        (self.root / CALENDAR_NAME).write_bytes(self.calendar_path.read_bytes())
        with self.assertRaisesRegex(ValueError, "Calendar differs"):
            run_study(self.root, coverage, self.root / "out2", self.root / "none")

    def test_packing_keeps_prior_year_halt_and_uses_full_window_cagr(self):
        result = SimpleNamespace(permanent_halt_reason="daily loss limit reached", halted_at="2018-02-05T21:00:00Z")
        packed = {"metrics": {"total_return": .331, "annual_returns": {"2017": .1, "2018": .1, "2019": .1}}}
        with patch("backtesting.earlier_history.pack_policy", return_value=packed):
            report = _pack_window(result, "2017-01-01", "2020-01-01")
        self.assertAlmostEqual(report["metrics"]["annualized_return_cagr"], .1)
        self.assertEqual(list(report["metrics"]["annual_entry_halt_status"].values()),
                         ["not_halted", "halt_reached_in_year", "halt_already_active_at_year_start"])

    def test_non_breakout_config_is_rejected(self):
        with patch("backtesting.allocation_research.market_regime", return_value={}):
            with self.assertRaisesRegex(ValueError, "breakout rules"):
                simulate_policy(ARMS[0], {}, pd.DataFrame(), BacktestConfig(), start="2017-01-01",
                                end="2019-01-01", rule_config=DailyRuleConfig("trend"))

    def test_neighbor_config_is_forwarded_and_default_remains_55_20(self):
        with patch("backtesting.allocation_research.market_regime", return_value={}), \
                patch("backtesting.allocation_research.DailyResearchStrategy") as strategy, \
                patch("backtesting.allocation_research.PortfolioBacktestEngine"):
            for config in (None, DailyRuleConfig("breakout", 40, 15), DailyRuleConfig("breakout", 70, 25)):
                simulate_policy(ARMS[0], {}, pd.DataFrame(), BacktestConfig(), start="2017-01-01",
                                end="2019-01-01", rule_config=config)
                self.assertEqual(strategy.call_args.args[0], config or DailyRuleConfig("breakout"))

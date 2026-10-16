"""Offline checks for position sizing, the persistent stop, and risk config."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.risk import (
    KillSwitch, RiskLimits, RiskPortfolioSnapshot, RiskPosition,
    load_paper_risk_limits, size_buy,
)
from app.strategy.base import Signal, SignalAction


NOW = datetime(2026, 1, 2, 15, 0, tzinfo=UTC)


def signal(action=SignalAction.BUY):
    return Signal("AAPL", action, 1.0, "test", NOW, "test_strategy")


def snapshot(*, cash=10000, equity=10000, day_start=10000, peak=10000,
             positions=(), complete=True):
    return RiskPortfolioSnapshot(NOW - timedelta(seconds=30), cash, equity, day_start, peak,
                                 positions, complete)


class PositionSizingTests(TestCase):
    def test_stop_risk_caps_whole_share_quantity(self) -> None:
        result = size_buy(signal(), snapshot(), estimated_price=100, stop_price=90)
        self.assertEqual(result.quantity, 10)
        self.assertEqual(result.allowed_risk, 100)
        self.assertEqual(result.stop_distance, 10)
        self.assertEqual(result.binding_cap, "stop_risk")
        self.assertTrue(result.risk_decision.approved)

    def test_single_position_and_portfolio_exposure_caps(self) -> None:
        single = size_buy(signal(), snapshot(), estimated_price=100, stop_price=95,
                          limits=RiskLimits(max_single_position=0.05))
        self.assertEqual((single.quantity, single.binding_cap), (5, "single_position"))
        holding = (RiskPosition("MSFT", 65, 100),)
        exposed = size_buy(signal(), snapshot(cash=3500, positions=holding),
                           estimated_price=100, stop_price=95)
        self.assertEqual((exposed.quantity, exposed.binding_cap), (5, "portfolio_exposure"))

    def test_sector_cap_and_cash_limit_are_observed(self) -> None:
        holding = (RiskPosition("MSFT", 15, 100, "TECH"),)
        sector = size_buy(signal(), snapshot(cash=8500, positions=holding),
                          estimated_price=100, stop_price=95,
                          limits=RiskLimits(max_sector_exposure=0.20), sector="TECH")
        self.assertEqual((sector.quantity, sector.binding_cap), (5, "sector_exposure"))
        self.assertLessEqual(sector.quantity * 100, 8500)

    def test_invalid_stop_stale_account_and_sell_produce_no_size(self) -> None:
        bad_stop = size_buy(signal(), snapshot(), estimated_price=100, stop_price=100)
        self.assertEqual(bad_stop.quantity, 0)
        self.assertFalse(bad_stop.risk_decision.approved)
        stale = size_buy(signal(), snapshot(complete=False), estimated_price=100, stop_price=90)
        self.assertEqual(stale.quantity, 0)
        sell = size_buy(signal(SignalAction.SELL), snapshot(), estimated_price=100, stop_price=90)
        self.assertEqual(sell.quantity, 0)


class KillSwitchTests(TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "stop.sqlite3"
        self.switch = KillSwitch(self.path, max_api_failures=3)

    def test_missing_latch_denies_and_reset_requires_note(self) -> None:
        self.assertFalse(self.switch.status().allow_new_orders)
        self.assertEqual(self.switch.status().reason, "uninitialized")
        with self.assertRaises(ValueError):
            self.switch.reset(" ")
        self.assertTrue(self.switch.reset("Reviewed paper account").allow_new_orders)

    def test_trip_persists_and_success_does_not_clear_it(self) -> None:
        self.switch.reset("Reviewed paper account")
        self.switch.trip("data_quality_failure")
        self.assertFalse(KillSwitch(self.path).status().allow_new_orders)
        self.assertEqual(self.switch.record_api_success().reason, "data_quality_failure")
        self.assertEqual(self.switch.trip("model_unavailable").reason, "data_quality_failure")
        self.assertTrue(self.switch.reset("Investigated data issue").allow_new_orders)

    def test_consecutive_api_failures_trip_and_success_resets_count(self) -> None:
        self.switch.reset("Ready")
        self.assertEqual(self.switch.record_api_failure().consecutive_api_failures, 1)
        self.assertEqual(self.switch.record_api_success().consecutive_api_failures, 0)
        self.switch.record_api_failure()
        self.switch.record_api_failure()
        final = self.switch.record_api_failure()
        self.assertFalse(final.allow_new_orders)
        self.assertEqual(final.reason, "api_failure_threshold")
        self.assertEqual(KillSwitch(self.path).status().consecutive_api_failures, 3)

    def test_invalid_account_and_loss_ceilings_trip(self) -> None:
        self.switch.reset("Ready")
        self.assertEqual(self.switch.observe_portfolio(None, RiskLimits()).reason, "unexpected_account_state")
        self.switch.reset("Reviewed account")
        daily = self.switch.observe_portfolio(
            snapshot(cash=9700, equity=9700), RiskLimits(),
        )
        self.assertEqual(daily.reason, "daily_loss_limit")
        self.switch.reset("Reviewed daily loss")
        drawdown = self.switch.observe_portfolio(
            snapshot(cash=9000, equity=9000, day_start=9000, peak=10000), RiskLimits(),
        )
        self.assertEqual(drawdown.reason, "drawdown_limit")

    def test_unreadable_database_denies_orders(self) -> None:
        self.path.write_bytes(b"not a sqlite database")
        status = self.switch.status()
        self.assertFalse(status.allow_new_orders)
        self.assertEqual(status.reason, "kill_switch_unavailable")


class PaperRiskConfigTests(TestCase):
    def test_template_requires_explicit_approval(self) -> None:
        template = Path("config/risk_limits.example.json")
        with self.assertRaisesRegex(ValueError, "explicitly approved"):
            load_paper_risk_limits(template)

    def test_approved_config_loads_and_invalid_limit_fails(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "risk_limits.json"
            values = json.loads(Path("config/risk_limits.example.json").read_text(encoding="utf-8"))
            values["approved_for_paper"] = True
            path.write_text(json.dumps(values), encoding="utf-8")
            self.assertEqual(load_paper_risk_limits(path).max_single_position, 0.10)
            values["max_single_position"] = 0.80
            path.write_text(json.dumps(values), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_paper_risk_limits(path)

    def test_duplicate_config_key_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "risk_limits.json"
            path.write_text('{"approved_for_paper": true, "approved_for_paper": false}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                load_paper_risk_limits(path)

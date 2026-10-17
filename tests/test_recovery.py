"""Offline Phase 13 startup recovery tests; the fake broker cannot trade."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase

from app.data.database import TradingDatabase
from app.portfolio.portfolio_manager import PortfolioManager
from app.recovery.state_recovery import RecoveryManager
from app.risk.kill_switch import KillSwitch


class FakeReadOnlyBroker:
    def __init__(self) -> None:
        self.account = SimpleNamespace(
            id="paper-account-1", currency="USD", cash="10000",
            buying_power="10000", equity="10000", last_equity="10000",
            status="active", trading_blocked=False, account_blocked=False,
        )
        self.positions: list[SimpleNamespace] = []
        self.open_orders: list[SimpleNamespace] = []
        self.orders: dict[str, SimpleNamespace] = {}
        self.clock_open = True
        self.clock_offset = timedelta(0)
        self.fail_account = False
        self.fail_positions = False
        self.fail_clock = False
        self.lookups = 0

    def get_account(self) -> SimpleNamespace:
        if self.fail_account:
            raise ConnectionError("simulated account outage")
        return self.account

    def get_positions(self) -> list[SimpleNamespace]:
        if self.fail_positions:
            raise ConnectionError("simulated position outage")
        return self.positions

    def get_open_orders(self) -> list[SimpleNamespace]:
        return self.open_orders

    def get_order_by_client_id(self, client_id: str) -> SimpleNamespace | None:
        self.lookups += 1
        return self.orders.get(client_id)

    def get_market_clock(self) -> SimpleNamespace:
        if self.fail_clock:
            raise ConnectionError("simulated clock outage")
        return SimpleNamespace(
            is_open=self.clock_open,
            timestamp=datetime.now(timezone.utc) + self.clock_offset,
        )

    def submit_order(self, request: object) -> None:
        raise AssertionError("Recovery must never submit an order")

    def cancel_order(self, order_id: str) -> None:
        raise AssertionError("Recovery must never cancel an order")


def broker_order(client_id: str, **changes: object) -> SimpleNamespace:
    values = dict(
        id="alpaca-1", client_order_id=client_id, symbol="AAPL", side="buy",
        qty="1", type="limit", time_in_force="day", limit_price="100",
        extended_hours=False, status="new", filled_qty="0", filled_avg_price=None,
    )
    values.update(changes)
    return SimpleNamespace(**values)


class RecoveryTests(TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.database = TradingDatabase(root / "trading.sqlite3")
        self.kill_switch = KillSwitch(root / "kill.sqlite3")
        self.kill_switch.reset("Reviewed isolated test account")
        self.broker = FakeReadOnlyBroker()
        self.config_path = root / "risk.json"
        config = json.loads(Path("config/risk_limits.example.json").read_text(encoding="utf-8"))
        config["approved_for_paper"] = True
        self.config_path.write_text(json.dumps(config), encoding="utf-8")

    def recover(self, **kwargs: object):
        return RecoveryManager(
            self.database, self.kill_switch, risk_config_path=self.config_path,
            broker_factory=lambda: self.broker, **kwargs,
        ).run()

    def baseline(self) -> None:
        PortfolioManager(self.broker, self.database).reconcile()

    def reserve(self, client_id: str = "client-1", *, status: str = "reserved") -> None:
        now = datetime.now(timezone.utc)
        self.database.reserve_order(
            client_order_id=client_id, timestamp=now, symbol="AAPL", side="buy",
            quantity=1, limit_price="100",
        )
        if status != "reserved":
            self.database.record_order_update(
                client_order_id=client_id, timestamp=now, status=status,
                alpaca_order_id="alpaca-1" if status == "new" else None,
            )

    def test_clean_startup_is_ready_and_audited_without_orders(self) -> None:
        self.baseline()
        report = self.recover()
        self.assertTrue(report.can_resume_order_evaluation)
        self.assertTrue(report.database_valid)
        self.assertEqual(report.account_id, "paper-account-1")
        self.assertEqual(report.reasons, ())
        self.assertTrue(self.kill_switch.status().allow_new_orders)
        self.assertIn("can_resume_order_evaluation", report.as_dict())
        with closing(sqlite3.connect(self.database.path)) as connection:
            event = connection.execute(
                "SELECT level, payload_json FROM system_events WHERE event_type='startup_recovery'"
            ).fetchone()
        self.assertEqual(event[0], "info")
        self.assertTrue(json.loads(event[1])["can_resume_order_evaluation"])

    def test_first_start_creates_baseline_but_requires_explicit_reset(self) -> None:
        first = self.recover()
        self.assertFalse(first.can_resume_order_evaluation)
        self.assertIn("no_prior_portfolio_baseline", first.reasons)
        self.assertIsNotNone(self.database.get_latest_portfolio_state())
        self.assertFalse(self.kill_switch.status().allow_new_orders)
        self.assertIn("kill_switch_denied", self.recover().reasons)
        self.kill_switch.reset("Reviewed first snapshot")
        self.assertTrue(self.recover().can_resume_order_evaluation)

    def test_unapproved_limits_block_readiness_but_allow_read_only_report(self) -> None:
        self.baseline()
        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        data["approved_for_paper"] = False
        self.config_path.write_text(json.dumps(data), encoding="utf-8")
        report = self.recover()
        self.assertIn("risk_config_unapproved_or_invalid", report.reasons)
        self.assertFalse(report.can_resume_order_evaluation)
        self.assertTrue(self.kill_switch.status().allow_new_orders)

    def test_corrupt_database_blocks_before_broker_construction(self) -> None:
        self.database.path.write_bytes(b"not SQLite")
        called = []
        report = RecoveryManager(
            self.database, self.kill_switch, risk_config_path=self.config_path,
            broker_factory=lambda: called.append(True),
        ).run()
        self.assertIn("database_invalid_or_unavailable", report.reasons)
        self.assertFalse(report.database_valid)
        self.assertEqual(called, [])
        self.assertFalse(self.kill_switch.status().allow_new_orders)

    def test_broker_account_failure_blocks_and_latches(self) -> None:
        self.baseline()
        self.broker.fail_account = True
        report = self.recover()
        self.assertIn("paper_broker_unavailable", report.reasons)
        self.assertFalse(self.kill_switch.status().allow_new_orders)

    def test_missing_local_order_at_broker_blocks_without_resubmission(self) -> None:
        self.baseline()
        self.reserve()
        report = self.recover()
        self.assertEqual(report.local_orders_checked, 1)
        self.assertEqual(report.unresolved_order_ids, ("client-1",))
        self.assertIn("unresolved_local_orders", report.reasons)
        self.assertEqual(self.database.get_order_record("client-1")["status"], "reserved")
        self.assertFalse(self.kill_switch.status().allow_new_orders)

    def test_matching_open_order_is_recognized_but_blocks_readiness(self) -> None:
        self.reserve(status="new")
        order = broker_order("client-1")
        self.broker.orders["client-1"] = order
        self.broker.open_orders = [order]
        self.baseline()
        report = self.recover()
        self.assertFalse(report.can_resume_order_evaluation)
        self.assertIn("open_orders_present", report.reasons)
        self.assertEqual(report.resolved_order_ids, ("client-1",))
        self.assertEqual(report.status_changes, ())
        self.assertEqual(self.broker.lookups, 1)
        self.assertTrue(self.kill_switch.status().allow_new_orders)

    def test_changed_status_during_downtime_requires_review(self) -> None:
        self.reserve(status="new")
        order = broker_order("client-1")
        self.broker.orders["client-1"] = order
        self.broker.open_orders = [order]
        self.baseline()
        self.broker.orders["client-1"] = broker_order("client-1", status="filled", filled_qty="1", filled_avg_price="100")
        self.broker.open_orders = []
        report = self.recover()
        self.assertIn("order_status_changed_during_downtime", report.reasons)
        self.assertEqual(report.status_changes, ("client-1: new -> filled",))
        self.assertEqual(self.database.get_order_record("client-1")["status"], "filled")
        self.assertFalse(self.kill_switch.status().allow_new_orders)

    def test_order_identity_mismatch_blocks(self) -> None:
        self.baseline()
        self.reserve()
        self.broker.orders["client-1"] = broker_order("client-1", symbol="MSFT")
        report = self.recover()
        self.assertIn("unresolved_local_orders", report.reasons)
        self.assertEqual(report.unresolved_order_ids, ("client-1",))

    def test_external_open_order_blocks(self) -> None:
        self.baseline()
        self.broker.open_orders = [broker_order("external-1", id="alpaca-external")]
        report = self.recover()
        self.assertIn("external_or_mismatched_open_orders", report.reasons)
        self.assertEqual(report.external_open_order_ids, ("alpaca-external",))
        self.assertFalse(self.kill_switch.status().allow_new_orders)

    def test_changed_holdings_block(self) -> None:
        self.baseline()
        self.broker.positions = [SimpleNamespace(
            symbol="AAPL", side="long", qty="1", avg_entry_price="100",
            current_price="100", market_value="100", unrealized_pl="0",
        )]
        self.broker.account.cash = "9900"
        self.broker.account.buying_power = "9900"
        report = self.recover()
        self.assertIn("holdings_or_open_orders_changed_during_downtime", report.reasons)
        self.assertTrue(any("position AAPL" in change for change in report.portfolio_changes))

    def test_inconsistent_accounting_blocks(self) -> None:
        self.baseline()
        self.broker.account.equity = "11000"
        report = self.recover()
        self.assertIn("incomplete_or_inconsistent_account_state", report.reasons)
        self.assertFalse(self.kill_switch.status().allow_new_orders)

    def test_closed_market_blocks_without_latching(self) -> None:
        self.baseline()
        self.broker.clock_open = False
        report = self.recover()
        self.assertIn("market_closed", report.reasons)
        self.assertIs(report.market_open, False)
        self.assertTrue(self.kill_switch.status().allow_new_orders)

    def test_stale_and_unavailable_clock_latch(self) -> None:
        self.baseline()
        self.broker.clock_offset = timedelta(minutes=-2)
        report = self.recover()
        self.assertIn("market_clock_invalid_or_stale", report.reasons)
        self.assertFalse(self.kill_switch.status().allow_new_orders)
        self.kill_switch.reset("Reviewed clock failure")
        self.broker.clock_offset = timedelta(0)
        self.broker.fail_clock = True
        self.assertIn("market_clock_unavailable", self.recover().reasons)

    def test_portfolio_reconciliation_failure_blocks(self) -> None:
        self.baseline()
        self.broker.fail_positions = True
        report = self.recover()
        self.assertIn("portfolio_reconciliation_failed", report.reasons)
        self.assertFalse(self.kill_switch.status().allow_new_orders)

    def test_lookup_limit_blocks_before_broker_construction(self) -> None:
        self.baseline()
        self.reserve("client-1")
        self.reserve("client-2")
        called = []
        report = RecoveryManager(
            self.database, self.kill_switch, risk_config_path=self.config_path,
            broker_factory=lambda: called.append(True), max_order_lookups=1,
        ).run()
        self.assertIn("too_many_unsettled_orders", report.reasons)
        self.assertEqual(called, [])
        self.assertFalse(self.kill_switch.status().allow_new_orders)

    def test_active_broker_order_missing_from_open_inventory_blocks(self) -> None:
        self.baseline()
        self.reserve(status="new")
        self.broker.orders["client-1"] = broker_order("client-1")
        report = self.recover()
        self.assertIn("broker_order_inventory_mismatch", report.reasons)
        self.assertFalse(self.kill_switch.status().allow_new_orders)

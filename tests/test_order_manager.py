"""Offline Phase 12/Section 27 tests. Every broker here is an in-memory fake."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase

from app.data.database import TradingDatabase
from app.orders import OrderIntent, OrderManager, client_order_id_for
from app.risk import KillSwitch
from app.strategy.base import Signal, SignalAction


def broker_order(intent: OrderIntent, **changes: object) -> SimpleNamespace:
    values = dict(
        id="alpaca-1", client_order_id=intent.client_order_id,
        symbol=intent.signal.symbol, side=intent.signal.action.value.lower(),
        qty=str(intent.quantity), type="limit", time_in_force="day",
        limit_price=str(intent.limit_price), extended_hours=False,
        status="new", filled_qty="0", filled_avg_price=None,
    )
    values.update(changes)
    return SimpleNamespace(**values)


class FakePaperBroker:
    def __init__(self) -> None:
        self.account = SimpleNamespace(
            id="paper-account-1", currency="USD", cash="10000",
            buying_power="10000", equity="10000", last_equity="10000",
            status="active", trading_blocked=False, account_blocked=False,
        )
        self.positions: list[SimpleNamespace] = []
        self.open_orders: list[SimpleNamespace] = []
        self.asset = SimpleNamespace(
            symbol="AAPL", asset_class="us_equity", status="active", tradable=True,
        )
        self.orders: dict[str, SimpleNamespace] = {}
        self.clock_open = True
        self.clock_offset = timedelta(0)
        self.submit_behavior = "accept"
        self.submit_calls = 0
        self.lookup_calls = 0
        self.clock_reads = 0
        self.close_on_second_clock = False
        self.on_submit = None

    def get_account(self) -> SimpleNamespace:
        return self.account

    def get_positions(self) -> list[SimpleNamespace]:
        return self.positions

    def get_open_orders(self) -> list[SimpleNamespace]:
        return self.open_orders

    def get_market_clock(self) -> SimpleNamespace:
        self.clock_reads += 1
        return SimpleNamespace(
            is_open=self.clock_open and not (self.close_on_second_clock and self.clock_reads == 2),
            timestamp=datetime.now(timezone.utc) + self.clock_offset,
        )

    def get_asset(self, symbol: str) -> SimpleNamespace:
        return self.asset

    def get_order_by_client_id(self, client_id: str) -> SimpleNamespace | None:
        self.lookup_calls += 1
        return self.orders.get(client_id)

    def submit_order(self, request: object) -> SimpleNamespace:
        if self.on_submit is not None:
            self.on_submit(request)
        self.submit_calls += 1
        order = SimpleNamespace(
            id=f"alpaca-{self.submit_calls}", client_order_id=request.client_order_id,
            symbol=request.symbol, side=request.side.value,
            qty=str(request.qty), type=request.type.value,
            time_in_force=request.time_in_force.value,
            limit_price=str(request.limit_price), extended_hours=request.extended_hours,
            status="new", filled_qty="0", filled_avg_price=None,
        )
        if self.submit_behavior == "timeout_before_accept":
            raise TimeoutError("simulated lost request")
        self.orders[request.client_order_id] = order
        if self.submit_behavior == "timeout_after_accept":
            raise TimeoutError("simulated lost response")
        return order


class OrderManagerTests(TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.database = TradingDatabase(root / "bot.sqlite3")
        self.kill_switch = KillSwitch(root / "kill.sqlite3")
        self.kill_switch.reset("Reviewed isolated fake paper account")
        self.broker = FakePaperBroker()
        self.risk_path = root / "risk_limits.json"
        self.risk_path.write_text(json.dumps({
            "approved_for_paper": True,
            "max_portfolio_exposure": 0.70,
            "max_single_position": 0.10,
            "max_risk_per_trade": 0.01,
            "max_daily_loss": 0.03,
            "max_drawdown": 0.10,
            "max_positions": 7,
            "max_snapshot_age_seconds": 300,
            "max_signal_age_seconds": 300,
            "max_sector_exposure": None,
            "max_annualized_volatility": None,
        }), encoding="utf-8")
        signal = Signal(
            "AAPL", SignalAction.BUY, 1.0, "test",
            datetime.now(timezone.utc) - timedelta(seconds=10), "test_strategy",
        )
        self.intent = OrderIntent.for_signal(signal, 5, 100.0, 100.0, stop_price=90.0)

    def manager(self, *, enabled: bool = True) -> OrderManager:
        return OrderManager(
            self.broker, self.database, self.kill_switch,
            risk_config_path=self.risk_path, enable_paper_submission=enabled,
        )

    def events(self, client_id: str) -> list[tuple[str, str | None]]:
        with closing(sqlite3.connect(self.database.path)) as connection:
            return connection.execute(
                "SELECT status, filled_quantity FROM order_events WHERE client_order_id = ? ORDER BY id",
                (client_id,),
            ).fetchall()

    def test_client_id_is_stable_across_timezone_representation_and_restarts(self) -> None:
        other_signal = replace(
            self.intent.signal,
            timestamp=self.intent.signal.timestamp.astimezone(timezone(timedelta(hours=3))),
        )
        self.assertEqual(client_order_id_for(other_signal), self.intent.client_order_id)
        self.assertEqual(OrderIntent.for_signal(other_signal, 5, 100, 100, stop_price=90).client_order_id,
                         self.intent.client_order_id)
        self.assertLessEqual(len(self.intent.client_order_id), 48)

    def test_submission_disabled_and_unapproved_config_never_touch_broker(self) -> None:
        disabled = self.manager(enabled=False).submit(self.intent)
        self.assertEqual(disabled.status, "disabled")
        self.risk_path.write_text('{"approved_for_paper": false}', encoding="utf-8")
        blocked = self.manager().submit(self.intent)
        self.assertEqual(blocked.status, "blocked")
        self.assertIn("risk_config_unapproved", blocked.reasons[0])
        self.assertEqual(self.broker.lookup_calls, 0)
        self.assertEqual(self.broker.submit_calls, 0)

    def test_different_client_id_for_same_signal_is_rejected_before_lookup(self) -> None:
        invalid = replace(self.intent, client_order_id="new-random-retry-id")
        outcome = self.manager().submit(invalid)
        self.assertEqual(outcome.status, "blocked")
        self.assertEqual(outcome.reasons, ("invalid_order_intent",))
        self.assertEqual(self.broker.lookup_calls, 0)

    def test_offline_preview_creates_no_broker_order(self) -> None:
        from app.portfolio.portfolio_manager import PortfolioManager

        portfolio = PortfolioManager(self.broker, self.database).reconcile().snapshot
        decision = self.manager().preview(
            self.intent, portfolio, self.broker.get_market_clock(), peak_equity=10000.0,
        )
        self.assertTrue(decision.approved, decision.reasons)
        self.assertEqual(decision.request.client_order_id, self.intent.client_order_id)
        self.assertEqual(self.broker.submit_calls, 0)

    def test_success_reserves_id_before_submission_and_journals_status(self) -> None:
        observed: list[dict[str, object] | None] = []
        self.broker.on_submit = lambda request: observed.append(
            self.database.get_order_record(request.client_order_id)
        )
        outcome = self.manager().submit(self.intent)
        self.assertEqual(outcome.status, "new")
        self.assertTrue(outcome.submitted)
        self.assertEqual(self.broker.submit_calls, 1)
        self.assertEqual(observed[0]["status"], "reserved")
        row = self.database.get_order_record(self.intent.client_order_id)
        self.assertEqual(row["limit_price"], "100.0")
        self.assertEqual(row["alpaca_order_id"], "alpaca-1")
        self.assertEqual([status for status, _ in self.events(self.intent.client_order_id)],
                         ["reserved", "new"])

    def test_same_id_is_not_submitted_again_after_success(self) -> None:
        manager = self.manager()
        manager.submit(self.intent)
        duplicate = manager.submit(self.intent)
        self.assertFalse(duplicate.submitted)
        self.assertEqual(duplicate.reasons, ("already_recorded_no_resubmit",))
        self.assertEqual(self.broker.submit_calls, 1)
        self.assertEqual(len(self.events(self.intent.client_order_id)), 2)

    def test_same_id_with_changed_limit_trips_identity_conflict(self) -> None:
        manager = self.manager()
        manager.submit(self.intent)
        changed = replace(self.intent, limit_price=99.0)
        result = manager.submit(changed)
        self.assertEqual(result.status, "identity_conflict")
        self.assertEqual(self.broker.submit_calls, 1)
        self.assertFalse(self.kill_switch.status().allow_new_orders)

    def test_broker_order_found_before_submission_is_recorded_without_resend(self) -> None:
        self.broker.orders[self.intent.client_order_id] = broker_order(self.intent)
        result = self.manager().submit(self.intent)
        self.assertFalse(result.submitted)
        self.assertEqual(result.status, "new")
        self.assertEqual(self.broker.submit_calls, 0)
        self.assertEqual(self.database.get_order_record(self.intent.client_order_id)["alpaca_order_id"],
                         "alpaca-1")

    def test_broker_order_with_wrong_limit_trips_without_resend(self) -> None:
        self.broker.orders[self.intent.client_order_id] = broker_order(self.intent, limit_price="99")
        result = self.manager().submit(self.intent)
        self.assertEqual(result.status, "identity_conflict")
        self.assertEqual(self.broker.submit_calls, 0)
        self.assertFalse(self.kill_switch.status().allow_new_orders)

    def test_timeout_after_accept_queries_once_and_records_broker_order(self) -> None:
        self.broker.submit_behavior = "timeout_after_accept"
        result = self.manager().submit(self.intent)
        self.assertTrue(result.submitted)
        self.assertEqual(result.status, "new")
        self.assertEqual(self.broker.submit_calls, 1)
        self.assertEqual(self.broker.lookup_calls, 2)

    def test_timeout_without_visible_order_stays_unknown_and_never_retries(self) -> None:
        self.broker.submit_behavior = "timeout_before_accept"
        manager = self.manager()
        result = manager.submit(self.intent)
        self.assertEqual(result.status, "unknown")
        self.assertFalse(result.submitted)
        self.assertFalse(self.kill_switch.status().allow_new_orders)
        self.assertEqual(self.database.get_order_record(self.intent.client_order_id)["status"], "unknown")
        manager.submit(self.intent)
        self.assertEqual(self.broker.submit_calls, 1)

    def test_unknown_order_can_later_be_reconciled_without_new_submission(self) -> None:
        self.broker.submit_behavior = "timeout_before_accept"
        manager = self.manager()
        manager.submit(self.intent)
        self.broker.orders[self.intent.client_order_id] = broker_order(self.intent)
        result = manager.refresh_status(self.intent.client_order_id)
        self.assertEqual(result.status, "new")
        self.assertEqual(self.database.get_order_record(self.intent.client_order_id)["alpaca_order_id"],
                         "alpaca-1")
        self.assertEqual(self.broker.submit_calls, 1)

    def test_partial_fill_and_cancel_are_audited(self) -> None:
        manager = self.manager()
        manager.submit(self.intent)
        order = self.broker.orders[self.intent.client_order_id]
        order.status = "partially_filled"
        order.filled_qty = "2"
        order.filled_avg_price = "99.50"
        self.assertEqual(manager.refresh_status(self.intent.client_order_id).status, "partially_filled")
        order.status = "canceled"
        self.assertEqual(manager.refresh_status(self.intent.client_order_id).status, "canceled")
        self.assertEqual(self.events(self.intent.client_order_id)[-2:],
                         [("partially_filled", "2"), ("canceled", "2")])
        self.assertEqual(self.broker.submit_calls, 1)

    def test_broker_rejection_is_audited_without_resubmission(self) -> None:
        manager = self.manager()
        manager.submit(self.intent)
        self.broker.orders[self.intent.client_order_id].status = "rejected"
        self.assertEqual(manager.refresh_status(self.intent.client_order_id).status, "rejected")
        self.assertEqual(self.database.get_order_record(self.intent.client_order_id)["status"], "rejected")
        manager.submit(self.intent)
        self.assertEqual(self.broker.submit_calls, 1)

    def test_broker_identity_change_during_refresh_trips_switch(self) -> None:
        manager = self.manager()
        manager.submit(self.intent)
        self.broker.orders[self.intent.client_order_id].limit_price = "99"
        result = manager.refresh_status(self.intent.client_order_id)
        self.assertEqual(result.status, "identity_conflict")
        self.assertFalse(self.kill_switch.status().allow_new_orders)
        self.assertEqual(self.broker.submit_calls, 1)

    def test_closed_market_and_insufficient_buying_power_block_order(self) -> None:
        self.broker.clock_open = False
        closed = self.manager().submit(self.intent)
        self.assertIn("market_closed_or_clock_invalid", closed.reasons)
        self.broker.clock_open = True
        self.broker.account.buying_power = "1"
        low_power = self.manager().submit(self.intent)
        self.assertIn("insufficient_buying_power", low_power.reasons)
        self.assertEqual(self.broker.submit_calls, 0)

    def test_market_closes_between_preview_and_submit(self) -> None:
        self.broker.close_on_second_clock = True
        result = self.manager().submit(self.intent)
        self.assertEqual(result.status, "blocked")
        self.assertIn("market_closed_or_clock_invalid", result.reasons)
        self.assertEqual(self.database.get_order_record(self.intent.client_order_id)["status"], "blocked")
        self.assertEqual(self.broker.submit_calls, 0)

    def test_existing_open_order_blocks_new_order(self) -> None:
        self.broker.open_orders = [SimpleNamespace(
            id="other-order", client_order_id="external", symbol="MSFT", side="buy",
            status="new", qty="1", notional=None, filled_qty="0",
        )]
        result = self.manager().submit(self.intent)
        self.assertIn("existing_open_orders", result.reasons)
        self.assertEqual(self.broker.submit_calls, 0)

    def test_database_reservation_is_atomic_and_cannot_be_reused(self) -> None:
        arguments = dict(
            client_order_id=self.intent.client_order_id,
            timestamp=datetime.now(timezone.utc), symbol="AAPL", side="buy",
            quantity=5, limit_price="100",
        )
        first, _ = self.database.reserve_order(**arguments)
        second, _ = TradingDatabase(self.database.path).reserve_order(**arguments)
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(self.events(self.intent.client_order_id), [("reserved", None)])

    def test_existing_database_schema_is_migrated_without_losing_orders(self) -> None:
        with closing(sqlite3.connect(self.database.path)) as connection:
            connection.execute(
                """CREATE TABLE orders (id INTEGER PRIMARY KEY, client_order_id TEXT NOT NULL UNIQUE,
                timestamp TEXT NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL,
                quantity REAL NOT NULL, order_type TEXT NOT NULL, status TEXT NOT NULL,
                alpaca_order_id TEXT UNIQUE)"""
            )
            connection.execute(
                """INSERT INTO orders (client_order_id, timestamp, symbol, side, quantity, order_type, status)
                VALUES ('old-id', '2026-01-01T00:00:00Z', 'AAPL', 'buy', 1, 'limit', 'new')"""
            )
            connection.commit()
        self.database.initialize()
        self.assertIn("limit_price", self.database.get_order_record("old-id"))
        self.assertIsNone(self.database.get_order_record("old-id")["limit_price"])

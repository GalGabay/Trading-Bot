"""Offline Phase 11 tests; broker objects are fakes and no orders are sent."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase

from app.broker.alpaca_client import AlpacaClient
from app.data.database import DataStorageError, TradingDatabase
from app.portfolio.portfolio_manager import PortfolioManager, PortfolioValidationError


def account(**changes):
    values = dict(id="paper-account-1", currency="USD", cash="9000", buying_power="9000",
                  equity="10000", last_equity="10000")
    values.update(changes)
    return SimpleNamespace(**values)


def position(**changes):
    values = dict(symbol="AAPL", side="long", qty="10", avg_entry_price="90",
                  current_price="100", market_value="1000", unrealized_pl="100")
    values.update(changes)
    return SimpleNamespace(**values)


def order(**changes):
    values = dict(id="order-1", client_order_id="client-1", symbol="MSFT", side="buy",
                  status="new", qty="2", notional=None, filled_qty="0")
    values.update(changes)
    return SimpleNamespace(**values)


class FakeBroker:
    def __init__(self, *, account_value=None, positions=None, orders=None):
        self.account_value = account_value if account_value is not None else account()
        self.positions = positions if positions is not None else [position()]
        self.orders = orders if orders is not None else [order()]
        self.fail_orders = False

    def get_account(self):
        return self.account_value

    def get_positions(self):
        return self.positions

    def get_open_orders(self):
        if self.fail_orders:
            raise RuntimeError("simulated broker outage")
        return self.orders


class PortfolioManagerTests(TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "portfolio.sqlite3"
        self.database = TradingDatabase(self.path)
        self.broker = FakeBroker()
        self.manager = PortfolioManager(self.broker, self.database)

    def _rows(self, table: str):
        with closing(sqlite3.connect(self.path)) as connection:
            return connection.execute(f"SELECT * FROM {table}").fetchall()

    def test_valid_snapshot_calculates_exposure_and_persists_current_state(self) -> None:
        result = self.manager.reconcile()
        snapshot = result.snapshot
        self.assertEqual(result.changes, ())
        self.assertEqual(snapshot.cash, Decimal("9000"))
        self.assertEqual(snapshot.buying_power, Decimal("9000"))
        self.assertEqual(snapshot.equity, Decimal("10000"))
        self.assertEqual(snapshot.gross_exposure, Decimal("0.1"))
        self.assertEqual(snapshot.net_exposure, Decimal("0.1"))
        self.assertEqual(snapshot.unrealized_pl, Decimal("100"))
        self.assertIsNone(snapshot.realized_pl)
        self.assertTrue(snapshot.accounting_consistent)
        self.assertEqual(self.database.get_latest_portfolio_state()["positions"][0]["symbol"], "AAPL")
        self.assertEqual(len(self._rows("portfolio_snapshots")), 1)
        self.assertEqual(len(self._rows("broker_current_positions")), 1)
        self.assertEqual(len(self._rows("broker_open_orders")), 1)

    def test_reconciliation_replaces_positions_and_open_orders(self) -> None:
        self.manager.reconcile()
        self.broker.account_value = account(cash="10000", buying_power="10000")
        self.broker.positions = []
        self.broker.orders = []
        second = self.manager.reconcile()
        self.assertEqual(second.snapshot.gross_exposure, Decimal(0))
        self.assertEqual(second.snapshot.unrealized_pl, Decimal(0))
        self.assertTrue(any("position AAPL" in change for change in second.changes))
        self.assertTrue(any("open order order-1" in change for change in second.changes))
        self.assertEqual(len(self._rows("portfolio_snapshots")), 2)
        self.assertEqual(len(self._rows("broker_current_positions")), 0)
        self.assertEqual(len(self._rows("broker_open_orders")), 0)

    def test_fractional_and_short_positions_use_signed_value(self) -> None:
        self.broker.positions = [position(side="short", qty="-2.5", market_value="-250",
                                          current_price="100", unrealized_pl="-20")]
        self.broker.account_value = account(cash="10250", buying_power="10250")
        self.broker.orders = []
        snapshot = self.manager.reconcile().snapshot
        self.assertEqual(snapshot.positions[0].quantity, Decimal("2.5"))
        self.assertEqual(snapshot.positions[0].market_value, Decimal("-250"))
        self.assertEqual(snapshot.gross_exposure, Decimal("0.025"))
        self.assertEqual(snapshot.net_exposure, Decimal("-0.025"))
        self.assertTrue(snapshot.accounting_consistent)
        self.assertEqual(self._rows("positions")[0][3], -2.5)

    def test_notional_order_and_missing_unrealized_pl_remain_explicit(self) -> None:
        self.broker.positions = [position(unrealized_pl=None)]
        self.broker.orders = [order(qty=None, notional="50", filled_qty="0.2")]
        snapshot = self.manager.reconcile().snapshot
        self.assertIsNone(snapshot.unrealized_pl)
        self.assertIsNone(snapshot.open_orders[0].quantity)
        self.assertEqual(snapshot.open_orders[0].notional, Decimal("50"))

    def test_accounting_gap_is_flagged(self) -> None:
        self.broker.account_value = account(equity="11000")
        snapshot = self.manager.reconcile().snapshot
        self.assertFalse(snapshot.accounting_consistent)
        self.assertEqual(snapshot.valuation_gap, Decimal("1000"))

    def test_invalid_broker_values_and_duplicate_positions_do_not_write(self) -> None:
        cases = [
            [position(current_price="0")],
            [position(qty="NaN")],
            [position(), position(symbol="aapl")],
            [position(side="unknown")],
        ]
        for positions in cases:
            with self.subTest(positions=positions):
                self.broker.positions = positions
                with self.assertRaises(PortfolioValidationError):
                    self.manager.reconcile()
        self.assertIsNone(self.database.get_latest_portfolio_state())

    def test_invalid_and_duplicate_orders_do_not_write(self) -> None:
        cases = [[order(qty=None, notional=None)], [order(), order(id="order-1")],
                 [order(filled_qty="-1")]]
        for orders in cases:
            with self.subTest(orders=orders):
                self.broker.orders = orders
                with self.assertRaises(PortfolioValidationError):
                    self.manager.reconcile()
        self.assertIsNone(self.database.get_latest_portfolio_state())

    def test_broker_failure_leaves_previous_state_untouched(self) -> None:
        self.manager.reconcile()
        self.broker.fail_orders = True
        with self.assertRaisesRegex(RuntimeError, "outage"):
            self.manager.reconcile()
        self.assertEqual(len(self._rows("portfolio_snapshots")), 1)
        self.assertEqual(len(self._rows("broker_open_orders")), 1)

    def test_different_account_cannot_overwrite_database(self) -> None:
        self.manager.reconcile()
        self.broker.account_value = account(id="another-paper-account")
        with self.assertRaises(DataStorageError):
            self.manager.reconcile()
        self.assertEqual(len(self._rows("portfolio_snapshots")), 1)

    def test_full_open_order_page_is_rejected(self) -> None:
        class Trading:
            def get_orders(self, filter):
                return [order(id=f"order-{index}") for index in range(500)]

        client = AlpacaClient.__new__(AlpacaClient)
        client._trading = Trading()
        with self.assertRaisesRegex(RuntimeError, "500-order limit"):
            client.get_open_orders()

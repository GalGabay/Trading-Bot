"""Offline synthetic calendar/lifecycle/accounting checks; no broker calls."""

from dataclasses import replace
from datetime import timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import pandas as pd

from app.data.market_calendar import TradingSession
from app.data.market_data import CANONICAL_CANDLE_COLUMNS
from backtesting.daily_research import pack
from backtesting.engine import BacktestConfig
from backtesting.portfolio_engine import PortfolioBacktestEngine, ResearchPortfolioLimits, summarize_portfolio
from backtesting.universe import CashOutcome, HistoricalUniverse, ListingPeriod, UniverseDataError
from tests.test_portfolio_backtesting import ScriptedDailyStrategy
from app.strategy.base import SignalAction


class UniverseFixture(TestCase):
    def setUp(self):
        # Deliberately synthetic weekdays, not a historical exchange calendar.
        local = pd.bdate_range("2021-01-04", periods=410, tz="America/New_York")
        self.dates = local.tz_convert("UTC")
        self.sessions = [TradingSession(pd.Timestamp(f"{t.date()} 09:30", tz="America/New_York").tz_convert("UTC"),
                                        pd.Timestamp(f"{t.date()} 16:00", tz="America/New_York").tz_convert("UTC")) for t in local]

    def day(self, index):
        return self.dates[index].date().isoformat()

    def known(self, index):
        return (self.dates[index].to_pydatetime() - timedelta(days=1)).isoformat()

    def listing(self, *, key="ID-A", symbol="AAA", start=0, end=None):
        return ListingPeriod(key, symbol, "NASDAQ", "common_stock", self.day(start),
                             None if end is None else self.day(end), self.known(start),
                             None if end is None else self.known(end), "synthetic evidence")

    def universe(self, *, n=208, listings=None, cash=None, **kwargs):
        scope = kwargs.pop("action_scope", "event_free_except_terminal_cash")
        return HistoricalUniverse(sessions=self.sessions[:n], listings=listings or [self.listing()],
                                  cash_outcomes=cash, price_basis="raw", action_scope=scope, **kwargs)

    def bars(self, *, start=0, end=208, symbol="AAA", price=100):
        return pd.DataFrame({"timestamp": self.dates[start:end], "symbol": symbol,
                             "open": price, "high": price, "low": price, "close": price, "volume": 1000})

    def engine(self, actions=None, **kwargs):
        plan = {(key, self.day(index)): side for (key, index), side in (actions or {("ID-A", 199): SignalAction.BUY}).items()}
        return PortfolioBacktestEngine(
            ScriptedDailyStrategy(plan), costs=BacktestConfig(initial_cash=10000, slippage_bps=0, spread_bps=0),
            limits=ResearchPortfolioLimits(max_daily_loss=.99, max_drawdown=.99), **kwargs,
        )

    def run_case(self, universe=None, bars=None, engine=None):
        universe = universe or self.universe()
        return (engine or self.engine()).run({"ID-A": self.bars() if bars is None else bars},
                                            trade_start=self.dates[0], trade_end=self.dates[len(universe.sessions)], universe=universe)


class HistoricalUniverseTests(UniverseFixture):
    def test_example_manifest_loads_and_has_a_hash(self):
        value = HistoricalUniverse.load(Path("docs/examples/historical_universe.example.json"))
        self.assertEqual(len(value.instrument_ids), 2)
        self.assertEqual(len(value.manifest_sha256), 64)
        self.assertFalse(value.metadata()["market_wide_performance_ready"])

    def test_version_two_manifest_loads_explicit_actions(self):
        value = json.loads(Path("docs/examples/historical_universe.example.json").read_text())
        value.update(schema_version=2, action_scope="explicit_splits_and_ordinary_cash_dividends",
                     splits=[{"event_id": "split", "instrument_id": "EXAMPLE-001", "effective_session": "2023-01-05",
                              "new_shares": 2, "old_shares": 1, "known_at": "2023-01-04T12:00:00Z", "source": "synthetic"}],
                     dividends=[])
        with TemporaryDirectory() as directory:
            path = Path(directory) / "v2.json"
            path.write_text(json.dumps(value))
            result = HistoricalUniverse.load(path)
            self.assertEqual(result.splits[0].ratio, 2)
            self.assertEqual(result.metadata()["schema_version"], 2)

    def test_boolean_manifest_version_is_not_integer_version(self):
        value = json.loads(Path("docs/examples/historical_universe.example.json").read_text())
        value["schema_version"] = True
        with TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(UniverseDataError, "manifest"):
                HistoricalUniverse.load(path)

    def test_empty_pre_ipo_history_can_remain_in_the_universe(self):
        result = self.run_case(self.universe(listings=[self.listing(start=209)]), pd.DataFrame(columns=CANONICAL_CANDLE_COLUMNS))
        self.assertFalse(result.fills)
        self.assertEqual(summarize_portfolio(result)["final_equity"], 10000)

    def test_later_ipo_uses_own_200_session_warmup(self):
        universe = self.universe(n=210, listings=[self.listing(start=5)])
        result = self.run_case(universe, self.bars(start=5, end=210),
                               self.engine({("ID-A", 199): SignalAction.BUY, ("ID-A", 204): SignalAction.BUY}))
        self.assertEqual([f.timestamp for f in result.fills], [self.dates[205]])

    def test_ticker_change_preserves_holding_and_cost_basis(self):
        universe = self.universe(listings=[self.listing(end=201), self.listing(symbol="BBB", start=201)])
        data = self.bars()
        data.loc[201:, "symbol"] = "BBB"
        result = self.run_case(universe, data)
        self.assertEqual(result.final_positions, {"ID-A": 10})
        self.assertEqual(summarize_portfolio(result)["final_equity"], 10000)
        self.assertEqual(len(result.fills), 1)

    def test_unknown_in_lifetime_gap_is_rejected(self):
        with self.assertRaisesRegex(UniverseDataError, "unexplained in-lifetime"):
            self.run_case(bars=self.bars().drop(index=90))

    def test_wrong_dated_alias_is_rejected(self):
        data = self.bars()
        data.loc[100, "symbol"] = "BBB"
        with self.assertRaisesRegex(UniverseDataError, "ticker"):
            self.run_case(bars=data)

    def test_duplicate_observations_across_aliases_are_rejected(self):
        data = self.bars()
        duplicate = data.iloc[[100]].copy()
        duplicate["symbol"] = "BBB"
        with self.assertRaisesRegex(UniverseDataError, "duplicate"):
            self.run_case(bars=pd.concat([data, duplicate]))

    def test_unexplained_terminal_outcome_blocks_held_position(self):
        with self.assertRaisesRegex(UniverseDataError, "held instruments"):
            self.run_case(self.universe(listings=[self.listing(end=202)]), self.bars(end=202))

    def test_unavailable_scheduled_buy_expires(self):
        result = self.run_case(self.universe(listings=[self.listing(end=200)]), self.bars(end=200))
        self.assertFalse(result.fills)
        self.assertTrue(any("expired BUY" in event for event in result.events))

    def test_zero_volume_held_session_is_not_a_fill_or_stale_mark(self):
        data = self.bars()
        data.loc[201, "volume"] = 0
        with self.assertRaisesRegex(UniverseDataError, "positive-volume"):
            self.run_case(bars=data)

    def test_zero_volume_restarts_unheld_warmup(self):
        data = self.bars(end=305)
        data.loc[100, "volume"] = 0
        result = self.run_case(self.universe(n=305), data,
                               self.engine({("ID-A", 205): SignalAction.BUY, ("ID-A", 300): SignalAction.BUY}))
        self.assertEqual([f.timestamp for f in result.fills], [self.dates[301]])

    def test_empty_listed_instrument_is_not_dropped(self):
        with self.assertRaisesRegex(UniverseDataError, "empty history"):
            self.run_case(bars=pd.DataFrame(columns=CANONICAL_CANDLE_COLUMNS))

    def test_undeclared_instrument_omission_rejected(self):
        universe = self.universe(listings=[self.listing(), self.listing(key="ID-B", symbol="BBB")])
        with self.assertRaisesRegex(UniverseDataError, "every declared"):
            self.run_case(universe)

    def test_overlapping_listing_intervals_rejected(self):
        with self.assertRaisesRegex(UniverseDataError, "overlapping"):
            self.universe(listings=[self.listing(), self.listing(symbol="BBB", start=200)])

    def test_alias_cannot_belong_to_two_instruments_at_once(self):
        with self.assertRaisesRegex(UniverseDataError, "ambiguous"):
            self.universe(listings=[self.listing(), self.listing(key="ID-B")])

    def test_late_listing_evidence_rejected(self):
        with self.assertRaisesRegex(UniverseDataError, "not known"):
            self.universe(listings=[replace(self.listing(), start_known_at=self.sessions[0].closes_at.isoformat())])

    def test_late_end_evidence_rejected(self):
        with self.assertRaisesRegex(UniverseDataError, "not known"):
            self.universe(listings=[replace(self.listing(end=202), end_known_at=self.sessions[202].closes_at.isoformat())])

    def test_naive_evidence_rejected(self):
        with self.assertRaisesRegex(UniverseDataError, "timezone"):
            replace(self.listing(), start_known_at="2021-01-01")

    def test_adjusted_price_declaration_rejected(self):
        with self.assertRaisesRegex(UniverseDataError, "raw"):
            HistoricalUniverse(sessions=self.sessions[:2], listings=[self.listing()], price_basis="all", action_scope="event_free_except_terminal_cash")

    def test_unclassified_security_rejected(self):
        with self.assertRaisesRegex(UniverseDataError, "classified"):
            replace(self.listing(), security_type="unknown")

    def test_duplicate_calendar_rejected(self):
        with self.assertRaisesRegex(UniverseDataError, "unique"):
            HistoricalUniverse(sessions=[self.sessions[0]] * 2, listings=[self.listing()], price_basis="raw", action_scope="event_free_except_terminal_cash")

    def test_canonical_rows_are_not_filled_or_mutated(self):
        source = self.bars(start=20)
        original = source.copy(deep=True)
        value = self.universe(listings=[self.listing(start=20)]).prepare("ID-A", source)
        pd.testing.assert_frame_equal(source, original)
        self.assertEqual(list(value.index), list(range(20, 208)))
        self.assertEqual(len(value), len(source))


class TerminalCashTests(UniverseFixture):
    def outcome(self, amount=110):
        return CashOutcome("cash-1", "ID-A", self.day(202), amount, self.known(202), "synthetic payment evidence")

    def test_payment_reconciles_without_a_fake_sell(self):
        result = self.run_case(self.universe(listings=[self.listing(end=202)], cash=[self.outcome()]), self.bars(end=202))
        metrics = summarize_portfolio(result)
        self.assertEqual(metrics["final_equity"], 10100)
        self.assertEqual(metrics["cash_settlement_realized_pnl"], 100)
        self.assertEqual(metrics["completed_trades"], 0)
        self.assertEqual(len(result.fills), 1)
        self.assertEqual(len(pack(result)["cash_settlements"]), 1)

    def test_zero_recovery_requires_explicit_event_and_accounts_for_loss(self):
        result = self.run_case(self.universe(listings=[self.listing(end=202)], cash=[self.outcome(0)]), self.bars(end=202))
        self.assertEqual(summarize_portfolio(result)["final_equity"], 9000)

    def test_no_holding_no_payment_credit(self):
        engine = self.engine({("ID-A", 0): SignalAction.HOLD})
        result = self.run_case(self.universe(listings=[self.listing(end=202)], cash=[self.outcome()]), self.bars(end=202), engine)
        self.assertFalse(result.cash_settlements)
        self.assertEqual(result.equity_curve[-1].cash, 10000)

    def test_duplicate_terminal_events_rejected(self):
        with self.assertRaisesRegex(UniverseDataError, "Duplicate"):
            self.universe(listings=[self.listing(end=202)], cash=[self.outcome(), self.outcome()])

    def test_late_payment_knowledge_rejected(self):
        with self.assertRaisesRegex(UniverseDataError, "not known"):
            self.universe(listings=[self.listing(end=202)], cash=[replace(self.outcome(), known_at=self.sessions[202].closes_at.isoformat())])

    def test_negative_or_nonfinite_payment_rejected(self):
        for amount in (-1, float("nan"), float("inf"), True):
            with self.subTest(amount=amount), self.assertRaises(UniverseDataError):
                self.outcome(amount)

    def test_payment_cannot_leave_a_live_identity(self):
        with self.assertRaisesRegex(UniverseDataError, "ended identity"):
            self.universe(cash=[self.outcome()])

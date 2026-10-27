"""Offline synthetic integration checks; no real holdings or broker calls.

Synthetic sessions are explicit weekdays, not a claim about historical exchange
holidays. Evidence strings/approvals below are fixtures, never source reviews.
"""

from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from app.strategy.base import SignalAction
from backtesting.claim_accounting import AccountingError, OwnershipEvent, ShareLeg
from backtesting.daily_research import pack
from backtesting.engine import BacktestConfig
from backtesting.holding_policy import HoldingPolicy
from backtesting.ownership_adapter import CashInstruction, OwnershipSchedule, ReviewedOwnership, replay_accounting
from backtesting.portfolio_engine import PortfolioBacktestEngine, ResearchPortfolioLimits, summarize_portfolio
from backtesting.protective_exits import ProtectiveExitConfig
from backtesting.risk_diagnostics import daily_risk_envelope
from backtesting.universe import OWNERSHIP_SCOPE, CashDividend, CashOutcome, HistoricalUniverse, SplitAction, UniverseDataError
from tests.test_portfolio_backtesting import ScriptedDailyStrategy
from tests.test_universe import UniverseFixture


class OwnershipFixture(UniverseFixture):
    def evidence(self, *, kind="spinoff", at=201, cash="0", ratio="1", child="ID-B"):
        shares = () if ratio is None else (ShareLeg(child, ratio),)
        event = OwnershipEvent("EVENT", "ID-A", kind, self.sessions[at].opens_at, self.known(at),
                               "SYNTHETIC TERMS ONLY", cash, shares, True)
        return ReviewedOwnership(event, "prior_close_holders_confirmed", "SYNTHETIC ENTITLEMENT ONLY",
                                 self.known(at), "SYNTHETIC DELIVERY ONLY" if shares else None,
                                 self.sessions[at].opens_at.isoformat() if shares else None,
                                 self.known(at) if shares else None, True)

    def instruction(self, claim, *, at=204, amount="outstanding_claim", name="PAY", **kwargs):
        return CashInstruction(name, claim, self.sessions[at].opens_at.isoformat(), self.known(at),
                               amount, "SYNTHETIC CASH CONVENTION ONLY", **kwargs)

    def setup_case(self, *, kind="spinoff", ratio="1", cash="0", n=210, entries=None,
                   payments=(), fixings=(), splits=(), dividends=(), outcomes=(), existing_child=False):
        reviewed = self.evidence(kind=kind, cash=cash, ratio=ratio)
        listings = [self.listing(end=201 if kind == "exchange" else None)]
        frames = {"ID-A": self.bars(end=201 if kind == "exchange" else n).copy()}
        frames["ID-A"]["high"], frames["ID-A"]["low"] = 101, 99
        if kind != "exchange":
            frames["ID-A"].loc[201:, ["open", "close", "high", "low"]] = [70, 70, 71, 69]
        if ratio is not None:
            start = 0 if existing_child else 201
            listings.append(self.listing(key="ID-B", symbol="BBB", start=start))
            frames["ID-B"] = self.bars(start=start, end=n, symbol="BBB", price=30).copy()
            frames["ID-B"].index = range(start, n)
            frames["ID-B"]["high"], frames["ID-B"]["low"] = 30.5, 29.5
        universe = self.universe(n=n, listings=listings, action_scope=OWNERSHIP_SCOPE,
                                 splits=list(splits), dividends=list(dividends), cash=list(outcomes))
        schedule = OwnershipSchedule(entry_instrument_ids=entries or ["ID-A"], events=[reviewed],
                                     payments=payments, fixings=fixings)
        for frame in frames.values():
            frame[["open", "high", "low", "close"]] = frame[["open", "high", "low", "close"]].astype(float)
        return universe, schedule, frames

    def run_ownership(self, universe, schedule, frames, *, actions=None, protection=None, costs=None, limits=None, **kwargs):
        actions = actions if actions is not None else {("ID-A", 199): SignalAction.BUY}
        strategy = ScriptedDailyStrategy({(key, self.day(i)): side for (key, i), side in actions.items()})
        engine = PortfolioBacktestEngine(strategy,
            costs=costs or BacktestConfig(initial_cash=10000, slippage_bps=0, spread_bps=0),
            limits=limits or ResearchPortfolioLimits(max_daily_loss=.99, max_drawdown=.99),
            protection=protection, record_decisions=True, **kwargs)
        result = engine.run(frames, trade_start=self.dates[0], trade_end=self.dates[len(universe.sessions)],
                            universe=universe, ownership=schedule)
        return result

    def assert_reconciles(self, result, frames):
        packed = pack(result)
        packed = json.loads(json.dumps(packed, allow_nan=False))
        risk = daily_risk_envelope(packed, frames)
        self.assertTrue(risk["ledger_reconciled"])
        self.assertTrue(risk["external_source_prices_verified"])
        self.assertFalse(risk["intraday_equity_observed"])
        self.assertEqual(risk["daily_envelopes"], result.ownership_accounting["daily_risk_envelopes"])
        self.assertTrue(packed["metrics"]["ownership_accounting_reconciled"])
        self.assertAlmostEqual(packed["metrics"]["realized_pnl"] + packed["metrics"]["marked_unrealized_pnl"],
                               packed["metrics"]["final_equity"] - packed["metrics"]["initial_cash"])
        return packed


class OwnershipExecutionTests(OwnershipFixture):
    def test_spinoff_keeps_parent_and_separate_child_with_conserved_basis(self):
        u, s, frames = self.setup_case()
        result = self.run_ownership(u, s, frames)
        self.assertEqual(result.final_positions, {"ID-A": 10, "ID-B": 10})
        self.assertEqual(len(result.fills), 1)
        self.assertEqual(result.equity_curve[-1].equity, 10000)
        lots = result.ownership_accounting["marks"][-1]["lots"]
        self.assertEqual({lot["instrument_id"]: Fraction(lot["basis"]) for lot in lots}, {"ID-A": 700, "ID-B": 300})
        self.assert_reconciles(result, frames)

    def test_mixed_exchange_records_cash_and_exact_fraction(self):
        u, s, frames = self.setup_case(kind="exchange", cash="30", ratio="0.8378")
        result = self.run_ownership(u, s, frames)
        self.assertEqual(result.final_positions, {"ID-B": 8})
        point = result.equity_curve[-1]
        self.assertEqual(point.cash, 9000)
        self.assertEqual(point.ownership_cash_receivable, 300)
        self.assertAlmostEqual(point.fractional_claim_value, .378 * 30)
        claims = result.ownership_accounting["marks"][-1]["claims"]
        self.assertEqual(next(Fraction(c["units"]) for c in claims if c["kind"] == "fractional_shares"), Fraction("0.378"))
        packed = self.assert_reconciles(result, frames)
        self.assertIsNone(packed["metrics"]["hypothetical_liquidated_return"])
        self.assertTrue(packed["metrics"]["claims_not_liquidated"])

    def test_unpaid_cash_right_has_no_quote_after_ended_parent(self):
        u, s, frames = self.setup_case(kind="exchange", cash="42", ratio=None)
        result = self.run_ownership(u, s, frames)
        self.assertEqual(result.final_positions, {})
        self.assertEqual(result.equity_curve[-1].cash, 9000)
        self.assertEqual(result.equity_curve[-1].equity, 9420)
        self.assertEqual(result.equity_curve[-1].ownership_cash_receivable, 420)
        self.assertEqual(summarize_portfolio(result)["completed_trades"], 0)
        self.assert_reconciles(result, frames)

    def test_cash_credit_occurs_only_at_explicit_open(self):
        payment = self.instruction("action:EVENT:0")
        u, s, frames = self.setup_case(kind="exchange", cash="42", ratio=None, payments=[payment])
        result = self.run_ownership(u, s, frames)
        self.assertEqual(result.equity_curve[203].cash, 9000)
        self.assertEqual(result.equity_curve[204].cash, 9420)
        self.assertEqual(result.equity_curve[-1].ownership_cash_receivable, 0)
        self.assert_reconciles(result, frames)

    def test_cash_right_cannot_fund_buy_before_credit(self):
        payment = self.instruction("action:EVENT:0")
        u, s, frames = self.setup_case(kind="exchange", cash="42", ratio=None, payments=[payment])
        u = self.universe(n=210, action_scope=OWNERSHIP_SCOPE,
                          listings=[self.listing(end=201), self.listing(key="ID-C", symbol="CCC")])
        frames["ID-C"] = self.bars(end=210, symbol="CCC")
        s = OwnershipSchedule(entry_instrument_ids=["ID-A", "ID-C"], events=s.events, payments=s.payments)
        result = self.run_ownership(u, s, frames,
            costs=BacktestConfig(initial_cash=1000, position_fraction=1, slippage_bps=0, spread_bps=0),
            limits=ResearchPortfolioLimits(max_portfolio_exposure=1, max_single_position=1, max_daily_loss=.99, max_drawdown=.99),
            actions={("ID-A", 199): SignalAction.BUY, ("ID-C", 201): SignalAction.BUY, ("ID-C", 203): SignalAction.BUY})
        buys = [f for f in result.fills if f.symbol == "ID-C"]
        self.assertEqual([(f.timestamp, f.quantity) for f in buys], [(self.dates[204], 4)])
        self.assert_reconciles(result, frames)

    def test_fraction_survives_whole_position_sale(self):
        u, s, frames = self.setup_case(kind="exchange", cash="30", ratio="0.8378")
        result = self.run_ownership(u, s, frames, actions={("ID-A", 199): SignalAction.BUY, ("ID-B", 202): SignalAction.SELL})
        self.assertEqual(result.final_positions, {})
        self.assertGreater(result.equity_curve[-1].fractional_claim_value, 0)
        self.assertEqual(result.equity_curve[-1].position_count, 1)
        packed = self.assert_reconciles(result, frames)
        self.assertEqual(packed["metrics"]["completed_trades"], 1)

    def test_per_unit_fraction_fix_and_later_payment(self):
        fixing = self.instruction("action:EVENT:1", at=203, name="FIX", amount="31", amount_basis="per_fractional_share")
        payment = self.instruction("action:EVENT:1", at=205)
        u, s, frames = self.setup_case(kind="exchange", cash="30", ratio="0.8378", fixings=[fixing], payments=[payment])
        result = self.run_ownership(u, s, frames)
        self.assertAlmostEqual(result.equity_curve[202].fractional_claim_value, .378 * 30)
        self.assertEqual(result.equity_curve[203].fractional_claim_value, 0)
        self.assertEqual(result.equity_curve[204].cash, 9000)
        self.assertAlmostEqual(result.equity_curve[205].cash, 9000 + .378 * 31)
        self.assert_reconciles(result, frames)

    def test_holder_specific_fraction_payout_rejects_other_quantity(self):
        fixing = self.instruction("action:EVENT:1", at=203, name="FIX", amount="10", expected_fractional_units="0.5")
        u, s, frames = self.setup_case(kind="exchange", cash="30", ratio="0.8378", fixings=[fixing])
        with self.assertRaisesRegex(UniverseDataError, "eligible units"):
            self.run_ownership(u, s, frames)

    def test_existing_destination_lot_is_not_overwritten(self):
        u, s, frames = self.setup_case(existing_child=True, entries=["ID-A", "ID-B"])
        result = self.run_ownership(u, s, frames, actions={("ID-A", 199): SignalAction.BUY, ("ID-B", 199): SignalAction.BUY})
        self.assertEqual(result.final_positions, {"ID-A": 10, "ID-B": 43})
        self.assertEqual(len([lot for lot in result.ownership_accounting["marks"][-1]["lots"] if lot["instrument_id"] == "ID-B"]), 2)
        self.assert_reconciles(result, frames)

    def test_inherited_stops_rebased_using_open_values(self):
        u, s, frames = self.setup_case()
        result = self.run_ownership(u, s, frames, protection=ProtectiveExitConfig(trailing=False))
        self.assertAlmostEqual(result.final_stops["ID-A"], 70 * .96)
        self.assertAlmostEqual(result.final_stops["ID-B"], 30 * .96)
        self.assert_reconciles(result, frames)

    def test_inherited_intraday_stop_is_in_risk_bounds_and_ledger(self):
        u, s, frames = self.setup_case()
        frames["ID-B"].loc[201, "low"] = 28
        result = self.run_ownership(u, s, frames, protection=ProtectiveExitConfig(trailing=False))
        exits = [f for f in result.fills if f.side == SignalAction.SELL]
        self.assertEqual([(f.symbol, f.timestamp) for f in exits], [("ID-B", self.dates[201])])
        self.assertAlmostEqual(exits[0].fill_price, 28.8)
        self.assert_reconciles(result, frames)

    def test_inherited_gap_floor_exits_use_open_not_obsolete_stop(self):
        u, s, frames = self.setup_case()
        frames["ID-A"].loc[201:, ["open", "close", "high", "low"]] = [40, 40, 41, 39]
        result = self.run_ownership(u, s, frames, protection=ProtectiveExitConfig(trailing=False))
        sells = [f for f in result.fills if f.side == SignalAction.SELL]
        self.assertEqual(len(sells), 2)
        self.assertTrue(all(f.signal_reason.startswith("PROTECTIVE_STOP_GAP_OPEN") for f in sells))
        self.assertEqual(result.final_positions, {})
        self.assertEqual(result.equity_curve[-1].equity, 9700)
        self.assert_reconciles(result, frames)

    def test_stop_equal_to_event_open_is_accounted_as_opening_fill(self):
        u, s, frames = self.setup_case()
        frames["ID-A"].loc[201:, ["open", "close", "high", "low"]] = [66, 66, 67, 65]
        result = self.run_ownership(u, s, frames, protection=ProtectiveExitConfig(trailing=False))
        sells = [f for f in result.fills if f.side == SignalAction.SELL]
        self.assertEqual(len(sells), 2)
        self.assertTrue(all(f.signal_reason.startswith("PROTECTIVE_STOP_TOUCH") for f in sells))
        self.assertTrue(all(d["phase"] == "open" for d in result.ownership_accounting["fill_details"]))
        self.assert_reconciles(result, frames)

    def test_existing_destination_stop_is_not_loosened(self):
        u, s, frames = self.setup_case(existing_child=True, entries=["ID-A", "ID-B"])
        result = self.run_ownership(u, s, frames, protection=ProtectiveExitConfig(trailing=False),
                                    actions={("ID-A", 199): SignalAction.BUY, ("ID-B", 199): SignalAction.BUY})
        self.assertGreaterEqual(result.final_stops["ID-B"], 28)
        self.assert_reconciles(result, frames)

    def test_queued_parent_sell_is_canceled_at_event(self):
        u, s, frames = self.setup_case()
        result = self.run_ownership(u, s, frames, actions={("ID-A", 199): SignalAction.BUY, ("ID-A", 200): SignalAction.SELL})
        self.assertEqual(len(result.fills), 1)
        self.assertTrue(any("queued orders canceled" in event for event in result.events))
        self.assert_reconciles(result, frames)

    def test_queued_destination_buy_is_canceled_instead_of_pyramiding(self):
        u, s, frames = self.setup_case(existing_child=True, entries=["ID-A", "ID-B"])
        result = self.run_ownership(u, s, frames, actions={("ID-A", 199): SignalAction.BUY, ("ID-B", 200): SignalAction.BUY})
        self.assertEqual(len(result.fills), 1)
        self.assertEqual(result.final_positions["ID-B"], 10)
        self.assert_reconciles(result, frames)

    def test_commissions_spread_and_stop_slippage_reconcile(self):
        u, s, frames = self.setup_case()
        frames["ID-B"].loc[201, "low"] = 28.79
        result = self.run_ownership(u, s, frames,
            protection=ProtectiveExitConfig(trailing=False, extra_stop_slippage_bps=5),
            costs=BacktestConfig(initial_cash=10000, slippage_bps=2, spread_bps=4, commission_per_order=.25))
        exits = [f for f in result.fills if f.side == SignalAction.SELL]
        self.assertEqual(len(exits), 1)
        self.assertLess(exits[0].fill_price, 28.8)
        self.assert_reconciles(result, frames)

    def test_sources_are_not_mutated_during_simulation_or_reconciliation(self):
        u, s, frames = self.setup_case()
        originals = {key: frame.copy(deep=True) for key, frame in frames.items()}
        self.assert_reconciles(self.run_ownership(u, s, frames), frames)
        for key in frames:
            pd.testing.assert_frame_equal(frames[key], originals[key])

    def test_explicit_zero_outcome_resolves_inherited_child(self):
        u, s, frames = self.setup_case()
        outcome = CashOutcome("ZERO", "ID-B", self.day(205), 0, self.known(205), "SYNTHETIC CONFIRMED ZERO")
        u = self.universe(n=210, action_scope=OWNERSHIP_SCOPE, cash=[outcome],
                         listings=[self.listing(), self.listing(key="ID-B", symbol="BBB", start=201, end=205)])
        frames["ID-B"] = frames["ID-B"].loc[:204].copy()
        result = self.run_ownership(u, s, frames)
        self.assertEqual(result.final_positions, {"ID-A": 10})
        self.assertEqual(result.equity_curve[-1].equity, 9700)
        self.assertEqual(summarize_portfolio(result)["completed_trades"], 0)
        self.assert_reconciles(result, frames)

    def test_inherited_holding_review_keeps_original_age(self):
        u, s, frames = self.setup_case()
        result = self.run_ownership(u, s, frames, holding_policy=HoldingPolicy(mode="maximum", first_review=3))
        reviews = [r for r in result.holding_reviews if r["timestamp"] == self.dates[202].isoformat()]
        self.assertEqual({r["symbol"]: r["age_sessions"] for r in reviews}, {"ID-A": 3, "ID-B": 3})
        self.assertEqual(result.final_positions, {})
        self.assert_reconciles(result, frames)

    def test_parent_and_child_features_restart_without_resetting_holding_age(self):
        u, s, frames = self.setup_case(entries=["ID-A", "ID-B"])
        result = self.run_ownership(u, s, frames, actions={("ID-A", 199): SignalAction.BUY, ("ID-B", 202): SignalAction.BUY})
        self.assertEqual(len(result.fills), 1)
        self.assertTrue(any("200 continuous" in event for event in result.events))
        self.assert_reconciles(result, frames)

    def test_new_buy_waits_until_200_completed_post_event_sessions(self):
        u, s, frames = self.setup_case(kind="exchange", existing_child=True, n=405, entries=["ID-A", "ID-B"])
        result = self.run_ownership(u, s, frames, actions={
            ("ID-A", 199): SignalAction.BUY, ("ID-B", 202): SignalAction.SELL,
            ("ID-B", 399): SignalAction.BUY, ("ID-B", 400): SignalAction.BUY})
        self.assertEqual([f.timestamp for f in result.fills if f.symbol == "ID-B" and f.side == SignalAction.BUY], [self.dates[401]])
        self.assert_reconciles(result, frames)

    def test_fractional_rate_scales_with_account_size(self):
        fixing = self.instruction("action:EVENT:1", at=203, name="FIX", amount="31", amount_basis="per_fractional_share")
        payment = self.instruction("action:EVENT:1", at=205)
        u, s, frames = self.setup_case(kind="exchange", cash="30", ratio="0.8378", fixings=[fixing], payments=[payment])
        received = []
        for capital in (10000, 20000):
            result = self.run_ownership(u, s, frames, costs=BacktestConfig(initial_cash=capital, slippage_bps=0, spread_bps=0))
            received.append(result.equity_curve[205].cash - result.equity_curve[204].cash)
            self.assert_reconciles(result, frames)
        self.assertAlmostEqual(received[1], 2 * received[0])

    def test_open_basis_does_not_use_event_close(self):
        u, s, frames = self.setup_case()
        frames["ID-B"].loc[201:, ["close", "high"]] = [60, 61]
        result = self.run_ownership(u, s, frames)
        lots = result.ownership_accounting["marks"][-1]["lots"]
        self.assertEqual({lot["instrument_id"]: Fraction(lot["basis"]) for lot in lots}, {"ID-A": 700, "ID-B": 300})
        self.assert_reconciles(result, frames)

    def test_passive_distribution_above_position_cap_blocks_new_buys(self):
        u, s, frames = self.setup_case()
        result = self.run_ownership(u, s, frames, limits=ResearchPortfolioLimits(max_positions=1, max_daily_loss=.99, max_drawdown=.99))
        self.assertEqual(result.equity_curve[-1].position_count, 2)
        self.assertTrue(any("exceeds entry position cap" in event for event in result.events))
        self.assert_reconciles(result, frames)

    def test_genuine_split_and_dividend_apply_to_inherited_whole_shares(self):
        split = SplitAction("SPLIT", "ID-B", self.day(203), 2, 1, self.known(203), "SYNTHETIC SPLIT")
        dividend = CashDividend("DIV", "ID-B", self.day(204), self.day(205), 1, self.known(204), "SYNTHETIC DIVIDEND")
        payment = self.instruction("dividend:DIV", at=207)
        u, s, frames = self.setup_case(splits=[split], dividends=[dividend], payments=[payment])
        frames["ID-B"].loc[203:, ["open", "high", "low", "close"]] = [15, 15.5, 14.5, 15]
        result = self.run_ownership(u, s, frames)
        self.assertEqual(result.final_positions["ID-B"], 20)
        self.assertEqual(result.equity_curve[205].dividend_receivable, 20)
        self.assertEqual(result.equity_curve[206].cash, 9000)
        self.assertEqual(result.equity_curve[207].cash, 9020)
        self.assert_reconciles(result, frames)

    def test_reverse_split_keeps_fraction_without_rounding_away(self):
        split = SplitAction("SPLIT", "ID-B", self.day(203), 1, 3, self.known(203), "SYNTHETIC REVERSE SPLIT")
        u, s, frames = self.setup_case(splits=[split])
        frames["ID-B"].loc[203:, ["open", "high", "low", "close"]] = [90, 91, 89, 90]
        result = self.run_ownership(u, s, frames)
        self.assertEqual(result.final_positions["ID-B"], 3)
        claims = result.ownership_accounting["marks"][-1]["claims"]
        self.assertEqual(Fraction(claims[0]["units"]), Fraction(1, 3))
        self.assert_reconciles(result, frames)

    def test_unresolved_fractional_dividend_entitlement_is_rejected(self):
        dividend = CashDividend("DIV", "ID-B", self.day(204), self.day(205), 1, self.known(204), "SYNTHETIC DIVIDEND")
        u, s, frames = self.setup_case(kind="exchange", cash="30", ratio="0.8378", dividends=[dividend])
        with self.assertRaisesRegex(AccountingError, "fractional ownership"):
            self.run_ownership(u, s, frames)

    def test_flat_start_creates_no_claim_or_free_cash(self):
        payment = self.instruction("action:EVENT:0")
        u, s, frames = self.setup_case(kind="exchange", cash="42", ratio=None, payments=[payment])
        result = self.run_ownership(u, s, frames, actions={})
        self.assertEqual(result.equity_curve[-1].cash, 10000)
        self.assertEqual(result.ownership_accounting["marks"][-1]["claims"], [])
        self.assert_reconciles(result, frames)


class OwnershipValidationTests(OwnershipFixture):
    def test_example_files_round_trip_and_keep_source_hash(self):
        u = HistoricalUniverse.load(Path("docs/examples/ownership_universe.example.json"))
        s = OwnershipSchedule.load(Path("docs/examples/ownership_schedule.example.json"))
        s.bind(u)
        self.assertEqual(len(s.manifest_sha256), 64)
        self.assertEqual(s.metadata(), OwnershipSchedule.from_dict(s.metadata()).metadata())

    def test_loaded_schedule_hash_survives_report_round_trip(self):
        u, s, frames = self.setup_case()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "schedule.json"
            path.write_text(json.dumps(s.metadata()), encoding="utf-8")
            loaded = OwnershipSchedule.load(path)
            result = self.run_ownership(u, loaded, frames)
            self.assertEqual(result.ownership_accounting["schedule_source_sha256"], loaded.manifest_sha256)
            self.assert_reconciles(result, frames)

    def test_schedule_version_and_unknown_fields_fail_closed(self):
        _, schedule, _ = self.setup_case()
        for change in ({"schema_version": True}, {"schema_version": 9}, {"unexpected": "not permitted"}):
            with self.subTest(change=change), self.assertRaises(UniverseDataError):
                OwnershipSchedule.from_dict({**schedule.metadata(), **change})

    def test_scope_without_schedule_and_schedule_without_universe_rejected(self):
        u, s, frames = self.setup_case()
        engine = self.engine()
        with self.assertRaisesRegex(UniverseDataError, "schedule"):
            engine.run(frames, trade_start=self.dates[0], trade_end=self.dates[210], universe=u)
        with self.assertRaisesRegex(UniverseDataError, "universe"):
            engine.run(frames, trade_start=self.dates[0], trade_end=self.dates[210], ownership=s)

    def test_unapproved_late_eligibility_and_delayed_delivery_rejected(self):
        r = self.evidence()
        for changes in ({"reviewed_for_research": False}, {"eligibility_policy": "record_date_only"},
                        {"eligibility_known_at": self.sessions[202].opens_at.isoformat()},
                        {"delivered_at": self.sessions[202].opens_at.isoformat()}, {"delivery_source": ""}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(r, **changes)

    def test_non_open_event_and_unended_parent_rejected(self):
        u, s, frames = self.setup_case()
        late = replace(s.events[0].event, effective_at=self.sessions[201].closes_at)
        r = replace(s.events[0], event=late, delivered_at=late.effective_at.isoformat())
        with self.assertRaisesRegex(UniverseDataError, "exchange open"):
            OwnershipSchedule(entry_instrument_ids=["ID-A"], events=[r]).bind(u)
        exchange = self.evidence(kind="exchange", cash="42", ratio=None)
        with self.assertRaisesRegex(UniverseDataError, "ended parent"):
            OwnershipSchedule(entry_instrument_ids=["ID-A"], events=[exchange]).bind(u)

    def test_duplicate_event_instruction_claim_and_reserved_fill_id_rejected(self):
        r = self.evidence(kind="exchange", cash="42", ratio=None)
        i = self.instruction("action:EVENT:0")
        cases = [dict(events=[r, r]), dict(payments=[i, i]), dict(payments=[i, replace(i, instruction_id="OTHER")]),
                 dict(payments=[replace(i, instruction_id="fill-0")])]
        for fields in cases:
            with self.subTest(fields=fields), self.assertRaises(UniverseDataError):
                OwnershipSchedule(entry_instrument_ids=["ID-A"], **fields)

    def test_unknown_claim_and_unfixed_fraction_payment_rejected(self):
        u, s, frames = self.setup_case()
        for claim in ("not-a-claim", "action:EVENT:1"):
            with self.subTest(claim=claim), self.assertRaises(UniverseDataError):
                OwnershipSchedule(entry_instrument_ids=["ID-A"], events=s.events,
                                  payments=[self.instruction(claim)]).bind(u)

    def test_total_fraction_fix_requires_units_and_preceding_date(self):
        u, s, frames = self.setup_case()
        for fixing in (self.instruction("action:EVENT:1", name="FIX", amount="10"),
                       self.instruction("action:EVENT:1", name="FIX", at=200, amount="10", expected_fractional_units="0.5")):
            with self.subTest(fixing=fixing), self.assertRaises(UniverseDataError):
                OwnershipSchedule(entry_instrument_ids=["ID-A"], events=s.events, fixings=[fixing]).bind(u)

    def test_missing_whole_and_fractional_quotes_block_without_fill(self):
        for ratio in ("1", "0.01"):
            with self.subTest(ratio=ratio):
                u, s, frames = self.setup_case(kind="exchange", ratio=ratio)
                frames["ID-B"].loc[202, "volume"] = 0
                with self.assertRaisesRegex(UniverseDataError, "quote"):
                    self.run_ownership(u, s, frames)

    def test_report_tampering_rejected_by_replay(self):
        u, s, frames = self.setup_case(kind="exchange", cash="30", ratio="0.8378")
        packed = pack(self.run_ownership(u, s, frames))
        for field in ("cash", "equity", "exposure", "ownership_cash_receivable", "fractional_claim_value"):
            bad = deepcopy(packed)
            bad["equity_curve"][-1][field] += 1
            with self.subTest(field=field), self.assertRaises(UniverseDataError):
                daily_risk_envelope(bad, frames)
        for field in ("journal", "marks", "daily_risk_envelopes"):
            bad = deepcopy(packed)
            bad["ownership_accounting"][field].pop()
            with self.subTest(field=field), self.assertRaises(UniverseDataError):
                daily_risk_envelope(bad, frames)

    def test_summary_and_cost_capital_corruption_rejected(self):
        u, s, frames = self.setup_case()
        packed = pack(self.run_ownership(u, s, frames))
        for section, field in (("metrics", "initial_cash"), ("metrics", "final_equity"),
                               ("metrics", "total_return"), ("metrics", "max_drawdown"),
                               ("metrics", "completed_trades"), ("metrics", "winning_trades"),
                               ("metrics", "max_observed_positions"), ("costs", "initial_cash")):
            bad = deepcopy(packed)
            bad[section][field] += 1
            with self.subTest(section=section, field=field), self.assertRaises(UniverseDataError):
                daily_risk_envelope(bad, frames)
        for field in ("last_close", "marked_unrealized_pnl"):
            bad = deepcopy(packed)
            bad["metrics"]["open_positions"]["ID-B"][field] += 1
            with self.subTest(position_field=field), self.assertRaises(UniverseDataError):
                daily_risk_envelope(bad, frames)

    def test_claim_payment_rejects_wrong_amount_without_credit(self):
        payment = self.instruction("action:EVENT:0", amount="421")
        u, s, frames = self.setup_case(kind="exchange", cash="42", ratio=None, payments=[payment])
        with self.assertRaisesRegex(AccountingError, "amount differs"):
            self.run_ownership(u, s, frames)

    def test_reserved_calendar_is_rejected_without_reading_any_prices(self):
        session = type(self.sessions[0])(pd.Timestamp("2024-01-02T14:30:00Z"), pd.Timestamp("2024-01-02T21:00:00Z"))
        u = HistoricalUniverse(sessions=[session], listings=[self.listing()], price_basis="raw", action_scope=OWNERSHIP_SCOPE)
        with self.assertRaisesRegex(UniverseDataError, "reserved holdout"):
            OwnershipSchedule(entry_instrument_ids=["ID-A"]).bind(u)

    def test_external_data_price_and_alias_corruption_rejected(self):
        u, s, frames = self.setup_case()
        packed = pack(self.run_ownership(u, s, frames))
        for field, value in (("close", 30.25), ("symbol", "WRONG"), ("volume", 0)):
            bad = {key: frame.copy() for key, frame in frames.items()}
            bad["ID-B"].loc[201, field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                daily_risk_envelope(packed, bad)

    def test_event_free_legacy_mode_keeps_exact_financial_output(self):
        frames = {"ID-A": self.bars()}
        u = self.universe(action_scope=OWNERSHIP_SCOPE)
        schedule = OwnershipSchedule(entry_instrument_ids=["ID-A"])
        adapted = self.run_ownership(u, schedule, frames)
        legacy = self.run_case()
        self.assertEqual(adapted.fills, legacy.fills)
        for p, q in zip(adapted.equity_curve, legacy.equity_curve):
            self.assertEqual((p.cash, p.equity, p.gross_exposure, p.position_count, p.drawdown),
                             (q.cash, q.equity, q.gross_exposure, q.position_count, q.drawdown))
        self.assert_reconciles(adapted, frames)

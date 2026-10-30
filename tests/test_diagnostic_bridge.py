"""Focused synthetic verification of the approved-assumption integration.

No network, credentials, real holdings or research strategy/performance batch.
Synthetic approval strings and weekday calendars are fixtures, not evidence.
"""

from copy import deepcopy
from fractions import Fraction
import json

import pandas as pd

from app.strategy.base import SignalAction
from backtesting.claim_accounting import AccountingError, Quote
from backtesting.daily_research import pack
from backtesting.diagnostic_bridge import DiagnosticLedger, DiagnosticRuntime, DiagnosticSchedule, DiagnosticUniverse, replay_diagnostic
from backtesting.portfolio_engine import ResearchPortfolioLimits
from backtesting.protective_exits import ProtectiveExitConfig
from backtesting.risk_diagnostics import daily_risk_envelope
from backtesting.universe import UniverseDataError, SplitAction
from tests.test_universe import UniverseFixture


class DiagnosticFixture(UniverseFixture):
    def make_case(self, *, scenario="base", kind="retained_parent_spinoff", release=201, n=209, dividend=False, split=False):
        def stream(key, start=0, end=n):
            return dict(instrument_id=key, root_id="ID-A", parts=[dict(start=self.day(start), end_exclusive=self.day(end))])
        frames = {"ID-A": self.bars(end=201 if kind == "cash_merger" else n, symbol="ID-A").astype({"open":float,"high":float,"low":float,"close":float})}
        frames["ID-A"]["high"], frames["ID-A"]["low"] = 101.0, 99.0
        streams = [stream("ID-A", end=201 if kind == "cash_merger" else n)]
        material = []
        if kind is not None:
            if kind != "cash_merger":
                frames["ID-A"].loc[201:, ["open", "high", "low", "close"]] = [70, 71, 69, 70]
                streams.append(stream("ID-B", start=201))
                frames["ID-B"] = self.bars(start=201, end=n, symbol="ID-B", price=120)
                frames["ID-B"]["high"], frames["ID-B"]["low"] = 121, 119
            material.append(dict(event_id="MATERIAL", parent_id="ID-A", root_id="ID-A", kind=kind,
                scenario=scenario, economic_date=self.day(201), modeled_accounting_at=self.sessions[201].opens_at.isoformat(),
                cash_per_parent="100" if kind == "cash_merger" else "0", modeled_cash_release_at=None,
                status="admitted_diagnostic_cash_receivable" if kind == "cash_merger" else "admitted_diagnostic_due_bill_spinoff",
                data_terms_resolved=True,consume_parent_once=True,preserve_parent_quantity=kind!="cash_merger",
                required_ownership_snapshot_at=self.sessions[200].closes_at.isoformat(),
                share_legs=[] if kind == "cash_merger" else [dict(instrument_id="ID-B", shares_per_parent="1/4",
                    modeled_release_at=None if release is None else self.sessions[release].opens_at.isoformat())],
                historical_known_at=None, execution_ready=False, blockers=[]))
        splits = []
        if split:
            splits.append(SplitAction("SPLIT", "ID-A", self.day(201), 2, 1, self.sessions[201].opens_at.isoformat(), "SYNTHETIC modeled split"))
            frames["ID-A"].loc[201:, ["open", "high", "low", "close"]] = [50, 50.5, 49.5, 50]
        dividends = []
        if dividend:
            dividends.append(dict(event_id="DIV", instrument_id="ID-A", scenario=scenario,
                economic_at=self.sessions[201].opens_at.isoformat(), cash_per_eligible_share="1/2",
                modeled_release_at=None if release is None else self.sessions[release].opens_at.isoformat(),
                historical_known_at=None, execution_ready=False, blockers=[]))
        universe = DiagnosticUniverse(self.sessions[:n], streams, splits)
        schedule = DiagnosticSchedule(entry_instrument_ids=["ID-A"], dividends=dividends, material=material,
            scenario=scenario, approval_sha256="SYNTHETIC NOT AN OWNER APPROVAL", membership_not_before=self.known(0))
        return universe, schedule, frames

    def run_diag(self, universe, schedule, frames, *, actions=None, **kwargs):
        engine = self.engine(actions=actions, record_decisions=True, **kwargs)
        return engine.run(frames, trade_start=self.dates[0], trade_end=self.dates[len(universe.sessions)],
            universe=universe, diagnostic=schedule)

    def reconciles(self, result, frames):
        saved = json.loads(json.dumps(pack(result), allow_nan=False))
        risk = daily_risk_envelope(saved, frames)
        self.assertTrue(risk["ledger_reconciled"])
        self.assertTrue(risk["external_source_prices_verified"])
        m = saved["metrics"]
        self.assertAlmostEqual(m["realized_pnl"]+m["marked_unrealized_pnl"],m["final_equity"]-m["initial_cash"])
        self.assertIsNone(result.ownership_accounting)
        self.assertFalse(saved["diagnostic_accounting"]["strict_evidence_approved"])
        return saved


class PendingRightsEngineTests(DiagnosticFixture):
    def test_same_open_release_and_exact_fraction_preserve_equity(self):
        u,s,data = self.make_case()
        result = self.run_diag(u,s,data)
        self.assertEqual(result.final_positions,{"ID-A":10,"ID-B":2})
        self.assertEqual(result.equity_curve[-1].equity,10000)
        self.assertEqual(result.equity_curve[-1].fractional_claim_value,60)
        self.assertEqual(result.equity_curve[-1].pending_share_claim_value,0)
        self.assertEqual(len(result.fills),1)
        saved=self.reconciles(result,data)
        self.assertIsNone(saved["metrics"]["hypothetical_liquidated_return"])
        self.assertTrue(saved["metrics"]["claims_not_liquidated"])

    def test_no_credit_values_undelivered_whole_and_fractional_shares(self):
        u,s,data=self.make_case(scenario="no_credit",release=None)
        result=self.run_diag(u,s,data)
        p=result.equity_curve[-1]
        self.assertEqual(result.final_positions,{"ID-A":10})
        self.assertEqual((p.pending_share_claim_value,p.fractional_claim_value),(240,60))
        self.assertEqual(p.position_count,2)
        self.assertAlmostEqual(p.gross_exposure,.10)
        self.assertEqual(p.cash,9000)
        self.reconciles(result,data)

    def test_delayed_right_survives_parent_sale_and_keeps_original_age(self):
        u,s,data=self.make_case(scenario="delayed_five_sessions",release=206)
        result=self.run_diag(u,s,data,actions={("ID-A",199):SignalAction.BUY,("ID-A",202):SignalAction.SELL})
        self.assertEqual(result.final_positions,{"ID-B":2})
        self.assertEqual(result.equity_curve[-1].equity,10000)
        lots=result.diagnostic_accounting["marks"][-1]["lots"]
        self.assertEqual(lots[0]["acquired_at"],self.sessions[200].opens_at.isoformat())
        self.assertEqual(sum(r["kind"]=="diagnostic_share_release" for r in result.diagnostic_accounting["journal"]),1)
        self.reconciles(result,data)

    def test_cash_merger_keeps_face_value_without_parent_quotes_or_cash_credit(self):
        u,s,data=self.make_case(kind="cash_merger")
        result=self.run_diag(u,s,data)
        self.assertEqual(result.final_positions,{})
        self.assertEqual(result.equity_curve[-1].ownership_cash_receivable,1000)
        self.assertEqual(result.equity_curve[-1].cash,9000)
        self.assertEqual(result.equity_curve[-1].equity,10000)
        self.assertAlmostEqual(result.equity_curve[-1].gross_exposure,.10)
        self.reconciles(result,data)

    def test_dividend_cash_releases_once_after_selling_parent(self):
        u,s,data=self.make_case(kind=None,dividend=True,release=204)
        result=self.run_diag(u,s,data,actions={("ID-A",199):SignalAction.BUY,("ID-A",201):SignalAction.SELL})
        self.assertEqual(result.equity_curve[-1].cash,10005)
        self.assertEqual(result.equity_curve[-1].dividend_receivable,0)
        saved=self.reconciles(result,data)
        self.assertEqual(saved["metrics"]["dividend_cash_received"],5)

    def test_unpaid_cash_right_reserves_exposure_after_parent_sale(self):
        u,s,data=self.make_case(kind=None,dividend=True,release=None)
        result=self.run_diag(u,s,data,actions={("ID-A",199):SignalAction.BUY,("ID-A",201):SignalAction.SELL})
        self.assertEqual(result.equity_curve[-1].dividend_receivable,5)
        self.assertAlmostEqual(result.equity_curve[-1].gross_exposure,5/10005)
        self.reconciles(result,data)

    def test_unknown_payment_date_retains_earned_dividend(self):
        u,s,data=self.make_case(kind=None,dividend=True,release=None)
        result=self.run_diag(u,s,data)
        self.assertEqual(result.equity_curve[-1].dividend_receivable,5)
        self.assertEqual(result.equity_curve[-1].cash,9000)
        self.reconciles(result,data)

    def test_ex_open_buyer_does_not_earn_dividend(self):
        u,s,data=self.make_case(kind=None,dividend=True,release=204)
        result=self.run_diag(u,s,data,actions={("ID-A",200):SignalAction.BUY})
        self.assertEqual(result.equity_curve[-1].equity,10000)
        self.assertEqual(pack(result)["metrics"]["dividend_income_earned"],0)
        self.reconciles(result,data)

    def test_reviewed_component_in_total_is_retained_without_duplicate_credit(self):
        u,s,data=self.make_case(kind=None,dividend=True,release=204)
        component=deepcopy(s.dividends[0])
        component.update(event_id="COMPONENT",cash_per_eligible_share="0",modeled_release_at=None,
            independent_entitlement=False,status="reviewed_component_in_total_no_independent_right",
            represented_by_event_id="DIV",component_review=dict(kind="aggregate_includes_component",total_rate="1/2"))
        s.dividends.append(component)
        result=self.run_diag(u,s,data)
        self.assertEqual(result.equity_curve[-1].cash,9005)
        self.assertEqual(sum(r["kind"]=="diagnostic_dividend_component_context" for r in result.diagnostic_accounting["journal"]),1)
        self.reconciles(result,data)

    def test_unreviewed_zero_dividend_cannot_be_treated_as_harmless(self):
        u,s,data=self.make_case(kind=None,dividend=True)
        s.dividends[0]["cash_per_eligible_share"]="0"
        with self.assertRaises(AccountingError):
            self.run_diag(u,s,data)

    def test_split_units_preserve_basis_and_equity(self):
        u,s,data=self.make_case(kind=None,split=True)
        result=self.run_diag(u,s,data)
        self.assertEqual(result.final_positions,{"ID-A":20})
        self.assertEqual(result.equity_curve[-1].equity,10000)
        self.reconciles(result,data)

    def test_material_boundary_cancels_queued_parent_sale(self):
        u,s,data=self.make_case()
        result=self.run_diag(u,s,data,actions={("ID-A",199):SignalAction.BUY,("ID-A",200):SignalAction.SELL})
        self.assertEqual(result.final_positions,{"ID-A":10,"ID-B":2})
        self.assertFalse(any(f.side==SignalAction.SELL for f in result.fills))
        self.reconciles(result,data)

    def test_new_buys_need_fresh_features_after_distribution(self):
        u,s,data=self.make_case()
        result=self.run_diag(u,s,data,actions={("ID-A",202):SignalAction.BUY})
        self.assertFalse(result.fills)
        self.assertTrue(any("200 continuous" in message for message in result.events))

    def test_undelivered_child_is_not_available_for_sell(self):
        u,s,data=self.make_case(scenario="no_credit",release=None)
        result=self.run_diag(u,s,data,actions={("ID-A",199):SignalAction.BUY,("ID-B",202):SignalAction.SELL})
        self.assertFalse(any(f.symbol=="ID-B" for f in result.fills))
        self.assertEqual(result.equity_curve[-1].pending_share_claim_value,240)

    def test_delivered_child_has_inherited_stop_and_delayed_gap_exit(self):
        u,s,data=self.make_case(scenario="delayed_five_sessions",release=206)
        data["ID-B"][["open","high","low","close"]]=data["ID-B"][["open","high","low","close"]].astype(float)
        data["ID-B"].loc[data["ID-B"]["timestamp"]>=self.dates[206],["open","high","low","close"]]=[90,91,89,90]
        result=self.run_diag(u,s,data,protection=ProtectiveExitConfig(atr_multiple=3,max_risk_per_trade=.99))
        sold=[f for f in result.fills if f.symbol=="ID-B"]
        self.assertEqual(len(sold),1)
        self.assertEqual(sold[0].timestamp,self.dates[206])
        self.assertTrue(sold[0].signal_reason.startswith("PROTECTIVE_STOP_GAP_OPEN"))
        self.assertEqual(set(result.final_stops),set(result.final_positions))
        self.reconciles(result,data)

    def test_parent_sale_does_not_remove_pending_rights_from_exposure(self):
        u,s,data=self.make_case(scenario="no_credit",release=None)
        result=self.run_diag(u,s,data,actions={("ID-A",199):SignalAction.BUY,("ID-A",202):SignalAction.SELL})
        self.assertEqual(result.equity_curve[-1].position_count,1)
        self.assertAlmostEqual(result.equity_curve[-1].gross_exposure,.03)
        self.reconciles(result,data)


class DiagnosticAdmissionAndReplayTests(DiagnosticFixture):
    def test_correct_prior_close_ownership_is_required(self):
        u,s,data=self.make_case()
        s.material[0]["required_ownership_snapshot_at"]=self.sessions[199].closes_at.isoformat()
        with self.assertRaisesRegex(UniverseDataError,"preceding saved close"):
            self.run_diag(u,s,data)

    def test_no_invented_cash_merger_payment(self):
        u,s,data=self.make_case(kind="cash_merger")
        s.material[0]["modeled_cash_release_at"]=self.sessions[205].opens_at.isoformat()
        with self.assertRaisesRegex(UniverseDataError,"unpaid fixed"):
            self.run_diag(u,s,data)

    def test_removed_explanatory_blockers_do_not_admit_unknown_terms(self):
        u,s,data=self.make_case()
        s.material[0]["data_terms_resolved"]=False
        with self.assertRaisesRegex(UniverseDataError,"unresolved economic"):
            self.run_diag(u,s,data)

    def test_cannot_ignore_diagnostic_schedule(self):
        u,s,data=self.make_case()
        with self.assertRaisesRegex(UniverseDataError,"requires its schedule"):
            self.engine().run(data,trade_start=self.dates[0],trade_end=self.dates[209],universe=u)

    def test_duplicate_event_is_rejected(self):
        u,s,data=self.make_case()
        s.material.append(deepcopy(s.material[0]))
        with self.assertRaisesRegex(UniverseDataError,"Duplicate"):
            self.run_diag(u,s,data)

    def test_no_credit_cannot_schedule_delivery(self):
        u,s,data=self.make_case(scenario="no_credit")
        with self.assertRaisesRegex(UniverseDataError,"No-credit"):
            self.run_diag(u,s,data)

    def test_strict_evidence_flag_cannot_be_promoted(self):
        u,s,data=self.make_case()
        s.material[0]["execution_ready"]=True
        with self.assertRaisesRegex(UniverseDataError,"strict"):
            self.run_diag(u,s,data)

    def test_missing_candle_is_not_filled(self):
        u,s,data=self.make_case()
        data["ID-A"]=data["ID-A"].drop(180)
        with self.assertRaisesRegex(UniverseDataError,"gap"):
            self.run_diag(u,s,data)

    def test_empty_outside_lifetime_stream_is_retained(self):
        u,s,data=self.make_case(kind=None)
        u.streams.append(dict(instrument_id="ID-ENDED",parts=[dict(start="2016-01-01",end_exclusive="2018-01-01")]))
        u=DiagnosticUniverse(u.sessions,u.streams)
        data["ID-ENDED"]=data["ID-A"].iloc[:0].copy()
        result=self.run_diag(u,s,data)
        self.assertIn("ID-ENDED",result.universe_metadata["streams"][-1]["instrument_id"])
        self.reconciles(result,data)

    def test_missing_current_pending_share_quote_blocks_valuation(self):
        u,s,data=self.make_case(scenario="no_credit",release=None)
        data["ID-B"].loc[data["ID-B"]["timestamp"]==self.dates[205],"volume"]=0
        with self.assertRaisesRegex(UniverseDataError,"current session mark"):
            self.run_diag(u,s,data)

    def test_external_quote_tampering_is_rejected(self):
        u,s,data=self.make_case()
        saved=pack(self.run_diag(u,s,data))
        saved["diagnostic_accounting"]["days"][-1]["quotes"]["ID-B"]["close"]="120.5"
        with self.assertRaisesRegex(UniverseDataError,"differs"):
            daily_risk_envelope(saved,data)

    def test_equity_tampering_is_rejected(self):
        u,s,data=self.make_case()
        saved=pack(self.run_diag(u,s,data))
        saved["equity_curve"][-1]["equity"]+=1
        with self.assertRaisesRegex(UniverseDataError,"equity"):
            daily_risk_envelope(saved,data)

    def test_trade_count_tampering_is_rejected(self):
        u,s,data=self.make_case()
        saved=pack(self.run_diag(u,s,data))
        saved["metrics"]["completed_trades"]=500
        with self.assertRaisesRegex(UniverseDataError,"completed_trades"):
            daily_risk_envelope(saved,data)

    def test_final_position_price_tampering_is_rejected(self):
        u,s,data=self.make_case()
        saved=pack(self.run_diag(u,s,data))
        saved["metrics"]["open_positions"]["ID-B"]["last_close"]=999
        with self.assertRaisesRegex(UniverseDataError,"price/basis"):
            daily_risk_envelope(saved,data)

    def test_pending_whole_value_tampering_is_rejected(self):
        u,s,data=self.make_case(scenario="no_credit",release=None)
        saved=pack(self.run_diag(u,s,data))
        saved["equity_curve"][-1]["pending_share_claim_value"]=0
        with self.assertRaisesRegex(UniverseDataError,"pending_share"):
            daily_risk_envelope(saved,data)

    def test_duplicate_release_raises_without_mutation(self):
        u,s,data=self.make_case()
        ledger=DiagnosticLedger("10000",u.clock)
        at=self.sessions[200].opens_at
        ledger.buy("BUY","ID-A",10,"100",at=at)
        at=self.sessions[201].opens_at
        quotes={k:Quote(k,at,p,p,p) for k,p in (("ID-A","70"),("ID-B","120"))}
        ledger.action(s.material[0],quotes,at=at)
        ledger.release_due(at=at)
        before=deepcopy(ledger.journal)
        # The retained fractional right is unscheduled, rather than delivered again.
        ledger.release_due(at=self.sessions[202].opens_at)
        self.assertEqual(ledger.journal,before)
        claim=ledger.rights.pending[0]
        with self.assertRaises(AccountingError):
            ledger.rights.release(claim.claim_id,at=self.sessions[202].opens_at)
        self.assertEqual(ledger.journal,before)

    def test_pending_cash_cannot_fund_buy(self):
        u,s,data=self.make_case(kind="cash_merger")
        ledger=DiagnosticLedger("10000",u.clock)
        ledger.buy("BUY","ID-A",10,"100",at=self.sessions[200].opens_at)
        ledger.action(s.material[0],{},at=self.sessions[201].opens_at)
        with self.assertRaisesRegex(AccountingError,"spendable"):
            ledger.buy("TOO-LARGE","ID-Z",100,"100",at=self.sessions[202].opens_at)
        self.assertEqual(ledger.cash,9000)
        self.assertEqual(sum(c.amount for c in ledger.claims),1000)

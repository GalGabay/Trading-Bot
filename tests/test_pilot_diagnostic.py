"""Focused synthetic checks for the approved diagnostic, with no real orders."""

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from app.strategy.base import SignalAction
from backtesting.corporate_actions import feature_views
from backtesting.daily_research import pack
from backtesting.pilot_diagnostic import DiagnosticDividend, DiagnosticUniverse, cash_open, diagnostic_pack
from backtesting.holding_policy import HoldingPolicy
from backtesting.portfolio_engine import summarize_portfolio
from backtesting.protective_exits import ProtectiveExitConfig
from backtesting.risk_diagnostics import daily_risk_envelope
from backtesting.universe import CashDividend, HistoricalUniverse, UniverseDataError
from tests.test_universe import UniverseFixture


class PilotDiagnosticTests(UniverseFixture):
    def dividend(self, pay=205, **kwargs):
        values=dict(event_id="D1",instrument_id="ID-A",ex_session=self.day(202),
                    pay_session=None if pay is None else self.day(pay),cash_per_share=1.0,
                    known_at=self.known(202),source="Synthetic diagnostic ordinary dividend")
        values.update(kwargs)
        return DiagnosticDividend(**values)

    def diagnostic(self, policy="base", dividends=None, splits=(), approved=True, listings=None):
        if dividends is None:
            dividends=[self.dividend(None if policy=="no_credit" else 205)]
        return DiagnosticUniverse(sessions=self.sessions[:208], listings=listings or [self.listing()],
            splits=splits,dividends=dividends,cash_policy=policy,approval_sha256="synthetic-approval",
            owner_approved=approved,journal=[dict(scope="synthetic")])

    def dropped(self):
        data=self.bars()
        data.loc[202:,["open","high","low","close"]]=99
        return data

    def test_base_payment_preserves_exact_economic_equity(self):
        result=self.run_case(self.diagnostic(),self.dropped())
        self.assertEqual(result.equity_curve[-1].cash,9010)
        self.assertEqual(result.equity_curve[-1].equity,10000)
        self.assertEqual(len(result.dividend_entitlements),1)
        self.assertEqual(len(result.dividend_payments),1)
        self.assertFalse(result.final_dividend_receivables)

    def test_no_credit_never_fabricates_pay_date_or_cash(self):
        result=self.run_case(self.diagnostic("no_credit"),self.dropped())
        self.assertEqual(result.equity_curve[-1].cash,9000)
        self.assertEqual(result.equity_curve[-1].equity,10000)
        self.assertEqual(result.equity_curve[-1].dividend_receivable,10)
        self.assertFalse(result.dividend_payments)
        self.assertIsNone(result.final_dividend_receivables[0]["pay_session"])
        case=diagnostic_pack(result,1)
        self.assertIsNone(case["metrics"]["hypothetical_liquidated_return"])
        self.assertTrue(case["metrics"]["claims_not_liquidated"])
        self.assertTrue(daily_risk_envelope(case,{"ID-A":self.dropped()})["corporate_actions_reconciled"])

    def test_delayed_cash_remains_unspendable_until_scheduled_open(self):
        result=self.run_case(self.diagnostic("delayed_five_sessions",[self.dividend(207)]),self.dropped())
        self.assertEqual(result.equity_curve[206].cash,9000)
        self.assertEqual(result.equity_curve[207].cash,9010)
        self.assertEqual(sum(p["amount"] for p in result.dividend_payments),10)

    def test_cash_policy_uses_actual_sessions_and_skips_weekend(self):
        # Calendar fixture starts Monday January 4, 2021; this Friday's next
        # open is Monday, not a fabricated Saturday session.
        self.assertEqual(cash_open(self.sessions,"2021-01-08","base","2022-01-01"),"2021-01-11")
        self.assertEqual(cash_open(self.sessions,"2021-01-08","delayed_five_sessions","2022-01-01"),"2021-01-18")

    def test_cash_after_window_is_none_not_a_fake_future_session(self):
        self.assertIsNone(cash_open(self.sessions,"2021-01-08","base","2021-01-11"))
        self.assertIsNone(cash_open(self.sessions[:3],"2021-01-08","base","2022-01-01"))
        self.assertIsNone(cash_open(self.sessions,"2021-01-08","no_credit","2022-01-01"))

    def test_cash_skips_an_explicitly_absent_holiday_session(self):
        sessions=[s for s in self.sessions if s.opens_at.date().isoformat()!="2021-01-18"]
        self.assertEqual(cash_open(sessions,"2021-01-15","base","2022-01-01"),"2021-01-19")

    def test_invalid_cash_policy_rejected(self):
        with self.assertRaises(ValueError): cash_open(self.sessions,"2021-01-08","best_return","2022-01-01")

    def test_owner_approval_is_required(self):
        with self.assertRaisesRegex(UniverseDataError,"approval"): self.diagnostic(approved=False)

    def test_unknown_scenario_rejected(self):
        with self.assertRaises(UniverseDataError): self.diagnostic(policy="invented")

    def test_no_credit_cannot_sneak_in_a_payment(self):
        with self.assertRaisesRegex(UniverseDataError,"No-credit"): self.diagnostic("no_credit",[self.dividend()])

    def test_late_knowledge_rejected(self):
        item=self.dividend(known_at=self.sessions[202].closes_at.isoformat())
        with self.assertRaisesRegex(UniverseDataError,"not known"): self.diagnostic(dividends=[item])

    def test_duplicate_dividend_cannot_create_duplicate_income(self):
        with self.assertRaisesRegex(UniverseDataError,"Duplicate"): self.diagnostic(dividends=[self.dividend(),self.dividend()])

    def test_non_session_payment_rejected(self):
        item=self.dividend(pay_session="2021-10-16")
        with self.assertRaisesRegex(UniverseDataError,"actual session"): self.diagnostic(dividends=[item])

    def test_payment_before_ex_date_rejected(self):
        with self.assertRaisesRegex(UniverseDataError,"precedes"): self.dividend(pay=201)

    def test_invalid_amounts_rejected(self):
        for value in (0,-1,True,float("nan"),float("inf")):
            with self.subTest(value=value),self.assertRaises(UniverseDataError): self.dividend(cash_per_share=value)

    def test_special_or_ambiguous_share_basis_rejected(self):
        for kwargs in (dict(kind="special"),dict(share_basis="unreviewed")):
            with self.subTest(kwargs=kwargs),self.assertRaises(UniverseDataError): self.dividend(**kwargs)

    def test_evidence_flags_stay_false_despite_owner_model_approval(self):
        mode=self.diagnostic().metadata()["diagnostic_research"]
        self.assertTrue(mode["owner_approved"])
        for key in ("independently_verified_entitlement","broker_cash_credit_verified","ready_for_strict_scoring","paper_authorized"):
            self.assertIs(mode[key],False)

    def test_strict_dividend_contract_still_rejects_none(self):
        with self.assertRaises(UniverseDataError):
            CashDividend("strict","ID-A",self.day(202),None,1,self.known(202),"synthetic")

    def test_legacy_loader_does_not_accept_diagnostic_metadata(self):
        with TemporaryDirectory() as directory:
            p=Path(directory)/"diagnostic.json"
            p.write_text(json.dumps(self.diagnostic().metadata()),encoding="utf-8")
            with self.assertRaises(UniverseDataError): HistoricalUniverse.load(p)

    def test_risk_rejects_deferred_claim_without_diagnostic_schedule(self):
        case=diagnostic_pack(self.run_case(self.diagnostic("no_credit"),self.dropped()),1)
        del case["universe_metadata"]["diagnostic_research"]
        with self.assertRaisesRegex(ValueError,"explicit approved diagnostic"): daily_risk_envelope(case,{"ID-A":self.dropped()})

    def test_risk_rejects_invented_verified_credit_flag(self):
        case=diagnostic_pack(self.run_case(self.diagnostic("no_credit"),self.dropped()),1)
        case["universe_metadata"]["diagnostic_research"]["broker_cash_credit_verified"]=True
        with self.assertRaisesRegex(ValueError,"explicit approved diagnostic"): daily_risk_envelope(case,{"ID-A":self.dropped()})

    def test_risk_rejects_paper_flag_and_boolean_schema(self):
        original=diagnostic_pack(self.run_case(self.diagnostic("no_credit"),self.dropped()),1)
        for key,value in (("paper_authorized",True),("schema_version",True),("ready_for_strict_scoring",True)):
            case=deepcopy(original)
            case["universe_metadata"]["diagnostic_research"][key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,"explicit approved diagnostic"):
                daily_risk_envelope(case,{"ID-A":self.dropped()})

    def test_sale_at_ex_open_keeps_prior_holder_entitlement(self):
        actions={("ID-A",199):SignalAction.BUY,("ID-A",201):SignalAction.SELL}
        result=self.run_case(self.diagnostic("no_credit"),self.dropped(),self.engine(actions))
        self.assertFalse(result.final_positions)
        self.assertEqual(result.final_dividend_receivables[0]["amount"],10)
        self.assertEqual(summarize_portfolio(result)["final_equity"],10000)

    def test_buy_at_ex_open_does_not_get_prior_holder_entitlement(self):
        result=self.run_case(self.diagnostic(),self.dropped(),self.engine({("ID-A",201):SignalAction.BUY}))
        self.assertFalse(result.dividend_entitlements)
        self.assertFalse(result.dividend_payments)

    def test_rename_preserves_position_without_synthetic_trade(self):
        listings=[self.listing(end=202),self.listing(symbol="BBB",start=202)]
        data=self.bars(); data.loc[202:,"symbol"]="BBB"
        result=self.run_case(self.diagnostic(dividends=[],listings=listings),data)
        self.assertEqual(result.final_positions,{"ID-A":10})
        self.assertEqual(len(result.fills),1)

    def test_split_features_stop_and_holding_age_use_existing_causal_engine(self):
        from backtesting.universe import SplitAction
        split=SplitAction("S1","ID-A",self.day(202),4,1,self.known(202),"synthetic split")
        u=self.diagnostic(dividends=[],splits=[split])
        data=self.bars(); data[["open","high","low","close","volume"]]=data[["open","high","low","close","volume"]].astype(float)
        data["high"]=101.;data["low"]=99.
        data.loc[202:,["open","high","low","close"]]/=4
        data.loc[202:,"volume"]*=4
        prepared=u.prepare("ID-A",data);views,_=feature_views(prepared,"ID-A",u,252)
        self.assertEqual(views[201].loc[201,"close"],100)
        self.assertEqual(views[202].loc[201,"close"],25)
        self.assertEqual(views[202].loc[201,"volume"],4000)
        result=self.run_case(u,data,self.engine(protection=ProtectiveExitConfig(atr_multiple=3,max_risk_per_trade=.01,trailing=False)))
        self.assertEqual(result.final_positions,{"ID-A":40})
        self.assertAlmostEqual(result.final_stops["ID-A"],23.5)
        self.assertAlmostEqual(summarize_portfolio(result)["final_equity"],10000)
        exited=self.run_case(u,data,self.engine(holding_policy=HoldingPolicy("maximum",first_review=6)))
        self.assertEqual(exited.fills[-1].quantity,40)
        self.assertEqual(exited.fills[-1].timestamp,self.dates[206])

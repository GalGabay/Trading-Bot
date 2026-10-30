"""Offline saved-result attribution/report checks; no strategy or broker calls."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from backtesting.subset_results import contributions,summarize
from backtesting.subset_runner import APPROVAL,atomic_json,pin


class RootAttributionTests(TestCase):
    def case(self):
        return dict(metrics=dict(initial_cash=1000,final_equity=1050),
            diagnostic_accounting=dict(universe=dict(streams=[
                dict(instrument_id="A",root_id="ROOT",role="original_member",snapshot_alias="OLD-A"),
                dict(instrument_id="B",root_id="ROOT",role="received_security",snapshot_alias="OLD-A")]),
                journal=[],schedule=dict(dividends=[dict(event_id="DIV",instrument_id="A")],material=[dict(event_id="MERGER",parent_id="A")]),
                marks=[dict(lots=[dict(instrument_id="A",quantity=5,basis="500")],claims=[])],
                days=[dict(quotes=dict(A=dict(close="110"),B=dict(close="100")))]))

    def test_open_marked_profit_is_attributed_once(self):
        result=contributions(self.case())
        self.assertEqual(result,[dict(root_id="ROOT",snapshot_alias="OLD-A",marked_profit_before_estimated_final_exits=50)])

    def test_paid_dividend_is_not_added_twice(self):
        case=self.case()
        case["diagnostic_accounting"]["journal"].append(dict(kind="diagnostic_cash_release",claim_id="dividend:DIV",amount="10",basis="0"))
        case["metrics"]["final_equity"]=1060
        self.assertEqual(contributions(case)[0]["marked_profit_before_estimated_final_exits"],60)

    def test_unpaid_dividend_is_unrealized_claim_value(self):
        case=self.case()
        case["diagnostic_accounting"]["marks"][-1]["claims"].append(dict(instrument_id="A",kind="cash",amount="10",basis="0"))
        case["metrics"]["final_equity"]=1060
        self.assertEqual(contributions(case)[0]["marked_profit_before_estimated_final_exits"],60)

    def test_child_fraction_is_assigned_to_original_root(self):
        case=self.case()
        case["diagnostic_accounting"]["marks"][-1]["claims"].append(dict(instrument_id="B",kind="pending_shares",units="1/2",basis="30"))
        case["metrics"]["final_equity"]=1070
        self.assertEqual(contributions(case)[0]["marked_profit_before_estimated_final_exits"],70)

    def test_realized_sale_uses_economic_basis_not_gross_proceeds(self):
        case=self.case()
        case["diagnostic_accounting"]["journal"].append(dict(kind="simulated_sell",instrument_id="B",proceeds="60",basis="40"))
        case["metrics"]["final_equity"]=1070
        self.assertEqual(contributions(case)[0]["marked_profit_before_estimated_final_exits"],70)

    def test_paid_action_claim_uses_its_parent_root(self):
        case=self.case()
        case["diagnostic_accounting"]["journal"].append(dict(kind="diagnostic_cash_release",claim_id="diagnostic:MERGER:0",amount="100",basis="80"))
        case["metrics"]["final_equity"]=1070
        self.assertEqual(contributions(case)[0]["marked_profit_before_estimated_final_exits"],70)

    def test_contribution_mismatch_is_not_hidden(self):
        case=self.case()
        case["metrics"]["final_equity"]=9999
        with self.assertRaisesRegex(ValueError,"does not reconcile"):contributions(case)

    def test_unused_roots_are_retained_with_zero_profit(self):
        case=self.case()
        case["diagnostic_accounting"]["universe"]["streams"].append(dict(instrument_id="C",root_id="OTHER",role="original_member",snapshot_alias="C"))
        result={r["root_id"]:r["marked_profit_before_estimated_final_exits"] for r in contributions(case)}
        self.assertEqual(result,dict(ROOT=50,OTHER=0))


class BatchReportTests(TestCase):
    def setUp(self):
        root=Path("data/reports")
        root.mkdir(parents=True,exist_ok=True)
        self.temp=TemporaryDirectory(dir=root)
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def execution(self,status="stopped",attempts=1):
        run=self.root/"run"
        run.mkdir()
        ledger=run/"ledger.json"
        atomic_json(ledger,dict(status=status,completed=[]))
        atomic_json(run/"summary.json",dict(status=status,ledger=pin(ledger),approval=pin(APPROVAL),attempts=attempts,completed=0,stop_reason="SYNTHETIC STOP"))
        return run

    def test_stopped_empty_batch_is_reported_incomplete(self):
        result=summarize(self.root/"output",self.execution())
        self.assertFalse(result["step3_complete"])
        self.assertEqual(result["strategy_attempts"],1)
        self.assertEqual(result["completed_strategy_runs"],0)

    def test_running_batch_cannot_be_called_a_final_report(self):
        with self.assertRaisesRegex(ValueError,"Wait for the batch"):
            summarize(self.root/"output",self.execution("running"))

    def test_overscope_attempt_count_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"exceeds"):
            summarize(self.root/"output",self.execution(attempts=25))

    def test_existing_output_cannot_replace_prior_evidence(self):
        output=self.root/"output"
        output.mkdir()
        with self.assertRaises(ValueError): summarize(output,self.root/"not_read")

"""Owner approval, conditional economic terms and blocked Step 2 handoff."""

from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from backtesting.broad_collection import pin
from backtesting.diagnostic_approval import approved_policy,validate_approval
from backtesting.diagnostic_preflight import assess,require_data_ready,DiagnosticIntegrationBlocked
from backtesting.election_terms import resolve_election
from backtesting.pilot_readiness_review import write_json

ROOT=Path(__file__).resolve().parents[1]


class ApprovalTests(TestCase):
    def setUp(self):
        temp=TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        before=Path.cwd()
        os.chdir(temp.name)
        self.addCleanup(os.chdir,before)
        self.proposal=dict(schema_version=1,owner_approved=False,scenarios=["base","delayed_five_sessions","no_credit"],
            purchases_usd=0,performance_authorized=False,implementation=[],position_parameters_owner_approved=False)
        write_json(Path("proposal.json"),self.proposal)
        Path("review.md").write_text("Synthetic approved defaults",encoding="utf-8")
        self.record=dict(owner_approved=True,diagnostic_accounting_defaults_approved=True,
            proposed_policy=pin("proposal.json"),resolved_document=pin("review.md"),
            allocation=dict(total_entry_exposure=.70,per_stock_entry_cap=.05,max_positions=20,scope="historical_research_only"),
            new_performance_batch_authorized=False,paper_authorized=False,max_strategy_runs=0,purchases_usd=0)
        self.freeze()
        self.policy=dict(self.proposal,owner_approved=True,position_parameters_owner_approved=True,
                         approval=pin("approval.json"),source_proposal=pin("proposal.json"))

    def freeze(self): write_json(Path("approval.json"),self.record)

    def test_valid_owner_record_clears_assumptions_only(self):
        r=validate_approval(self.policy)
        self.assertFalse(r["paper_authorized"])
        self.assertFalse(r["new_performance_batch_authorized"])

    def test_approved_copy_marks_position_choices_without_rewriting_proposal(self):
        Path("backtesting").mkdir()
        for name in ("diagnostic_accounting","diagnostic_preparation","diagnostic_approval"):
            (Path("backtesting")/(name+".py")).write_text("# synthetic source",encoding="utf-8")
        before=Path("proposal.json").read_bytes()
        p=approved_policy(Path("proposal.json"),Path("approval.json"))
        self.assertTrue(p["position_parameters_owner_approved"])
        self.assertEqual(Path("proposal.json").read_bytes(),before)
        p["position_parameters_owner_approved"]=False
        with self.assertRaises(ValueError):validate_approval(p)

    def test_changed_assumptions_rejected(self):
        self.policy["scenarios"]=["base"]
        with self.assertRaises(ValueError):validate_approval(self.policy)

    def test_altered_approval_document_or_proposal_rejected(self):
        Path("review.md").write_text("altered")
        with self.assertRaises(ValueError):validate_approval(self.policy)

    def test_changed_numeric_allocation_cannot_use_original_assent(self):
        self.record["allocation"]["max_positions"]=200
        self.freeze()
        self.policy["approval"]=pin("approval.json")
        with self.assertRaises(ValueError):validate_approval(self.policy)

    def test_changing_execution_hashes_does_not_change_research_semantics(self):
        self.policy["implementation"]=[dict(path="new-code.py",sha256="new")]
        validate_approval(self.policy)

    def test_paper_or_performance_authority_not_inferred(self):
        for field in ("paper_authorized","new_performance_batch_authorized"):
            self.record[field]=True
            self.freeze()
            self.policy["approval"]=pin("approval.json")
            with self.assertRaises(ValueError):validate_approval(self.policy)
            self.record[field]=False


class ElectionTests(TestCase):
    def setUp(self):
        self.review=json.loads((ROOT/"docs/broad_remaining_terms_review_2026-10-30.json").read_text(encoding="utf-8"))
        self.terms={e["id"]:e for e in self.review["election_terms"]}

    def test_aiv_2019_no_election_does_not_win_lottery(self):
        r=resolve_election(self.terms["aiv_2019"],"no_election")
        self.assertEqual(r["cash_per_record_share"],"11/25")
        self.assertEqual(r["shares_per_record_share"],"158/4993")
        self.assertFalse(r["execution_ready"])

    def test_cash_election_needs_actual_lottery_branch(self):
        t=self.terms["aiv_2019"]
        self.assertEqual(resolve_election(t,"cash")["status"],"blocked_terms")
        self.assertEqual(resolve_election(t,"cash",lottery_selected=True)["cash_per_record_share"],"101/50")
        self.assertEqual(resolve_election(t,"cash",lottery_selected=False)["cash_per_record_share"],"11/25")

    def test_aiv_2020_default_is_prorated_not_all_cash(self):
        r=resolve_election(self.terms["aiv_2020"],"no_election")
        self.assertEqual(r["cash_per_record_share"],"25731/25000")
        self.assertNotEqual(r["shares_per_record_share"],"0")
        self.assertIsNone(r["historical_known_at"])

    def test_stock_choice_is_explicit_and_does_not_mutate_terms(self):
        t=self.terms["aiv_2020"]
        before=deepcopy(t)
        self.assertEqual(resolve_election(t,"stock")["cash_per_record_share"],"0")
        self.assertEqual(t,before)

    def test_rounded_slg_terms_remain_blocked(self):
        for name in ("slg_2021","slg_2022"):
            for election in ("no_election","cash","stock"):
                self.assertEqual(resolve_election(self.terms[name],election)["status"],"blocked_terms")

    def test_unspecified_election_and_negative_terms_rejected(self):
        with self.assertRaises(ValueError):resolve_election(self.terms["aiv_2020"],None)
        t=deepcopy(self.terms["aiv_2020"])
        t["branches"]["stock"]["cash"]="-1"
        with self.assertRaises(ValueError):resolve_election(t,"stock")


class GateTests(TestCase):
    def assess(self,**changes):
        args=dict(material=[],dividends=[],routes=[],feature_events=[],terms_review=dict(feature_corrections=[]),membership_not_before="2016-11-30")
        args.update(changes)
        return assess(**args)

    def test_missing_terms_block_even_with_owner_approval(self):
        r=self.assess(material=[dict(scenario="base",parent_id="A",event_id="E")])
        r["owner_assumptions_approved"]=True
        with self.assertRaises(DiagnosticIntegrationBlocked):require_data_ready(r)

    def test_supported_peak_diagnostic_terms_do_not_promote_strict_evidence(self):
        r=self.assess(material=[dict(scenario="base",event_id="peak_holding_company_reorganization",diagnostic_terms_admitted=True,execution_ready=False)])
        self.assertTrue(r["data_gates_clear"])

    def test_no_owner_assent_blocks_clean_data(self):
        with self.assertRaises(DiagnosticIntegrationBlocked):require_data_ready(self.assess())

    def test_clear_synthetic_data_and_explicit_assent_pass_data_gate_only(self):
        r=self.assess()
        r["owner_assumptions_approved"]=True
        require_data_ready(r)

    def test_reference_only_predecessor_dividend_is_inapplicable(self):
        r=self.assess(dividends=[dict(scenario="base",blockers=["reference_only_predecessor_never_earns_a_portfolio_right"])])
        self.assertTrue(r["data_gates_clear"])

    def test_special_terms_in_reference_record_do_not_become_a_portfolio_event(self):
        # The entire reference-only security is permanently ineligible.
        r=self.assess(dividends=[dict(scenario="base",instrument_id="OLD",event_id="E",blockers=[
            "reference_only_predecessor_never_earns_a_portfolio_right","special_foreign_or_unclassified_distribution_requires_terms"])])
        self.assertTrue(r["data_gates_clear"])

    def test_ordinary_record_missing_payment_is_not_an_approval_gate(self):
        self.assertTrue(self.assess(dividends=[dict(scenario="base",blockers=[],modeled_release_at=None)])["data_gates_clear"])

    def test_feature_correction_requires_uninvested_event(self):
        event=dict(instrument_id="JCI",reason="ADNT")
        correction=dict(instrument_id="JCI",economic_date="2016-10-31",first_regular_session="2016-10-31",no_pre_reset_feature_history=True,source={})
        r=self.assess(feature_events=[event],terms_review=dict(feature_corrections=[correction]))
        self.assertTrue(r["data_gates_clear"])
        self.assertEqual(r["effective_feature_resets"][0]["from_session"],"2016-10-31")
        correction["economic_date"]="2017-01-01"
        self.assertFalse(self.assess(feature_events=[event],terms_review=dict(feature_corrections=[correction]))["data_gates_clear"])

    def test_context_and_superseded_provider_rows_do_not_double_apply(self):
        for state in ("context_only_no_portfolio_credit","wrong_predecessor_ratio_do_not_apply",
                      "represented_by_peak_holding_company_reorganization_do_not_apply_twice"):
            self.assertTrue(self.assess(routes=[dict(disposition=state)])["data_gates_clear"])

    def test_unresolved_provider_action_still_blocks(self):
        self.assertFalse(self.assess(routes=[dict(instrument_id="A",event_id="E",disposition="requires_identity_or_economic_review")])["data_gates_clear"])

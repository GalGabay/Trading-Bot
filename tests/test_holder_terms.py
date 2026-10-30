"""Synthetic offline holder schedules: source binding, timing and routing."""

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from backtesting.broad_collection import pin
from backtesting.diagnostic_accounting import DiagnosticClock, SCENARIOS
from backtesting.diagnostic_preflight import assess
from backtesting.diagnostic_preflight import prepare as prepare_preflight
from backtesting.diagnostic_preparation import prepare
from backtesting.diagnostic_approval import approved_policy
from backtesting.holder_terms import (annotate_election_boundary, apply_spinoff_terms,
                                     gate_due_bill_spinoff, load_holder_terms)
from backtesting.pilot_readiness_review import write_json, write_csv

ROOT = Path(__file__).resolve().parents[1]


class HolderFixture(TestCase):
    def setUp(self):
        for name in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection",
                     "app.broker.research_client._AlpacaCredentials.load"):
            self.enterContext(patch(name, side_effect=AssertionError("Offline fixtures only")))
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        before = Path.cwd()
        os.chdir(temp.name)
        self.addCleanup(os.chdir, before)
        Path("provider.csv").write_bytes(b"synthetic provider inventory\n")
        Path("browser.txt").write_bytes(b"synthetic primary terms\n")
        self.event = dict(id="spin", parent_id="ROOT", root_id="ROOT", kind="retained_parent_spinoff",
            economic_date="2023-10-02", cash_per_parent=None,
            share_legs=[dict(instrument_id="CHILD", shares_per_parent="1/4")])
        self.spec = dict(membership_not_before="2016-11-30", material_events=[self.event], streams=[
            dict(instrument_id="ROOT", root_id="ROOT", role="original_member"),
            dict(instrument_id="CHILD", root_id="ROOT", role="received_security",
                 eligible_for_new_entries_candidate=False, parts=[dict(start="2023-10-02")])])
        self.regular = dict(id="regular", access="primary_browser_text_reviewed", browser_evidence=pin("browser.txt"),
            parent_symbol="P", child_symbol="C", shares_per_parent="1/4", fixed_cash_per_parent="0",
            economic_date="2023-10-02", economic_effective_at="2023-10-02T00:01:00-04:00",
            record_date="2023-09-21", ex_date="2023-10-02", first_regular_session="2023-10-02",
            regular_way_due_bills_start="2023-09-20", regular_way_due_bills_end="2023-09-29",
            regular_way_sale_transfers_child_right=True,
            fractional_treatment="aggregate_sell_net_proceeds_actual_price_and_receipt_unknown")
        self.completion = dict(id="complete", access="primary_audited_plan_filing_browser_text_reviewed",
            economic_date="2023-10-02", record_date="2023-09-21", shares_per_parent="1/4",
            browser_evidence=pin("browser.txt"))
        self.ex_fact = dict(id="ex", access="primary_clearinghouse_browser_pdf_text_reviewed",
                            ex_date="2023-09-21", record_date="2023-09-22", browser_evidence=pin("browser.txt"))
        self.facts = dict(sources=[self.regular, self.completion, self.ex_fact])
        self.provider = dict(id="P1", ex_date="2023-10-02", record_date="2023-09-21", payable_date="2023-10-02",
                             source_symbol="P", new_symbol="C", new_rate="1/4", source_rate="1", due_bill_redemption_date="2023-10-03")
        self.alias_record = dict(id="A1", old_symbol="C.WI", new_symbol="C", old_cusip="123", new_cusip="123")
        self.rows = [dict(instrument_id="ROOT", root_id="ROOT", event_id="P1", category="spin_offs", day="2023-10-02",
                         role="parent_distribution_requires_ownership", record=json.dumps(self.provider)),
                     dict(instrument_id="CHILD", root_id="ROOT", event_id="A1", category="name_changes", day="2023-10-02",
                          role="incoming_alias_requires_identity_review", record=json.dumps(self.alias_record))]
        self.review = dict(schema_version=1, provider_source=pin("provider.csv"), sources=[],
            spinoffs=[dict(event_id="spin", parent_id="ROOT", child_id="CHILD", source_id="issuer",
                           fact_id="regular", completion_fact_id="complete", provider_event_id="P1")],
            regular_start_aliases=[dict(event_id="spin", instrument_id="CHILD", provider_event_id="A1")],
            election_boundaries=[dict(event_id="election", instrument_id="ROOT", source_id="issuer", fact_id="ex")])
        self.clock = DiagnosticClock([dict(opens_at=d+"T13:30:00Z", closes_at=d+"T20:00:00Z") for d in (
            "2023-09-20", "2023-09-21", "2023-09-22", "2023-09-29", "2023-10-02", "2023-10-03", "2023-10-04",
            "2023-10-05", "2023-10-06", "2023-10-09")])
        self.sync()

    def sync(self):
        write_json(Path("spec.json"), self.spec)
        write_json(Path("facts.json"), self.facts)
        self.review.update(spec=pin("spec.json"), sources=[dict(id="issuer", evidence=pin("facts.json"))])
        self.rows[0]["record"] = json.dumps(self.provider)
        self.rows[1]["record"] = json.dumps(self.alias_record)

    def load(self, clock=None):
        write_json(Path("review.json"), self.review)
        return load_holder_terms(Path("review.json"), self.spec, self.rows, pin("provider.csv"), clock or self.clock)

    def plan(self):
        return self.load()[0]["spin"]

    def item(self, scenario="base", plan=None, clock=None):
        item = dict(event_id="spin", parent_id="ROOT", root_id="ROOT", kind="retained_parent_spinoff",
            economic_date="2023-10-02", scenario=scenario, historical_known_at=None,
            prior_close_entitlement_verified=False, actual_delivery_at=None, execution_ready=False,
            blockers=["needs_terms"], share_legs=[dict(instrument_id="CHILD", shares_per_parent="1/4")])
        apply_spinoff_terms(item, plan or self.plan(), clock or self.clock)
        return item

    def items(self):
        plan = self.plan()
        return [self.item(s, plan=plan) for s in SCENARIOS]

    def assess(self, items=None, routes=()):
        return assess(self.items() if items is None else items, [], routes, [],
                      dict(feature_corrections=[]), "2016-11-30")

    def election(self):
        return dict(event_id="election", instrument_id="ROOT", record_date="2023-09-22",
            provider_records=[dict(record=dict(ex_date="2023-09-21"))], blockers=["approximate allocation"],
            selected_conditional_allocation=None, execution_ready=False, actual_broker_received_at=None)


class HolderTermTests(HolderFixture):

    def test_valid_review_preserves_sources_and_provider_rows(self):
        before = deepcopy((self.spec, self.rows, self.review, self.facts))
        plans, aliases, boundaries = self.load()
        self.assertEqual(set(plans), {"spin"})
        self.assertEqual(aliases, {("CHILD", "A1"): "spin"})
        self.assertEqual(set(boundaries), {"election"})
        self.assertEqual((self.spec, self.rows, self.review, self.facts), before)

    def test_entitlement_uses_last_cum_close_not_earlier_record_close(self):
        self.assertEqual(self.plan()["ownership_snapshot_at"], "2023-09-29T20:00:00+00:00")

    def test_three_scenarios_use_exact_saved_opens(self):
        expected = dict(base="2023-10-02T13:30:00+00:00", delayed_five_sessions="2023-10-09T13:30:00+00:00", no_credit=None)
        for item in self.items():
            self.assertEqual(item["share_legs"][0]["modeled_release_at"], expected[item["scenario"]])
            self.assertTrue(gate_due_bill_spinoff(item))

    def test_parent_and_later_rights_preserved_without_fabricated_cash(self):
        item = self.item()
        for flag in ("preserve_parent_quantity", "issue_child_right_once", "rights_survive_later_parent_sale",
                     "invalidate_pending_orders_and_stops", "pending_claims_must_count_toward_equity_and_exposure"):
            self.assertTrue(item[flag])
        self.assertIsNone(item["fractional_cash_fixing"])
        self.assertIsNone(item["modeled_cash_release_at"])
        self.assertFalse(item["execution_ready"])
        self.assertIsNone(item["historical_known_at"])
        self.assertFalse(item["prior_close_entitlement_verified"])

    def test_provider_redemption_date_not_used_as_delivery(self):
        self.assertEqual(self.plan()["provider_due_bill_redemption_date"], "2023-10-03")
        self.assertTrue(self.item()["share_legs"][0]["modeled_release_at"].startswith("2023-10-02"))

    def test_parent_raw_price_features_reset_at_distribution(self):
        reset = self.item()["required_feature_reset"]
        self.assertEqual((reset["instrument_id"], reset["from_session"]), ("ROOT", "2023-10-02"))

    def test_alias_context_creates_no_when_issued_position(self):
        alias = self.plan()["regular_start_aliases"][0]
        self.assertEqual(alias["quantity_effect"], "none_no_when_issued_positions")

    def test_provider_pin_mismatch_rejected(self):
        self.review["provider_source"]["sha256"] = "0"*64
        with self.assertRaises(ValueError): self.load()

    def test_nested_browser_checksum_rejected(self):
        Path("browser.txt").write_bytes(b"changed")
        with self.assertRaises(ValueError): self.load()

    def test_spec_mutation_rejected(self):
        self.spec["membership_not_before"] = "2017-01-01"
        with self.assertRaises(ValueError): self.load()

    def test_duplicate_source_id_rejected(self):
        self.review["sources"] *= 2
        with self.assertRaises(ValueError): self.load()

    def test_duplicate_primary_fact_rejected(self):
        self.facts["sources"].append(deepcopy(self.regular))
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_search_excerpt_cannot_establish_ownership(self):
        self.regular["access"] = "search_only"
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_duplicate_material_spec_identity_rejected(self):
        self.spec["material_events"].append(deepcopy(self.event))
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_duplicate_stream_spec_identity_rejected(self):
        self.spec["streams"].append(deepcopy(self.spec["streams"][1]))
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_duplicate_provider_identity_rejected(self):
        self.rows.append(deepcopy(self.rows[0]))
        with self.assertRaises(ValueError): self.load()

    def test_provider_record_id_mismatch_rejected(self):
        self.provider["id"] = "OTHER"
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_wrong_provider_root_rejected(self):
        self.rows[0]["root_id"] = "OTHER"
        with self.assertRaises(ValueError): self.load()

    def test_wrong_ratio_rejected(self):
        self.regular["shares_per_parent"] = "1/5"
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_completion_date_or_ratio_conflict_rejected(self):
        for field, value in (("economic_date", "2023-10-03"), ("shares_per_parent", "1/5")):
            old = self.completion[field]
            with self.subTest(field=field):
                self.completion[field] = value
                self.sync()
                with self.assertRaises(ValueError): self.load()
                self.completion[field] = old

    def test_fixed_cash_cannot_be_hidden_in_share_only_instruction(self):
        self.event["cash_per_parent"] = "1"
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_child_cannot_be_discretionary_entry_candidate(self):
        self.spec["streams"][1]["eligible_for_new_entries_candidate"] = True
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_child_regular_start_must_match_source(self):
        self.spec["streams"][1]["parts"][0]["start"] = "2023-10-03"
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_due_bill_end_must_match_last_saved_cum_session(self):
        self.regular["regular_way_due_bills_end"] = "2023-09-22"
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_no_transfer_rule_cannot_establish_last_cum_ownership(self):
        self.regular["regular_way_sale_transfers_child_right"] = False
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_invalid_record_date_rejected(self):
        self.regular["record_date"] = self.completion["record_date"] = self.provider["record_date"] = "2023-09-23"
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_effective_timestamp_cannot_come_from_another_year(self):
        self.regular["economic_effective_at"] = "2016-10-02T00:01:00-04:00"
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_future_effective_instant_rejected(self):
        self.regular["economic_effective_at"] = "2023-10-02T16:01:00-04:00"
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_missing_prior_close_rejected(self):
        clock = DiagnosticClock([dict(opens_at="2023-10-02T13:30:00Z", closes_at="2023-10-02T20:00:00Z")])
        with self.assertRaises(ValueError): self.load(clock)

    def test_duplicate_decisions_rejected(self):
        for key in ("spinoffs", "regular_start_aliases", "election_boundaries"):
            old = deepcopy(self.review[key])
            with self.subTest(key=key):
                self.review[key] *= 2
                with self.assertRaises(ValueError): self.load()
                self.review[key] = old

    def test_alias_cusip_change_rejected(self):
        self.alias_record["new_cusip"] = "OTHER"
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_alias_other_than_when_issued_start_rejected(self):
        self.alias_record["old_symbol"] = "UNRELATED"
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_alias_wrong_root_rejected(self):
        self.rows[1]["root_id"] = "OTHER"
        with self.assertRaises(ValueError): self.load()

    def test_applying_to_wrong_event_rejected(self):
        item = self.item()
        item["event_id"] = "OTHER"
        with self.assertRaises(ValueError): apply_spinoff_terms(item, self.plan(), self.clock)

    def test_scenario_without_five_future_opens_remains_pending(self):
        clock = DiagnosticClock([dict(opens_at=d+"T13:30:00Z", closes_at=d+"T20:00:00Z")
            for d in ("2023-09-20", "2023-09-21", "2023-09-22", "2023-09-29", "2023-10-02")])
        plan = self.load(clock)[0]["spin"]
        item = self.item("delayed_five_sessions", plan, clock)
        self.assertIsNone(item["share_legs"][0]["modeled_release_at"])
        self.assertTrue(gate_due_bill_spinoff(item))

    def test_gate_requires_preservation_and_claim_risk_flags(self):
        item = self.item()
        for field in ("preserve_parent_quantity", "issue_child_right_once", "rights_survive_later_parent_sale",
                      "invalidate_pending_orders_and_stops", "pending_claims_must_count_toward_equity_and_exposure"):
            with self.subTest(field=field):
                mutated = deepcopy(item)
                del mutated[field]
                self.assertFalse(gate_due_bill_spinoff(mutated))

    def test_gate_rejects_actual_receipt_and_spendable_cash(self):
        for field, value in (("actual_delivery_at", "2023-10-02"), ("modeled_cash_release_at", "2023-10-03"),
                             ("execution_ready", True), ("fractional_cash_fixing", "1"), ("cash_per_parent", "1")):
            with self.subTest(field=field):
                self.assertFalse(gate_due_bill_spinoff(dict(self.item(), **{field: value})))

    def test_gate_rejects_unknown_scenario(self):
        item = self.item()
        item["scenario"] = "invented"
        self.assertFalse(gate_due_bill_spinoff(item))

    def test_gate_rejects_non_session_release(self):
        item = self.item()
        item["share_legs"][0]["modeled_release_at"] = "2023-10-02T04:02:00Z"
        self.assertFalse(gate_due_bill_spinoff(item))

    def test_gate_rejects_removed_delivery_delay(self):
        item = self.item("delayed_five_sessions")
        item["share_legs"][0]["modeled_release_at"] = "2023-10-02T13:30:00Z"
        self.assertFalse(gate_due_bill_spinoff(item))

    def test_no_credit_cannot_release_shares(self):
        item = self.item("no_credit")
        item["share_legs"][0]["modeled_release_at"] = "2023-10-02T13:30:00Z"
        self.assertFalse(gate_due_bill_spinoff(item))

    def test_all_scenarios_admit_one_canonical_material_event(self):
        result = self.assess()
        self.assertTrue(result["data_gates_clear"])
        self.assertEqual(len(result["effective_feature_resets"]), 1)

    def test_missing_scenario_blocks_admission(self):
        self.assertFalse(self.assess(self.items()[:1])["data_gates_clear"])

    def test_invalid_nonbase_scenario_blocks_admission(self):
        items = self.items()
        items[1]["share_legs"][0]["modeled_release_at"] = items[0]["share_legs"][0]["modeled_release_at"]
        self.assertFalse(self.assess(items)["data_gates_clear"])

    def test_missing_base_scenario_blocks_admission(self):
        self.assertFalse(self.assess(self.items()[1:])["data_gates_clear"])

    def test_scenarios_cannot_have_different_entitlement_ratios(self):
        items = self.items()
        items[1]["holder_terms_review"]["shares_per_parent"] = "1/5"
        items[1]["share_legs"][0]["shares_per_parent"] = "1/5"
        self.assertFalse(self.assess(items)["data_gates_clear"])

    def test_duplicate_scenario_rejected(self):
        items = self.items()
        with self.assertRaises(ValueError): self.assess(items+[deepcopy(items[0])])

    def test_only_canonical_provider_record_is_represented(self):
        route = dict(instrument_id="ROOT", event_id="P1", related_material_events='["spin"]',
                     disposition="represented_by_reviewed_due_bill_spinoff")
        self.assertTrue(self.assess(routes=[route])["data_gates_clear"])
        route["event_id"] = "UNRELATED"
        self.assertFalse(self.assess(routes=[route])["data_gates_clear"])

    def test_alias_route_requires_exact_identity_and_canonical_event(self):
        route = dict(instrument_id="CHILD", event_id="A1", related_material_events=["spin"],
                     disposition="represented_by_reviewed_regular_start_context")
        self.assertTrue(self.assess(routes=[route])["data_gates_clear"])
        route["related_material_events"] = ["OTHER"]
        self.assertFalse(self.assess(routes=[route])["data_gates_clear"])

    def test_source_election_boundary_preserves_allocation_block(self):
        item = self.election()
        annotate_election_boundary(item, self.load()[2]["election"])
        self.assertEqual(item["reviewed_ownership_boundary"]["ownership_snapshot_at"], "2023-09-20T20:00:00+00:00")
        self.assertEqual(item["blockers"], ["approximate allocation"])
        self.assertIsNone(item["selected_conditional_allocation"])
        self.assertFalse(item["execution_ready"])

    def test_election_instrument_record_or_ex_date_conflict_rejected(self):
        boundary = self.load()[2]["election"]
        for field, value in (("instrument_id", "OTHER"), ("record_date", "2023-09-29")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                annotate_election_boundary(dict(self.election(), **{field: value}), boundary)
        item = self.election()
        item["provider_records"][0]["record"]["ex_date"] = "2023-09-22"
        with self.assertRaises(ValueError): annotate_election_boundary(item, boundary)

    def test_election_identity_must_match_boundary(self):
        item = self.election()
        item["event_id"] = "OTHER"
        with self.assertRaises(ValueError): annotate_election_boundary(item, self.load()[2]["election"])


class HolderPreparationTests(HolderFixture):
    def setUp(self):
        super().setUp()
        Path("backtesting").mkdir()
        for name in ("diagnostic_preparation", "diagnostic_preflight", "diagnostic_accounting", "diagnostic_approval",
                     "dividend_components", "diagnostic_event_terms", "corporate_action_terms", "election_schedule",
                     "election_terms", "holder_terms"):
            shutil.copyfile(ROOT/"backtesting"/(name+".py"), Path("backtesting")/(name+".py"))
        sessions = [dict(opens_at=o.isoformat(), closes_at=c.isoformat()) for o,c in zip(self.clock.opens,self.clock.closes)]
        write_json(Path("calendar.json"), sessions)
        self.spec["calendar"] = pin("calendar.json")
        self.rows[0]["query_symbol"] = "P"
        self.rows[1]["query_symbol"] = "C"
        write_csv(Path("provider.csv"), self.rows)
        self.review["provider_source"] = pin("provider.csv")
        self.review["election_boundaries"] = []
        self.sync()
        write_json(Path("review.json"), self.review)
        write_json(Path("decisions.json"), [])
        write_json(Path("terms.json"), dict(sources=[], feature_corrections=[]))
        write_json(Path("mapping.json"), dict(provider_overrides=[], unresolved_feature_events=[]))
        write_json(Path("candidate.json"), dict(event_roles=pin("provider.csv")))
        Path("revision").mkdir()
        revision = dict(inputs={}, spec=pin("spec.json"), mapping=pin("mapping.json"), candidate_report=pin("candidate.json"),
                        performance_ready=False, strict_flags_promoted=False, strategy_runs=0, selected_originals=1, candidate_streams=2)
        write_json(Path("revision/summary.json"), revision)
        proposal = json.loads((ROOT/"docs/broad_diagnostic_accounting_policy.json").read_text(encoding="utf-8"))
        proposal.update(event_decisions=pin("decisions.json"), implementation=[])
        write_json(Path("proposal.json"), proposal)
        Path("owner_review.md").write_bytes(b"Synthetic holder accounting approval\n")
        approval = dict(owner_approved=True, diagnostic_accounting_defaults_approved=True, proposed_policy=pin("proposal.json"),
            resolved_document=pin("owner_review.md"), allocation=dict(total_entry_exposure=.70, per_stock_entry_cap=.05,
            max_positions=20, scope="historical_research_only"), new_performance_batch_authorized=False,
            paper_authorized=False, max_strategy_runs=0, purchases_usd=0)
        write_json(Path("approval.json"), approval)
        write_json(Path("policy.json"), approved_policy(Path("proposal.json"),Path("approval.json")))

    def prepare(self, holder=True):
        return prepare(Path("revision"), Path("policy.json"), Path("prepared"),
                       holder_terms_path=Path("review.json") if holder else None)

    def preflight(self):
        return prepare_preflight(Path("prepared"), Path("terms.json"), Path("preflight"))

    def test_preparation_and_preflight_preserve_scope_and_record_all_scenarios(self):
        summary = self.prepare()
        report = self.preflight()
        self.assertEqual(summary["selected_originals"], 1)
        self.assertEqual(summary["reviewed_due_bill_spinoffs"], 1)
        self.assertEqual(summary["holder_terms_review"], pin("review.json"))
        self.assertTrue(report["data_gates_clear"])
        self.assertFalse(report["engine_adapter_integrated"])
        self.assertFalse(report["performance_authorized"] or report["paper_authorized"])
        self.assertEqual(report["orders"], 0)
        material = json.loads(Path("prepared/material_candidates.json").read_text())
        self.assertEqual({m["scenario"] for m in material}, set(SCENARIOS))
        self.assertTrue(all(gate_due_bill_spinoff(m) for m in material))

    def test_optional_review_absence_keeps_unresolved_events_blocked(self):
        summary = self.prepare(holder=False)
        self.assertIsNone(summary["holder_terms_review"])
        self.assertFalse(self.preflight()["data_gates_clear"])

    def test_unmatched_election_boundary_rejected_before_outputs(self):
        self.review["election_boundaries"] = [dict(event_id="missing", instrument_id="ROOT", source_id="issuer", fact_id="ex")]
        write_json(Path("review.json"), self.review)
        with self.assertRaises(ValueError): self.prepare()
        self.assertFalse(Path("prepared").exists())

    def test_holder_instructions_require_owner_accounting_approval(self):
        policy = json.loads(Path("policy.json").read_text())
        policy["owner_approved"] = False
        write_json(Path("policy.json"), policy)
        with self.assertRaises(ValueError): self.prepare()
        self.assertFalse(Path("prepared").exists())

    def test_changed_holder_review_after_preparation_rejected(self):
        self.prepare()
        Path("review.json").write_bytes(b"{}")
        with self.assertRaises(ValueError): self.preflight()

    def test_changed_nested_holder_browser_evidence_rejected(self):
        self.prepare()
        Path("browser.txt").write_bytes(b"changed after preparation")
        with self.assertRaises(ValueError): self.preflight()

    def test_changed_execution_source_after_preparation_rejected(self):
        self.prepare()
        Path("backtesting/holder_terms.py").write_bytes(b"changed")
        with self.assertRaises(ValueError): self.preflight()

    def test_changed_material_output_after_preparation_rejected(self):
        self.prepare()
        Path("prepared/material_candidates.json").write_bytes(b"[]")
        with self.assertRaises(ValueError): self.preflight()

    def test_preparation_does_not_modify_original_inputs(self):
        files = ["spec.json", "provider.csv", "facts.json", "review.json", "policy.json", "proposal.json", "approval.json"]
        before = {f: Path(f).read_bytes() for f in files}
        self.prepare()
        self.assertEqual({f: Path(f).read_bytes() for f in files}, before)

    def test_preparation_requires_fresh_workspace_output(self):
        self.prepare()
        with self.assertRaises(ValueError): self.prepare()

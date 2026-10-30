"""Offline dividend-component review, accounting and readiness regression tests."""

from copy import deepcopy
from fractions import Fraction
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from backtesting.broad_collection import pin
from backtesting.diagnostic_accounting import DiagnosticClock, SCENARIOS, plan_dividend
from backtesting.diagnostic_preflight import assess
from backtesting.dividend_components import apply_review, load_review
from backtesting.pilot_readiness_review import write_json


class ComponentReviewTests(TestCase):
    def setUp(self):
        for name in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection",
                     "app.broker.research_client._AlpacaCredentials.load"):
            self.enterContext(patch(name, side_effect=AssertionError("Offline fixture only")))
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        before = Path.cwd()
        os.chdir(temp.name)
        self.addCleanup(os.chdir, before)
        Path("provider.csv").write_bytes(b"synthetic pinned provider input\n")
        Path("browser.txt").write_bytes(b"synthetic primary text\n")
        write_json(Path("facts.json"), {"browser_text": pin("browser.txt")})
        self.rows = [self.row("BASE", "0.075"), self.row("TOTAL", "0.15")]
        self.decision = dict(instrument_id="A", ex_date="2023-07-03",
            provider_event_ids=["BASE", "TOTAL"], record_date="2023-07-05",
            payable_date="2023-07-06", source_ids=["issuer"], kind="aggregate_includes_component",
            total_event_id="TOTAL", component_event_id="BASE", total_rate="0.15",
            component_rate="0.075", other_component_rate="0.075")
        self.review = dict(schema_version=1, provider_source=pin("provider.csv"),
            sources=[dict(id="issuer", evidence=pin("facts.json"))], decisions=[self.decision])
        self.clock = DiagnosticClock([dict(opens_at=d+"T13:30:00Z", closes_at=d+"T20:00:00Z")
            for d in ("2023-07-03", "2023-07-05", "2023-07-06", "2023-07-07", "2023-07-10",
                      "2023-07-11", "2023-07-12", "2023-07-13", "2023-07-14", "2023-07-17")])

    def row(self, event_id, rate):
        record = dict(id=event_id, symbol="ABC", ex_date="2023-07-03", record_date="2023-07-05",
                      payable_date="2023-07-06", rate=rate, special=False, foreign=False)
        return dict(category="cash_dividends", instrument_id="A", root_id="A", day="2023-07-03",
                    event_id=event_id, source_key="fixture", record=json.dumps(record))

    def load(self):
        write_json(Path("review.json"), self.review)
        return load_review(Path("review.json"), self.rows, pin("provider.csv"))

    def separate(self):
        self.decision.update(kind="separate_cash_components", rates_by_event_id={"BASE": "0.075", "TOTAL": "0.15"})

    def test_valid_aggregate_covers_both_records_without_mutation(self):
        before = deepcopy((self.rows, self.review))
        self.assertEqual(set(self.load()), {("A", "BASE"), ("A", "TOTAL")})
        self.assertEqual((self.rows, self.review), before)

    def test_source_pin_mismatch_rejected(self):
        self.review["provider_source"]["sha256"] = "0"*64
        with self.assertRaises(ValueError): self.load()

    def test_mutated_evidence_rejected(self):
        Path("facts.json").write_text("altered", encoding="utf-8")
        with self.assertRaises(ValueError): self.load()

    def test_mutated_nested_browser_evidence_rejected(self):
        Path("browser.txt").write_text("altered", encoding="utf-8")
        with self.assertRaises(ValueError): self.load()

    def test_evidence_outside_workspace_rejected(self):
        self.review["sources"][0]["evidence"]["path"] = "../outside.json"
        with self.assertRaises(ValueError): self.load()

    def test_duplicate_evidence_id_rejected(self):
        self.review["sources"].append(deepcopy(self.review["sources"][0]))
        with self.assertRaises(ValueError): self.load()

    def test_missing_evidence_reference_rejected(self):
        self.decision["source_ids"] = ["absent"]
        with self.assertRaises(ValueError): self.load()

    def test_empty_evidence_reference_rejected(self):
        self.decision["source_ids"] = []
        with self.assertRaises(ValueError): self.load()

    def test_unsupported_schema_rejected(self):
        self.review["schema_version"] = 2
        with self.assertRaises(ValueError): self.load()

    def test_incomplete_observed_group_rejected(self):
        self.rows.append(self.row("EXTRA", "0.075"))
        with self.assertRaises(ValueError): self.load()

    def test_duplicate_decision_event_id_rejected(self):
        self.decision["provider_event_ids"] = ["BASE", "BASE", "TOTAL"]
        with self.assertRaises(ValueError): self.load()

    def test_single_record_group_not_deduplicated(self):
        self.rows = self.rows[:1]
        self.decision["provider_event_ids"] = ["BASE"]
        with self.assertRaises(ValueError): self.load()

    def test_overlapping_decisions_rejected(self):
        self.review["decisions"].append(deepcopy(self.decision))
        with self.assertRaises(ValueError): self.load()

    def test_duplicate_provider_identity_not_silently_overwritten(self):
        self.rows.append(self.row("BASE", "99"))
        with self.assertRaises(ValueError): self.load()

    def test_identical_duplicate_provider_row_rejected(self):
        self.rows.append(deepcopy(self.rows[0]))
        with self.assertRaises(ValueError): self.load()

    def test_record_id_disagreement_rejected(self):
        r = json.loads(self.rows[0]["record"])
        r["id"] = "DIFFERENT"
        self.rows[0]["record"] = json.dumps(r)
        with self.assertRaises(ValueError): self.load()

    def test_date_fields_must_match_review(self):
        for field in ("ex_date", "record_date", "payable_date"):
            original = self.decision[field]
            self.decision[field] = "2023-07-07"
            with self.subTest(field=field), self.assertRaises(ValueError): self.load()
            self.decision[field] = original

    def test_unrelated_security_rejected(self):
        self.decision["instrument_id"] = "OTHER"
        with self.assertRaises(ValueError): self.load()

    def test_unknown_decision_kind_rejected(self):
        self.decision["kind"] = "choose_largest"
        with self.assertRaises(ValueError): self.load()

    def test_total_record_must_differ_from_component(self):
        self.decision["total_event_id"] = "BASE"
        with self.assertRaises(ValueError): self.load()

    def test_total_must_equal_component_sum_exactly(self):
        self.decision["other_component_rate"] = "0.075000000000000001"
        with self.assertRaises(ValueError): self.load()

    def test_observed_nominal_rate_cannot_change(self):
        for field in ("total_rate", "component_rate"):
            original = self.decision[field]
            self.decision[field] = "100"
            with self.subTest(field=field), self.assertRaises(ValueError): self.load()
            self.decision[field] = original

    def test_invalid_amounts_rejected(self):
        for amount in ("0", "-1", "NaN", "Infinity", "bad"):
            self.decision["other_component_rate"] = amount
            with self.subTest(amount=amount), self.assertRaises(ValueError): self.load()

    def test_genuine_components_both_retained(self):
        self.separate()
        resolved = self.load()
        items = []
        for row in self.rows:
            item = plan_dividend(row, self.clock, "base")
            apply_review(item, resolved[("A", row["event_id"])])
            items.append(item)
        self.assertEqual(sum(Fraction(i["cash_per_eligible_share"]) for i in items), Fraction("0.225"))
        self.assertTrue(all(i["modeled_release_at"] for i in items))

    def test_separate_components_require_complete_rate_mapping(self):
        self.separate()
        del self.decision["rates_by_event_id"]["BASE"]
        with self.assertRaises(ValueError): self.load()

    def test_separate_components_require_matching_nominal_rates(self):
        self.separate()
        self.decision["rates_by_event_id"]["BASE"] = "0.076"
        with self.assertRaises(ValueError): self.load()

    def test_aggregate_total_counted_once_in_each_scenario(self):
        resolved = self.load()
        for scenario in SCENARIOS:
            items = []
            for row in self.rows:
                item = plan_dividend(row, self.clock, scenario)
                apply_review(item, resolved[("A", row["event_id"])])
                items.append(item)
            with self.subTest(scenario=scenario):
                self.assertEqual(sum(Fraction(i["cash_per_eligible_share"]) for i in items), Fraction("0.15"))
                self.assertEqual(items[0]["provider_record"]["rate"], "0.075")
                self.assertIsNone(items[0]["modeled_release_at"])
                self.assertFalse(items[0]["independent_entitlement"])
                self.assertEqual(items[0]["represented_by_event_id"], "TOTAL")

    def test_review_never_promotes_verified_flags(self):
        item = plan_dividend(self.rows[0], self.clock, "base")
        apply_review(item, self.load()[("A", "BASE")])
        self.assertFalse(item["execution_ready"])
        self.assertFalse(item["known_at_verified"])
        self.assertFalse(item["independently_verified_entitlement"])
        self.assertIsNone(item["actual_broker_received_at"])
        self.assertIsNone(item["historical_known_at"])

    def test_election_cannot_be_credited_as_cash(self):
        self.decision["kind"] = "cash_stock_election_unresolved"
        resolved = self.load()
        for scenario in SCENARIOS:
            for row in self.rows:
                item = plan_dividend(row, self.clock, scenario)
                apply_review(item, resolved[("A", row["event_id"])])
                self.assertIsNone(item["cash_per_eligible_share"])
                self.assertIsNone(item["modeled_release_at"])
                self.assertTrue(item["blockers"])

    def test_foreign_special_and_same_boundary_blocks_survive_review(self):
        item = plan_dividend(self.rows[0], self.clock, "base")
        item["blockers"] = ["foreign", "same_boundary_order"]
        apply_review(item, self.load()[("A", "BASE")])
        self.assertEqual(item["blockers"], ["foreign", "same_boundary_order"])

    def test_unrelated_row_cannot_receive_a_decision(self):
        item = plan_dividend(self.rows[0], self.clock, "base")
        item["instrument_id"] = "WRONG"
        with self.assertRaises(ValueError): apply_review(item, self.load()[("A", "BASE")])

    def test_clean_aggregate_has_no_remaining_cash_gate(self):
        items = []
        resolved = self.load()
        for row in self.rows:
            item = plan_dividend(row, self.clock, "base")
            apply_review(item, resolved[("A", row["event_id"])])
            items.append(item)
        self.assertTrue(assess([], items, [], [], {"feature_corrections": []}, "2016-11-30")["data_gates_clear"])

    def test_election_review_keeps_readiness_blocked(self):
        self.decision["kind"] = "cash_stock_election_unresolved"
        item = plan_dividend(self.rows[0], self.clock, "base")
        apply_review(item, self.load()[("A", "BASE")])
        self.assertFalse(assess([], [item], [], [], {"feature_corrections": []}, "2016-11-30")["data_gates_clear"])

    def test_empty_review_does_not_invent_decisions(self):
        self.review["decisions"] = []
        self.assertEqual(self.load(), {})

    def test_no_credit_never_creates_payment_after_review(self):
        item = plan_dividend(self.rows[1], self.clock, "no_credit")
        apply_review(item, self.load()[("A", "TOTAL")])
        self.assertIsNone(item["modeled_release_at"])

    def test_separate_high_precision_components_do_not_round(self):
        self.separate()
        rate = "0.1234567890123456789012345"
        self.rows[0] = self.row("BASE", rate)
        self.decision["rates_by_event_id"]["BASE"] = rate
        item = plan_dividend(self.rows[0], self.clock, "base")
        apply_review(item, self.load()[("A", "BASE")])
        self.assertEqual(Fraction(item["cash_per_eligible_share"]), Fraction(rate))

    def same_payment(self):
        self.rows[0] = self.row("BASE", "0.15")
        self.decision.update(kind="same_cash_payment_representations", representative_event_id="TOTAL",
            cash_rate="0.15", ex_date_basis="provider_metadata_assumption_not_independently_verified",
            remaining_blockers=[])

    def test_same_payment_has_one_entitlement_and_two_audit_rows(self):
        self.same_payment()
        resolved = self.load()
        items = []
        for row in self.rows:
            item = plan_dividend(row, self.clock, "base")
            apply_review(item, resolved[("A", row["event_id"])])
            items.append(item)
        self.assertEqual(sum(Fraction(i["cash_per_eligible_share"]) for i in items), Fraction("0.15"))
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["represented_by_event_id"], "TOTAL")

    def test_same_payment_cannot_merge_different_amounts(self):
        self.same_payment()
        self.rows[0] = self.row("BASE", "0.075")
        with self.assertRaises(ValueError): self.load()

    def test_same_payment_requires_present_representative(self):
        self.same_payment()
        self.decision["representative_event_id"] = "ABSENT"
        with self.assertRaises(ValueError): self.load()

    def test_payment_review_cannot_claim_verified_ex_date(self):
        self.same_payment()
        self.decision["ex_date_basis"] = "verified"
        with self.assertRaises(ValueError): self.load()

    def test_date_conflict_remains_on_both_representations(self):
        self.same_payment()
        self.decision["remaining_blockers"] = ["conflicting_ex_dates"]
        resolved = self.load()
        for row in self.rows:
            item = plan_dividend(row, self.clock, "base")
            apply_review(item, resolved[("A", row["event_id"])])
            self.assertIn("conflicting_ex_dates", item["blockers"])
        self.assertFalse(assess([], [item], [], [], {"feature_corrections": []}, "2016-11-30")["data_gates_clear"])

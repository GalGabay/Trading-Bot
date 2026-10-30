"""Offline event term, preinvestment exclusion and incoming-record checks."""

from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from backtesting.broad_collection import pin
from backtesting.diagnostic_accounting import DiagnosticClock
from backtesting.diagnostic_event_terms import apply_material_terms, load_event_terms
from backtesting.diagnostic_preflight import assess
from backtesting.pilot_readiness_review import write_json


class EventTermTests(TestCase):
    def setUp(self):
        for name in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection",
                     "app.broker.research_client._AlpacaCredentials.load"):
            self.enterContext(patch(name, side_effect=AssertionError("Offline fixture only")))
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        before = Path.cwd()
        os.chdir(temp.name)
        self.addCleanup(os.chdir, before)
        self.spec = dict(membership_not_before="2016-11-30", streams=[dict(instrument_id="CHILD", root_id="ROOT", role="received_security")],
            material_events=[dict(id="W", parent_id="ROOT", kind="preinvestable_warmup_spinoff", economic_date="2016-10-01"),
                dict(id="S", parent_id="ROOT", kind="successor_spinoff", economic_date="2023-07-03",
                     share_legs=[dict(instrument_id="CHILD", shares_per_parent="1/5")])])
        write_json(Path("spec.json"), self.spec)
        Path("provider.csv").write_bytes(b"synthetic input\n")
        Path("browser.txt").write_bytes(b"synthetic primary text\n")
        self.facts = dict(browser_text=pin("browser.txt"), sources=[dict(id="primary", access="primary_browser_text_reviewed",
                            economic_date="2023-07-03", shares_per_parent="1/5")])
        write_json(Path("facts.json"), self.facts)
        self.rows = [dict(instrument_id="CHILD", root_id="ROOT", event_id="P", category="spin_offs",
            role="other_security_unattached", query_symbol="NEW", record=json.dumps(dict(source_symbol="PARENT", new_symbol="NEW")))]
        self.warmup = dict(event_id="W", parent_id="ROOT", economic_date="2016-10-01", kind="uninvested_warmup_event")
        self.ratio = dict(event_id="S", parent_id="ROOT", economic_date="2023-07-03", kind="primary_ratio_reviewed_other_terms_unresolved",
            child_id="CHILD", shares_per_parent="1/5", source_ids=["issuer"], primary_fact_id="primary")
        self.context = dict(instrument_id="CHILD", event_id="P", source_symbol="PARENT", received_symbol="NEW")
        self.review = dict(schema_version=1, provider_source=pin("provider.csv"), spec=pin("spec.json"),
            sources=[dict(id="issuer", evidence=pin("facts.json"))], material_decisions=[self.warmup, self.ratio],
            provider_context_decisions=[self.context])
        self.clock = DiagnosticClock([dict(opens_at=d+"T13:30:00Z", closes_at=d+"T20:00:00Z")
            for d in ("2016-09-30", "2016-10-03", "2016-10-04", "2016-11-30", "2023-07-03", "2023-07-05")])

    def load(self):
        write_json(Path("review.json"), self.review)
        return load_event_terms(Path("review.json"), self.spec, self.rows, pin("provider.csv"))

    def candidate(self, event_id="W", scenario="base"):
        d = self.warmup if event_id=="W" else self.ratio
        return dict(event_id=event_id, parent_id="ROOT", economic_date=d["economic_date"], scenario=scenario,
            share_legs=[dict(instrument_id="CHILD", modeled_release_at="placeholder")], modeled_cash_release_at=None,
            status="candidate_economic_terms_unresolved", blockers=["needs_review"],
            execution_ready=False, actual_delivery_at=None)

    def test_valid_overlay_preserves_inputs(self):
        before = deepcopy((self.spec, self.rows, self.review))
        events, routes = self.load()
        self.assertEqual(set(events), {"W", "S"})
        self.assertEqual(set(routes), {("CHILD", "P")})
        self.assertEqual((self.spec, self.rows, self.review), before)

    def test_warmup_has_no_credit_and_resets_first_saved_session(self):
        item = self.candidate()
        apply_material_terms(item, self.load()[0]["W"], self.clock)
        self.assertEqual(item["required_feature_reset"]["from_session"], "2016-10-03")
        self.assertTrue(item["no_portfolio_entitlement"])
        self.assertIsNone(item["share_legs"][0]["modeled_release_at"])
        self.assertFalse(item["execution_ready"])
        self.assertIsNone(item["actual_delivery_at"])

    def test_warmup_gate_clears_with_explicit_feature_reset(self):
        item = self.candidate()
        apply_material_terms(item, self.load()[0]["W"], self.clock)
        result = assess([item], [], [], [], {"feature_corrections": []}, "2016-11-30")
        self.assertTrue(result["data_gates_clear"])
        self.assertEqual(len(result["effective_feature_resets"]), 1)

    def test_warmup_cannot_exempt_event_after_membership(self):
        item = self.candidate()
        apply_material_terms(item, self.load()[0]["W"], self.clock)
        item["economic_date"] = "2017-01-01"
        self.assertFalse(assess([item], [], [], [], {"feature_corrections": []}, "2016-11-30")["data_gates_clear"])

    def test_warmup_without_reset_stays_blocked(self):
        item = self.candidate()
        item.update(status="inapplicable_preinvestable_event", no_portfolio_entitlement=True)
        self.assertFalse(assess([item], [], [], [], {"feature_corrections": []}, "2016-11-30")["data_gates_clear"])

    def test_wrong_reset_parent_stays_blocked(self):
        item = self.candidate()
        apply_material_terms(item, self.load()[0]["W"], self.clock)
        item["required_feature_reset"]["instrument_id"] = "WRONG"
        self.assertFalse(assess([item], [], [], [], {"feature_corrections": []}, "2016-11-30")["data_gates_clear"])

    def test_investable_event_cannot_be_classified_as_warmup(self):
        self.ratio["kind"] = "uninvested_warmup_event"
        with self.assertRaises(ValueError): self.load()

    def test_wrong_economic_date_rejected(self):
        self.warmup["economic_date"] = "2016-09-30"
        with self.assertRaises(ValueError): self.load()

    def test_duplicated_material_decision_rejected(self):
        self.review["material_decisions"].append(deepcopy(self.warmup))
        with self.assertRaises(ValueError): self.load()

    def test_primary_ratio_does_not_clear_other_terms(self):
        item = self.candidate("S")
        apply_material_terms(item, self.load()[0]["S"], self.clock)
        self.assertTrue(item["primary_share_ratio_reviewed"])
        self.assertFalse(item["execution_ready"])
        self.assertTrue(item["blockers"])
        self.assertFalse(assess([item], [], [], [], {"feature_corrections": []}, "2016-11-30")["data_gates_clear"])

    def test_wrong_ratio_rejected(self):
        self.ratio["shares_per_parent"] = "1/4"
        with self.assertRaises(ValueError): self.load()

    def test_wrong_child_rejected(self):
        self.ratio["child_id"] = "OTHER"
        with self.assertRaises(ValueError): self.load()

    def test_search_only_fact_cannot_become_primary(self):
        self.facts["sources"][0]["access"] = "search_only"
        write_json(Path("facts.json"), self.facts)
        self.review["sources"][0]["evidence"] = pin("facts.json")
        with self.assertRaises(ValueError): self.load()

    def test_missing_primary_fact_rejected(self):
        self.ratio["primary_fact_id"] = "absent"
        with self.assertRaises(ValueError): self.load()

    def test_mutated_browser_pin_rejected(self):
        Path("browser.txt").write_bytes(b"altered")
        with self.assertRaises(ValueError): self.load()

    def test_changed_spec_rejected(self):
        self.spec["membership_not_before"] = "2016-01-01"
        with self.assertRaises(ValueError): self.load()

    def test_incoming_context_does_not_apply_to_parent_holder_row(self):
        self.rows[0]["role"] = "parent_distribution_requires_ownership"
        with self.assertRaises(ValueError): self.load()

    def test_incoming_context_requires_received_security(self):
        self.spec["streams"][0]["role"] = "original_member"
        write_json(Path("spec.json"), self.spec)
        self.review["spec"] = pin("spec.json")
        with self.assertRaises(ValueError): self.load()

    def test_context_mismatched_source_or_child_rejected(self):
        for field in ("source_symbol", "received_symbol"):
            old = self.context[field]
            self.context[field] = "WRONG"
            with self.subTest(field=field), self.assertRaises(ValueError): self.load()
            self.context[field] = old

    def test_duplicated_context_decision_rejected(self):
        self.review["provider_context_decisions"].append(deepcopy(self.context))
        with self.assertRaises(ValueError): self.load()

    def test_applying_material_decision_to_wrong_event_rejected(self):
        with self.assertRaises(ValueError): apply_material_terms(self.candidate("S"), self.warmup, self.clock)

    def test_incoming_context_cannot_hide_material_parent_block(self):
        item = self.candidate("S")
        apply_material_terms(item, self.load()[0]["S"], self.clock)
        result = assess([item], [], [dict(disposition="context_only_no_portfolio_credit")], [], {"feature_corrections": []}, "2016-11-30")
        self.assertFalse(result["data_gates_clear"])
        self.assertEqual(result["blockers"][0]["kind"], "material_terms")

"""Offline checks of gross cash rights; no fabricated payment or buying power."""

from copy import deepcopy
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


class CashMergerTermTests(TestCase):
    def setUp(self):
        for name in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection",
                     "app.broker.research_client._AlpacaCredentials.load"):
            self.enterContext(patch(name, side_effect=AssertionError("Offline fixture only")))
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        before = Path.cwd()
        os.chdir(temp.name)
        self.addCleanup(os.chdir, before)
        Path("provider.csv").write_bytes(b"synthetic provider\n")
        Path("browser.txt").write_bytes(b"synthetic cash merger notice\n")
        self.event = dict(id="cash_X", parent_id="ROOT", kind="cash_merger", economic_date="2022-10-11",
                          cash_per_parent="28", share_legs=[])
        self.spec = dict(membership_not_before="2016-11-30", material_events=[self.event], streams=[
            dict(instrument_id="ROOT", parts=[dict(end_exclusive="2022-10-12")])])
        self.fact = dict(id="primary", access="primary_browser_text_reviewed", all_common_holders_supported=True,
                         currency="USD", event_id="cash_X", economic_date="2022-10-11", cash_per_parent="28",
                         cash_receipt_date=None, browser_evidence=pin("browser.txt"))
        self.decision = dict(event_id="cash_X", parent_id="ROOT", economic_date="2022-10-11",
            kind="primary_cash_consideration_reviewed", source_ids=["issuer"], primary_fact_id="primary",
            cash_per_parent="28", first_nontradeable_session="2022-10-12")
        self.review = dict(schema_version=1, provider_source=pin("provider.csv"), sources=[],
                           material_decisions=[self.decision], provider_context_decisions=[])
        self.clock = DiagnosticClock([dict(opens_at=d+"T13:30:00Z", closes_at=d+"T20:00:00Z")
            for d in ("2022-10-10", "2022-10-11", "2022-10-12")])

    def load(self):
        write_json(Path("spec.json"), self.spec)
        write_json(Path("facts.json"), dict(sources=[self.fact]))
        self.review.update(spec=pin("spec.json"), sources=[dict(id="issuer", evidence=pin("facts.json"))])
        write_json(Path("review.json"), self.review)
        return load_event_terms(Path("review.json"), self.spec, [], pin("provider.csv"))[0]["cash_X"]

    def candidate(self, scenario="base"):
        return dict(event_id="cash_X", parent_id="ROOT", kind="cash_merger", economic_date="2022-10-11",
                    scenario=scenario, share_legs=[], execution_ready=False, historical_known_at=None,
                    prior_close_entitlement_verified=False, blockers=["unresolved"], actual_delivery_at=None)

    def test_valid_gross_cash_terms_are_source_bound(self):
        before = deepcopy(self.decision)
        self.assertEqual(self.load(), before)

    def test_boundary_uses_first_nontradeable_open_and_prior_close(self):
        item = self.candidate()
        apply_material_terms(item, self.load(), self.clock)
        self.assertTrue(item["modeled_accounting_at"].startswith("2022-10-12T13:30"))
        self.assertTrue(item["required_ownership_snapshot_at"].startswith("2022-10-11T20:00"))

    def test_all_scenarios_keep_cash_unspendable(self):
        for scenario in ("base", "delayed_five_sessions", "no_credit"):
            with self.subTest(scenario=scenario):
                item = self.candidate(scenario)
                apply_material_terms(item, self.load(), self.clock)
                self.assertIsNone(item["modeled_cash_release_at"])
                self.assertIsNone(item["actual_delivery_at"])
                self.assertFalse(item["execution_ready"])
                self.assertFalse(item["prior_close_entitlement_verified"])
                self.assertIsNone(item["historical_known_at"])

    def test_parent_consumed_once_and_stale_execution_invalidated(self):
        item = self.candidate()
        apply_material_terms(item, self.load(), self.clock)
        self.assertTrue(item["consume_parent_once"])
        self.assertTrue(item["invalidate_pending_orders_and_stops"])
        self.assertEqual(item["cash_per_parent"], "28")

    def test_tender_only_evidence_cannot_admit_all_common_holders(self):
        self.fact["all_common_holders_supported"] = False
        with self.assertRaises(ValueError): self.load()

    def test_non_usd_consideration_requires_new_policy(self):
        self.fact["currency"] = "EUR"
        with self.assertRaises(ValueError): self.load()

    def test_price_conflict_rejected(self):
        self.fact["cash_per_parent"] = "27"
        with self.assertRaises(ValueError): self.load()

    def test_unsupported_receipt_date_not_silently_accepted(self):
        self.fact["cash_receipt_date"] = "2022-10-12"
        with self.assertRaises(ValueError): self.load()

    def test_wrong_terminal_boundary_rejected(self):
        self.decision["first_nontradeable_session"] = "2022-10-11"
        with self.assertRaises(ValueError): self.load()

    def test_boundary_cannot_precede_legal_completion(self):
        self.event["economic_date"] = self.decision["economic_date"] = self.fact["economic_date"] = "2022-10-13"
        with self.assertRaises(ValueError): self.load()

    def test_cash_only_review_cannot_hide_share_leg(self):
        self.event["share_legs"] = [dict(instrument_id="CHILD", shares_per_parent="1")]
        with self.assertRaises(ValueError): self.load()

    def test_missing_saved_boundary_open_rejected(self):
        clock = DiagnosticClock([dict(opens_at="2022-10-11T13:30:00Z", closes_at="2022-10-11T20:00:00Z")])
        with self.assertRaises(ValueError): apply_material_terms(self.candidate(), self.load(), clock)

    def test_missing_prior_ownership_close_rejected(self):
        clock = DiagnosticClock([dict(opens_at="2022-10-12T13:30:00Z", closes_at="2022-10-12T20:00:00Z")])
        with self.assertRaises(ValueError): apply_material_terms(self.candidate(), self.load(), clock)

    def test_preflight_admits_right_but_not_cash_availability(self):
        item = self.candidate()
        apply_material_terms(item, self.load(), self.clock)
        result = assess([item], [], [], [], dict(feature_corrections=[]), "2016-11-30")
        self.assertTrue(result["data_gates_clear"])
        self.assertIsNone(item["modeled_cash_release_at"])

    def test_preflight_rejects_cash_release_or_missing_once_only_safeguard(self):
        item = self.candidate()
        apply_material_terms(item, self.load(), self.clock)
        for field, value in (("modeled_cash_release_at", "2022-10-12T13:30:00Z"), ("consume_parent_once", False),
                             ("invalidate_pending_orders_and_stops", False), ("actual_delivery_at", "2022-10-12")):
            with self.subTest(field=field):
                result = assess([dict(item, **{field: value})], [], [], [], dict(feature_corrections=[]), "2016-11-30")
                self.assertFalse(result["data_gates_clear"])

    def test_provider_cash_duplicate_requires_matching_admitted_event(self):
        item = self.candidate()
        apply_material_terms(item, self.load(), self.clock)
        route = dict(instrument_id="ROOT", event_id="provider", disposition="represented_by_reviewed_cash_merger",
                     related_material_events='["cash_X"]')
        self.assertTrue(assess([item], [], [route], [], dict(feature_corrections=[]), "2016-11-30")["data_gates_clear"])
        route["related_material_events"] = '["OTHER"]'
        self.assertFalse(assess([item], [], [route], [], dict(feature_corrections=[]), "2016-11-30")["data_gates_clear"])

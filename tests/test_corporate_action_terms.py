"""Synthetic, offline tests of reviewed action instructions and admission."""

from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from backtesting.broad_collection import pin
from backtesting.corporate_action_terms import gate_action, load_actions
from backtesting.diagnostic_accounting import DiagnosticClock
from backtesting.diagnostic_preflight import assess
from backtesting.pilot_readiness_review import write_json


class CorporateActionTermTests(TestCase):
    def setUp(self):
        for name in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection",
                     "app.broker.research_client._AlpacaCredentials.load"):
            self.enterContext(patch(name, side_effect=AssertionError("Offline fixture only")))
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        before = Path.cwd()
        os.chdir(temp.name)
        self.addCleanup(os.chdir, before)
        Path("provider.csv").write_bytes(b"synthetic inventory\n")
        Path("browser.txt").write_bytes(b"synthetic primary evidence\n")
        self.spec = dict(membership_not_before="2016-11-30", streams=[dict(instrument_id="ROOT", parts=[
            dict(source_key="old", start="2016-01-01", end_exclusive="2020-08-31"),
            dict(source_key="new", start="2020-08-31", end_exclusive="2024-01-01")])])
        self.facts = dict(sources=[
            dict(id="alias", access="primary_browser_text_reviewed", url="https://example.invalid/alias",
                 browser_evidence=pin("browser.txt"), old_symbol="OLD", new_symbol="NEW", same_instrument=True,
                 first_session="2020-08-31", session_basis="reviewed_first_session"),
            dict(id="split", access="primary_browser_text_reviewed", url="https://example.invalid/split",
                 browser_evidence=pin("browser.txt"), new_shares_per_old="4", first_adjusted_session="2020-08-31")])
        self.rows = [
            dict(instrument_id="ROOT", root_id="ROOT", event_id="A", category="name_changes", day="2020-09-01",
                 record=json.dumps(dict(id="A", old_symbol="OLD", new_symbol="NEW"))),
            dict(instrument_id="ROOT", root_id="ROOT", event_id="S", category="forward_splits", day="2020-08-31",
                 record=json.dumps(dict(id="S", new_rate=4, old_rate=1))),
            dict(instrument_id="ROOT", root_id="ROOT", event_id="W", category="forward_splits", day="2016-10-03",
                 record=json.dumps(dict(id="W", new_rate=2, old_rate=1)))]
        self.review = dict(schema_version=1, provider_source=pin("provider.csv"), sources=[], decisions=[
            dict(instrument_id="ROOT", event_id="A", provider_day="2020-09-01", kind="same_instrument_alias",
                 source_id="issuer", fact_id="alias", old_source_key="old", new_source_key="new"),
            dict(instrument_id="ROOT", event_id="S", provider_day="2020-08-31", kind="ordinary_split",
                 source_id="issuer", fact_id="split"),
            dict(instrument_id="ROOT", event_id="W", provider_day="2016-10-03", kind="preinvestment_reference_action")])
        self.clock = DiagnosticClock([dict(opens_at=d+"T13:30:00Z", closes_at=d+"T20:00:00Z")
            for d in ("2016-10-03", "2016-11-30", "2020-08-28", "2020-08-31", "2020-09-01")])
        self.sync()

    def sync(self):
        write_json(Path("spec.json"), self.spec)
        write_json(Path("facts.json"), self.facts)
        self.review["spec"] = pin("spec.json")
        self.review["sources"] = [dict(id="issuer", evidence=pin("facts.json"))]

    def load(self):
        write_json(Path("review.json"), self.review)
        return load_actions(Path("review.json"), self.spec, self.rows, pin("provider.csv"), self.clock)

    def action(self, event="S"):
        return self.load()[("ROOT", event)]

    def test_valid_instructions_preserve_inputs(self):
        before = deepcopy((self.spec, self.rows, self.review, self.facts))
        actions = self.load()
        self.assertEqual(len(actions), 3)
        self.assertTrue(all(gate_action(a, "2016-11-30") for a in actions.values()))
        self.assertEqual((self.spec, self.rows, self.review, self.facts), before)

    def test_alias_uses_reviewed_session_instead_of_late_provider_notice(self):
        action = self.action("A")
        self.assertTrue(action["effective_at"].startswith("2020-08-31"))
        self.assertTrue(action["provider_date_differs_from_effective_session"])
        self.assertEqual(action["share_multiplier"], "1")
        self.assertTrue(action["preserve_position_age"] and action["preserve_feature_history"])
        self.assertTrue(action["invalidate_symbol_bound_execution_state"])

    def test_split_keeps_basis_and_rebases_unfixed_rights(self):
        action = self.action()
        self.assertEqual(action["share_multiplier"], "4")
        for flag in ("preserve_total_cost_basis", "rebase_stops_and_per_share_basis", "rebase_pending_share_rights", "invalidate_pending_orders"):
            self.assertTrue(action[flag])
        self.assertEqual(action["cash_delta"], "0")
        self.assertEqual(action["fractional_policy"], "pending_share_claim_no_automatic_cash")

    def test_preinvestment_action_only_resets_features(self):
        action = self.action("W")
        self.assertEqual(action["quantity_effect"], "none_no_portfolio_holdings")
        self.assertEqual(action["required_feature_reset"]["from_session"], "2016-10-03")
        self.assertFalse(action["execution_ready"])

    def test_daily_split_convention_uses_first_saved_open_after_distribution(self):
        fact = self.facts["sources"][1]
        del fact["first_adjusted_session"]
        fact["distribution_date"] = "2020-08-28"
        self.sync()
        self.assertIn("daily_convention", self.action()["effective_session_basis"])

    def test_clearinghouse_primary_evidence_is_accepted(self):
        self.facts["sources"][1]["access"] = "primary_clearinghouse_browser_pdf_text_reviewed"
        self.sync()
        self.assertEqual(self.action()["share_multiplier"], "4")

    def test_provider_pin_mismatch_rejected(self):
        self.review["provider_source"]["sha256"] = "0"*64
        with self.assertRaises(ValueError): self.load()

    def test_mutated_nested_evidence_rejected(self):
        Path("browser.txt").write_bytes(b"changed")
        with self.assertRaises(ValueError): self.load()

    def test_changed_spec_rejected(self):
        self.spec["membership_not_before"] = "2016-01-01"
        with self.assertRaises(ValueError): self.load()

    def test_repeated_source_rejected(self):
        self.review["sources"] *= 2
        with self.assertRaises(ValueError): self.load()

    def test_repeated_decision_rejected(self):
        self.review["decisions"].append(deepcopy(self.review["decisions"][0]))
        with self.assertRaises(ValueError): self.load()

    def test_repeated_provider_identity_rejected(self):
        self.rows.append(deepcopy(self.rows[0]))
        with self.assertRaises(ValueError): self.load()

    def test_missing_provider_event_rejected(self):
        self.rows.pop()
        with self.assertRaises(ValueError): self.load()

    def test_changed_provider_record_identity_rejected(self):
        self.rows[0]["record"] = json.dumps(dict(id="WRONG"))
        with self.assertRaises(ValueError): self.load()

    def test_changed_provider_day_rejected(self):
        self.rows[0]["day"] = "2020-09-02"
        with self.assertRaises(ValueError): self.load()

    def test_search_excerpt_cannot_establish_action(self):
        self.facts["sources"][0]["access"] = "search_only"
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_merger_cannot_masquerade_as_alias(self):
        self.facts["sources"][0]["same_instrument"] = False
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_wrong_alias_symbol_rejected(self):
        self.facts["sources"][0]["new_symbol"] = "OTHER"
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_discontinuous_alias_segments_rejected(self):
        self.spec["streams"][0]["parts"][0]["end_exclusive"] = "2020-08-28"
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_wrong_split_ratio_rejected(self):
        self.facts["sources"][1]["new_shares_per_old"] = "3"
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_zero_split_denominator_rejected(self):
        self.rows[1]["record"] = json.dumps(dict(id="S", new_rate=4, old_rate=0))
        with self.assertRaises(ValueError): self.load()

    def test_wrong_primary_split_session_rejected(self):
        self.facts["sources"][1]["first_adjusted_session"] = "2020-08-28"
        self.sync()
        with self.assertRaises(ValueError): self.load()

    def test_postmembership_action_cannot_use_warmup_exclusion(self):
        self.review["decisions"][1]["kind"] = "preinvestment_reference_action"
        with self.assertRaises(ValueError): self.load()

    def test_gate_rejects_missing_common_safeguards(self):
        action = self.action()
        for field, value in (("execution_ready", True), ("actual_broker_received_at", "2020-08-31"),
                             ("historical_known_at", "2020-08-01"), ("cash_delta", "1"),
                             ("blockers", ["unresolved"]), ("effective_at", None)):
            with self.subTest(field=field):
                self.assertFalse(gate_action(dict(action, **{field: value}), "2016-11-30"))

    def test_alias_gate_requires_preservation_and_execution_invalidation(self):
        action = self.action("A")
        for flag in ("preserve_feature_history", "preserve_position_age", "invalidate_symbol_bound_execution_state"):
            with self.subTest(flag=flag):
                item = deepcopy(action)
                del item[flag]
                self.assertFalse(gate_action(item, "2016-11-30"))

    def test_split_gate_requires_pending_right_rebasing(self):
        action = self.action()
        del action["rebase_pending_share_rights"]
        self.assertFalse(gate_action(action, "2016-11-30"))

    def test_gate_malformed_split_ratio_stays_blocked(self):
        action = self.action()
        action["share_multiplier"] = "unknown"
        self.assertFalse(gate_action(action, "2016-11-30"))

    def test_preflight_requires_matching_action_for_route(self):
        route = dict(instrument_id="ROOT", event_id="S", disposition="handled_by_reviewed_corporate_action")
        self.assertFalse(assess([], [], [route], [], dict(feature_corrections=[]), "2016-11-30")["data_gates_clear"])
        self.assertTrue(assess([], [], [route], [], dict(feature_corrections=[]), "2016-11-30",
                               corporate_actions=[self.action()])["data_gates_clear"])

    def test_preflight_rejects_repeated_instructions(self):
        action = self.action()
        with self.assertRaises(ValueError):
            assess([], [], [], [], dict(feature_corrections=[]), "2016-11-30", corporate_actions=[action, action])

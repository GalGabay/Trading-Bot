"""Offline owner-policy, conditional allocation and calendar-order tests."""

from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from backtesting.broad_collection import pin
from backtesting.diagnostic_accounting import DiagnosticClock
from backtesting.diagnostic_preflight import assess
from backtesting.election_schedule import apply_holder_policy, compile_schedules, load_holder_policy
from backtesting.election_terms import resolve_election
from backtesting.pilot_readiness_review import write_json


class ElectionScheduleTests(TestCase):
    def setUp(self):
        for name in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection",
                     "app.broker.research_client._AlpacaCredentials.load"):
            self.enterContext(patch(name, side_effect=AssertionError("Offline fixture only")))
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        before = Path.cwd()
        os.chdir(temp.name)
        self.addCleanup(os.chdir, before)
        Path("proposal.md").write_bytes(b"Synthetic proposal: follow documented no-election defaults.\n")
        Path("browser.txt").write_bytes(b"Synthetic issuer notice.\n")
        self.approval = dict(schema_version=1, owner_approved=True, choice="no_election",
            scope="historical_research_only", proposal=pin("proposal.md"), purchases_usd=0,
            unknown_defaults_may_be_assumed=False, rounded_allocations_approved=False,
            missing_entitlement_may_be_assumed=False, actual_broker_receipt_may_be_inferred=False,
            performance_authorized=False, paper_authorized=False, broker_requests_authorized=False)
        self.inputs = dict(holder_election_selected="no_election")
        self.term = dict(id="aiv_2019", record_date="2019-02-22", payable_date="2019-03-22",
            published_date="2019-03-22", source=pin("browser.txt"), no_election_branch="prorated_cash",
            share_allocation_approximate=False, stock_conversion_price="49.93", cash_lottery=True,
            branches=dict(prorated_cash=dict(cash="0.44", stock_value="1.58"),
                          stock=dict(cash="0", stock_value="2.02"), lottery_cash=dict(cash="2.02", stock_value="0")))
        self.terms = dict(sources=[dict(browser_text=pin("browser.txt"))], election_terms=[self.term])
        self.splits = dict(sources=[dict(id="aiv_2019", facts=dict(first_adjusted_session="2019-02-21",
                                                                  new_shares_per_old="100/101"))])
        self.resolution = dict(sources=[])
        self.mac = dict(sources=[dict(id="mac", browser_evidence=pin("browser.txt"), facts=dict(
            record_date="2020-04-22", payable_date="2020-06-03", total_dividend_value="0.50"))])
        self.rows = [dict(instrument_id="COHORT-2016-0046", category="cash_dividends", event_id="A",
            record=json.dumps(dict(id="A", record_date="2019-02-22", payable_date="2019-03-22"))),
            dict(instrument_id="COHORT-2016-0288", category="cash_dividends", event_id="M",
            record=json.dumps(dict(id="M", record_date="2020-04-22", payable_date="2020-06-03")))]
        self.clock = DiagnosticClock([dict(opens_at=d+"T14:30:00Z", closes_at=d+"T21:00:00Z")
            for d in ("2019-02-21", "2019-02-22", "2019-03-22", "2019-03-25",
                      "2020-04-22", "2020-06-03", "2021-12-15", "2022-01-18", "2022-01-24")])

    def policy(self):
        write_json(Path("approval.json"), self.approval)
        self.inputs["holder_election_approval"] = pin("approval.json")
        return load_holder_policy(self.inputs)

    def compile(self, approved=False):
        for name, obj in (("terms", self.terms), ("splits", self.splits), ("resolution", self.resolution), ("mac", self.mac)):
            write_json(Path(name+".json"), obj)
        return compile_schedules(self.rows, self.clock, *(Path(n+".json") for n in ("terms", "splits", "resolution", "mac")),
                                 holder_policy=self.policy() if approved else None)

    def test_no_selection_preserves_pending_policy(self):
        self.assertIsNone(load_holder_policy({}))

    def test_selection_requires_separate_approval(self):
        with self.assertRaises(ValueError): load_holder_policy(self.inputs)

    def test_orphan_approval_rejected(self):
        with self.assertRaises(ValueError): load_holder_policy(dict(holder_election_approval={}))

    def test_approved_policy_validates_pins_and_preserves_inputs(self):
        record = self.policy()
        self.assertEqual(record["choice"], "no_election")
        self.assertEqual(record["approval"], pin("approval.json"))
        self.assertNotIn("approval", self.approval)

    def test_unsupported_selection_rejected(self):
        self.inputs["holder_election_selected"] = "cash"
        with self.assertRaises(ValueError): self.policy()

    def test_approval_scope_and_choice_must_match(self):
        for field, value in (("scope", "paper"), ("choice", "stock"), ("owner_approved", False), ("schema_version", 2)):
            old = self.approval[field]
            with self.subTest(field=field):
                self.approval[field] = value
                with self.assertRaises(ValueError): self.policy()
                self.approval[field] = old

    def test_restrictions_cannot_be_relaxed_or_omitted(self):
        for field in ("unknown_defaults_may_be_assumed", "rounded_allocations_approved", "missing_entitlement_may_be_assumed",
                      "actual_broker_receipt_may_be_inferred", "performance_authorized", "paper_authorized", "broker_requests_authorized"):
            for value in (True, None, 0):
                with self.subTest(field=field, value=value):
                    self.approval[field] = value
                    with self.assertRaises(ValueError): self.policy()
            self.approval[field] = False

    def test_purchase_budget_requires_exact_integer_zero(self):
        for value in (1, False, 0.0, "0", None):
            with self.subTest(value=value):
                self.approval["purchases_usd"] = value
                with self.assertRaises(ValueError): self.policy()

    def test_changed_approval_bytes_rejected(self):
        self.policy()
        Path("approval.json").write_bytes(b"{}")
        with self.assertRaises(ValueError): load_holder_policy(self.inputs)

    def test_changed_proposal_bytes_rejected(self):
        self.policy()
        Path("proposal.md").write_bytes(b"changed")
        with self.assertRaises(ValueError): load_holder_policy(self.inputs)

    def test_compile_does_not_mutate_source_terms(self):
        before = deepcopy((self.term, self.terms, self.rows, self.splits))
        self.compile(approved=True)
        self.assertEqual((self.term, self.terms, self.rows, self.splits), before)

    def test_unapproved_schedules_keep_election_pending(self):
        for schedule in self.compile():
            self.assertIsNone(schedule["selected_holder_election"])
            self.assertFalse(schedule["execution_ready"])

    def test_approved_default_has_exact_conditional_allocation(self):
        schedule = self.compile(approved=True)[0]
        self.assertEqual(schedule["selected_holder_election"], "no_election")
        self.assertEqual(schedule["selected_conditional_allocation"]["cash_per_record_share"], "11/25")
        self.assertEqual(schedule["selected_conditional_allocation"]["shares_per_record_share"], "158/4993")
        self.assertFalse(schedule["historical_ex_date_verified"])
        self.assertFalse(schedule["execution_ready"])
        self.assertIsNone(schedule["actual_broker_received_at"])
        self.assertTrue(schedule["blockers"])

    def test_pre_record_split_precedes_record_snapshot(self):
        schedule = self.compile()[0]
        self.assertTrue(schedule["split_precedes_record_snapshot"])
        self.assertEqual(schedule["required_operation_order"][0], "split_existing_lots")
        self.assertFalse(schedule["undelivered_share_rights_need_unit_rebasing"])

    def test_post_issue_split_rebases_unfixed_rights_not_cash(self):
        self.splits["sources"][0]["facts"]["first_adjusted_session"] = "2019-03-25"
        schedule = self.compile()[0]
        self.assertFalse(schedule["split_precedes_record_snapshot"])
        self.assertEqual(schedule["required_operation_order"][-1], "split_existing_lots_and_unfixed_share_rights")
        self.assertTrue(schedule["cash_receivables_must_not_be_rebased"])
        self.assertTrue(schedule["rights_survive_sale_of_parent"])

    def test_missing_provider_event_exposed_without_fabrication(self):
        self.rows.pop(0)
        schedule = self.compile(approved=True)[0]
        self.assertTrue(schedule["provider_event_missing"])
        self.assertEqual(schedule["provider_event_ids"], [])
        self.assertTrue(any("absent" in b for b in schedule["blockers"]))

    def test_rounded_allocation_stays_blocked(self):
        self.term.update(share_allocation_approximate=True,
                         reported_cash_election=dict(cash="0.3735", shares="0.0279"),
                         reported_stock_election=dict(shares="0.0343"))
        schedule = self.compile(approved=True)[0]
        self.assertIsNone(schedule["selected_conditional_allocation"])
        self.assertTrue(any("approximate" in b for b in schedule["blockers"]))

    def test_unknown_default_stays_blocked(self):
        self.term["no_election_branch"] = None
        schedule = self.compile(approved=True)[0]
        self.assertIsNone(schedule["selected_default_branch"])
        self.assertTrue(any("not established" in b for b in schedule["blockers"]))

    def test_mac_default_does_not_invent_conversion(self):
        schedule = self.compile(approved=True)[1]
        self.assertEqual(schedule["selected_default_branch"], "20_percent_cash_80_percent_stock")
        self.assertIsNone(schedule["selected_conditional_allocation"])
        self.assertIsNone(schedule["stock_conversion_price"])
        self.assertTrue(schedule["blockers"])

    def test_choice_removes_only_owner_blocker(self):
        before = self.compile()[0]
        after = self.compile(approved=True)[0]
        removed = set(before["blockers"]) - set(after["blockers"])
        self.assertEqual(removed, {"Holder election is not selected; general accounting approval does not select a branch"})

    def test_conflicting_default_allocation_rejected(self):
        schedules = self.compile()
        schedules[0]["conditional_allocations"]["no_election"]["branch"] = "stock"
        with self.assertRaises(ValueError): apply_holder_policy(schedules, self.policy())

    def test_selected_allocation_is_not_shared_mutable_input(self):
        schedule = self.compile(approved=True)[0]
        schedule["selected_conditional_allocation"]["cash_per_record_share"] = "0"
        self.assertEqual(schedule["conditional_allocations"]["no_election"]["cash_per_record_share"], "11/25")

    def test_cash_lottery_never_inferred(self):
        outcome = resolve_election(self.term, "cash")
        self.assertEqual(outcome["status"], "blocked_terms")
        self.assertIn("lottery", outcome["reason"])

    def test_duplicate_schedule_identity_rejected(self):
        self.terms["election_terms"].append(deepcopy(self.term))
        with self.assertRaises(ValueError): self.compile()

    def test_duplicate_provider_event_rejected(self):
        self.rows.append(deepcopy(self.rows[0]))
        with self.assertRaises(ValueError): self.compile()

    def test_provider_record_identity_mismatch_rejected(self):
        record = json.loads(self.rows[0]["record"])
        record["id"] = "OTHER"
        self.rows[0]["record"] = json.dumps(record)
        with self.assertRaises(ValueError): self.compile()

    def test_nonpositive_split_multiplier_rejected(self):
        for value in ("0", "-1"):
            with self.subTest(value=value):
                self.splits["sources"][0]["facts"]["new_shares_per_old"] = value
                with self.assertRaises(ValueError): self.compile()

    def test_payment_cannot_precede_record_date(self):
        self.term["payable_date"] = "2019-02-21"
        with self.assertRaises(ValueError): self.compile()

    def test_split_between_record_and_issue_requires_different_schedule(self):
        self.splits["sources"][0]["facts"]["first_adjusted_session"] = "2019-03-22"
        with self.assertRaises(ValueError): self.compile()

    def test_unknown_calendar_session_rejected(self):
        self.splits["sources"][0]["facts"]["first_adjusted_session"] = "2019-02-23"
        with self.assertRaises(ValueError): self.compile()

    def test_tampered_evidence_pin_rejected(self):
        Path("browser.txt").write_bytes(b"altered")
        with self.assertRaises(ValueError): self.compile()

    def test_preflight_keeps_incomplete_schedules_blocked(self):
        result = assess([], [], [], [], dict(feature_corrections=[]), "2016-11-30", election_schedules=self.compile(approved=True))
        self.assertFalse(result["data_gates_clear"])
        self.assertEqual(len(result["blockers"]), 2)

    def test_clearing_text_blockers_does_not_admit_conditional_schedule(self):
        schedules = self.compile(approved=True)
        for schedule in schedules:
            schedule["blockers"] = []
        result = assess([], [], [], [], dict(feature_corrections=[]), "2016-11-30", election_schedules=schedules)
        self.assertFalse(result["data_gates_clear"])

    def test_duplicate_election_schedule_in_preflight_rejected(self):
        schedule = self.compile(approved=True)[0]
        with self.assertRaises(ValueError):
            assess([], [], [], [], dict(feature_corrections=[]), "2016-11-30", election_schedules=[schedule, schedule])

    def use_slg(self, year):
        event = "slg_"+str(year)
        record, payment, split = (("2020-12-15", "2021-01-15", "2021-01-21") if year == 2021 else
                                  ("2021-12-15", "2022-01-18", "2022-01-24"))
        self.term.update(id=event, record_date=record, payable_date=payment, share_allocation_approximate=True,
            no_election_branch=None, reported_cash_election=dict(cash="0.3976", approximate_shares="0.0295"),
            reported_stock_election=dict(approximate_shares="0.0345"))
        self.splits["sources"] = [dict(id=event, facts=dict(first_adjusted_session=split, new_shares_per_old="5000/5153"))]
        self.resolution["sources"] = [dict(id=event+"_declaration", access="primary_browser_text_reviewed",
            record_date=record, payable_date=payment, no_election_branch="stock_subject_to_proration",
            browser_evidence=pin("browser.txt"))]
        if year == 2022:
            self.resolution["sources"].append(dict(id="slg_2022_split", access="primary_browser_text_reviewed",
                first_adjusted_session=split, new_shares_per_old="5000/5153"))
        self.clock = DiagnosticClock([dict(opens_at=d+"T14:30:00Z", closes_at=d+"T21:00:00Z")
            for d in sorted({record, payment, split, "2020-04-22", "2020-06-03"})])

    def test_slg_2021_uses_own_declaration_default(self):
        self.use_slg(2021)
        schedule = self.compile(approved=True)[0]
        self.assertEqual(schedule["selected_default_branch"], "stock_subject_to_proration")
        self.assertIsNone(schedule["selected_conditional_allocation"])

    def test_slg_2022_uses_new_independently_reviewed_default(self):
        self.use_slg(2022)
        schedule = self.compile(approved=True)[0]
        self.assertEqual(schedule["selected_default_branch"], "stock_subject_to_proration")
        self.assertIsNone(schedule["selected_conditional_allocation"])
        self.assertTrue(any("approximate" in b for b in schedule["blockers"]))

    def test_slg_2022_does_not_reuse_previous_year_default(self):
        self.use_slg(2022)
        self.resolution["sources"].pop(0)
        self.assertIsNone(self.compile(approved=True)[0]["selected_default_branch"])

    def test_slg_declaration_must_match_record_and_payment(self):
        self.use_slg(2022)
        self.resolution["sources"][0]["record_date"] = "2020-12-15"
        with self.assertRaises(ValueError): self.compile(approved=True)

    def test_slg_default_requires_direct_primary_evidence(self):
        self.use_slg(2021)
        self.resolution["sources"][0]["access"] = "search_only"
        with self.assertRaises(ValueError): self.compile(approved=True)

    def test_duplicate_split_fact_identity_rejected(self):
        self.splits["sources"] *= 2
        with self.assertRaises(ValueError): self.compile()

    def test_invalid_payment_date_rejected(self):
        self.term["payable_date"] = "2019-99-99"
        with self.assertRaises(ValueError): self.compile()

    def test_split_nested_source_pin_is_verified(self):
        Path("split_browser.txt").write_bytes(b"split evidence")
        self.splits["sources"][0]["browser_evidence"] = pin("split_browser.txt")
        Path("split_browser.txt").write_bytes(b"tampered")
        with self.assertRaises(ValueError): self.compile()

"""Offline tests for research assumptions, pending rights and mapping revisions."""

from copy import deepcopy
from datetime import UTC, datetime
from fractions import Fraction
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from backtesting.claim_accounting import AccountingError, Quote
from backtesting.corrected_input import revised_spec
from backtesting.diagnostic_accounting import DiagnosticClock, DiagnosticRightsBook, PendingRight, plan_dividend
from backtesting.diagnostic_preparation import material_plan, validate_policy,validate_peak_continuity,dividend_multiplicity
from backtesting.input_guards import validate_streams

ROOT = Path(__file__).resolve().parents[1]


def sessions():
    days = ("2023-06-29","2023-06-30","2023-07-03","2023-07-05","2023-07-06",
            "2023-07-07","2023-07-10","2023-07-11","2023-07-12","2023-07-13")
    return [dict(opens_at=d+"T13:30:00+00:00",closes_at=d+("T17:00:00+00:00" if d=="2023-07-03" else "T20:00:00+00:00")) for d in days]


def dividend(**changes):
    record = dict(ex_date="2023-06-30",payable_date="2023-06-30",rate="0.1234567890123456789",special=False,foreign=False,symbol="ABC")
    record.update(changes)
    return dict(category="cash_dividends",event_id="D1",instrument_id="ID-A",root_id="ID-A",source_key="fixture",record=json.dumps(record))


class Offline(TestCase):
    def setUp(self):
        for name in ("socket.socket.connect","socket.socket.connect_ex","socket.create_connection",
                     "app.broker.research_client._AlpacaCredentials.load"):
            self.enterContext(patch(name,side_effect=AssertionError("No network or real credentials")))
        self.clock = DiagnosticClock(sessions())


class ClockTests(Offline):
    def test_calendar_keeps_holiday_and_early_close(self):
        self.assertIsNone(self.clock.open_on("2023-07-04"))
        self.assertEqual(self.clock.closes[2].hour,17)

    def test_payable_date_uses_next_actual_session(self):
        for day in ("2023-06-30","2023-07-01","2023-07-02"):
            self.assertEqual(self.clock.cash_release(day,"base"),self.clock.opens[2])
        self.assertEqual(self.clock.cash_release("2023-07-04","base"),self.clock.opens[3])

    def test_five_additional_sessions_and_no_credit(self):
        self.assertEqual(self.clock.cash_release("2023-06-30","delayed_five_sessions"),self.clock.opens[7])
        self.assertIsNone(self.clock.cash_release("2023-06-30","no_credit"))

    def test_missing_or_beyond_window_payment_stays_unscheduled(self):
        self.assertIsNone(self.clock.cash_release(None,"base"))
        self.assertIsNone(self.clock.cash_release("2024-01-15","base"))
        self.assertIsNone(self.clock.cash_release("2023-07-13","base"))

    def test_share_delivery_respects_economic_time_and_first_regular_quote(self):
        self.assertEqual(self.clock.share_release("2023-07-03T21:00:00Z","2023-07-05","base"),self.clock.opens[3])
        self.assertEqual(self.clock.share_release("2023-07-03T21:00:00Z","2023-07-05","delayed_five_sessions"),self.clock.opens[8])
        self.assertIsNone(self.clock.share_release("2023-07-03T21:00:00Z","2023-07-05","no_credit"))

    def test_share_release_does_not_anticipate_later_intraday_event(self):
        self.assertEqual(self.clock.share_release("2023-07-05T15:00:00Z","2023-07-05","base"),self.clock.opens[4])

    def test_invalid_sessions_rejected(self):
        for change in ([],sessions()[::-1],sessions()+sessions()[:1],
                       [dict(opens_at="2023-07-03T13:30:00",closes_at="2023-07-03T17:00:00Z")],
                       [dict(opens_at="2024-01-02T14:30:00Z",closes_at="2024-01-02T21:00:00Z")],
                       [dict(opens_at="2023-07-03T13:30:00Z",closes_at="2023-07-04T17:00:00Z")]):
            with self.subTest(change=change),self.assertRaises(ValueError):
                DiagnosticClock(change)

    def test_invalid_scenario_and_naive_share_time_rejected(self):
        with self.assertRaises(ValueError): self.clock.cash_release("2023-06-30","fast")
        with self.assertRaises(ValueError): self.clock.share_release("2023-07-03T17:00:00","2023-07-05","base")

    def test_no_credit_still_validates_supplied_dates(self):
        with self.assertRaises(ValueError): self.clock.cash_release("bad","no_credit")
        with self.assertRaises(ValueError): self.clock.share_release("bad","bad","no_credit")


class DividendTests(Offline):
    def test_same_security_ex_date_multiple_ids_require_review_without_deleting(self):
        rows=[dict(category="cash_dividends",instrument_id="A",day="2023-06-30",event_id=i) for i in ("D1","D2")]
        self.assertEqual(dividend_multiplicity(rows),{("A","2023-06-30"):["D1","D2"]})
        self.assertEqual(len(rows),2)

    def test_multiplicity_does_not_merge_different_securities_or_dates(self):
        rows=[dict(category="cash_dividends",instrument_id="A",day="2023-06-30",event_id="D1"),
              dict(category="cash_dividends",instrument_id="B",day="2023-06-30",event_id="D2"),
              dict(category="cash_dividends",instrument_id="A",day="2023-07-03",event_id="D3")]
        self.assertEqual(dividend_multiplicity(rows),{})

    def test_split_and_cash_components_are_not_silently_merged(self):
        rows=[dict(category=k,instrument_id="A",day="2023-06-30",event_id=i) for k,i in
              (("forward_splits","S"),("cash_dividends","D1"),("cash_dividends","D2"))]
        self.assertEqual(dividend_multiplicity(rows)[("A","2023-06-30")],["D1","D2"])
    def test_valid_plan_keeps_exact_amount_and_unverified_provenance(self):
        p=plan_dividend(dividend(),self.clock,"base")
        self.assertEqual(Fraction(p["cash_per_eligible_share"]),Fraction("0.1234567890123456789"))
        self.assertEqual(p["modeled_release_at"],self.clock.opens[2].isoformat())
        self.assertIsNone(p["historical_known_at"])
        self.assertIsNone(p["actual_broker_received_at"])
        self.assertFalse(p["execution_ready"])

    def test_missing_payment_keeps_receivable_without_fabrication(self):
        p=plan_dividend(dividend(payable_date=None),self.clock,"base")
        self.assertEqual(p["status"],"candidate_receivable_only")
        self.assertIsNone(p["modeled_release_at"])

    def test_payment_before_ex_date_blocks_due_bill_ambiguity(self):
        p=plan_dividend(dividend(payable_date="2023-06-29"),self.clock,"base")
        self.assertEqual(p["status"],"blocked_terms")

    def test_special_foreign_unknown_classification_or_currency_blocks(self):
        for changes in (dict(special=True),dict(foreign=True),dict(special=None),dict(currency="EUR")):
            with self.subTest(changes=changes):
                self.assertEqual(plan_dividend(dividend(**changes),self.clock,"base")["status"],"blocked_terms")

    def test_zero_negative_unknown_and_nonfinite_rates_block(self):
        for rate in (0,-1,None,"NaN","Infinity",True):
            with self.subTest(rate=rate):
                p=plan_dividend(dividend(rate=rate),self.clock,"base")
                self.assertEqual(p["status"],"blocked_terms")
                self.assertIsNone(p["cash_per_eligible_share"])

    def test_non_session_ex_date_blocks(self):
        self.assertEqual(plan_dividend(dividend(ex_date="2023-07-04"),self.clock,"base")["status"],"blocked_terms")

    def test_no_credit_retains_value_but_no_release(self):
        p=plan_dividend(dividend(),self.clock,"no_credit")
        self.assertIsNotNone(p["cash_per_eligible_share"])
        self.assertIsNone(p["modeled_release_at"])


class RightsTests(Offline):
    def setUp(self):
        super().setUp()
        self.book=DiagnosticRightsBook(self.clock)

    def right(self,**changes):
        values=dict(claim_id="C1",instrument_id="ID-A",kind="cash",units="10",cash_amount="5",
                    created_at=self.clock.opens[1],release_at=self.clock.opens[2],source="synthetic diagnostic terms")
        values.update(changes)
        return PendingRight(**values)

    def quote(self,index=2,**changes):
        values=dict(instrument_id="ID-A",timestamp=self.clock.closes[index],low="9",close="10",high="11")
        values.update(changes)
        return Quote(**values)

    def test_known_cash_marks_as_receivable_without_spendable_cash(self):
        self.book.recognize(self.right())
        p=self.book.mark(at=self.clock.closes[1],quotes={})
        self.assertEqual(p["pending_right_value"],"5")
        self.assertEqual(p["spendable_contribution"],"0")
        self.assertEqual(self.book.released_cash,0)

    def test_early_release_fails_atomically(self):
        self.book.recognize(self.right())
        before=(self.book.pending,self.book.journal,self.book.released_cash)
        with self.assertRaises(ValueError): self.book.release("C1",at=self.clock.opens[1])
        self.assertEqual(before,(self.book.pending,self.book.journal,self.book.released_cash))

    def test_release_once_removes_claim_preventing_double_count(self):
        self.book.recognize(self.right())
        self.book.release("C1",at=self.clock.opens[2])
        self.assertEqual(self.book.released_cash,5)
        self.assertEqual(self.book.mark(at=self.clock.closes[2],quotes={})["pending_right_value"],"0")
        with self.assertRaises(ValueError): self.book.release("C1",at=self.clock.opens[3])

    def test_duplicate_recognition_rejected_even_after_release(self):
        right=self.right()
        self.book.recognize(right)
        self.book.release("C1",at=self.clock.opens[2])
        with self.assertRaises(ValueError): self.book.recognize(right)

    def test_unknown_cash_cannot_be_zeroed_or_released(self):
        self.book.recognize(self.right(cash_amount=None))
        self.assertFalse(self.book.mark(at=self.clock.closes[1],quotes={})["complete"])
        with self.assertRaises(ValueError): self.book.release("C1",at=self.clock.opens[2])
        self.assertEqual(self.book.released_cash,0)

    def test_unscheduled_right_persists_across_later_sessions(self):
        self.book.recognize(self.right(release_at=None))
        for index in (1,2,5,9):
            self.assertEqual(self.book.mark(at=self.clock.closes[index],quotes={})["pending_right_value"],"5")
        self.assertEqual(len(self.book.pending),1)

    def test_whole_share_release_keeps_exact_fraction(self):
        self.book.recognize(self.right(kind="shares",units="7/3",cash_amount=None))
        result=self.book.release("C1",at=self.clock.opens[2])
        self.assertEqual(result["whole_shares"],2)
        self.assertEqual(self.book.pending[0].units,Fraction(1,3))
        self.assertEqual(self.book.mark(at=self.clock.closes[2],quotes={"ID-A":self.quote()})["pending_right_value"],"10/3")
        with self.assertRaises(ValueError): self.book.release("C1",at=self.clock.opens[3])

    def test_fraction_only_cannot_be_automatically_sold(self):
        self.book.recognize(self.right(kind="shares",units="1/3",cash_amount=None))
        with self.assertRaises(ValueError): self.book.release("C1",at=self.clock.opens[2])
        self.assertEqual(self.book.pending[0].units,Fraction(1,3))

    def test_missing_stale_future_or_wrong_identity_quotes_make_mark_incomplete(self):
        self.book.recognize(self.right(kind="shares",units="1/3",cash_amount=None))
        for quotes in ({},{"ID-A":self.quote(index=1)},{"ID-A":self.quote(index=3)},
                       {"ID-A":self.quote(instrument_id="ID-B")}):
            self.assertFalse(self.book.mark(at=self.clock.closes[2],quotes=quotes)["complete"])

    def test_time_reversal_and_non_close_mark_rejected(self):
        self.book.recognize(self.right())
        self.book.mark(at=self.clock.closes[2],quotes={})
        with self.assertRaises(ValueError): self.book.mark(at=self.clock.closes[1],quotes={})
        with self.assertRaises(ValueError): self.book.mark(at=self.clock.opens[3],quotes={})

    def test_nonsession_availability_and_reserved_dates_rejected(self):
        with self.assertRaises(ValueError): self.book.recognize(self.right(release_at="2023-07-04T13:30:00Z"))
        with self.assertRaises(ValueError): self.book.recognize(self.right(created_at="2024-01-02T14:30:00Z",release_at=None))

    def test_invalid_quantities_cash_and_invented_fixing_rejected(self):
        for changes in (dict(units=0),dict(units=-1),dict(units=True),dict(cash_amount="-1"),
                        dict(kind="shares",cash_amount="1"),dict(created_at="2023-06-30T13:30:00")):
            with self.subTest(changes=changes),self.assertRaises(ValueError): self.right(**changes)

    def test_journal_is_a_copy(self):
        self.book.recognize(self.right())
        journal=self.book.journal
        journal[0]["kind"]="changed"
        self.assertEqual(self.book.journal[0]["kind"],"diagnostic_right")


class MappingTests(Offline):
    def setUp(self):
        super().setUp()
        self.original=json.loads((ROOT/"docs/broad_historical_input_spec.json").read_text(encoding="utf-8"))
        self.facts=json.loads((ROOT/"docs/broad_event_primary_review.json").read_text(encoding="utf-8"))
        self.primary=dict(path="fixture.json",sha256="fixture")

    def revise(self): return revised_spec(self.original,self.facts,self.primary)

    def test_original_is_unchanged_and_all_member_ids_retained(self):
        before=deepcopy(self.original)
        result=self.revise()
        self.assertEqual(self.original,before)
        self.assertEqual(len(result["streams"]),121)
        self.assertEqual([s["instrument_id"] for s in result["streams"] if s["role"]=="original_member"],
                         [s["instrument_id"] for s in before["streams"] if s["role"]=="original_member"])

    def test_jci_predecessor_and_features_are_separate(self):
        result=self.revise()
        streams={s["instrument_id"]:s for s in result["streams"]}
        self.assertEqual(streams["COHORT-2016-0258"]["parts"][0]["start"],"2016-09-06")
        old=streams["COHORT-2016-0258.PREMERGER-REFERENCE"]
        self.assertTrue(old["feature_use_prohibited"])
        self.assertFalse(old["eligible_for_new_entries_candidate"])

    def test_peak_exchange_is_one_for_one_without_execution_approval(self):
        result=self.revise()
        event=next(e for e in result["material_events"] if e["id"]=="peak_holding_company_reorganization")
        self.assertEqual(event["share_legs"][0]["shares_per_parent"],"1")
        self.assertFalse(event["execution_ready"])
        self.assertIsNone(event["actual_delivery_at"])

    def test_peak_admission_checks_primary_economics_and_exact_security_legs(self):
        event=next(e for e in self.revise()["material_events"] if e["id"]=="peak_holding_company_reorganization")
        source=next(s for s in self.facts["sources"] if s["id"]=="peak_2023")
        validate_peak_continuity(event,source)
        for change in (dict(cash_per_parent="1"),dict(parent_id="OTHER"),dict(economic_date="2023-02-13"),
                       dict(share_legs=[dict(instrument_id="OTHER",shares_per_parent="1")])):
            with self.subTest(change=change),self.assertRaises(ValueError):validate_peak_continuity(dict(event,**change),source)
        with self.assertRaises(ValueError):validate_peak_continuity(event,dict(source,access="search_only"))

    def test_phin_distribution_time_is_distinct_from_first_quote(self):
        event=next(e for e in self.revise()["material_events"] if e["id"]=="bwa_phin_distribution")
        self.assertEqual(event["economic_date"],"2023-07-03")
        self.assertEqual(event["first_regular_session"],"2023-07-05")

    def test_source_downgrade_or_changed_original_binding_rejected(self):
        self.facts["sources"][-1]["access"]="search_only"
        with self.assertRaises(ValueError): self.revise()
        self.facts["sources"][-1]["access"]="primary_browser_text_reviewed"
        next(s for s in self.original["streams"] if s["snapshot_alias"]=="JCI")["parts"][0]["start"]="2016-02-01"
        with self.assertRaises(ValueError): self.revise()

    def test_adnt_remains_a_blocker(self):
        self.assertTrue(self.revise()["diagnostic_mapping"]["unresolved_feature_events"])


class MaterialPlanTests(Offline):
    def event(self,**changes):
        event=dict(id="E1",parent_id="ID-A",root_id="ID-A",kind="retained_parent_spinoff",
            economic_date="2023-07-03",economic_effective_at="2023-07-03T21:00:00Z",
            first_regular_session="2023-07-05",share_legs=[dict(instrument_id="ID-B",shares_per_parent="1/5")],cash_per_parent=None)
        event.update(changes)
        return event

    def plan(self,event,scenario="base"):
        return material_plan(event,self.clock,scenario,{"ID-B":dict(parts=[dict(start="2023-07-05")])})

    def test_child_quote_start_and_explicit_effective_time_are_respected(self):
        p=self.plan(self.event())
        self.assertEqual(p["share_legs"][0]["modeled_release_at"],self.clock.opens[3].isoformat())
        self.assertFalse(p["execution_ready"])
        self.assertIsNone(p["cash_per_parent"])

    def test_weekend_effective_date_maps_to_next_saved_open(self):
        p=self.plan(self.event(economic_date="2023-07-01",economic_effective_at=None))
        self.assertEqual(p["modeled_accounting_at"],self.clock.opens[2].isoformat())

    def test_out_of_calendar_event_remains_unscheduled(self):
        p=self.plan(self.event(economic_date="2023-12-31",economic_effective_at=None))
        self.assertIsNone(p["modeled_accounting_at"])
        self.assertIsNone(p["share_legs"][0]["modeled_release_at"])

    def test_policy_cannot_authorize_trading_or_invent_unsupported_semantics(self):
        policy=json.loads((ROOT/"docs/broad_diagnostic_accounting_policy.json").read_text(encoding="utf-8"))
        validate_policy(policy)
        for changes in (dict(performance_authorized=True),dict(purchases_usd=1),dict(unknown_value_policy="zero"),
                        dict(known_cash_policy="immediate"),dict(original_members_may_be_dropped=True)):
            with self.subTest(changes=changes),self.assertRaises(ValueError):validate_policy(dict(policy,**changes))

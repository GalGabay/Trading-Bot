"""Synthetic evidence classification; no company sources or network access."""

from copy import deepcopy
from unittest import TestCase

import pandas as pd

from backtesting.broad_history_review import assess


class HistoryReviewTests(TestCase):
    def setUp(self):
        self.target=dict(instrument_id="fixture-id",snapshot_alias="OLD")
        self.frame=pd.DataFrame(dict(timestamp=["2017-01-03T05:00:00Z","2017-01-04T05:00:00Z"]))
        self.fact=dict(snapshot_alias="OLD",execution_ready=False,event_date="2017-01-03",
            primary_source_url="https://www.sec.gov/fixture",unsegmented_identity_conflict=False,
            classification="rename",next_alias_candidate="NEW",cash_per_original_share=None,
            share_ratio=None,source_access="synthetic",summary="Fixture only")

    def test_same_issuer_rename_is_not_a_forced_cash_sale(self):
        row=assess(self.target,self.frame,self.fact)
        self.assertEqual(row["next_alias_candidate"],"NEW")
        self.assertIsNone(row["cash_per_original_share"])
        self.assertFalse(row["actual_delivery_time_known"])

    def test_cash_merger_creates_review_terms_without_booking_cash(self):
        self.fact.update(classification="cash_merger",next_alias_candidate=None,cash_per_original_share="57.60")
        row=assess(self.target,self.frame,self.fact)
        self.assertEqual(row["cash_per_original_share"],"57.60")
        self.assertFalse(row["execution_ready"])

    def test_reused_ticker_requires_quarantine_without_editing_prices(self):
        self.fact["unsegmented_identity_conflict"]=True
        before=self.frame.copy(deep=True)
        row=assess(self.target,self.frame,self.fact)
        self.assertEqual(row["observed_rows_after_economic_anchor"],1)
        self.assertIn("Quarantine",row["required_work"])
        pd.testing.assert_frame_equal(self.frame,before)

    def test_merger_day_is_not_silently_called_last_trading_day(self):
        row=assess(self.target,self.frame,self.fact)
        self.assertEqual(row["economic_event_date"],"2017-01-03")
        self.assertNotIn("last_valid_trading_day",row)

    def test_unresolved_date_is_not_filled_from_last_candle(self):
        self.fact.update(event_date=None,primary_source_url=None)
        row=assess(self.target,self.frame,self.fact)
        self.assertIsNone(row["economic_event_date"])
        self.assertIsNone(row["observed_rows_after_economic_anchor"])

    def test_identity_mismatch_and_approval_rejected(self):
        for changes in (dict(snapshot_alias="OTHER"),dict(execution_ready=True)):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                assess(self.target,self.frame,{**self.fact,**changes})

    def test_future_or_invalid_economic_dates_rejected(self):
        for value in ("2024-01-01","2017-02-30"):
            with self.subTest(value=value),self.assertRaises(ValueError):
                assess(self.target,self.frame,{**self.fact,"event_date":value})

    def test_reserved_year_prices_rejected(self):
        with self.assertRaises(ValueError):
            assess(self.target,pd.DataFrame(dict(timestamp=["2024-01-02T05:00:00Z"])),self.fact)

    def test_unsupported_conflict_claim_without_later_rows_rejected(self):
        with self.assertRaises(ValueError):
            assess(self.target,self.frame,{**self.fact,"event_date":"2017-01-05","unsegmented_identity_conflict":True})

    def test_duplicate_empty_or_unordered_history_rejected(self):
        for frame in (self.frame.iloc[:0],pd.concat([self.frame,self.frame]),self.frame.iloc[::-1]):
            with self.subTest(rows=len(frame)),self.assertRaises(ValueError):
                assess(self.target,frame,self.fact)

    def test_insecure_evidence_reference_rejected(self):
        with self.assertRaises(ValueError):
            assess(self.target,self.frame,{**self.fact,"primary_source_url":"http://fixture"})

    def test_review_does_not_mutate_the_fact_record(self):
        before=deepcopy(self.fact)
        assess(self.target,self.frame,self.fact)
        self.assertEqual(before,self.fact)

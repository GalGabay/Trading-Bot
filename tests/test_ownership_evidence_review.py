"""Synthetic source fixtures; no saved market data or network required."""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from backtesting.ownership_evidence_review import advance_terms, classify_cases, match_mechanics, run_review


class OwnershipEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.check = dict(case_name="arconic_howmet_and_new_arconic_branch", source_id="source",
                          publication_date="2020-02-06", recognition_session="2020-04-01",
                          shares_per_parent="1/4", terms=["every four shares"])
        self.texts = {"source": "February 6, 2020: one child for every four shares."}
        self.sessions = [pd.Timestamp(s) for s in ("2020-02-07T14:30:00Z", "2020-02-10T14:30:00Z",
                                                  "2020-04-01T13:30:00Z")]
        self.case = dict(name=self.check["case_name"], session="2020-04-01", cash_per_parent="0",
                         shares=[dict(ratio="1/4", synthetic_close="10")])

    def review(self, **changes):
        return advance_terms([{**self.check, **changes}], self.texts, self.sessions)

    def test_conservative_bound_skips_non_session_days_without_certifying_delivery(self):
        row = self.review()[0]
        self.assertEqual(row["conservative_known_at"], "2020-02-10T14:30:00+00:00")
        self.assertTrue(row["planned_terms_known_by_recognition_open"])
        self.assertFalse(row["actual_delivery_verified"])
        self.assertFalse(row["approved_for_strategy_scoring"])

    def test_changed_literal_source_rejected(self):
        with self.assertRaisesRegex(ValueError, "pinned source"):
            self.review(terms=["every three shares"])

    def test_false_publication_date_rejected(self):
        with self.assertRaisesRegex(ValueError, "Publication date"):
            self.review(publication_date="2020-02-05")

    def test_missing_effective_session_rejected(self):
        with self.assertRaisesRegex(ValueError, "calendar"):
            self.review(recognition_session="2020-04-02")

    def test_duplicate_review_and_nonpositive_ratio_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            advance_terms([self.check, self.check], self.texts, self.sessions)
        for ratio in ("0", "-1/4"):
            with self.subTest(ratio=ratio), self.assertRaisesRegex(ValueError, "positive"):
                self.review(shares_per_parent=ratio)

    def test_late_knowledge_never_passes_recognition_gate(self):
        rows = advance_terms([{**self.check, "recognition_session": "2020-02-07"}], self.texts, self.sessions)
        self.assertFalse(rows[0]["planned_terms_known_by_recognition_open"])

    def test_advance_and_mechanics_must_agree(self):
        match_mechanics(self.review(), [self.case])
        for change in (dict(session="2020-04-02"), dict(shares=[dict(ratio="1/3")])):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "disagree"):
                match_mechanics(self.review(), [{**self.case, **change}])

    def test_missing_provider_event_and_quote_never_automatically_approved(self):
        row = classify_cases([self.case], self.review(),
                             [dict(name="arconic_2020_distribution", provider_event_present=False)])[0]
        self.assertTrue(row["advance_planned_terms_supported"])
        self.assertFalse(row["provider_event_present"])
        self.assertIn("synthetic", row["event_quotes"])
        for key in ("prior_close_entitlement_verified", "share_delivery_verified",
                    "full_lifecycle_price_and_action_coverage_certified", "approved_for_strategy_scoring"):
            self.assertFalse(row[key])

    def test_existing_output_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError):
                run_review(Path(directory), review_path=Path("not-read.json"))

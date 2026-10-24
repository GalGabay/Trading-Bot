"""Offline checks for curated pilot inputs; no downloads or private files."""

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import pandas as pd

from app.data.market_calendar import TradingSession
from backtesting.raw_action_pilot import checked_file, curate_manifest, digest, run_pilot, session_after
from backtesting.universe import HistoricalUniverse, ListingPeriod, CashDividend, SplitAction


class RawActionPilotTests(TestCase):
    def setUp(self):
        dates = pd.bdate_range("2019-01-02", "2020-12-31", tz="America/New_York")
        self.sessions = [TradingSession(pd.Timestamp(f"{d.date()} 09:30", tz="America/New_York"),
                                        pd.Timestamp(f"{d.date()} 16:00", tz="America/New_York")) for d in dates]
        self.review = {"instrument_id": "AAPL-LOCAL", "prices": {"adjustment": "raw", "feed": "sip"},
                       "sources": {name: {"url": f"https://example.test/{name}"} for name in ("listing", "january", "april", "july", "october")},
                       "split": {"event_id": "split", "announcement": "2020-07-30", "effective_session": "2020-08-31", "new_shares": 4, "old_shares": 1},
                       "dividends": []}
        self.provider = {"next_page_token": None, "corporate_actions": {"cash_dividends": [], "forward_splits": [
            {"id": "split", "symbol": "AAPL", "cusip": "037833100", "ex_date": "2020-08-31", "new_rate": 4, "old_rate": 1}]}}
        self.texts = {"listing": "Apple Inc. Common Stock Nasdaq under the symbol AAPL", "listing_index": "2018-11-05"}
        for name, announcement, ex, pay, amount in (
                ("january", "2020-01-28", "2020-02-07", "2020-02-13", .77),
                ("april", "2020-04-30", "2020-05-08", "2020-05-14", .82),
                ("july", "2020-07-30", "2020-08-07", "2020-08-13", .82),
                ("october", "2020-10-29", "2020-11-06", "2020-11-12", .205)):
            self.review["dividends"].append({"event_id": name, "ex_session": ex, "issuer_payable_date": pay,
                                             "cash_per_share": amount, "source": name, "announcement": announcement})
            self.provider["corporate_actions"]["cash_dividends"].append({"id": name, "symbol": "AAPL", "ex_date": ex, "rate": amount,
                                                                       "special": False, "foreign": False, "cusip": "037833100"})
            self.texts[name] = f"{pd.Timestamp(announcement).strftime('%B')} {pd.Timestamp(announcement).day}, 2020: ${amount} per share payable on {pd.Timestamp(pay).strftime('%B')} {pd.Timestamp(pay).day}, 2020"
        self.texts["july"] += " four-for-one split trading August 31, 2020"

    def curate(self):
        return curate_manifest(self.review, self.provider, self.sessions, self.texts)

    def test_primary_source_can_resolve_missing_provider_payable_field_explicitly(self):
        manifest = self.curate()
        self.assertEqual(manifest["dividends"][0]["pay_session"], "2020-02-14")
        self.assertEqual(manifest["dividends"][0]["known_at"], "2020-01-30T09:30:00-05:00")
        universe = HistoricalUniverse(sessions=self.sessions, price_basis="raw", action_scope=manifest["action_scope"],
                                      listings=[ListingPeriod(**v) for v in manifest["listings"]],
                                      splits=[SplitAction(**v) for v in manifest["splits"]],
                                      dividends=[CashDividend(**v) for v in manifest["dividends"]])
        self.assertEqual(len(universe.dividends), 4)

    def test_cash_convention_skips_weekend_and_is_strictly_after_payment(self):
        self.assertEqual(session_after(self.sessions, "2020-02-14").opens_at.date().isoformat(), "2020-02-17")
        # Synthetic weekday calendar above; explicitly remove a synthetic holiday.
        sessions = [s for s in self.sessions if s.opens_at.date().isoformat() != "2020-02-17"]
        self.assertEqual(session_after(sessions, "2020-02-14").opens_at.date().isoformat(), "2020-02-18")

    def test_uncovered_cash_date_is_not_invented(self):
        with self.assertRaisesRegex(ValueError, "Calendar"):
            session_after(self.sessions, "2021-01-01")

    def test_unknown_extra_action_type_requires_review(self):
        self.provider["corporate_actions"]["stock_mergers"] = []
        with self.assertRaisesRegex(ValueError, "category"):
            self.curate()

    def test_incomplete_pagination_is_rejected(self):
        self.provider["next_page_token"] = "more"
        with self.assertRaisesRegex(ValueError, "pagination"):
            self.curate()

    def test_dividend_terms_and_primary_evidence_must_agree(self):
        for change in ("rate", "payable", "source", "special"):
            provider, texts = deepcopy(self.provider), deepcopy(self.texts)
            row = self.provider["corporate_actions"]["cash_dividends"][0]
            if change == "rate": row["rate"] = .99
            if change == "payable": row["payable_date"] = "2020-02-12"
            if change == "source": self.texts["january"] = "Payment terms not available"
            if change == "special": row["special"] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.curate()
            self.provider, self.texts = provider, texts

    def test_duplicate_or_missing_dividends_rejected(self):
        self.provider["corporate_actions"]["cash_dividends"][1] = self.provider["corporate_actions"]["cash_dividends"][0]
        with self.assertRaises(ValueError):
            self.curate()

    def test_split_uses_trading_date_not_distribution_date(self):
        self.provider["corporate_actions"]["forward_splits"][0]["ex_date"] = "2020-08-28"
        with self.assertRaisesRegex(ValueError, "Split"):
            self.curate()

    def test_adjusted_input_cannot_double_count_events(self):
        self.review["prices"]["adjustment"] = "all"
        with self.assertRaisesRegex(ValueError, "raw"):
            self.curate()

    def test_missing_historical_security_identity_rejected(self):
        self.texts["listing"] = "Current ticker list"
        with self.assertRaisesRegex(ValueError, "identity"):
            self.curate()

    def test_changed_source_hash_and_path_escape_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            p = root / "source.html"
            p.write_text("original")
            entry = {"path": p.name, "sha256": digest(p)}
            self.assertEqual(checked_file(root, entry), p.resolve())
            p.write_text("changed")
            with self.assertRaisesRegex(ValueError, "checksum"):
                checked_file(root, entry)
            with self.assertRaisesRegex(ValueError, "escapes"):
                checked_file(root, {"path": "../outside.html", "sha256": ""})

    def test_existing_output_is_never_overwritten(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError):
                run_pilot(Path(directory))

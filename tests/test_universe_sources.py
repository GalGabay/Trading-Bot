"""No-network broker pagination and preserved source-candidate checks."""

from contextlib import redirect_stdout
from datetime import date, datetime, timezone
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock

from app.broker.alpaca_client import AlpacaClient
from backtesting.universe_sources import review_existing


class CatalogGatewayTests(TestCase):
    def client(self, responses):
        client = AlpacaClient.__new__(AlpacaClient)  # No credentials, constructor or HTTP.
        client._historical_data = Mock()
        client._historical_data.get.side_effect = responses
        client._trading = Mock()
        return client

    def bars(self, client):
        return client.get_market_data_batch(["AAA"], start=datetime(2021, 1, 1, tzinfo=timezone.utc),
                                           end=datetime(2021, 2, 1, tzinfo=timezone.utc))

    def test_catalog_keeps_unknown_exchange_values(self):
        client = self.client([])
        client._trading.get.return_value = [{"symbol": "AAA", "exchange": "NEW_EXCHANGE"}]
        self.assertEqual(client.get_assets()[0]["exchange"], "NEW_EXCHANGE")
        self.assertFalse(client._trading.submit_order.called)

    def test_catalog_rejects_non_object_rows(self):
        client = self.client([])
        client._trading.get.return_value = [None]
        with self.assertRaisesRegex(ValueError, "metadata"):
            client.get_assets()

    def test_empty_bars_are_a_genuine_empty_result(self):
        client = self.client([{"bars": None, "next_page_token": None}])
        self.assertEqual(self.bars(client).data, {})

    def test_every_page_is_read(self):
        bar = {"t": "2021-01-04T05:00:00Z", "o": 10, "h": 11, "l": 9, "c": 10, "v": 100}
        client = self.client([{"bars": {"AAA": [bar]}, "next_page_token": "second"},
                              {"bars": {"AAA": [{**bar, "t": "2021-01-05T05:00:00Z"}]}, "next_page_token": None}])
        self.assertEqual(len(self.bars(client).data["AAA"]), 2)
        self.assertEqual(client._historical_data.get.call_count, 2)

    def test_repeated_page_token_rejected(self):
        client = self.client([{"bars": {}, "next_page_token": "again"}] * 2)
        with self.assertRaisesRegex(ValueError, "repeated"):
            self.bars(client)

    def test_malformed_bar_page_rejected(self):
        for page in ({}, {"bars": []}, {"bars": {"AAA": None}}):
            with self.subTest(page=page), self.assertRaises(ValueError):
                self.bars(self.client([page]))

    def test_page_budget_is_bounded(self):
        client = self.client([{"bars": {}, "next_page_token": str(i)} for i in range(100)])
        with self.assertRaisesRegex(ValueError, "100-page"):
            self.bars(client)
        self.assertEqual(client._historical_data.get.call_count, 100)

    def test_company_event_dates_are_explicit_and_use_v1(self):
        client = self.client([{"corporate_actions": {}}])
        client.get_corporate_actions_page(symbols=["aapl"], start=date(2020, 1, 1), end=date(2020, 12, 31))
        args, kwargs = client._historical_data.get.call_args
        self.assertEqual(args[1]["symbols"], "AAPL")
        self.assertEqual(args[1]["end"], "2020-12-31")
        self.assertEqual(kwargs["api_version"], "v1")
        self.assertFalse(client._trading.submit_order.called)


class SourceCandidateTests(TestCase):
    def snapshot(self, directory):
        page = directory / "page.json"
        page.write_text(json.dumps({"corporate_actions": {"cash_mergers": [{"id": "event-1", "process_date": "2022-10-28", "rate": 54.2}]}}))
        record = {"path": page.name, "sha256": hashlib.sha256(page.read_bytes()).hexdigest()}
        report = {"probes": [{"symbol": "TWTR", "status": "accessible", "pages": [record]}]}
        (directory / "report.json").write_text(json.dumps(report))
        return page, report

    def review(self, directory):
        with redirect_stdout(io.StringIO()):
            return review_existing(directory)

    def test_process_date_does_not_become_publication_or_payment_date(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.snapshot(directory)
            candidate = self.review(directory)["candidates"][0]
            self.assertIsNone(candidate["historical_known_at"])
            self.assertIsNone(candidate["cash_available_session"])
            self.assertFalse(candidate["ready_for_simulation"])

    def test_modified_event_page_is_rejected(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            page, _ = self.snapshot(directory)
            page.write_text("{}")
            with self.assertRaisesRegex(ValueError, "checksum"):
                self.review(directory)

    def test_existing_candidate_evidence_is_never_overwritten(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.snapshot(directory)
            self.review(directory)
            with self.assertRaises(FileExistsError):
                self.review(directory)

    def test_duplicate_source_event_id_is_not_double_counted(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            _, report = self.snapshot(directory)
            report["probes"] *= 2
            (directory / "report.json").write_text(json.dumps(report))
            self.assertEqual(len(self.review(directory)["candidates"]), 1)

    def test_page_path_cannot_escape_its_snapshot(self):
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            _, report = self.snapshot(directory)
            report["probes"][0]["pages"][0]["path"] = "../page.json"
            (directory / "report.json").write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "inside"):
                self.review(directory)

"""Synthetic responses only; any real socket connection fails the tests."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

import requests

from backtesting.public_document_collection import collect


class PublicDocumentCollectionTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.queue_path, self.output = self.root / "queue.json", self.root / "out"
        self.queue = dict(purchases_budget_usd=0, max_http_attempts=40, allowed_domains=["issuer.test"],
                          documents=[self.entry("first"), self.entry("second")])
        self.session = Mock()
        self.factory = self.enterContext(patch("backtesting.public_document_collection.requests.Session", return_value=self.session))
        self.sleep = self.enterContext(patch("backtesting.public_document_collection.time.sleep"))
        self.enterContext(patch("socket.socket.connect", side_effect=AssertionError("Real network is forbidden")))

    def entry(self, name):
        return dict(id=name, url=f"https://issuer.test/{name}", targets=["SYNTHETIC-DOCUMENT"])

    def response(self, status=200, body=b"<html>synthetic</html>", **headers):
        response = Mock(status_code=status, headers=headers)
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.iter_content.return_value = iter([body])
        return response

    def run_collection(self):
        self.queue_path.write_text(json.dumps(self.queue), encoding="utf-8")
        return collect(self.queue_path, self.output)

    def test_success_preserves_raw_bytes_hash_and_unreviewed_status(self):
        self.queue["documents"] = [self.entry("first")]
        body = b"<html>unchanged\x00 bytes</html>"
        self.session.get.return_value = self.response(body=body)
        result = self.run_collection()
        item = result["attempts"][0]
        self.assertEqual((self.output/item["file"]).read_bytes(), body)
        self.assertEqual(item["sha256"], hashlib.sha256(body).hexdigest())
        self.assertEqual(item["status"], "saved_unreviewed")
        self.assertEqual(json.loads((self.output/"report.json").read_text()), result)
        self.assertFalse(self.session.trust_env)
        self.assertFalse(self.session.get.call_args.kwargs["allow_redirects"])
        self.assertEqual(self.session.get.call_args.kwargs["timeout"], 30)
        self.assertNotIn("Authorization", self.session.get.call_args.kwargs["headers"])
        self.session.close.assert_called_once()

    def test_access_payment_and_rate_denials_stop_before_next_request(self):
        for status in (401, 402, 403, 407, 429):
            with self.subTest(status=status), TemporaryDirectory() as d:
                self.output = Path(d)/"out"
                self.session.get.reset_mock()
                self.session.get.return_value = self.response(status)
                result = self.run_collection()
                self.assertTrue(result["stopped"])
                self.assertEqual(result["network_http_attempts"], 1)
                self.session.get.assert_called_once()
                self.assertEqual(list(self.output.iterdir()), [self.output/"report.json"])

    def test_redirect_is_recorded_without_following_external_destination(self):
        self.session.get.side_effect = [self.response(302, Location="https://unapproved.test/private"), self.response()]
        result = self.run_collection()
        self.assertEqual(result["attempts"][0]["status"], "redirect_requires_review")
        self.assertEqual([c.args[0] for c in self.session.get.call_args_list], [e["url"] for e in self.queue["documents"]])
        self.assertTrue(all(c.kwargs["allow_redirects"] is False for c in self.session.get.call_args_list))

    def test_missing_document_is_recorded_once_without_retry(self):
        self.session.get.side_effect = [self.response(404), self.response()]
        result = self.run_collection()
        self.assertFalse(result["stopped"])
        self.assertEqual(self.session.get.call_count, 2)
        self.assertEqual(result["attempts"][0]["status"], "unavailable_no_retry")

    def test_transport_failure_is_sanitized_and_session_closed(self):
        self.queue["documents"] = [self.entry("first")]
        self.session.get.side_effect = requests.ConnectionError("SYNTHETIC_SECRET_MUST_NOT_BE_SAVED")
        result = self.run_collection()
        self.assertEqual(result["network_http_attempts"], 1)
        self.assertEqual(result["attempts"][0]["error_type"], "ConnectionError")
        self.assertNotIn("SYNTHETIC_SECRET", (self.output/"report.json").read_text())
        self.session.close.assert_called_once()

    def test_pdf_and_workbook_signatures_determine_filename(self):
        self.session.get.side_effect = [self.response(body=b"%PDF-1.7 fixture"), self.response(body=b"PK fixture")]
        result = self.run_collection()
        self.assertEqual([r["file"] for r in result["attempts"]], ["first.pdf", "second.xlsx"])

    def test_request_spacing_between_documents(self):
        self.session.get.side_effect = [self.response(), self.response()]
        self.run_collection()
        self.sleep.assert_called_once_with(1.1)

    def test_exact_budget_is_respected(self):
        self.queue["max_http_attempts"] = 2
        self.session.get.side_effect = [self.response(), self.response()]
        self.assertEqual(self.run_collection()["network_http_attempts"], 2)

    def test_hard_cap_40_is_accepted_without_a_41st_request(self):
        self.queue["documents"] = [self.entry(f"doc_{i}") for i in range(40)]
        self.session.get.side_effect = [self.response() for _ in range(40)]
        self.assertEqual(self.run_collection()["network_http_attempts"], 40)
        self.assertEqual(self.session.get.call_count, 40)

    def test_invalid_budgets_are_rejected_before_creating_session(self):
        original = deepcopy(self.queue)
        for budget in (-1, 0, True, 2.5, 41, "40", None):
            with self.subTest(budget=budget):
                self.queue = {**original, "max_http_attempts": budget}
                with self.assertRaises(ValueError):
                    self.run_collection()
                self.factory.assert_not_called()

    def test_nonzero_or_non_numeric_purchase_budget_rejected(self):
        for budget in (1, -1, True, False, "0", None):
            with self.subTest(budget=budget):
                self.queue["purchases_budget_usd"] = budget
                with self.assertRaises(ValueError):
                    self.run_collection()
                self.factory.assert_not_called()

    def test_empty_duplicate_or_over_budget_documents_rejected(self):
        cases=([], [self.entry("first")]*2, [self.entry("first"), self.entry("FIRST")],
               [self.entry(f"x_{i}") for i in range(41)])
        for index, entries in enumerate(cases):
            with self.subTest(entries=len(entries)):
                self.factory.reset_mock()
                self.output=self.root/f"invalid_{index}"
                self.queue["documents"] = entries
                with self.assertRaises(ValueError):
                    self.run_collection()
                self.factory.assert_not_called()

    def test_invalid_or_unapproved_urls_rejected_before_network(self):
        for url in ("http://issuer.test/doc", "https://unapproved.test/doc", "https://issuer.test.evil.test/doc",
                    "https://user:secret@issuer.test/doc", "https://issuer.test:8443/doc", "https:///missing-host",
                    "https://issuer.test/doc#fragment"):
            with self.subTest(url=url):
                self.queue["documents"] = [{**self.entry("first"), "url": url}]
                with self.assertRaises(ValueError):
                    self.run_collection()
                self.factory.assert_not_called()

    def test_filename_cannot_escape_directory_or_use_windows_reserved_name(self):
        for name in ("../outside", "a/b", "a\\b", "", "..", "CON", "nul", "LPT1", "report"):
            with self.subTest(name=name):
                self.queue["documents"] = [{**self.entry("first"), "id": name}]
                with self.assertRaises(ValueError):
                    self.run_collection()
                self.factory.assert_not_called()

    def test_missing_target_metadata_rejected_before_first_request(self):
        del self.queue["documents"][1]["targets"]
        with self.assertRaises(ValueError):
            self.run_collection()
        self.factory.assert_not_called()

    def test_existing_directory_is_never_overwritten(self):
        self.output.mkdir()
        marker = self.output/"report.json"
        marker.write_text("preserve")
        with self.assertRaises(FileExistsError):
            self.run_collection()
        self.assertEqual(marker.read_text(), "preserve")
        self.factory.assert_not_called()

    def test_oversize_response_does_not_save_partial_document(self):
        self.queue["documents"] = [self.entry("first")]
        response = self.response()
        response.iter_content.return_value = iter([b"x"*1024*1024]*17)
        self.session.get.return_value = response
        result = self.run_collection()
        self.assertEqual(result["attempts"][0]["status"], "transport_or_size_failure_no_retry")
        self.assertEqual(list(self.output.iterdir()), [self.output/"report.json"])

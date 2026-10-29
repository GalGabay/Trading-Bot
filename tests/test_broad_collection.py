"""Offline transport, collection and qualification tests; no real credentials."""

from contextlib import redirect_stdout
from datetime import UTC, datetime
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

from backtesting import broad_collection as collection
from backtesting.pilot_readiness_review import write_json


def bar(day="2016-01-04T05:00:00Z", **changes):
    return dict(t=day, o=100, h=102, l=99, c=101, v=100, **changes)


class Fixture(TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        before = Path.cwd()
        os.chdir(temporary.name)
        self.addCleanup(os.chdir, before)
        for name, value in (("PROTOCOL", Path("protocol.json")), ("PLAN", Path("plan.json")),
                            ("OUTPUT", Path("out")), ("ONCE", Path("once.json"))):
            self.enterContext(patch.object(collection, name, value))
        self.enterContext(patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")))
        self.enterContext(patch("socket.create_connection", side_effect=AssertionError("Network forbidden")))
        self.credentials = self.enterContext(patch("app.broker.research_client._AlpacaCredentials.load",
            return_value=SimpleNamespace(api_key="fake-key", secret_key="fake-secret")))
        self.enterContext(patch.object(collection.time, "sleep"))
        self.clock = self.enterContext(patch.object(collection.time, "monotonic", return_value=100.0))
        self.limits = dict(global_http_attempt_limit=800, per_batch_http_attempt_limit=192,
            global_wall_clock_limit_minutes=60, per_batch_wall_clock_limit_minutes=15,
            minimum_request_spacing_seconds=.4, timeout_seconds=30,
            max_probe_intervals_per_batch=24, max_pages_per_symbol_resource=4)
        write_json(Path("roster.json"), {})
        # The fixture has only two scheduled sessions; it is never real evidence.
        calendar = [dict(opens_at=f"2016-01-{day}T14:30:00+00:00", closes_at=f"2016-01-{day}T21:00:00+00:00")
                    for day in ("04", "05")]
        write_json(Path("calendar.json"), calendar)
        write_json(Path("prior.json"), dict(required_event_checks=[]))
        write_json(Path("evidence.json"), dict(sources={}))
        write_json(Path("dummy.json"), {})
        write_json(Path("plan.json"), dict(collection_proposal=self.limits))
        import csv
        with Path("roster.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["instrument_id", "snapshot_alias"])
            writer.writeheader()
            writer.writerows(dict(instrument_id=f"ID-{n:03d}", snapshot_alias=f"S{n:03d}") for n in range(100))
        self.protocol = dict(plan=collection.pin("plan.json"), roster=collection.pin("roster.csv"),
            qualification=collection.pin("dummy.json"), inventory=collection.pin("dummy.json"),
            prior_report=collection.pin("dummy.json"), prior_summary=collection.pin("prior.json"),
            calendar=collection.pin("calendar.json"), prior_event_review=collection.pin("evidence.json"),
            execution_sha256={}, limits=self.limits, performance_authorized=False, paper_authorized=False,
            purchase_budget_usd=0, queue=[dict(instrument_id=f"ID-{n:03d}", snapshot_alias=f"S{n:03d}",
                source_name=f"Fixture {n}", start="2016-01-01", end_exclusive="2024-01-01",
                cached_bars=None, cached_action_queries=[], ready_for_simulation=False) for n in range(100)])
        self.freeze()

    def freeze(self):
        write_json(collection.PROTOCOL, self.protocol)

    def client(self):
        collection.OUTPUT.mkdir(exist_ok=True)
        self.report = dict(attempts=[], limits=self.limits)
        self.save = Mock()
        client = collection.BoundedClient(self.report, self.save)
        client._opener = Mock()
        client.page_path = collection.OUTPUT / "page.json"
        return client

    def response(self, payload=b'{"bars":{},"next_page_token":null}'):
        return io.BytesIO(payload)

    def request(self, client):
        return client.bars_page(symbol="AAPL", start=datetime(2016, 1, 1, tzinfo=UTC),
                                end_exclusive=datetime(2024, 1, 1, tzinfo=UTC))

    def collect(self, responder=None):
        def open_fixture(request, timeout):
            if responder:
                return responder(request, timeout)
            query = parse_qs(urlparse(request.full_url).query)
            symbol = query["symbols"][0]
            value = (dict(bars={symbol: [bar(), bar("2016-01-05T05:00:00Z")]}, next_page_token=None)
                     if "/stocks/bars" in request.full_url else dict(corporate_actions={}, next_page_token=None))
            return self.response(json.dumps(value).encode())
        with patch.object(collection, "build_opener") as opener, redirect_stdout(io.StringIO()):
            opener.return_value.open.side_effect = open_fixture
            result = collection.collect()
        return result

    def saved(self, bars=None, actions=None):
        collection.OUTPUT.mkdir()
        folder = collection.OUTPUT / "001"
        folder.mkdir()
        if bars is None:
            bars = [bar(), bar("2016-01-05T05:00:00Z")]
        write_json(folder / "bars.json", dict(bars={"S000": bars}, next_page_token=None))
        write_json(folder / "actions.json", dict(corporate_actions=actions or {}, next_page_token=None))
        write_json(collection.OUTPUT / "frozen_protocol.json", self.protocol)
        report = dict(protocol=collection.pin(collection.PROTOCOL), candidates=[dict(instrument_id="ID-000",
            bars=dict(status="downloaded_not_certified", pages=[collection.pin(folder/"bars.json")]),
            actions=dict(status="downloaded_not_certified", pages=[collection.pin(folder/"actions.json")]))],
            attempts=[], completed=False, stop_reason="synthetic_stop")
        write_json(collection.OUTPUT / "report.json", report)
        return report

    def qualify(self):
        result = collection.qualify()
        import csv
        with (collection.OUTPUT / "qualification.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        return result, rows


class TransportTests(Fixture):
    def test_exact_response_bytes_saved_and_journal_precedes_open(self):
        client = self.client()
        payload = b'{ "bars": {} , "next_page_token": null }\n'
        def open_response(request, timeout):
            self.assertEqual(self.report["attempts"][0]["state"], "started")
            self.save.assert_called()
            self.assertEqual(timeout, 30)
            self.assertEqual(request.get_method(), "GET")
            return self.response(payload)
        client._opener.open.side_effect = open_response
        self.request(client)
        self.assertEqual(client.page_path.read_bytes(), payload)
        self.assertEqual(self.report["attempts"][0]["state"], "response_saved")
        self.assertNotIn("fake-secret", json.dumps(self.report))
        self.assertNotIn("fake-key", json.dumps(self.report))

    def test_bars_query_keeps_feed_adjustment_and_reserved_year_boundary(self):
        client = self.client()
        client._opener.open.return_value = self.response()
        self.request(client)
        query = parse_qs(urlparse(client._opener.open.call_args.args[0].full_url).query)
        for key, value in dict(feed="sip", adjustment="raw", timeframe="1Day", asof="-", currency="USD").items():
            self.assertEqual(query[key], [value])
        self.assertTrue(query["end"][0].startswith("2023-12-31"))

    def test_action_query_is_bounded_and_does_not_call_trading_endpoint(self):
        client = self.client()
        client._opener.open.return_value = self.response(b'{"corporate_actions":{}}')
        client.actions_page(symbol="AAPL")
        request = client._opener.open.call_args.args[0]
        self.assertEqual(urlparse(request.full_url).path, "/v1/corporate-actions")
        self.assertEqual(parse_qs(urlparse(request.full_url).query)["end"], ["2023-12-31"])

    def test_account_endpoint_blocked_before_http(self):
        client = self.client()
        with self.assertRaises(collection.CollectionStop):
            client._get("/v2/account", {"symbols": "AAPL"})
        client._opener.open.assert_not_called()
        self.assertFalse(self.report["attempts"])

    def test_denials_redirects_and_server_errors_stop_without_retry(self):
        client = self.client()
        for code in (301, 302, 307, 308, 401, 402, 403, 407, 429, 500, 503):
            with self.subTest(code=code):
                client._opener.open.reset_mock()
                client._opener.open.side_effect = HTTPError("https://fixture", code, "private error body", {}, None)
                with self.assertRaises(collection.CollectionStop):
                    self.request(client)
                self.assertEqual(client._opener.open.call_count, 1)
                self.assertEqual(self.report["attempts"][-1]["http_status"], code)
                self.assertNotIn("private error", json.dumps(self.report))

    def test_unsupported_historical_queries_are_recorded_gaps(self):
        client = self.client()
        for code in (400, 404, 422):
            with self.subTest(code=code):
                client._opener.open.side_effect = HTTPError("https://fixture", code, "", {}, None)
                with self.assertRaisesRegex(ValueError, "unsupported_historical_query"):
                    self.request(client)
                self.assertEqual(self.report["attempts"][-1]["http_status"], code)

    def test_transport_failures_consume_one_attempt_and_stop(self):
        client = self.client()
        for error in (TimeoutError(), URLError("private endpoint detail"), OSError(), EOFError()):
            with self.subTest(error=type(error).__name__):
                before = len(self.report["attempts"])
                client._opener.open.side_effect = error
                with self.assertRaisesRegex(collection.CollectionStop, "transport_failure"):
                    self.request(client)
                self.assertEqual(len(self.report["attempts"]), before + 1)
                self.assertEqual(self.report["attempts"][-1]["state"], "transport_failure")

    def test_page_size_cap_preserves_truncated_original_response(self):
        client = self.client()
        client._opener.open.return_value = self.response(b"x" * 8_000_001)
        with self.assertRaisesRegex(ValueError, "page_size_limit"):
            self.request(client)
        self.assertEqual(client.page_path.stat().st_size, 8_000_001)

    def test_bad_json_and_nonobject_payloads_are_preserved(self):
        client = self.client()
        for payload in (b"broken", b"[]", b"null"):
            with self.subTest(payload=payload):
                client._opener.open.return_value = self.response(payload)
                with self.assertRaises(ValueError):
                    self.request(client)
                self.assertEqual(client.page_path.read_bytes(), payload)

    def test_global_request_cap_survives_next_batch(self):
        client = self.client()
        self.report["attempts"] = [{}] * 800
        client.next_batch()
        with self.assertRaises(collection.CollectionStop):
            self.request(client)
        client._opener.open.assert_not_called()

    def test_batch_request_cap_blocks_before_http(self):
        client = self.client()
        client.batch_attempts = 192
        with self.assertRaises(collection.CollectionStop):
            self.request(client)
        client._opener.open.assert_not_called()

    def test_global_and_batch_time_caps_block_before_http(self):
        client = self.client()
        for started, batch_started in ((-3500, 100), (100, -800)):
            with self.subTest(started=started):
                client.started, client.batch_started = started, batch_started
                with self.assertRaises(collection.CollectionStop):
                    self.request(client)
        client._opener.open.assert_not_called()

    def test_timeout_reduced_to_remaining_elapsed_budget(self):
        client = self.client()
        client.batch_started = -795
        client._opener.open.return_value = self.response()
        self.request(client)
        self.assertEqual(client._opener.open.call_args.kwargs["timeout"], 5)

    def test_request_spacing_is_global_across_batches(self):
        client = self.client()
        client._last_request = 100
        client.next_batch()
        client._opener.open.return_value = self.response()
        self.request(client)
        collection.time.sleep.assert_called_once_with(.4)

    def test_future_naive_and_unsafe_symbol_queries_make_no_request(self):
        client = self.client()
        cases = [dict(symbol="AAPL", start=datetime(2023,1,1,tzinfo=UTC), end_exclusive=datetime(2025,1,1,tzinfo=UTC)),
                 dict(symbol="AAPL", start=datetime(2016,1,1), end_exclusive=datetime(2024,1,1,tzinfo=UTC)),
                 dict(symbol="../AAPL", start=datetime(2016,1,1,tzinfo=UTC), end_exclusive=datetime(2024,1,1,tzinfo=UTC))]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                client.bars_page(**args)
        client._opener.open.assert_not_called()


class ProtocolAndCollectorTests(Fixture):
    def test_protocol_retains_exact_100_order(self):
        self.assertEqual(len(collection.load_protocol()["queue"]), 100)
        self.protocol["queue"].reverse(); self.freeze()
        with self.assertRaisesRegex(ValueError, "sample"):
            collection.load_protocol()

    def test_changed_pinned_input_rejected(self):
        Path("dummy.json").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "checksum"):
            collection.load_protocol()

    def test_changed_execution_source_rejected(self):
        Path("source.py").write_text("original", encoding="utf-8")
        self.protocol["execution_sha256"] = {"source.py": collection.digest("source.py")}
        self.freeze()
        Path("source.py").write_text("changed", encoding="utf-8")
        with self.assertRaises(ValueError):
            collection.load_protocol()

    def test_performance_paper_and_spending_flags_rejected(self):
        for key,value in (("performance_authorized",True),("paper_authorized",True),("purchase_budget_usd",1)):
            with self.subTest(key=key):
                self.protocol[key]=value; self.freeze()
                with self.assertRaisesRegex(ValueError,"authorization"):
                    collection.load_protocol()
                self.protocol[key]=False if key!="purchase_budget_usd" else 0

    def test_changed_limits_rejected(self):
        self.protocol["limits"] = {**self.limits, "global_http_attempt_limit": 900}
        self.freeze()
        with self.assertRaisesRegex(ValueError, "limits"):
            collection.load_protocol()

    def test_reserved_dates_and_readiness_rejected(self):
        for key,value in (("end_exclusive","2025-01-01"),("start","2015-01-01"),("ready_for_simulation",True)):
            with self.subTest(key=key):
                original=self.protocol["queue"][0][key]
                self.protocol["queue"][0][key]=value; self.freeze()
                with self.assertRaises(ValueError): collection.load_protocol()
                self.protocol["queue"][0][key]=original

    def test_all_100_collected_with_cumulative_batches(self):
        result=self.collect()
        self.assertTrue(result["completed"])
        report=json.loads((collection.OUTPUT/"report.json").read_text())
        self.assertEqual(result["http_attempts"],200)
        self.assertEqual([sum(a["batch"]==b for a in report["attempts"]) for b in range(1,6)],[48,48,48,48,8])
        self.assertEqual(len(report["candidates"]),100)
        self.assertTrue(collection.ONCE.exists())

    def test_global_denial_stops_remaining_resources_and_candidates(self):
        def denied(request, timeout): raise HTTPError("https://fixture",403,"",{},None)
        result=self.collect(denied)
        report=json.loads((collection.OUTPUT/"report.json").read_text())
        self.assertFalse(result["completed"])
        self.assertEqual(result["http_attempts"],1)
        self.assertEqual(len(report["candidates"]),1)
        summary,rows=self.qualify()
        self.assertEqual(len(rows),100)
        self.assertEqual(summary["new_stocks_admitted"],0)

    def test_transport_failure_stops_all_batches_without_retry(self):
        def failed(request, timeout): raise TimeoutError()
        result=self.collect(failed)
        self.assertEqual(result["stop_reason"],"transport_failure")
        self.assertEqual(result["http_attempts"],1)

    def test_single_journal_prevents_restart_in_new_output(self):
        collection.ONCE.write_text("started",encoding="utf-8")
        with self.assertRaises(FileExistsError): collection.collect()
        self.credentials.assert_not_called()
        self.assertFalse(collection.OUTPUT.exists())

    def test_interrupted_request_remains_counted_and_cannot_restart(self):
        def interrupted(request, timeout): raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): self.collect(interrupted)
        report=json.loads((collection.OUTPUT/"report.json").read_text())
        self.assertEqual(len(report["attempts"]),1)
        self.assertEqual(report["attempts"][0]["state"],"started")
        self.assertTrue(collection.ONCE.exists())
        with self.assertRaises(FileExistsError): collection.collect()

    def test_existing_output_is_never_overwritten(self):
        collection.OUTPUT.mkdir()
        marker=collection.OUTPUT/"keep.txt"; marker.write_text("keep",encoding="utf-8")
        with self.assertRaises(FileExistsError): collection.collect()
        self.assertEqual(marker.read_text(),"keep")
        self.credentials.assert_not_called()

    def test_cache_reuse_does_not_request_cached_resources(self):
        frame="timestamp,symbol,open,high,low,close,volume\n2016-01-04T05:00:00Z,S000,100,102,99,101,100\n"
        Path("cached.csv").write_text(frame,encoding="utf-8")
        write_json(Path("actions.json"),dict(corporate_actions={},next_page_token=None))
        self.protocol["queue"][0]["cached_bars"]=collection.pin("cached.csv")
        self.protocol["queue"][0]["cached_action_queries"]=[dict(symbol="S000",pages=[collection.pin("actions.json")])]
        self.freeze()
        result=self.collect()
        self.assertEqual(result["http_attempts"],198)
        report=json.loads((collection.OUTPUT/"report.json").read_text())
        self.assertFalse(any(a["symbol"]=="S000" for a in report["attempts"]))

    def test_repeated_token_cannot_certify_complete_resource(self):
        def repeated(request,timeout):
            if parse_qs(urlparse(request.full_url).query)["symbols"] != ["S000"]:
                raise HTTPError("https://fixture",403,"",{},None)
            return self.response(b'{"bars":{},"corporate_actions":{},"next_page_token":"same"}')
        self.collect(repeated)
        report=json.loads((collection.OUTPUT/"report.json").read_text())
        self.assertEqual(report["candidates"][0]["bars"]["status"],"invalid_or_unavailable_saved_source")
        self.assertEqual(len(report["candidates"][0]["bars"]["pages"]),2)

    def test_four_page_cap_leaves_incomplete_not_accepted(self):
        counts={}
        def endless(request,timeout):
            key=urlparse(request.full_url).path,parse_qs(urlparse(request.full_url).query)["symbols"][0]
            if key[1] != "S000":
                raise HTTPError("https://fixture",403,"",{},None)
            counts[key]=counts.get(key,0)+1
            return self.response(json.dumps(dict(bars={},corporate_actions={},next_page_token=str(counts[key]))).encode())
        self.collect(endless)
        report=json.loads((collection.OUTPUT/"report.json").read_text())
        self.assertEqual(report["candidates"][0]["bars"]["status"],"incomplete_page_cap")
        self.assertEqual(len(report["candidates"][0]["bars"]["pages"]),4)
        self.assertTrue(all(n<=4 for n in counts.values()))


class QualificationTests(Fixture):
    def test_valid_candles_stay_unapproved_and_all_names_retained(self):
        self.saved()
        summary,rows=self.qualify()
        self.assertEqual(summary["selected_full_raw_calendar_observed"],1)
        self.assertEqual(summary["candle_rows"],2)
        self.assertTrue(all(r["ready_for_broad_scoring"]=="False" for r in rows))
        self.assertEqual(len(rows),100)
        self.credentials.assert_not_called()

    def test_empty_response_is_not_zero_price_or_terminal_recovery(self):
        self.saved(bars=[])
        _,rows=self.qualify()
        self.assertEqual(rows[0]["rows"],"0")
        self.assertEqual(rows[0]["full_calendar_observed"],"False")
        self.assertNotIn("zero recovery",rows[0]["blockers"])

    def test_partial_history_not_filled_or_called_confirmed_missing(self):
        self.saved(bars=[bar()])
        _,rows=self.qualify()
        self.assertEqual(rows[0]["rows"],"1")
        self.assertEqual(rows[0]["unobserved_calendar_sessions"],"1")
        self.assertIn("not automatically missing candles",rows[0]["blockers"])

    def test_duplicate_candles_are_hard_errors(self):
        self.saved(bars=[bar(),bar()])
        _,rows=self.qualify()
        self.assertEqual(rows[0]["price_status"],"hard_price_validation_error")
        self.assertIn("duplicate_candles",rows[0]["validation_error_codes"])

    def test_naive_and_missing_timestamps_are_hard_errors(self):
        self.saved(bars=[bar("2016-01-04T05:00:00")])
        _,rows=self.qualify()
        self.assertIn("timezone_missing",rows[0]["validation_error_codes"])

    def test_outside_scheduled_session_is_hard_error(self):
        self.saved(bars=[bar("2016-01-09T05:00:00Z")])
        _,rows=self.qualify()
        self.assertIn("outside_market_session",rows[0]["validation_error_codes"])

    def test_reserved_year_candle_is_never_admitted(self):
        self.saved(bars=[bar("2024-01-02T05:00:00Z")])
        _,rows=self.qualify()
        self.assertEqual(rows[0]["price_status"],"hard_price_validation_error")

    def test_invalid_ohlc_and_negative_prices_are_hard_errors(self):
        bad=bar(); bad["h"]=90
        self.saved(bars=[bad])
        _,rows=self.qualify()
        self.assertIn("invalid_high",rows[0]["validation_error_codes"])

    def test_zero_price_is_hard_error(self):
        bad=bar(); bad["l"]=0
        self.saved(bars=[bad])
        _,rows=self.qualify()
        self.assertIn("invalid_price",rows[0]["validation_error_codes"])

    def test_negative_price_is_hard_error(self):
        bad=bar(); bad["l"]=-1
        self.saved(bars=[bad])
        _,rows=self.qualify()
        self.assertIn("invalid_price",rows[0]["validation_error_codes"])

    def test_missing_timestamp_is_hard_error(self):
        bad=bar(); bad["t"]=None
        self.saved(bars=[bad])
        _,rows=self.qualify()
        self.assertIn("invalid_timestamp",rows[0]["validation_error_codes"])

    def test_zero_volume_is_warning_not_hard_error(self):
        bad=bar(); bad["v"]=0
        self.saved(bars=[bad,bar("2016-01-05T05:00:00Z")])
        _,rows=self.qualify()
        self.assertEqual(rows[0]["price_status"],"downloaded_raw_observation")
        self.assertIn("zero_volume",rows[0]["volume_warnings"])

    def test_negative_volume_is_hard_error(self):
        bad=bar(); bad["v"]=-1
        self.saved(bars=[bad])
        _,rows=self.qualify()
        self.assertIn("negative_volume",rows[0]["validation_error_codes"])

    def test_unordered_candles_cannot_be_silently_sorted(self):
        self.saved(bars=[bar("2016-01-05T05:00:00Z"),bar()])
        _,rows=self.qualify()
        self.assertEqual(rows[0]["price_status"],"hard_price_validation_error")

    def test_corrupt_saved_page_becomes_hard_error(self):
        self.saved()
        (collection.OUTPUT/"001/bars.json").write_text("changed",encoding="utf-8")
        _,rows=self.qualify()
        self.assertEqual(rows[0]["price_status"],"hard_price_validation_error")

    def test_unexpected_returned_symbol_is_not_relabelled(self):
        report=self.saved()
        path=collection.OUTPUT/"001/bars.json"
        write_json(path,dict(bars={"OTHER":[bar()]},next_page_token=None))
        report["candidates"][0]["bars"]["pages"]=[collection.pin(path)]
        write_json(collection.OUTPUT/"report.json",report)
        _,rows=self.qualify()
        self.assertEqual(rows[0]["price_status"],"hard_price_validation_error")

    def test_conflicting_duplicate_actions_are_hard_errors(self):
        self.saved(actions=dict(cash_dividends=[dict(id="same",rate=1),dict(id="same",rate=2)]))
        _,rows=self.qualify()
        self.assertEqual(rows[0]["action_status"],"hard_action_inventory_error")

    def test_identical_duplicate_action_is_counted_once(self):
        self.saved(actions=dict(cash_dividends=[dict(id="same",rate=1),dict(id="same",rate=1)]))
        _,rows=self.qualify()
        self.assertEqual(rows[0]["provider_event_count"],"1")

    def test_cash_and_noncash_inventory_do_not_invent_payment_or_approval(self):
        self.saved(actions=dict(cash_dividends=[dict(id="cash",rate=1,ex_date="2016-01-04")],
                                spin_offs=[dict(id="shares")]))
        _,rows=self.qualify()
        inventory=json.loads((collection.OUTPUT/"001/event_inventory.json").read_text())
        self.assertTrue(all(e["cash_available_session"] is None and not e["ready_for_simulation"] for e in inventory))
        self.assertIn("spin_offs",rows[0]["blockers"])

    def test_empty_event_inventory_is_not_event_free_certification(self):
        self.saved()
        _,rows=self.qualify()
        self.assertIn("not evidence of no company events",rows[0]["blockers"])

    def test_changed_protocol_snapshot_rejected(self):
        self.saved()
        write_json(collection.OUTPUT/"frozen_protocol.json",{})
        with self.assertRaisesRegex(ValueError,"protocol changed"): collection.qualify()

    def test_nonsequential_attempt_ledger_rejected(self):
        report=self.saved()
        report["attempts"]=[dict(number=2)]
        write_json(collection.OUTPUT/"report.json",report)
        with self.assertRaisesRegex(ValueError,"ledger"): collection.qualify()


class EvidenceReviewTests(Fixture):
    def setUp(self):
        super().setUp()
        from backtesting import broad_evidence_review
        self.review_module=broad_evidence_review
        self.enterContext(patch.object(broad_evidence_review,"OUTPUT",collection.OUTPUT))
        self.enterContext(patch.object(broad_evidence_review,"PROTOCOL",collection.PROTOCOL))
        # The reviewer records its code checksum relative to the fixture root.
        Path("backtesting").mkdir()
        Path("backtesting/broad_evidence_review.py").write_bytes(Path(broad_evidence_review.__file__).read_bytes())

    def review(self, **kwargs):
        self.saved(**kwargs)
        self.qualify()
        result=self.review_module.review()
        targets=json.loads((collection.OUTPUT/"evidence_review_targets.json").read_text())
        return result,targets

    def test_all_candidates_retained_without_identity_approval(self):
        result,targets=self.review()
        self.assertEqual(len(targets),100)
        self.assertEqual(result["new_stocks_admitted"],0)
        self.assertTrue(all(t["identity_review_required"] and not t["ready_for_broad_scoring"] for t in targets))
        self.credentials.assert_not_called()

    def test_process_and_ex_dates_do_not_become_payable_dates(self):
        result,targets=self.review(actions=dict(cash_dividends=[dict(id="D1",rate=1,
            ex_date="2016-01-04",process_date="2016-01-04")]))
        self.assertEqual(result["cash_dividends_without_payable_date"],1)
        self.assertEqual(targets[0]["cash_dividends_without_announcement_date"],1)

    def test_explicit_payable_and_announcement_fields_remain_provider_evidence(self):
        result,targets=self.review(actions=dict(cash_dividends=[dict(id="D1",rate=1,
            ex_date="2016-01-04",payable_date="2016-01-15",declaration_date="2015-12-15")]))
        self.assertEqual(result["cash_dividends_without_payable_date"],0)
        self.assertEqual(result["cash_dividends_without_announcement_date"],0)
        self.assertFalse(targets[0]["ready_for_broad_scoring"])

    def test_alternative_provider_date_fields_are_not_discarded(self):
        result,_=self.review(actions=dict(cash_dividends=[dict(id="D1",rate=1,
            payment_date="2016-01-15",announcement_date="2015-12-15")]))
        self.assertEqual(result["cash_dividends_without_payable_date"],0)
        self.assertEqual(result["cash_dividends_without_announcement_date"],0)

    def test_incoming_symbol_after_membership_requires_identity_review(self):
        result,targets=self.review(actions=dict(name_changes=[dict(id="N1",old_symbol="OTHER",
            new_symbol="S000",process_date="2020-01-01")]))
        self.assertEqual(result["histories_with_incoming_alias_flags"],1)
        self.assertIn("Priority identity quarantine"," ".join(targets[0]["remaining_review_tasks"]))

    def test_outgoing_symbol_change_is_not_an_incoming_reuse_flag(self):
        result,_=self.review(actions=dict(name_changes=[dict(id="N1",old_symbol="S000",
            new_symbol="OTHER",process_date="2020-01-01")]))
        self.assertEqual(result["histories_with_incoming_alias_flags"],0)

    def test_large_price_jump_flag_does_not_adjust_prices(self):
        second=dict(t="2016-01-05T05:00:00Z",o=200,h=205,l=198,c=202,v=100)
        result,targets=self.review(bars=[bar(),second])
        self.assertEqual(result["raw_close_moves_at_least_40_percent"],1)
        self.assertEqual(targets[0]["large_close_moves"],1)
        import pandas as pd
        self.assertEqual(pd.read_csv(collection.OUTPUT/"001/qualified_observations.csv")["close"].iloc[1],202)

    def test_partial_history_distinguishes_trailing_from_interior_gaps(self):
        _,targets=self.review(bars=[bar()])
        self.assertEqual(targets[0]["interior_unobserved_sessions"],0)
        self.assertEqual(targets[0]["after_last_observation"],1)

    def test_noncash_events_require_share_and_cash_outcome_review(self):
        result,targets=self.review(actions=dict(spin_offs=[dict(id="SPIN")]))
        self.assertEqual(result["histories_with_non_cash_events"],1)
        self.assertIn("spin_offs",targets[0]["noncash_categories"])

    def test_tampered_price_observation_hash_is_rejected(self):
        self.saved(); self.qualify()
        (collection.OUTPUT/"001/qualified_observations.csv").write_text("changed",encoding="utf-8")
        with self.assertRaises(ValueError): self.review_module.review()

    def test_tampered_event_inventory_hash_is_rejected(self):
        self.saved(); self.qualify()
        (collection.OUTPUT/"001/event_inventory.json").write_text("changed",encoding="utf-8")
        with self.assertRaises(ValueError): self.review_module.review()

    def test_reordered_or_dropped_review_candidate_is_rejected(self):
        self.saved(); self.qualify()
        import csv
        path=collection.OUTPUT/"qualification.csv"
        with path.open(encoding="utf-8",newline="") as stream: rows=list(csv.DictReader(stream))
        from backtesting.pilot_readiness_review import write_csv
        write_csv(path,rows[:-1])
        with self.assertRaisesRegex(ValueError,"candidate"): self.review_module.review()

"""Synthetic offline tests: no real credentials, sockets, account or orders."""

from contextlib import redirect_stdout
from copy import deepcopy
from datetime import UTC, datetime
import csv
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request

from backtesting import historical_input as inputs
from backtesting import successor_branch_probe as branch
from backtesting import successor_collection as collector
from backtesting.broad_collection import pin
from backtesting.event_review import review_rows
from backtesting.input_guards import validate_ledger, validate_public_report, validate_streams
from backtesting.pilot_readiness_review import write_csv, write_json


LIMITS = dict(max_elapsed_minutes=15, max_http_attempts=192,
              max_pages_per_resource=4, max_probe_intervals=32)


def candle(day="2016-01-04T05:00:00Z"):
    return dict(t=day, o=100, h=102, l=99, c=101, v=100)


class OfflineFixture(TestCase):
    def setUp(self):
        self.executed_builder = Path(inputs.__file__).read_bytes()
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        before = Path.cwd()
        os.chdir(temporary.name)
        self.addCleanup(os.chdir, before)
        self.enterContext(patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")))
        self.enterContext(patch("socket.create_connection", side_effect=AssertionError("Network forbidden")))
        self.credentials = self.enterContext(patch("app.broker.research_client._AlpacaCredentials.load",
            return_value=SimpleNamespace(api_key="fake-key", secret_key="fake-secret")))
        self.enterContext(patch.object(collector.time, "sleep"))
        self.clock = self.enterContext(patch.object(collector.time, "monotonic", return_value=100.0))
        for name, value in (("PLAN", Path("docs/broad_successor_collection_plan.json")),
                            ("OUTPUT", Path("successors")), ("JOURNAL", Path("once.json"))):
            self.enterContext(patch.object(collector, name, value))
        Path("docs").mkdir()
        write_json(Path("scope.json"), dict(price_collection_limits=LIMITS))
        self.probe = dict(id="probe", symbol="AAPL", start="2016-01-01",
                          end_exclusive="2016-01-06", readiness=False)
        self.plan = dict(scope=pin("scope.json"), limits=dict(LIMITS), purchases_usd=0,
                         probes=[self.probe], inputs=[], execution_sha256={})
        self.freeze()

    def freeze(self):
        write_json(collector.PLAN, self.plan)

    def collect(self, responder=None):
        def response(request, timeout):
            if responder:
                return responder(request, timeout)
            query = parse_qs(urlparse(request.full_url).query)
            symbol = query["symbols"][0]
            payload = (dict(bars={symbol: [candle()]}, next_page_token=None)
                       if "/stocks/bars" in request.full_url else dict(corporate_actions={}, next_page_token=None))
            return io.BytesIO(json.dumps(payload).encode())
        with patch.object(collector, "build_opener") as opener, redirect_stdout(io.StringIO()):
            opener.return_value.open.side_effect = response
            result = collector.collect()
        return result, json.loads((collector.OUTPUT / "report.json").read_text())


class CollectorTests(OfflineFixture):
    def test_valid_collection_preserves_bytes_and_closes_journal(self):
        result, report = self.collect()
        self.assertTrue(result["completed"])
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(json.loads(collector.JOURNAL.read_text())["state"], "closed_do_not_restart")
        for attempt in report["attempts"]:
            self.assertEqual(attempt["source"], pin(attempt["source"]["path"]))
        self.assertNotIn("fake-", json.dumps(report))

    def test_exact_saved_bytes_and_request_journal_precede_http(self):
        report, save = dict(attempts=[]), Mock()
        recorder = collector.RecordedOpener(report, save, LIMITS)
        recorder.page_path = Path("page.json")
        payload = b'{ "bars": {} }\n'
        def response(request, timeout):
            self.assertEqual(report["attempts"][0]["state"], "started")
            save.assert_called()
            return io.BytesIO(payload)
        recorder.opener = Mock()
        recorder.opener.open.side_effect = response
        with recorder.open(Request("https://fixture"), timeout=30) as handle:
            self.assertEqual(handle.read(100), payload)
        self.assertEqual(recorder.page_path.read_bytes(), payload)

    def test_access_rate_redirect_server_failures_stop_once(self):
        for code in (301, 401, 402, 403, 429, 500, 503):
            with self.subTest(code=code):
                collector.OUTPUT = Path(f"out{code}")
                collector.JOURNAL = Path(f"once{code}.json")
                def response(request, timeout):
                    raise HTTPError(request.full_url, code, "private", {}, None)
                result, report = self.collect(response)
                self.assertFalse(result["completed"])
                self.assertEqual(len(report["attempts"]), 1)
                self.assertEqual(report["attempts"][0]["http_status"], code)
                self.assertNotIn("private", json.dumps(report))

    def test_unsupported_symbol_is_gap_without_retry(self):
        def response(request, timeout):
            raise HTTPError(request.full_url, 404, "missing", {}, None)
        result, report = self.collect(response)
        self.assertTrue(result["completed"])
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(report["probes"][0]["bars"]["status"], "unavailable_no_retry")

    def test_transport_failure_stops_batch(self):
        result, report = self.collect(lambda *args: (_ for _ in ()).throw(OSError("private")))
        self.assertFalse(result["completed"])
        self.assertEqual(report["attempts"][0]["state"], "transport_failure")

    def test_response_read_failure_is_recorded(self):
        report, save = dict(attempts=[]), Mock()
        recorder = collector.RecordedOpener(report, save, LIMITS)
        recorder.opener = Mock()
        response = io.BytesIO()
        response.read = Mock(side_effect=EOFError("private"))
        recorder.opener.open.return_value = response
        recorder.page_path = Path("page.json")
        with self.assertRaises(EOFError):
            with recorder.open(Request("https://fixture"), 30) as handle:
                handle.read(100)
        self.assertEqual(report["attempts"][0]["state"], "transport_failure")
        self.assertFalse(recorder.page_path.exists())

    def test_request_and_elapsed_caps_block_before_open(self):
        for attempts, now in (([{}] * 192, 100), ([], 1000)):
            recorder = collector.RecordedOpener(dict(attempts=attempts), Mock(), LIMITS)
            recorder.opener = Mock()
            self.clock.return_value = now
            with self.assertRaises(collector.BatchStop):
                recorder.open(Request("https://fixture"), 30)
            recorder.opener.open.assert_not_called()
            self.clock.return_value = 100

    def test_invalid_and_repeated_tokens_rejected(self):
        for index, token in enumerate(("", 1, "repeat")):
            collector.OUTPUT, collector.JOURNAL = Path(f"out{index}"), Path(f"once{index}.json")
            result, report = self.collect(lambda *args: io.BytesIO(json.dumps(dict(next_page_token=token)).encode()))
            self.assertTrue(result["completed"])
            self.assertEqual(report["probes"][0]["bars"]["status"], "invalid_saved_response")

    def test_page_limit_marks_incomplete_without_followup(self):
        count = 0
        def response(*args):
            nonlocal count
            count += 1
            return io.BytesIO(json.dumps(dict(next_page_token=str(count))).encode())
        _, report = self.collect(response)
        self.assertEqual(len(report["attempts"]), 8)
        self.assertEqual(report["probes"][0]["bars"]["status"], "incomplete_page_cap")

    def test_malformed_json_and_oversize_pages_remain_saved_invalid(self):
        for index, payload in enumerate((b"invalid", b"[]", b"x" * 8_000_001)):
            collector.OUTPUT, collector.JOURNAL = Path(f"out{index}"), Path(f"once{index}.json")
            _, report = self.collect(lambda *args: io.BytesIO(payload))
            self.assertEqual(report["probes"][0]["bars"]["status"], "invalid_saved_response")
            self.assertEqual((collector.OUTPUT / "001/bars_1.json").read_bytes(), payload)

    def test_exclusive_journal_and_output_prevent_restarts(self):
        self.collect()
        with self.assertRaises(FileExistsError):
            collector.collect()
        collector.OUTPUT = Path("different")
        with self.assertRaises(FileExistsError):
            collector.collect()

    def test_invalid_plans_rejected_before_credentials(self):
        baseline = deepcopy(self.plan)
        for change in (dict(purchases_usd=1), dict(probes=[]),
                       dict(probes=[self.probe, self.probe]),
                       dict(probes=[dict(self.probe, symbol="JPM")]),
                       dict(probes=[dict(self.probe, end_exclusive="2025-01-01")]),
                       dict(probes=[dict(self.probe, start="2016-02-30")]),
                       dict(limits=dict(LIMITS, max_http_attempts=193))):
            with self.subTest(change=change):
                self.plan = dict(baseline, **change)
                self.freeze()
                with self.assertRaises(ValueError):
                    collector.collect()
        self.credentials.assert_not_called()

    def test_changed_input_pin_is_rejected(self):
        self.plan["inputs"] = [pin("scope.json")]
        self.freeze()
        Path("scope.json").write_text("{}")
        with self.assertRaises(ValueError):
            collector.load_plan()

    def test_changed_execution_pin_is_rejected(self):
        Path("executed.py").write_bytes(b"original")
        self.plan["execution_sha256"] = {"executed.py": pin("executed.py")["sha256"]}
        self.freeze()
        Path("executed.py").write_bytes(b"changed")
        with self.assertRaises(ValueError):
            collector.load_plan()


class BranchTests(OfflineFixture):
    def setUp(self):
        super().setUp()
        self.parent_result, self.parent = self.collect()
        for name, value in (("PLAN", Path("child.json")), ("OUTPUT", Path("child")),
                            ("JOURNAL", Path("child_once.json"))):
            self.enterContext(patch.object(branch, name, value))
        write_json(Path("evidence.json"), {})
        self.child_plan = dict(parent_report=pin(collector.OUTPUT / "report.json"),
            provider_evidence=pin("evidence.json"), execution_sha256={}, purchases_usd=0,
            conservative_budget_origin_utc="2023-01-01T00:00:00+00:00",
            probe=dict(id="bwa_phin", symbol="PHIN", start="2023-07-05", end_exclusive="2024-01-01", readiness=False))
        self.now = self.enterContext(patch.object(branch.time, "time", return_value=datetime(2023, 1, 1, tzinfo=UTC).timestamp()+100))
        self.freeze_child()

    def freeze_child(self):
        write_json(branch.PLAN, self.child_plan)

    def child(self, payload=b'{"next_page_token":null}'):
        with patch.object(collector, "build_opener") as opener:
            opener.return_value.open.side_effect = lambda *args, **kwargs: io.BytesIO(payload)
            return branch.collect()

    def test_valid_child_retains_original_ledger(self):
        result = self.child()
        report = json.loads((branch.OUTPUT / "report.json").read_text())
        self.assertTrue(result["completed"])
        self.assertEqual(result["new_attempts"], 2)
        self.assertEqual(report["attempts"][:2], self.parent["attempts"])
        self.assertEqual(report["attempts"][-1]["number"], 4)

    def test_stopped_parent_cannot_be_continued(self):
        self.parent.update(completed=False, stop_reason="access_stop")
        write_json(collector.OUTPUT / "report.json", self.parent)
        self.child_plan["parent_report"] = pin(collector.OUTPUT / "report.json")
        self.freeze_child()
        with self.assertRaisesRegex(ValueError, "stopped"):
            self.child()
        self.assertFalse(branch.JOURNAL.exists())

    def test_naive_future_and_expired_budget_rejected(self):
        for stamp in ("2023-01-01T00:00:00", "2023-01-02T00:00:00+00:00", "2022-12-31T00:00:00+00:00"):
            self.child_plan["conservative_budget_origin_utc"] = stamp
            self.freeze_child()
            with self.assertRaises(ValueError):
                self.child()

    def test_changed_branch_or_spending_rejected(self):
        baseline = deepcopy(self.child_plan)
        for spending in (False, True):
            self.child_plan = deepcopy(baseline)
            if spending:
                self.child_plan["purchases_usd"] = 1
            else:
                self.child_plan["probe"]["symbol"] = "OTHER"
            self.freeze_child()
            with self.assertRaises(ValueError):
                self.child()

    def test_client_setup_failure_finalizes_journal(self):
        self.credentials.side_effect = ValueError("secret configuration")
        result = self.child()
        self.assertFalse(result["completed"])
        self.assertEqual(json.loads(branch.JOURNAL.read_text())["state"], "closed_do_not_restart")
        self.assertNotIn("secret", (branch.OUTPUT / "report.json").read_text())

    def test_paginated_child_is_not_followed_automatically(self):
        result = self.child(b'{"next_page_token":"more"}')
        report = json.loads((branch.OUTPUT / "report.json").read_text())
        self.assertEqual(result["new_attempts"], 2)
        self.assertEqual(report["probes"][0]["bars"]["status"], "incomplete_no_followup")


class InputFixture(OfflineFixture):
    def setUp(self):
        super().setUp()
        self.enterContext(patch.object(inputs, "SPEC", Path("spec.json")))
        self.enterContext(patch.object(inputs, "SUCCESSORS", Path("successors")))
        self.enterContext(patch.object(inputs, "PUBLIC", Path("public")))
        Path("backtesting").mkdir()
        Path("backtesting/historical_input.py").write_bytes(self.executed_builder)
        self.roster, self.rows, self.streams = [], [], []
        for n in range(100):
            identity, symbol = f"ID-{n:03d}", f"S{n:03d}"
            folder = Path(f"data/reports/broad_100_collection_v1/{n+1:03d}")
            folder.mkdir(parents=True)
            price = folder / "bars.csv"
            write_csv(price, [dict(timestamp=day, symbol=symbol, open=100, high=102, low=99, close=101, volume=100)
                              for day in ("2016-01-04T05:00:00Z", "2016-01-05T05:00:00Z")])
            event = folder / "event_inventory.json"
            write_json(event, [])
            self.roster.append(dict(instrument_id=identity, snapshot_alias=symbol))
            self.rows.append(dict(instrument_id=identity, snapshot_alias=symbol,
                observation_csv=price.as_posix(), observation_sha256=pin(price)["sha256"], event_inventory_sha256=pin(event)["sha256"]))
            self.streams.append(dict(instrument_id=identity, root_id=identity, role="original_member", snapshot_alias=symbol,
                strict_identity_verified=False, parts=[dict(source_key="base:"+symbol, start="2016-01-01",
                end_exclusive="2016-01-06", primary_source_ids=[])]))
        write_csv(Path("roster.csv"), self.roster)
        write_csv(Path("inventory.csv"), self.rows)
        write_json(Path("prior.json"), dict(qualification_csv=pin("inventory.csv")))
        write_json(Path("calendar.json"), [dict(opens_at=f"2016-01-{day}T14:30:00+00:00", closes_at=f"2016-01-{day}T21:00:00+00:00") for day in ("04", "05")])
        write_json(Path("public_queue.json"), dict(documents=[], max_http_attempts=40))
        Path("public").mkdir()
        write_json(Path("public/report.json"), dict(queue_sha256=pin("public_queue.json")["sha256"], attempts=[], stopped=False, network_http_attempts=0))
        Path("successors").mkdir()
        write_json(Path("successors/report.json"), dict(plan=pin(collector.PLAN), attempts=[], probes=[], completed=True, stop_reason=None))
        self.spec = dict(scope=pin("scope.json"), roster=pin("roster.csv"), inventory=pin("inventory.csv"),
            prior_evidence=pin("prior.json"), calendar=pin("calendar.json"), public_queue=pin("public_queue.json"),
            successor_queue=pin(collector.PLAN), performance_authorized=False, strict_evidence_approved=False,
            streams=self.streams, material_events=[], membership_not_before="2016-11-30", readiness_blockers=["fixture only"])
        self.freeze_spec()

    def freeze_spec(self):
        write_json(inputs.SPEC, self.spec)

    def event(self):
        return dict(id="fixture", root_id="ID-000", parent_id="ID-000", economic_date="2016-01-05",
            kind="stock_merger", cash_per_parent="0", share_legs=[dict(instrument_id="ID-000", shares_per_parent="1/3")],
            execution_ready=False, prior_close_entitlement_verified=False, actual_delivery_at=None, fractional_cash_fixing=None)

    def guard(self):
        validate_streams(self.spec, self.roster)


class InputTests(InputFixture):
    def test_valid_build_preserves_100_members_and_actual_prices_without_promoting_flags(self):
        result = inputs.build(Path("prepared"))
        manifest = json.loads(Path("prepared/input_manifest.json").read_text())
        self.assertEqual(result["selected_originals"], 100)
        self.assertEqual(result["original_streams_with_complete_candidate_intervals"], 100)
        self.assertEqual(sum(s["rows"] for s in manifest["streams"]), 200)
        self.assertFalse(result["performance_ready"])
        self.assertEqual(manifest["max_total_research_exposure_selected"], .70)
        self.credentials.assert_not_called()

    def test_missing_candle_is_reported_without_filling(self):
        path = Path(self.rows[0]["observation_csv"])
        path.write_text("\n".join(path.read_text().splitlines()[:2])+"\n", encoding="utf-8")
        self.rows[0]["observation_sha256"] = pin(path)["sha256"]
        write_csv(Path("inventory.csv"), self.rows)
        write_json(Path("prior.json"), dict(qualification_csv=pin("inventory.csv")))
        self.spec.update(inventory=pin("inventory.csv"), prior_evidence=pin("prior.json"))
        self.freeze_spec()
        result = inputs.build(Path("prepared"))
        self.assertEqual(result["original_streams_with_complete_candidate_intervals"], 99)
        self.assertEqual(result["original_streams_with_gaps"][0]["missing"], ["2016-01-05"])

    def test_missing_member_duplicate_ids_or_wrong_root_rejected(self):
        baseline = deepcopy(self.spec)
        for mutate in (lambda: self.spec["streams"].pop(),
                       lambda: self.spec["streams"][1].update(instrument_id="ID-000"),
                       lambda: self.spec["streams"][0].update(root_id="ID-001"),
                       lambda: self.spec["streams"][0].update(snapshot_alias="OTHER")):
            self.spec = deepcopy(baseline)
            mutate()
            with self.assertRaises(ValueError):
                self.guard()

    def test_parts_reject_gaps_overlaps_reordering_and_holdout_dates(self):
        original = deepcopy(self.spec["streams"][0]["parts"][0])
        for start, end in (("2016-01-05", "2016-01-06"), ("2016-01-03", "2016-01-06"),
                           ("2024-01-01", "2025-01-01")):
            self.spec["streams"][0]["parts"] = [dict(original, end_exclusive="2016-01-04"), dict(original, start=start, end_exclusive=end)]
            with self.assertRaises(ValueError):
                self.guard()

    def test_contiguous_alias_parts_are_accepted(self):
        part = self.spec["streams"][0]["parts"][0]
        self.spec["streams"][0]["parts"] = [dict(part, end_exclusive="2016-01-05"), dict(part, start="2016-01-05")]
        self.guard()

    def test_bad_event_ratios_cash_dates_ids_and_promotions_rejected(self):
        changes = [dict(cash_per_parent=v) for v in ("-1", "NaN", "Infinity")]
        changes += [dict(parent_id="OTHER"), dict(root_id="ID-001"), dict(economic_date="2024-01-01"),
                    dict(execution_ready=True), dict(prior_close_entitlement_verified=True),
                    dict(actual_delivery_at="2016-01-05"), dict(fractional_cash_fixing="1")]
        changes += [dict(share_legs=[dict(instrument_id=i, shares_per_parent=r)])
                    for i, r in (("ID-000", "0"), ("ID-000", "-1"), ("ID-000", "NaN"), ("OTHER", "1"), ("ID-001", "1"))]
        for change in changes:
            with self.subTest(change=change):
                self.spec["material_events"] = [dict(self.event(), **change)]
                with self.assertRaises((ValueError, ZeroDivisionError)):
                    self.guard()

    def test_duplicate_material_event_rejected(self):
        self.spec["material_events"] = [self.event(), self.event()]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.guard()

    def test_valid_fractional_event_remains_unverified(self):
        self.spec["material_events"] = [self.event()]
        self.guard()
        self.assertFalse(self.spec["material_events"][0]["execution_ready"])

    def test_unknown_cash_remains_unknown_not_fabricated_zero(self):
        self.spec["material_events"] = [dict(self.event(), cash_per_parent=None)]
        self.guard()
        self.assertIsNone(self.spec["material_events"][0]["cash_per_parent"])

    def test_existing_outside_outputs_and_approval_promotions_rejected(self):
        Path("existing").mkdir()
        for output in (Path("existing"), Path.cwd().parent / "outside"):
            with self.assertRaises(ValueError):
                inputs.build(output)
        self.spec["performance_authorized"] = True
        self.freeze_spec()
        with self.assertRaises(ValueError):
            inputs.build(Path("prepared"))

    def test_changed_input_pin_rejected(self):
        Path("roster.csv").write_text("changed")
        with self.assertRaises(ValueError):
            inputs.build(Path("prepared"))

    def test_invalid_candles_rejected_by_builder(self):
        path = Path(self.rows[0]["observation_csv"])
        with path.open(encoding="utf-8", newline="") as handle:
            baseline = list(csv.DictReader(handle))
        for index, changes in enumerate((dict(high=90), dict(close=0), dict(volume=-1),
                                         dict(timestamp="invalid"), dict(timestamp="2016-01-09T05:00:00Z"))):
            bars = deepcopy(baseline)
            bars[0].update(changes)
            write_csv(path, bars)
            self.rows[0]["observation_sha256"] = pin(path)["sha256"]
            write_csv(Path("inventory.csv"), self.rows)
            write_json(Path("prior.json"), dict(qualification_csv=pin("inventory.csv")))
            self.spec.update(inventory=pin("inventory.csv"), prior_evidence=pin("prior.json"))
            self.freeze_spec()
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                inputs.build(Path(f"invalid{index}"))

    def test_duplicate_candles_are_not_silently_deduplicated(self):
        path = Path(self.rows[0]["observation_csv"])
        with path.open(encoding="utf-8", newline="") as handle:
            bars = list(csv.DictReader(handle))
        write_csv(path, bars + bars[:1])
        self.rows[0]["observation_sha256"] = pin(path)["sha256"]
        write_csv(Path("inventory.csv"), self.rows)
        write_json(Path("prior.json"), dict(qualification_csv=pin("inventory.csv")))
        self.spec.update(inventory=pin("inventory.csv"), prior_evidence=pin("prior.json"))
        self.freeze_spec()
        with self.assertRaises(ValueError):
            inputs.build(Path("duplicate"))

    def test_cumulative_ledger_number_clock_and_state_checks(self):
        valid = dict(attempts=[dict(number=1, elapsed_seconds=0, resource="bars", state="response_saved")],
                     probes=[], completed=True, stop_reason=None)
        validate_ledger(valid, LIMITS, require_completed=True)
        for change in (dict(number=2), dict(elapsed_seconds=-1), dict(elapsed_seconds=900),
                       dict(elapsed_seconds=float("nan")), dict(resource="account"), dict(state="started"),
                       dict(state="http_error", http_status=403)):
            report = deepcopy(valid)
            report["attempts"][0].update(change)
            with self.assertRaises(ValueError):
                validate_ledger(report, LIMITS, require_completed=True)

    def test_public_queue_cannot_hide_duplicate_requests_or_continue_after_denial(self):
        plan = dict(max_http_attempts=40, documents=[dict(id="a", url="https://fixture/a"), dict(id="b", url="https://fixture/b")])
        report = dict(network_http_attempts=1, stopped=True,
                      attempts=[dict(id="a", url="https://fixture/a", status="access_or_rate_barrier")])
        validate_public_report(report, plan)
        report["attempts"].append(dict(id="b", url="https://fixture/b", status="saved_unreviewed"))
        report["network_http_attempts"] = 2
        with self.assertRaises(ValueError):
            validate_public_report(report, plan)

        report["attempts"] = report["attempts"][:1]
        with self.assertRaises(ValueError):
            validate_public_report(report, plan)

    def test_unavailable_public_document_does_not_become_an_access_barrier(self):
        plan = dict(max_http_attempts=40, documents=[dict(id="a", url="https://fixture/a"), dict(id="b", url="https://fixture/b")])
        report = dict(network_http_attempts=2, stopped=False, attempts=[
            dict(id="a", url="https://fixture/a", status="unavailable_no_retry"),
            dict(id="b", url="https://fixture/b", status="saved_unreviewed")])
        validate_public_report(report, plan)


class EventReviewTests(TestCase):
    def setUp(self):
        self.rows = [dict(instrument_id="ROOT", event_id="provider", category="forward_splits", day="2018-03-01")]
        self.providers = [dict(self.rows[0], root_id="ROOT", record=json.dumps(dict(new_rate="5", old_rate="4")))]
        self.decisions = [dict(self.rows[0], status="genuine_fractional_stock_split", primary_source_id="source",
            primary_interpretation_supported=True, observed_new_shares_per_old="5/4", remaining="Fraction policy unknown")]
        self.sources = [dict(id="source", url="https://issuer.example/event", access="primary_browser_text_reviewed", facts=dict(new_shares_per_old="5/4"))]

    def review(self):
        return review_rows(self.rows, self.decisions, [], self.providers, self.sources)

    def test_economic_support_does_not_promote_execution_or_delivery(self):
        result = self.review()[0]
        self.assertTrue(result["economic_interpretation_primary_supported"])
        self.assertFalse(result["execution_ready"])
        self.assertFalse(result["known_at_verified"])
        self.assertIsNone(result["actual_delivery_at"])

    def test_search_only_cannot_be_promoted_to_direct_source_support(self):
        self.sources[0]["access"] = "search_only_direct_open_timeout_no_retry"
        with self.assertRaisesRegex(ValueError, "Search-only"):
            self.review()

    def test_changed_provider_or_primary_ratio_rejected(self):
        for target in (self.decisions[0], self.sources[0]["facts"]):
            field = "observed_new_shares_per_old" if target is self.decisions[0] else "new_shares_per_old"
            target[field] = "4"
            with self.assertRaises(ValueError):
                self.review()
            target[field] = "5/4"

    def test_missing_or_duplicate_decision_rejected(self):
        original = deepcopy(self.decisions)
        for decisions in ([], original * 2):
            self.decisions = decisions
            with self.assertRaises(ValueError):
                self.review()

    def test_unrelated_material_reference_rejected(self):
        self.decisions[0]["related_material_events"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "unrelated"):
            self.review()

    def test_changed_date_and_invented_receipt_rejected(self):
        for change in (dict(day="2019-01-01"), dict(execution_ready=True), dict(actual_delivery_at="2018-03-01")):
            self.decisions[0] = dict(self.decisions[0], **change)
            with self.assertRaises(ValueError):
                self.review()
            self.setUp()
class ActionRoleTests(TestCase):
    def test_acquirer_context_never_credits_buyer_holders(self):
        record = dict(acquiree_symbol="OLD", acquirer_symbol="BUY")
        self.assertEqual(inputs.classify_action("cash_mergers", record, "BUY"), "acquirer_context_only_no_holder_credit")
        self.assertEqual(inputs.classify_action("cash_mergers", record, "OLD"), "holder_outcome_candidate_requires_terms")
        self.assertEqual(inputs.classify_action("cash_mergers", record, "OTHER"), "other_security_unattached")

    def test_same_symbol_reorganization_is_not_automatic_merger(self):
        self.assertEqual(inputs.classify_action("stock_mergers", dict(acquiree_symbol="PEAK", acquirer_symbol="PEAK"), "PEAK"), "same_symbol_reorganization_requires_review")

    def test_split_ratios_are_exact_and_fractional_factors_need_review(self):
        for new, old, role in ((4, 1, "provider_split_candidate_not_primary_verified"),
                              (5, 4, "nonstandard_ratio_requires_primary_economic_review"),
                              (1, 3, "nonstandard_ratio_requires_primary_economic_review")):
            self.assertEqual(inputs.classify_action("forward_splits", dict(symbol="X", new_rate=new, old_rate=old), "X"), role)
        for new, old in ((0, 1), (1, 0), (-1, 1), ("NaN", 1)):
            with self.assertRaises((ValueError, ZeroDivisionError)):
                inputs.classify_action("forward_splits", dict(symbol="X", new_rate=new, old_rate=old), "X")

    def test_parent_and_alias_roles_are_explicit(self):
        cases = [("spin_offs", dict(source_symbol="X"), "parent_distribution_requires_ownership"),
                 ("name_changes", dict(old_symbol="X", new_symbol="Y"), "outgoing_alias_requires_identity_review"),
                 ("cash_dividends", dict(symbol="X"), "cash_dividend_candidate_unspendable_without_payable_terms"),
                 ("unknown", {}, "unsupported_category_requires_review")]
        for category, record, expected in cases:
            self.assertEqual(inputs.classify_action(category, record, "X"), expected)

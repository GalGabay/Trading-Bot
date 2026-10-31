"""Repeat-controller checks with synthetic sessions and no real credentials/I/O.

Network is denied; fake collection responses exercise real persistence and the
existing observer. Local subprocesses exercise the host's actual file lock.
"""

from contextlib import closing, redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import asdict, replace
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import pandas as pd

from app.shadow import repeat as R
from app.shadow.config import ROOT, ShadowConfig, canonical, digest, utc
from app.shadow.data import ShadowDataError
from app.shadow.observer import observe
from app.shadow.repeat_state import RepeatError, controller_lock, read_state, save_state
from app.shadow.store import ObservationStore
from tests.test_shadow_observer import fixture


class RepeatTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed_bundle = fixture()
        cls.config = ShadowConfig(("AAA", "BBB"))
        cls.seed_report = observe(cls.seed_bundle, cls.config)

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / "repeat"
        self.seed_path = self.root / "seed.json"
        self.seed_path.write_text(canonical(self.seed_bundle), encoding="utf-8")
        self.seed_db = self.root / "seed.sqlite3"
        ObservationStore(self.seed_db).record(self.seed_report)
        self.repeat_config = R.RepeatConfig()
        for target in ("socket.create_connection", "socket.socket.connect", "socket.socket.connect_ex",
                "app.broker.alpaca_client._AlpacaCredentials.load", "app.broker.alpaca_client.TradingClient"):
            guard = patch(target, side_effect=AssertionError("Forbidden network/credentials/trading construction"))
            guard.start()
            self.addCleanup(guard.stop)
        timer = patch.object(R, "clock", return_value=utc("2026-10-23T20:30:00Z"))
        self.clock = timer.start()
        self.addCleanup(timer.stop)
        R.initialize(self.directory, self.config, self.repeat_config, self.seed_path, self.seed_db)

    def state(self):
        return read_state(self.directory)

    def change(self, **fields):
        state = self.state()
        state.update(fields)
        save_state(self.directory, state)
        return state

    def plan(self, when, **fields):
        state = self.state()
        state.update(fields)
        # Most scheduling cases isolate session logic from the daily refresh.
        state["calendar_checked_at"] = when
        return R.plan(state, self.config, utc(when))

    def due(self):
        self.clock.return_value = utc("2026-10-26T20:30:00Z")
        self.change(calendar_checked_at=self.clock.return_value.isoformat())

    def next_bundle(self):
        bundle = deepcopy(self.seed_bundle)
        bundle["observed_at"] = "2026-10-26T20:30:00Z"
        bundle["requests"] = 7
        for rows in bundle["bars"].values():
            rows.append(dict(t="2026-10-26T04:00:00Z", o=123, h=126, l=122, c=125, v=10000))
        return bundle

    def client(self, bundle=None, error=None):
        def collect(config):
            # The reservation must already be durable before transport use.
            state = self.state()
            self.assertEqual(state["status"], "running")
            self.assertEqual(state["pending"]["reserved_requests"], 110)
            client.request_count = 7
            if error:
                raise error
            return deepcopy(bundle if bundle is not None else self.next_bundle())
        client = SimpleNamespace(request_count=0, collect=collect)
        return client

    def tick(self, client=None):
        with patch.object(R, "client_for", return_value=client or self.client()) as factory:
            state = R.tick(self.directory, self.config, self.repeat_config)
        return state, factory

    def cli(self, *arguments):
        config_path = self.root / "config.json"
        config_path.write_text(canonical(self.config.record()), encoding="utf-8")
        repeat_path = self.root / "repeat_config.json"
        repeat_path.write_text(canonical(asdict(self.repeat_config)), encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["repeat", *arguments, "--directory", str(self.directory),
                "--config", str(config_path), "--repeat-config", str(repeat_path)]), redirect_stdout(out), redirect_stderr(err):
            result = R.main()
        return result, out.getvalue(), err.getvalue()

    def test_initialize_adopts_seed_without_requests_or_seed_db_changes(self):
        state = self.state()
        self.assertEqual(state["last_session"], "2026-10-23")
        self.assertEqual((state["collection_attempts"], state["calendar_attempts"], state["reserved_requests"]), (0, 0, 0))
        self.assertFalse((self.directory / "observations.sqlite3").exists())
        self.assertEqual(canonical(ObservationStore(self.seed_db).latest()), canonical(self.seed_report))

    def test_init_cannot_reset_existing_campaign(self):
        before = (self.directory / "campaign.json").read_bytes()
        with self.assertRaisesRegex(RepeatError, "already exists"):
            R.initialize(self.directory, self.config, self.repeat_config, self.seed_path, self.seed_db)
        self.assertEqual((self.directory / "campaign.json").read_bytes(), before)

    def test_init_rejects_mismatched_bundle(self):
        self.seed_path.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(RepeatError, "Seed must match"):
            R.initialize(self.root / "new", self.config, self.repeat_config, self.seed_path, self.seed_db)

    def test_init_rejects_changed_config_or_environment(self):
        for config in (replace(self.config, target_exposure=.6), self.config):
            with self.subTest(config=config.target_exposure), patch.object(R, "policy", wraps=R.policy) as current:
                if config == self.config:
                    changed = R.policy(config, self.repeat_config)
                    changed["environment"]["python"] = "different"
                    current.return_value, current.side_effect = changed, None
                with self.assertRaises(RepeatError):
                    R.initialize(self.root / "new", config, self.repeat_config, self.seed_path, self.seed_db)

    def test_init_rejects_future_seed(self):
        self.clock.return_value = utc("2026-10-22T20:30:00Z")
        with self.assertRaisesRegex(RepeatError, "future"):
            R.initialize(self.root / "new", self.config, self.repeat_config, self.seed_path, self.seed_db)

    def test_configuration_rejects_boolean_float_negative_and_excessive_values(self):
        for field in asdict(self.repeat_config):
            for value in (True, 1.5, -1, 99999):
                with self.subTest(field=field, value=value), self.assertRaises(RepeatError):
                    R.RepeatConfig(**dict(asdict(self.repeat_config), **{field:value}))

    def test_repeat_json_rejects_extra_missing_and_duplicate_fields(self):
        path = self.root / "bad.json"
        for raw in ({}, dict(asdict(self.repeat_config), enable_orders=True)):
            path.write_text(canonical(raw), encoding="utf-8")
            with self.assertRaises(RepeatError): R.load_repeat_config(path)
        path.write_text('{"campaign_days":1,"campaign_days":2}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate"): R.load_repeat_config(path)

    def test_same_session_waits_without_constructing_transport(self):
        _, factory = self.tick()
        factory.assert_not_called()
        self.assertEqual(self.plan("2026-10-23T21:00:00Z")["action"], "waiting")

    def test_weekend_waits_without_full_collection(self):
        self.assertEqual(self.plan("2026-10-24T12:00:00Z")["action"], "waiting")

    def test_explicit_holiday_is_not_a_missing_session(self):
        state = self.state()
        state["last_session"] = "2026-07-02"
        state["expires_at"] = "2026-12-01T00:00:00Z"
        state["calendar_checked_at"] = "2026-07-03T12:00:00Z"
        self.assertEqual(R.plan(state, self.config, utc(state["calendar_checked_at"]))["action"], "waiting")

    def test_close_settling_buffer_and_exact_boundary(self):
        self.assertEqual(self.plan("2026-10-26T20:14:59Z")["action"], "waiting")
        action = self.plan("2026-10-26T20:15:00Z")
        self.assertEqual((action["action"], action["session"]), ("collect", "2026-10-26"))

    def test_calendar_early_close_uses_its_actual_time(self):
        state = self.state()
        next(r for r in state["calendar"] if r["date"] == "2026-10-26")["close"] = "13:00"
        self.change(calendar=state["calendar"])
        self.assertEqual(self.plan("2026-10-26T17:14:59Z")["action"], "waiting")
        self.assertEqual(self.plan("2026-10-26T17:15:00Z")["action"], "collect")

    def test_us_dst_change_moves_close_to_2100_utc(self):
        self.change(last_session="2026-10-30")
        self.assertEqual(self.plan("2026-11-02T20:15:00Z")["action"], "waiting")
        self.assertEqual(self.plan("2026-11-02T21:15:00Z")["action"], "collect")

    def test_next_midnight_uses_new_york_dst(self):
        self.change(last_session="2026-10-30")
        action = self.plan("2026-11-01T05:30:00Z")
        self.assertEqual(action["next_at"], "2026-11-02T05:00:00+00:00")

    def test_calendar_refreshed_once_per_new_york_date(self):
        self.clock.return_value = utc("2026-10-24T12:00:00Z")
        self.assertEqual(R.plan(self.state(), self.config, R.clock())["action"], "refresh_calendar")
        self.assertEqual(self.plan("2026-10-24T12:00:00Z")["action"], "waiting")

    def test_same_utc_date_can_still_be_previous_new_york_day(self):
        self.assertEqual(R.plan(self.state(), self.config, utc("2026-10-24T02:00:00Z"))["action"], "waiting")

    def test_expired_signal_waits_instead_of_collecting_old_session(self):
        action = self.plan("2026-10-27T13:30:00Z")
        self.assertEqual((action["action"], action["expired_session"]), ("waiting", "2026-10-26"))

    def test_missed_sessions_are_listed_and_only_latest_is_due(self):
        action = self.plan("2026-10-28T20:30:00Z")
        self.assertEqual(action["session"], "2026-10-28")
        self.assertEqual(action["missed_sessions"], ["2026-10-26", "2026-10-27"])

    def test_missing_following_session_halts(self):
        self.change(calendar=[r for r in self.state()["calendar"] if r["date"] <= "2026-10-26"])
        self.assertEqual(self.plan("2026-10-26T20:30:00Z")["action"], "halted")

    def test_expired_campaign_makes_no_request(self):
        self.clock.return_value = utc(self.state()["expires_at"])
        state, factory = self.tick()
        factory.assert_not_called()
        self.assertEqual(state["status"], "finished")

    def test_paused_and_halted_campaigns_do_not_request(self):
        for mode in ("paused", "halted", "finished"):
            self.change(status=mode)
            _, factory = self.tick()
            factory.assert_not_called()

    def test_budget_reservation_is_durable_before_client_construction(self):
        self.due()
        def make(state):
            saved = self.state()
            self.assertEqual(saved["reserved_requests"], 110)
            self.assertEqual(saved["collection_attempts"], 1)
            self.assertEqual(saved["pending"]["target"], "2026-10-26")
            return self.client()
        with patch.object(R, "client_for", side_effect=make): R.tick(self.directory, self.config, self.repeat_config)
        self.assertEqual(self.state()["known_requests"], 7)

    def test_success_records_one_report_and_never_carries_positions(self):
        self.due()
        state, _ = self.tick()
        report = ObservationStore(self.directory / "observations.sqlite3").latest()
        self.assertEqual(state["last_session"], "2026-10-26")
        self.assertEqual(state["reserved_requests"], 110)
        self.assertEqual(report["reference"]["positions"], {})
        self.assertEqual(report["reference"]["cash"], 10000)
        self.assertEqual((report["orders_submitted"], report["simulated_fills"]), (0, 0))

    def test_second_tick_does_not_recollect_completed_session(self):
        self.due()
        self.tick()
        _, factory = self.tick()
        factory.assert_not_called()
        with closing(sqlite3.connect(self.directory / "observations.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM shadow_observations").fetchone()[0], 1)

    def test_request_budget_must_cover_whole_reservation(self):
        self.due()
        self.change(reserved_requests=2391)
        state, factory = self.tick()
        factory.assert_not_called()
        self.assertEqual(state["status"], "finished")
        self.assertEqual(state["collection_attempts"], 0)

    def test_exact_request_budget_is_allowed_and_never_refunded(self):
        self.due()
        self.change(reserved_requests=2390)
        state, _ = self.tick()
        self.assertEqual(state["reserved_requests"], 2500)

    def test_collection_attempt_cap_stops_before_client(self):
        self.due()
        self.change(collection_attempts=22)
        state, factory = self.tick()
        factory.assert_not_called()
        self.assertEqual(state["status"], "finished")

    def test_calendar_attempt_cap_stops_before_client(self):
        self.clock.return_value = utc("2026-10-24T12:00:00Z")
        self.change(calendar_attempts=35)
        state, factory = self.tick()
        factory.assert_not_called()
        self.assertEqual(state["status"], "finished")

    def test_calendar_refresh_costs_one_and_does_not_collect_weekend(self):
        self.clock.return_value = utc("2026-10-24T12:00:00Z")
        client = SimpleNamespace(request_count=0)
        def get(path, params):
            self.assertEqual(path, "/v2/calendar")
            self.assertEqual(params["start"], "2026-01-01")
            self.assertEqual(self.state()["reserved_requests"], 1)
            client.request_count = 1
            return deepcopy(self.seed_bundle["calendar"])
        client._get = get
        state, factory = self.tick(client)
        self.assertEqual((state["calendar_attempts"], state["known_requests"], state["collection_attempts"]), (1, 1, 0))
        self.assertEqual(factory.call_count, 1)
        _, factory = self.tick(client)
        factory.assert_not_called()

    def test_refresh_then_due_collection_is_bounded_to_two_operations(self):
        self.clock.return_value = utc("2026-10-26T20:30:00Z")
        calendar = SimpleNamespace(request_count=1, _get=lambda *a:deepcopy(self.seed_bundle["calendar"]))
        with patch.object(R, "client_for", side_effect=[calendar, self.client()]) as factory:
            R.tick(self.directory, self.config, self.repeat_config)
        self.assertEqual(factory.call_count, 2)
        self.assertEqual((self.state()["reserved_requests"], self.state()["known_requests"]), (111, 8))

    def test_invalid_calendar_halts_without_stock_collection(self):
        self.clock.return_value = utc("2026-10-24T12:00:00Z")
        state, factory = self.tick(SimpleNamespace(request_count=1, _get=lambda *a:[]))
        self.assertEqual((state["status"], state["reserved_requests"]), ("halted", 1))
        self.assertEqual(factory.call_count, 1)

    def test_collection_failure_halts_and_does_not_retry_next_tick(self):
        self.due()
        state, _ = self.tick(self.client(error=ShadowDataError("HTTP 403; no upgrade")))
        self.assertEqual((state["status"], state["reserved_requests"]), ("halted", 110))
        self.assertIn("403", state["reason"])
        _, factory = self.tick()
        factory.assert_not_called()

    def test_exception_secret_is_not_saved(self):
        self.due()
        self.tick(self.client(error=OSError("SECRET_SENTINEL")))
        self.assertNotIn("SECRET_SENTINEL", (self.directory / "campaign.json").read_text())

    def test_credential_failure_keeps_reservation_and_unknown_count(self):
        self.due()
        with patch.object(R, "client_for", side_effect=ValueError("SECRET_SENTINEL")):
            state = R.tick(self.directory, self.config, self.repeat_config)
        self.assertEqual((state["status"], state["reserved_requests"]), ("halted", 110))
        self.assertIsNone(state["pending"]["known_requests"])

    def test_interrupt_during_collection_halts_durably(self):
        self.due()
        state, _ = self.tick(self.client(error=KeyboardInterrupt()))
        self.assertEqual(state["status"], "halted")
        self.assertEqual(state["pending"]["known_requests"], 7)

    def test_interrupted_reservation_halts_until_explicit_resume(self):
        self.due()
        R.reserve(self.directory, self.state(), self.repeat_config, "collect", "2026-10-26")
        state, factory = self.tick()
        factory.assert_not_called()
        self.assertIn("unknown", state["reason"])
        R.change_status(self.directory, self.config, self.repeat_config, "resume")
        self.assertEqual(self.state()["reserved_requests"], 110)
        self.tick()
        self.assertEqual((self.state()["collection_attempts"], self.state()["reserved_requests"]), (2, 220))

    def test_known_failed_requests_are_counted_once_after_resume(self):
        self.due()
        self.tick(self.client(error=ShadowDataError("failed")))
        self.assertEqual(R.status(self.directory, self.config, self.repeat_config)["known_requests"], 7)
        R.change_status(self.directory, self.config, self.repeat_config, "resume")
        self.assertEqual(R.status(self.directory, self.config, self.repeat_config)["known_requests"], 7)

    def save_pending_bundle(self):
        self.due()
        state = self.state()
        R.reserve(self.directory, state, self.repeat_config, "collect", "2026-10-26")
        path = self.root / "collected.json"
        path.write_text(canonical(self.next_bundle()), encoding="utf-8")
        state["pending"].update(bundle=R.pin(path), known_requests=7, phase="bundle_saved")
        save_state(self.directory, state)
        return state

    def test_saved_bundle_recovery_makes_no_request(self):
        self.save_pending_bundle()
        state, factory = self.tick()
        factory.assert_not_called()
        self.assertEqual((state["last_session"], state["known_requests"]), ("2026-10-26", 7))

    def test_crash_after_journal_commit_recovers_idempotently(self):
        self.save_pending_bundle()
        with patch.object(R, "complete_pending", side_effect=SystemExit("simulated process termination")):
            with self.assertRaises(SystemExit): R.tick(self.directory, self.config, self.repeat_config)
        self.assertEqual(self.state()["status"], "running")
        self.tick()
        with closing(sqlite3.connect(self.directory / "observations.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM shadow_observations").fetchone()[0], 1)
        self.assertEqual(self.state()["known_requests"], 7)

    def test_recovery_of_corrupted_bundle_halts_without_requests(self):
        state = self.save_pending_bundle()
        Path(state["pending"]["bundle"]["path"]).write_text("{}", encoding="utf-8")
        state, factory = self.tick()
        factory.assert_not_called()
        self.assertEqual(state["status"], "halted")
        self.assertEqual(state["last_session"], "2026-10-23")

    def test_wrong_collected_session_halts_and_preserves_bundle(self):
        self.due()
        state, _ = self.tick(self.client(bundle=self.seed_bundle))
        self.assertEqual(state["status"], "halted")
        self.assertIn("differs", state["reason"])
        self.assertTrue(Path(state["pending"]["bundle"]["path"]).exists())

    def test_data_blockers_are_recorded_once_and_visible_in_status(self):
        self.due()
        bundle = self.next_bundle()
        bundle["bars"]["AAA"][-1]["c"] = -1
        state, _ = self.tick(self.client(bundle=bundle))
        self.assertEqual(state["status"], "ready")
        value = R.status(self.directory, self.config, self.repeat_config)
        self.assertEqual(value["latest_unavailable_symbols"], ["AAA"])
        _, factory = self.tick()
        factory.assert_not_called()

    def test_pause_resume_retains_budgets_and_dates(self):
        original = self.change(reserved_requests=100, collection_attempts=1)
        R.change_status(self.directory, self.config, self.repeat_config, "pause")
        R.change_status(self.directory, self.config, self.repeat_config, "resume")
        self.assertEqual((self.state()["reserved_requests"], self.state()["expires_at"]), (100, original["expires_at"]))

    def test_resume_cannot_reset_finished_or_expired_campaign(self):
        self.change(status="finished")
        with self.assertRaises(RepeatError): R.change_status(self.directory, self.config, self.repeat_config, "resume")
        self.change(status="halted")
        self.clock.return_value = utc(self.state()["expires_at"])
        with self.assertRaises(RepeatError): R.change_status(self.directory, self.config, self.repeat_config, "resume")

    def test_resume_with_saved_bundle_only_schedules_offline_recovery(self):
        self.save_pending_bundle()
        self.change(status="halted")
        R.change_status(self.directory, self.config, self.repeat_config, "resume")
        self.assertEqual(self.state()["status"], "running")
        _, factory = self.tick()
        factory.assert_not_called()

    def test_running_attempt_must_be_reconciled_before_resume(self):
        self.save_pending_bundle()
        with self.assertRaisesRegex(RepeatError, "tick first"):
            R.change_status(self.directory, self.config, self.repeat_config, "resume")

    def test_changed_config_policy_blocks_tick_without_request(self):
        with patch.object(R, "client_for") as factory, self.assertRaisesRegex(RepeatError, "changed"):
            R.tick(self.directory, replace(self.config, target_exposure=.6), self.repeat_config)
        factory.assert_not_called()

    def test_changed_source_or_environment_is_visible_in_status(self):
        state = self.state()
        state["policy"]["implementation"]["app/shadow/repeat.py"] = "old"
        save_state(self.directory, state)
        value = R.status(self.directory, self.config, self.repeat_config)
        self.assertFalse(value["policy_matches"])
        self.assertEqual(value["action"]["action"], "halted")

    def test_checksum_corruption_is_rejected_without_transport(self):
        path = self.directory / "campaign.json"
        raw = json.loads(path.read_text())
        raw["payload"]["reserved_requests"] = 0
        raw["sha256"] = "bad"
        path.write_text(canonical(raw), encoding="utf-8")
        with patch.object(R, "client_for") as factory, self.assertRaisesRegex(RepeatError, "checksum"):
            R.tick(self.directory, self.config, self.repeat_config)
        factory.assert_not_called()

    def test_failed_atomic_replace_retains_previous_state(self):
        path = self.directory / "campaign.json"
        before = path.read_bytes()
        state = self.state()
        state["reserved_requests"] = 110
        with patch("app.shadow.repeat_state.os.replace", side_effect=OSError("disk full")), self.assertRaises(OSError):
            save_state(self.directory, state)
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse(list(self.directory.glob(".campaign-*.tmp")))

    def test_failed_reservation_write_prevents_transport(self):
        self.due()
        with patch.object(R, "save_state", side_effect=OSError("disk full")), patch.object(R, "client_for") as factory:
            with self.assertRaises(OSError): R.tick(self.directory, self.config, self.repeat_config)
        factory.assert_not_called()

    def test_lock_refuses_overlapping_process_and_releases_afterward(self):
        script = ("import sys\nfrom app.shadow.repeat_state import controller_lock, RepeatError\n"
            "try:\n with controller_lock(sys.argv[1]): pass\n"
            "except RepeatError: sys.exit(17)\n")
        with controller_lock(self.directory):
            child = subprocess.run([sys.executable, "-c", script, str(self.directory)], cwd=ROOT,
                capture_output=True, text=True, timeout=10)
            self.assertEqual(child.returncode, 17, child.stderr)
        child = subprocess.run([sys.executable, "-c", script, str(self.directory)], cwd=ROOT,
            capture_output=True, text=True, timeout=10)
        self.assertEqual(child.returncode, 0, child.stderr)

    def test_lock_releases_after_abrupt_process_death(self):
        script = ("import sys\nfrom app.shadow.repeat_state import controller_lock\n"
            "with controller_lock(sys.argv[1]):\n print('locked',flush=True)\n sys.stdin.read()\n")
        child = subprocess.Popen([sys.executable, "-c", script, str(self.directory)], cwd=ROOT,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), "locked")
            child.kill()
            child.wait(timeout=10)
            with controller_lock(self.directory): pass
        finally:
            if child.poll() is None: child.kill()
            child.communicate(timeout=10)

    def test_status_and_latest_cli_are_offline_and_leave_state_unchanged(self):
        before = (self.directory / "campaign.json").read_bytes()
        result, output, _ = self.cli("status", "--json")
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output)["last_session"], "2026-10-23")
        _, output, _ = self.cli("latest")
        self.assertIn("No orders", output)
        self.assertEqual((self.directory / "campaign.json").read_bytes(), before)

    def test_tick_cli_waits_without_transport(self):
        with patch.object(R, "client_for") as factory:
            result, output, _ = self.cli("tick", "--json")
        factory.assert_not_called()
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output)["action"]["action"], "waiting")

    def test_tick_cli_returns_failure_for_halted_campaign(self):
        self.change(status="halted", reason="review needed")
        result, output, _ = self.cli("tick")
        self.assertEqual(result, 2)
        self.assertIn("review needed", output)

    def test_signal_expiry_is_visible_without_a_new_collection(self):
        self.clock.return_value = utc("2026-10-26T13:30:00Z")
        self.assertTrue(R.status(self.directory, self.config, self.repeat_config)["signals_expired"])

    def test_foreground_duration_validation_rejects_nan_and_infinite(self):
        for value in ("0", "25", "nan", "inf"):
            with self.subTest(value=value), self.assertRaises(SystemExit) as stopped:
                self.cli("run", "--hours", value)
            self.assertEqual(stopped.exception.code, 2)

    def test_run_exits_after_its_foreground_budget(self):
        with patch.object(R.time, "monotonic", side_effect=[0, 2]), patch.object(R.time, "sleep") as sleep:
            result, _, _ = self.cli("run", "--hours", "0.0001")
        self.assertEqual(result, 0)
        sleep.assert_not_called()

    def test_keyboard_interrupt_in_wait_exits_without_background_work(self):
        with patch.object(R.time, "monotonic", return_value=0), patch.object(R.time, "sleep", side_effect=KeyboardInterrupt()):
            result, _, err = self.cli("run")
        self.assertEqual(result, 130)
        self.assertIn("no background", err)
        self.assertEqual(self.state()["status"], "ready")

    def test_transport_campaign_deadline_and_reservation_block_before_get(self):
        state = self.state()
        state["pending"] = dict(reserved_requests=1)
        with patch("app.broker.alpaca_client._AlpacaCredentials.load", return_value=SimpleNamespace(api_key="fake",secret_key="fake")):
            client = R.client_for(state)
        with patch("app.shadow.data.ShadowDataClient._get") as get:
            client.request_count = 1
            with self.assertRaises(ShadowDataError): client._get("/v2/calendar")
            client.request_count = 0
            self.clock.return_value = utc(state["expires_at"])
            with self.assertRaises(ShadowDataError): client._get("/v2/calendar")
            get.assert_not_called()

    def test_unrecognized_read_endpoint_stays_blocked(self):
        state = self.state()
        state["pending"] = dict(reserved_requests=1)
        with patch("app.broker.alpaca_client._AlpacaCredentials.load", return_value=SimpleNamespace(api_key="fake",secret_key="fake")):
            client = R.client_for(state)
        for path in ("/v2/orders", "/v2/positions", "/v2/account", "/billing"):
            with self.subTest(path=path), self.assertRaises(ValueError): client._get(path)
        self.assertEqual(client.request_count, 0)

    def test_failure_after_journal_commit_can_resume_without_recollection(self):
        self.due()
        original = ObservationStore.record
        def committed_then_error(store, report):
            original(store, report)
            raise OSError("filesystem interruption after journal commit")
        with patch.object(ObservationStore, "record", committed_then_error):
            state, _ = self.tick()
        self.assertEqual(state["status"], "halted")
        R.change_status(self.directory, self.config, self.repeat_config, "resume")
        state, factory = self.tick()
        factory.assert_not_called()
        self.assertEqual(state["known_requests"], 7)
        with closing(sqlite3.connect(self.directory / "observations.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM shadow_observations").fetchone()[0], 1)

    def test_market_context_blocker_is_visible_and_not_retried(self):
        self.due()
        bundle = self.next_bundle()
        bundle["bars"]["SPY"] = []
        self.tick(self.client(bundle=bundle))
        value = R.status(self.directory, self.config, self.repeat_config)
        self.assertIn("market_context_unavailable", value["latest_global_blockers"])
        _, factory = self.tick()
        factory.assert_not_called()

    def test_unknown_request_count_survives_resume_in_event_history(self):
        self.due()
        R.reserve(self.directory, self.state(), self.repeat_config, "collect", "2026-10-26")
        self.tick()
        self.assertEqual(R.status(self.directory, self.config, self.repeat_config)["unknown_request_attempts"], 1)
        R.change_status(self.directory, self.config, self.repeat_config, "resume")
        value = R.status(self.directory, self.config, self.repeat_config)
        self.assertEqual(value["unknown_request_attempts"], 1)
        self.assertEqual(value["reserved_requests"], 110)

    def test_missing_or_truncated_state_cannot_construct_transport(self):
        path = self.directory / "campaign.json"
        for content in ("", '{"payload":'):
            path.write_text(content, encoding="utf-8")
            with patch.object(R, "client_for") as factory, self.assertRaises(ValueError):
                R.tick(self.directory, self.config, self.repeat_config)
            factory.assert_not_called()
        path.unlink()
        with patch.object(R, "client_for") as factory, self.assertRaises(FileNotFoundError):
            R.tick(self.directory, self.config, self.repeat_config)
        factory.assert_not_called()

    def test_read_only_status_does_not_change_a_halted_attempt(self):
        self.due()
        self.tick(self.client(error=ShadowDataError("HTTP 429; no retry")))
        before = (self.directory / "campaign.json").read_bytes()
        result, output, _ = self.cli("status", "--json")
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output)["state"], "halted")
        self.assertEqual((self.directory / "campaign.json").read_bytes(), before)

    def test_repeat_config_change_is_versioned_and_cannot_raise_existing_budget(self):
        changed = replace(self.repeat_config, max_collection_attempts=23)
        with patch.object(R, "client_for") as factory, self.assertRaisesRegex(RepeatError, "changed"):
            R.tick(self.directory, self.config, changed)
        factory.assert_not_called()

    def test_init_rejects_a_seed_with_reference_holdings(self):
        report = deepcopy(self.seed_report)
        report["reference"]["positions"] = {"AAA":dict(quantity=1)}
        db = self.root / "held.sqlite3"
        ObservationStore(db).record(report)
        with self.assertRaisesRegex(RepeatError, "flat"):
            R.initialize(self.root / "new", self.config, self.repeat_config, self.seed_path, db)

    def test_transient_calendar_error_halts_without_followup_collection(self):
        self.clock.return_value = utc("2026-10-26T20:30:00Z")
        def fail(*args): raise ShadowDataError("HTTP 403; no upgrade")
        state, factory = self.tick(SimpleNamespace(request_count=1, _get=fail))
        self.assertEqual((state["status"], state["collection_attempts"]), ("halted", 0))
        self.assertEqual(factory.call_count, 1)

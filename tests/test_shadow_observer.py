"""Synthetic/offline observer checks. No real credentials or network requests."""

from copy import deepcopy
from contextlib import closing, redirect_stdout
from dataclasses import replace
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd

from app.shadow.config import ShadowConfig, canonical, digest, load_config, read_json, utc
from app.shadow.data import ShadowDataClient, ShadowDataError, _NoRedirects
from app.shadow.observer import daily_stamp, main, markdown, observe, sessions_from
from app.shadow.store import ObservationStore, write_once


def fixture(names=("AAA", "BBB")):
    """Artificial candles; explicit fixture calendar with holidays omitted."""
    excluded = {"2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07"}
    dates = [str(d.date()) for d in pd.bdate_range("2026-01-02", "2026-11-06") if str(d.date()) not in excluded]
    calendar = [dict(date=d, open="09:30", close="16:00") for d in dates]
    used = [d for d in dates if d <= "2026-10-23"]
    bars = {}
    for name in (*names, "SPY"):
        rows = []
        for i, day in enumerate(used):
            close = 80 + i * .2 + .1 * np.sin(i)
            if i == len(used) - 1:
                close += 2
            stamp = pd.Timestamp(day).tz_localize("America/New_York").tz_convert("UTC")
            rows.append(dict(t=stamp.isoformat(), o=close - .05, h=close + .1, l=close - .1, c=close, v=10000))
        bars[name] = rows
    return dict(schema_version=1, observed_at="2026-10-23T20:30:00Z", history_start="2026-01-01",
        feed="iex", adjustment="split", timeframe="1Day", symbols=list(names), calendar=calendar,
        assets={name:dict(id="fixture-" + name, symbol=name, status="active", tradable=True, **{"class":"us_equity"}) for name in (*names, "SPY")},
        bars=bars, requests=0, provenance="SYNTHETIC UNIT FIXTURE ONLY")


def reference(bundle, **changes):
    result = dict(dict(as_of_session="2026-10-23", cash=10000, positions=[]), **changes)
    equity = result["cash"] + sum(p["quantity"] * bundle["bars"][p["symbol"]][-1]["c"] for p in result["positions"])
    result.setdefault("peak_equity", equity)
    result.setdefault("day_start_equity", equity)
    return result


class ObserverTests(TestCase):
    def setUp(self):
        self.bundle = fixture()
        self.config = ShadowConfig(("AAA", "BBB"))

    def run_observer(self, **kwargs):
        return observe(self.bundle, self.config, **kwargs)

    def test_valid_buy_preview_has_no_orders_fills_or_position_transitions(self):
        result = self.run_observer()
        self.assertEqual([r["signal"] for r in result["signals"]], ["BUY", "BUY"])
        self.assertTrue(all(r["preview_quantity"] > 0 for r in result["signals"]))
        self.assertEqual(result["orders_submitted"], 0)
        self.assertEqual(result["simulated_fills"], 0)
        self.assertEqual(result["reference"]["positions"], {})
        self.assertFalse(result["paper_risk_approved"])

    def test_same_inputs_are_deterministic_and_unmodified(self):
        before = deepcopy(self.bundle)
        one, two = self.run_observer(), self.run_observer()
        self.assertEqual(one, two)
        self.assertEqual(self.bundle, before)

    def test_saved_observation_does_not_load_credentials_or_construct_trading_client(self):
        with patch("app.broker.alpaca_client._AlpacaCredentials.load", side_effect=AssertionError("credential load")), patch("app.broker.alpaca_client.TradingClient", side_effect=AssertionError("trading client")):
            self.run_observer()

    def test_reference_cash_and_actual_exposure_do_not_change_between_observations(self):
        result = self.run_observer()
        self.assertEqual(result["reference"]["cash"], 10000)
        self.assertEqual(result["preview"]["current_stock_exposure"], 0)
        self.assertGreater(result["preview"]["planned_stock_exposure"], 0)
        self.assertEqual(self.run_observer()["reference"]["cash"], 10000)

    def test_individual_position_and_combined_target_caps(self):
        result = self.run_observer()
        for row in result["signals"]:
            self.assertLessEqual(row["preview_notional"], 500)
            self.assertLessEqual(row["preview_quantity"] * (row["estimated_entry"] - row["proposed_stop"]), 50 + 1e-9)
        self.assertLessEqual(result["preview"]["planned_stock_exposure"], .70)
        self.assertGreaterEqual(result["preview"]["reference_cash_after_planned_buys"], 0)

    def test_target_room_binds_before_eighty_five_percent_ceiling(self):
        self.config = replace(self.config, target_exposure=.07)
        result = self.run_observer()
        self.assertLessEqual(result["preview"]["planned_stock_exposure"], .07)
        self.assertIn("target_room", [r.get("binding_cap") for r in result["signals"]])

    def test_position_slots_limit_candidates_in_alphabetical_order(self):
        self.config = replace(self.config, max_positions=1)
        result = self.run_observer()
        self.assertGreater(result["signals"][0]["preview_quantity"], 0)
        self.assertIn("position_slots_full", result["signals"][1]["blockers"])

    def test_stop_risk_prevents_even_one_share(self):
        self.config = replace(self.config, planned_stop_risk=.000001)
        result = self.run_observer()
        self.assertTrue(all(r["preview_quantity"] == 0 for r in result["signals"]))
        self.assertIn("stop_risk_below_one_whole_share", result["signals"][0]["blockers"])

    def test_volatility_sizing_can_prevent_one_share(self):
        self.config = replace(self.config, volatility_contribution=.00000001)
        result = self.run_observer()
        self.assertIn("volatility_sizing_below_one_whole_share", result["signals"][0]["blockers"])

    def test_market_filter_off_produces_no_buy(self):
        row = self.bundle["bars"]["SPY"][-1]
        row.update(o=60, h=61, l=59, c=60)
        result = self.run_observer()
        self.assertFalse(result["market_filter_on"])
        self.assertEqual([r["signal"] for r in result["signals"]], ["HOLD", "HOLD"])

    def test_bad_spy_blocks_all_candidates(self):
        self.bundle["bars"]["SPY"].pop()
        result = self.run_observer()
        self.assertIn("market_context_unavailable", result["global_blockers"])
        self.assertTrue(all(r["signal"] == "UNAVAILABLE" for r in result["signals"]))

    def test_missing_stock_bar_stays_visible_without_filling_or_dropping_symbol(self):
        self.bundle["bars"]["AAA"].pop(30)
        result = self.run_observer()
        self.assertEqual(len(result["signals"]), 2)
        self.assertEqual(result["signals"][0]["signal"], "UNAVAILABLE")
        self.assertIn("coverage unresolved", result["signals"][0]["reason"])
        self.assertEqual(result["signals"][1]["signal"], "BUY")

    def test_warmup_shortage_is_explained(self):
        self.bundle["calendar"] = self.bundle["calendar"][-100:]
        keep = {r["date"] for r in self.bundle["calendar"]}
        for name in self.bundle["bars"]:
            self.bundle["bars"][name] = [r for r in self.bundle["bars"][name] if utc(r["t"]).date().isoformat() in keep]
        result = self.run_observer()
        self.assertIn("warmup unavailable", result["signals"][0]["reason"])

    def test_duplicate_candle_blocks_symbol(self):
        self.bundle["bars"]["AAA"].append(deepcopy(self.bundle["bars"]["AAA"][-1]))
        self.assertIn("Duplicate", self.run_observer()["signals"][0]["reason"])

    def test_naive_candle_timestamp_blocks_symbol(self):
        self.bundle["bars"]["AAA"][-1]["t"] = "2026-10-23T00:00:00"
        self.assertIn("timezone", self.run_observer()["signals"][0]["reason"])

    def test_invalid_ohlc_blocks_symbol(self):
        self.bundle["bars"]["AAA"][-1]["h"] = 1
        self.assertEqual(self.run_observer()["signals"][0]["signal"], "UNAVAILABLE")

    def test_latest_zero_volume_blocks_actionable_price(self):
        self.bundle["bars"]["AAA"][-1]["v"] = 0
        self.assertIn("zero volume", self.run_observer()["signals"][0]["reason"])

    def test_volume_anomaly_is_a_reported_warning(self):
        self.bundle["bars"]["AAA"][-1]["v"] = 1000000
        result = self.run_observer()
        self.assertEqual(result["signals"][0]["signal"], "BUY")
        self.assertTrue(result["signals"][0]["quality"]["warnings"])

    def test_incomplete_daily_bar_cannot_change_completed_signal_features(self):
        before = self.run_observer()
        self.bundle["observed_at"] = "2026-10-26T13:00:00Z"  # Before Monday open.
        for name in self.bundle["bars"]:
            self.bundle["bars"][name].append(dict(t="2026-10-26T04:00:00Z", o=1000, h=1010, l=990, c=1000, v=1000000))
        after = self.run_observer()
        self.assertEqual(after["session"], "2026-10-23")
        self.assertEqual(after["next_session_open"], "2026-10-26T13:30:00+00:00")
        self.assertEqual(after["signals"][0]["reference_close"], before["signals"][0]["reference_close"])
        self.assertEqual(after["signals"][0]["quality"]["incomplete_bars_excluded"], 1)

    def test_invalid_partial_bar_is_not_hidden_by_filtering(self):
        self.bundle["observed_at"] = "2026-10-26T13:00:00Z"
        self.bundle["bars"]["AAA"].append(dict(t="2026-10-26T04:00:00Z", o=1000, h=1, l=990, c=1000, v=1))
        self.assertEqual(self.run_observer()["signals"][0]["signal"], "UNAVAILABLE")

    def test_weekend_does_not_invent_missing_sessions(self):
        self.bundle["observed_at"] = "2026-10-24T12:00:00Z"
        result = self.run_observer()
        self.assertEqual(result["session"], "2026-10-23")
        self.assertEqual(result["global_blockers"], [])

    def test_calendar_holiday_is_not_a_price_gap(self):
        result = self.run_observer()
        self.assertEqual(result["signals"][0]["signal"], "BUY")
        self.assertNotIn("2026-07-03", [s.opens_at.date().isoformat() for s in sessions_from(self.bundle["calendar"])])

    def test_early_close_and_settling_buffer_are_respected(self):
        # Synthetic early close to exercise calendar logic, not an NYSE assertion.
        next(r for r in self.bundle["calendar"] if r["date"] == "2026-10-23")["close"] = "13:00"
        self.bundle["observed_at"] = "2026-10-23T17:16:00Z"
        self.assertEqual(self.run_observer()["session"], "2026-10-23")
        self.bundle["observed_at"] = "2026-10-23T17:14:00Z"
        self.assertEqual(self.run_observer()["session"], "2026-10-22")

    def test_old_signal_is_not_rolled_to_later_open(self):
        self.bundle["observed_at"] = "2026-10-26T14:00:00Z"
        result = self.run_observer()
        self.assertIn("next_open_already_passed_wait_for_new_completed_session", result["global_blockers"])
        self.assertTrue(all(r["preview_quantity"] == 0 for r in result["signals"]))

    def test_missing_next_calendar_session_blocks_allocation(self):
        self.bundle["calendar"] = [r for r in self.bundle["calendar"] if r["date"] <= "2026-10-23"]
        self.assertIn("next_session_calendar_unavailable", self.run_observer()["global_blockers"])

    def test_future_observation_time_is_rejected(self):
        self.bundle["observed_at"] = "2099-01-01T00:00:00Z"
        with self.assertRaises(ValueError):self.run_observer()

    def test_old_reserved_price_row_is_rejected_before_clipping(self):
        self.bundle["bars"]["AAA"].insert(0, dict(t="2025-12-31T05:00:00Z", o=1, h=1, l=1, c=1, v=1))
        self.assertEqual(self.run_observer()["signals"][0]["signal"], "UNAVAILABLE")

    def test_inactive_or_mismatched_asset_is_blocked(self):
        self.bundle["assets"]["AAA"]["status"] = "inactive"
        self.assertIn("identity/status", self.run_observer()["signals"][0]["reason"])

    def test_unexpected_stream_or_feed_is_rejected(self):
        self.bundle["feed"] = "sip"
        with self.assertRaises(ValueError):self.run_observer()
        self.bundle["feed"] = "iex";self.bundle["bars"]["EXTRA"] = []
        with self.assertRaises(ValueError):self.run_observer()

    def test_stale_reference_blocks_book_not_just_one_stock(self):
        result = self.run_observer(reference=reference(self.bundle, as_of_session="2026-10-22"))
        self.assertIsNone(result["reference"])
        self.assertTrue(all(r["preview_quantity"] == 0 for r in result["signals"]))

    def test_reference_losses_block_new_entries_without_resetting_peak(self):
        result = self.run_observer(reference=reference(self.bundle, peak_equity=12000, day_start_equity=11000))
        self.assertIn("reference_legacy_drawdown_halt_10_percent", result["global_blockers"])
        self.assertIn("reference_legacy_daily_loss_halt_3_percent", result["global_blockers"])
        self.assertEqual(result["reference"]["peak_equity"], 12000)
        self.assertTrue(all(r["preview_quantity"] == 0 for r in result["signals"]))

    def position(self):
        close = self.bundle["bars"]["AAA"][-1]["c"]
        return dict(symbol="AAA", asset_id="fixture-AAA", quantity=1,
            average_entry_price=close + 20, stop_price=close + 10, entry_session="2026-10-01")

    def test_sell_is_a_signal_without_cash_credit_or_position_removal(self):
        r = reference(self.bundle, positions=[self.position()])
        result = self.run_observer(reference=r)
        self.assertEqual(result["signals"][0]["signal"], "SELL")
        self.assertEqual(result["signals"][0]["preview_exit_quantity"], 1)
        self.assertEqual(result["reference"]["cash"], 10000)
        self.assertIn("AAA", result["reference"]["positions"])

    def test_missing_held_price_cannot_be_treated_as_flat(self):
        self.bundle["bars"]["AAA"].pop()
        result = self.run_observer(reference=reference(self.bundle, positions=[self.position()]))
        self.assertIsNone(result["reference"])
        self.assertIsNone(result["preview"]["current_stock_exposure"])

    def test_reference_identity_or_fractional_quantity_is_rejected(self):
        for key, value in [("asset_id", "other"), ("quantity", .5), ("quantity", True)]:
            with self.subTest(key=key, value=value):
                pos = self.position();pos[key] = value
                self.assertIsNone(self.run_observer(reference=reference(self.bundle, positions=[pos]))["reference"])

    def test_holding_review_uses_calendar_age_without_assuming_a_sale(self):
        pos=self.position()
        pos["entry_session"]=utc(self.bundle["bars"]["AAA"][-30]["t"]).date().isoformat()
        pos["stop_price"]=40
        result=self.run_observer(reference=reference(self.bundle,positions=[pos]))
        row=result["signals"][0]
        self.assertEqual(row["holding_review"]["age_sessions"],30)
        self.assertEqual(row["signal"],"SELL")
        self.assertEqual(row["reason"],"HOLDING_REVIEW_FAILED")
        self.assertEqual(result["reference"]["positions"]["AAA"]["quantity"],1)

    def test_crossing_sixty_sessions_does_not_create_an_unapproved_hard_exit(self):
        pos=self.position();pos["stop_price"]=40
        pos["entry_session"]=utc(self.bundle["bars"]["AAA"][-61]["t"]).date().isoformat()
        result=self.run_observer(reference=reference(self.bundle,positions=[pos]))
        self.assertEqual(result["signals"][0]["signal"],"HOLD")
        self.assertIsNone(result["signals"][0]["holding_review"])

    def test_future_price_row_is_not_used_or_hidden_by_clipping(self):
        self.bundle["bars"]["AAA"].append(dict(t="2026-10-30T04:00:00Z",o=1,h=1,l=1,c=1,v=1))
        self.assertEqual(self.run_observer()["signals"][0]["signal"],"UNAVAILABLE")

    def test_duplicate_calendar_session_is_rejected(self):
        self.bundle["calendar"].append(self.bundle["calendar"][-1])
        with self.assertRaises(ValueError):self.run_observer()

    def test_markdown_reports_target_and_observation_limitations(self):
        text = markdown(self.run_observer())
        self.assertIn("70.00%", text)
        self.assertIn("85.00%", text)
        self.assertIn("No orders", text)
        self.assertIn("AAA", text)


class ConfigAndStoreTests(TestCase):
    def test_config_rejects_reserved_warmup_and_invalid_limits(self):
        for changes in [dict(history_start="2025-01-01"), dict(target_exposure=.90), dict(reference_cash=True),
                        dict(max_positions=True), dict(close_settle_minutes=-1), dict(planned_stop_risk=float("nan"))]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):ShadowConfig(("AAA",), **changes)

    def test_config_rejects_duplicate_or_context_symbols(self):
        for values in [("AAA", "AAA"), ("SPY",), ("aaa",), ()]:
            with self.subTest(values=values), self.assertRaises(ValueError):ShadowConfig(values)

    def test_json_rejects_duplicate_keys_unknown_execution_keys_and_non_array_watchlist(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp)/"settings.json"
            for text in ['{"symbols":["AAA"],"symbols":["BBB"]}', '{"symbols":["AAA"],"submit_orders":true}', '{"symbols":"AAA"}']:
                path.write_text(text)
                with self.subTest(text=text), self.assertRaises(ValueError):load_config(path)

    def test_timestamps_and_serialization_reject_naive_or_nonfinite_inputs(self):
        with self.assertRaises(ValueError):utc("2026-01-01")
        with self.assertRaises(ValueError):canonical(dict(value=float("nan")))

    def report(self):
        return dict(id="fixture-id", observed_at="2026-10-23T20:30:00+00:00", config=dict(target=.7),
            implementation=dict(module="fixture"), environment=dict(python="fixture"), value=1)

    def test_append_idempotence_and_read_only_latest(self):
        with TemporaryDirectory() as tmp:
            store = ObservationStore(Path(tmp)/"observer.sqlite3");report = self.report()
            self.assertTrue(store.record(report))
            self.assertFalse(store.record(report))
            self.assertEqual(store.latest(), report)
            with closing(sqlite3.connect(store.path)) as db:self.assertEqual(db.execute("SELECT count(*) FROM shadow_observations").fetchone()[0], 1)

    def test_different_content_cannot_replace_same_id(self):
        with TemporaryDirectory() as tmp:
            store = ObservationStore(Path(tmp)/"observer.sqlite3");report = self.report();store.record(report)
            with self.assertRaises(ValueError):store.record(dict(report, value=2))
            self.assertEqual(store.latest()["value"], 1)

    def test_changed_code_config_or_environment_requires_new_database(self):
        for key in ["config", "implementation", "environment"]:
            with self.subTest(key=key), TemporaryDirectory() as tmp:
                store = ObservationStore(Path(tmp)/"observer.sqlite3");report = self.report();store.record(report)
                with self.assertRaises(ValueError):store.record(dict(report, **{key:dict(changed=True)}))

    def test_non_shadow_database_is_not_modified(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp)/"trading.sqlite3"
            with closing(sqlite3.connect(path)) as db, db:db.execute("CREATE TABLE candles (id INTEGER)")
            with self.assertRaises(ValueError):ObservationStore(path).record(self.report())
            with closing(sqlite3.connect(path)) as db:self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(), [("candles",)])

    def test_corrupted_payload_is_detected(self):
        with TemporaryDirectory() as tmp:
            store = ObservationStore(Path(tmp)/"observer.sqlite3");store.record(self.report())
            with closing(sqlite3.connect(store.path)) as db, db:db.execute("UPDATE shadow_observations SET payload=?", (canonical(dict(self.report(), value=999)),))
            with self.assertRaises(ValueError):store.latest()

    def test_corrupted_checksum_is_not_silently_accepted_on_duplicate_record(self):
        with TemporaryDirectory() as tmp:
            store=ObservationStore(Path(tmp)/"observer.sqlite3");report=self.report();store.record(report)
            with closing(sqlite3.connect(store.path)) as db, db:db.execute("UPDATE shadow_observations SET payload_sha256='corrupt'")
            with self.assertRaises(ValueError):store.record(report)

    def test_all_connections_close_so_windows_can_move_database(self):
        with TemporaryDirectory() as tmp:
            store=ObservationStore(Path(tmp)/"observer.sqlite3");store.record(self.report());store.latest()
            moved=store.path.with_name("moved.sqlite3")
            store.path.rename(moved)
            self.assertTrue(moved.exists())

    def test_config_types_are_rejected_with_clear_value_errors(self):
        for changes in [dict(symbols="ABC"), dict(reference_cash="10000"), dict(history_start=True)]:
            values=dict(symbols=("AAA",));values.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):ShadowConfig(**values)

    def test_saved_bundle_cli_export_and_latest_do_not_connect(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);bundle=root/"bundle.json";settings=root/"config.json";db=root/"observer.sqlite3"
            bundle.write_text(canonical(fixture()))
            settings.write_text(canonical(ShadowConfig(("AAA","BBB")).record()))
            args=["observer", "observe", "--bundle",str(bundle),"--config",str(settings),"--database",str(db),"--output",str(root/"output")]
            with patch("app.broker.alpaca_client._AlpacaCredentials.load",side_effect=AssertionError("credentials")), redirect_stdout(io.StringIO()):
                with patch("sys.argv",args):main()
                with patch("sys.argv",args):main()
                with patch("sys.argv",["observer","latest","--database",str(db)]):main()
            self.assertEqual(len(list((root/"output/reports").glob("*.json"))),1)
            self.assertEqual(len(list((root/"output/reports").glob("*.md"))),1)

    def test_export_is_immutable_and_idempotent(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"report.md";write_once(path,"first\n");write_once(path,"first\n")
            with self.assertRaises(ValueError):write_once(path,"second\n")
            self.assertEqual(path.read_text(), "first\n")

    def test_latest_missing_database_does_not_create_it(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp)/"absent.sqlite3"
            with self.assertRaises(ValueError):ObservationStore(path).latest()
            self.assertFalse(path.exists())


class Reply:
    def __init__(self, data):self.data=data
    def __enter__(self):return self
    def __exit__(self, *args):return False
    def read(self, n):return self.data[:n]


class Opener:
    def __init__(self, payloads):self.payloads=list(payloads);self.calls=[]
    def open(self, request, timeout):
        self.calls.append((request, timeout))
        value=self.payloads.pop(0)
        if isinstance(value, Exception):raise value
        return Reply(value if isinstance(value, bytes) else json.dumps(value).encode())


class TransportTests(TestCase):
    def client(self, payloads):
        client=ShadowDataClient.__new__(ShadowDataClient)
        client._credentials=SimpleNamespace(api_key="FAKE-KEY-ONLY", secret_key="FAKE-SECRET-ONLY")
        client._opener=Opener(payloads);client.request_count=0;client._last_request=0;client._started=100;client._stopped=False
        self.enterContext(patch("app.shadow.data.time.monotonic", return_value=100))
        self.enterContext(patch("app.shadow.data.time.sleep"))
        return client

    def test_fixed_hosts_and_get_only_endpoints(self):
        client=self.client([{},[],{}])
        for path in ["/v2/stocks/bars", "/v2/calendar", "/v2/assets/AAA"]:client._get(path)
        requests=[c[0] for c in client._opener.calls]
        self.assertTrue(all(r.get_method()=="GET" for r in requests))
        self.assertEqual([urlparse(r.full_url).hostname for r in requests], ["data.alpaca.markets","paper-api.alpaca.markets","paper-api.alpaca.markets"])

    def test_account_order_billing_and_arbitrary_hosts_are_rejected(self):
        client=self.client([])
        for path in ["/v2/account","/v2/orders","/v2/positions","/billing","https://evil.invalid/v2/calendar","/v2/assets/../orders"]:
            with self.subTest(path=path), self.assertRaises(ValueError):client._get(path)
        self.assertEqual(client._opener.calls,[])

    def test_http_access_rate_or_redirect_failure_stops_without_retry(self):
        for code in [401,403,429,302]:
            with self.subTest(code=code):
                client=self.client([HTTPError("https://example.invalid",code,"fixture",{},None)])
                with self.assertRaises(ShadowDataError) as context:client._get("/v2/calendar")
                self.assertNotIn("FAKE-SECRET",str(context.exception))
                with self.assertRaises(ShadowDataError):client._get("/v2/calendar")
                self.assertEqual(len(client._opener.calls),1)

    def test_redirect_handler_does_not_follow(self):
        self.assertIsNone(_NoRedirects().redirect_request(None,None,302,"fixture",{},"https://other.invalid"))

    def test_invalid_json_or_oversized_payload_stops(self):
        for payload in [b"not-json",b"x"*5_000_001]:
            with self.subTest(size=len(payload)):
                client=self.client([payload])
                with self.assertRaises(ShadowDataError):client._get("/v2/calendar")
                self.assertTrue(client._stopped)

    def test_exhausted_request_or_time_budget_prevents_network(self):
        for change in [dict(request_count=110),dict(_started=-1000)]:
            client=self.client([])
            for k,v in change.items():setattr(client,k,v)
            with self.assertRaises(ShadowDataError):client._get("/v2/calendar")
            self.assertEqual(client._opener.calls,[])

    def test_transport_error_stops_without_retry(self):
        client=self.client([OSError("fixture")])
        with self.assertRaises(ShadowDataError):client._get("/v2/calendar")
        self.assertTrue(client._stopped)

    def test_response_after_collection_deadline_is_rejected(self):
        client=self.client([{}])
        with patch("app.shadow.data.time.monotonic",side_effect=[100,100,100,100,400]):
            with self.assertRaises(ShadowDataError):client._get("/v2/calendar")
        self.assertTrue(client._stopped)
        self.assertEqual(len(client._opener.calls),1)

    def collection(self, pages):
        client=self.client([])
        def get(path, params=None):
            if path=="/v2/calendar":return [dict(date="2026-01-02",open="09:30",close="16:00")]
            if path.startswith("/v2/assets/"):return {"symbol":path.split("/")[-1]}
            return pages.pop(0)
        client._get=get
        return client

    def test_pagination_appends_all_pages_for_both_streams(self):
        client=self.collection([dict(bars=dict(AAA=[dict(n=1)]),next_page_token="next"),
            dict(bars=dict(AAA=[dict(n=2)])),dict(bars=dict(SPY=[dict(n=3)]))])
        data=client.collect(ShadowConfig(("AAA",)))
        self.assertEqual(len(data["bars"]["AAA"]),2)
        self.assertEqual(data["feed"],"iex")
        self.assertEqual(data["adjustment"],"split")

    def test_repeated_or_excessive_page_tokens_stop(self):
        for tokens in [("repeat","repeat"),("one","two","three")]:
            client=self.collection([dict(bars=dict(AAA=[]),next_page_token=t) for t in tokens])
            with self.assertRaises(ShadowDataError):client.collect(ShadowConfig(("AAA",)))

    def test_unexpected_symbol_in_transport_response_stops(self):
        client=self.collection([dict(bars=dict(OTHER=[]))])
        with self.assertRaises(ShadowDataError):client.collect(ShadowConfig(("AAA",)))

    def test_real_get_parameters_never_query_reserved_history_or_paid_feed(self):
        client=self.client([[dict(date="2026-01-02",open="09:30",close="16:00")],{},dict(bars=dict(AAA=[])),{},dict(bars=dict(SPY=[]))])
        client.collect(ShadowConfig(("AAA",)))
        calls=[parse_qs(urlparse(r.full_url).query) for r,_ in client._opener.calls if "/stocks/bars" in r.full_url]
        self.assertEqual(len(calls),2)
        for params in calls:
            self.assertEqual(params["feed"],["iex"])
            self.assertEqual(params["adjustment"],["split"])
            self.assertTrue(params["start"][0].startswith("2026-01-01"))

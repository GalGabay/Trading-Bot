"""One bounded, GET-only acquisition for the frozen historical 100-name basket.

Collection is observation, not identity/action approval. No strategies or orders.
The one-shot journal prevents restarting an exhausted/denied protocol in another
directory. Offline qualification re-reads saved payloads, including partial ones.
"""

import argparse
from collections import Counter
import csv
from dataclasses import asdict
from datetime import UTC, datetime
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener

import pandas as pd
from alpaca.data.timeframe import TimeFrame

from app.broker.research_client import HistoricalResearchClient, _NoRedirects
from app.data.market_calendar import TradingSession
from app.data.market_data import ValidationConfig, validate_candles
from backtesting.cohort_audit import SavedCalendar, checked_file, digest
from backtesting.free_collection import action_inventory, raw_candles
from backtesting.pilot_qualification import compare_bars
from backtesting.pilot_readiness_review import offline_only, write_csv, write_json

PROTOCOL = Path("docs/broad_100_collection_protocol.json")
OUTPUT = Path("data/reports/broad_100_collection_v1")
ONCE = Path("data/reports/broad_100_collection_execution.json")
PLAN = Path("docs/broad_100_comparison_plan.json")
MODULES = ("backtesting/broad_collection.py", "app/broker/research_client.py",
           "backtesting/free_collection.py", "app/data/market_data.py",
           "backtesting/cohort_audit.py", "backtesting/pilot_qualification.py",
           "backtesting/pilot_readiness_review.py")


def pin(path):
    path = Path(path).resolve()
    return {"path": path.relative_to(Path.cwd().resolve()).as_posix(), "sha256": digest(path)}


def prepare():
    """Freeze exact requests/cache sources before credentials or network access."""
    if PROTOCOL.exists() or ONCE.exists() or OUTPUT.exists():
        raise FileExistsError("This one-shot collection is already prepared/started")
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    root = Path.cwd()
    roster_path = checked_file(root, plan["roster"])
    checked_file(root, plan["qualification"])
    with roster_path.open(encoding="utf-8", newline="") as stream:
        roster = list(csv.DictReader(stream))
    inventory_path = Path("docs/research_data/broad_100_cached_inventory.csv")
    with inventory_path.open(encoding="utf-8", newline="") as stream:
        inventory = {r["instrument_id"]: r for r in csv.DictReader(stream)}
    review = json.loads(Path("docs/broad_sample_qualification_review.json").read_text(encoding="utf-8"))
    for entry in review["inputs"].values():
        checked_file(root, entry)
    old_report_path = checked_file(root, review["inputs"]["collection_report"])
    old_report = json.loads(old_report_path.read_text(encoding="utf-8"))
    old_root = old_report_path.parent
    summary_path = checked_file(root, review["inputs"]["collection_summary"])
    old_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    queue = []
    for row in roster:
        stable, alias = row["instrument_id"], row["snapshot_alias"]
        HistoricalResearchClient._symbol(alias)
        item = dict(instrument_id=stable, snapshot_alias=alias, source_name=row["source_name"],
                    start="2016-01-01", end_exclusive="2024-01-01", cached_bars=None,
                    cached_action_queries=[], ready_for_simulation=False)
        cached = inventory[stable]
        if cached["full_2016_2023_raw_calendar_observed"] == "True":
            paths = json.loads(cached["raw_candidate_paths"])
            item["cached_bars"] = pin(paths[-1])
        # These are provider SYMBOL query results, not certified attachments to
        # an issuer. Preserve both reviewed rename branches, never merge by id.
        aliases = {"CBG": {"CBG", "CBRE"}, "UA": {"UA", "UAA"}}.get(alias, {alias})
        seen = set()
        for probe in old_report["probes"]:
            actions = probe["actions"]
            if probe["symbol"] not in aliases or probe["symbol"] in seen or "pages" not in actions:
                continue
            seen.add(probe["symbol"])
            directory = actions.get("source_directory", probe["directory"])
            pages = [pin(checked_file(root, dict(path=(old_root / directory / p["file"]).as_posix(),
                                                sha256=p["sha256"]))) for p in actions["pages"]]
            item["cached_action_queries"].append(dict(symbol=probe["symbol"], pages=pages))
        queue.append(item)
    protocol = dict(schema_version=1, authorized_on="2026-10-29",
        authorization="Owner requested implementation and execution of bounded free collection for this fixed basket",
        purchase_budget_usd=0, performance_authorized=False, paper_authorized=False,
        plan=pin(PLAN), roster=plan["roster"], qualification=plan["qualification"],
        inventory=pin(inventory_path), prior_report=pin(old_report_path), prior_summary=pin(summary_path),
        calendar=pin("data/reports/broad_universe_audit_final/calendar.json"),
        prior_event_review=review["inputs"]["collection_review"],
        execution_sha256={name: digest(name) for name in MODULES},
        limits=plan["collection_proposal"], queue=queue,
        output=OUTPUT.as_posix(), one_shot_journal=ONCE.as_posix(),
        interpretation="Historical aliases are untrusted probes. No new successor/alias probes or public-document GETs authorized by this queue.")
    if len(queue) != 100 or len({p["instrument_id"] for p in queue}) != 100 or any(p["snapshot_alias"] == "JPM" for p in queue):
        raise ValueError("Frozen sample/parked-JPM constraint violated")
    for item in queue:
        if item["cached_bars"]:
            checked_file(root, item["cached_bars"])
    write_json(PROTOCOL, protocol)
    return {"candidates": len(queue), "cached_full_price_streams": sum(bool(p["cached_bars"]) for p in queue),
            "cached_action_candidates": sum(bool(p["cached_action_queries"]) for p in queue)}


def load_protocol():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    for name in ("plan", "roster", "qualification", "inventory", "prior_report", "prior_summary", "calendar", "prior_event_review"):
        checked_file(Path.cwd(), protocol[name])
    for name, sha in protocol["execution_sha256"].items():
        checked_file(Path.cwd(), dict(path=name, sha256=sha))
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    if protocol["limits"] != plan["collection_proposal"] or protocol["performance_authorized"] or protocol["paper_authorized"] or protocol["purchase_budget_usd"] != 0:
        raise ValueError("Collection authorization/limits changed")
    with checked_file(Path.cwd(), protocol["roster"]).open(encoding="utf-8", newline="") as stream:
        roster = list(csv.DictReader(stream))
    if [(r["instrument_id"], r["snapshot_alias"]) for r in roster] != [(r["instrument_id"], r["snapshot_alias"]) for r in protocol["queue"]] or len(roster) != 100:
        raise ValueError("Do not change/reroll the sample")
    for item in protocol["queue"]:
        if item["start"] != "2016-01-01" or item["end_exclusive"] != "2024-01-01" or item["snapshot_alias"] == "JPM" or item["ready_for_simulation"]:
            raise ValueError("Queue exceeds historical collection scope")
        HistoricalResearchClient._symbol(item["snapshot_alias"])
        if item["cached_bars"]:
            checked_file(Path.cwd(), item["cached_bars"])
        for query in item["cached_action_queries"]:
            for page in query["pages"]:
                checked_file(Path.cwd(), page)
    return protocol


class CollectionStop(RuntimeError):
    pass


class BoundedClient(HistoricalResearchClient):
    """Reuse the existing fixed query builders; journal/save actual GETs here."""

    def __init__(self, report, save):
        super().__init__()
        # Do not send API credentials through ambient shell proxies.
        self._opener = build_opener(ProxyHandler({}), _NoRedirects())
        self.report, self.save = report, save
        self.started = self.batch_started = time.monotonic()
        self.batch_attempts, self.batch = 0, 1
        self.limits = report["limits"]
        self.page_path = None

    def next_batch(self):
        self.batch += 1
        self.batch_attempts, self.batch_started = 0, time.monotonic()

    def _get(self, path, params):
        if path not in {"/v2/stocks/bars", "/v1/corporate-actions"}:
            raise CollectionStop("endpoint_not_allowed")
        limits = self.limits
        delay = limits["minimum_request_spacing_seconds"] - (time.monotonic() - self._last_request)
        if delay > 0:
            time.sleep(delay)
        now = time.monotonic()
        remaining = min(limits["global_wall_clock_limit_minutes"] * 60 - (now - self.started),
                        limits["per_batch_wall_clock_limit_minutes"] * 60 - (now - self.batch_started))
        if remaining <= 0 or len(self.report["attempts"]) >= limits["global_http_attempt_limit"] or self.batch_attempts >= limits["per_batch_http_attempt_limit"]:
            raise CollectionStop("request_or_elapsed_budget_exhausted")
        attempt = dict(number=len(self.report["attempts"]) + 1, batch=self.batch,
                       symbol=params["symbols"], resource=path, state="started",
                       elapsed_seconds=round(now - self.started, 3), utc=datetime.now(UTC).isoformat(),
                       page=self.page_path.relative_to(OUTPUT).as_posix())
        request = Request("https://data.alpaca.markets" + path + "?" + urlencode(params),
                          headers={"APCA-API-KEY-ID": self._credentials.api_key,
                                   "APCA-API-SECRET-KEY": self._credentials.secret_key}, method="GET")
        self.report["attempts"].append(attempt)
        self.batch_attempts += 1
        self.request_count += 1
        self._last_request = now
        self.save()  # An interrupted request consumes the cumulative allowance.
        try:
            with self._opener.open(request, timeout=min(limits["timeout_seconds"], remaining)) as response:
                payload = response.read(8_000_001)
            self.page_path.write_bytes(payload)  # Exact original response bytes.
            attempt.update(state="response_saved", sha256=digest(self.page_path), bytes=len(payload))
            self.save()
            if len(payload) > 8_000_000:
                raise ValueError("page_size_limit")
            result = json.loads(payload)
            if not isinstance(result, dict):
                raise ValueError("non_object_response")
            return result
        except HTTPError as exc:
            attempt.update(state="http_error", http_status=exc.code)
            # Unsupported old aliases may return 400/404/422. Preserve these as
            # gaps; every denial, redirect or server failure stops ALL batches.
            if exc.code in {400, 404, 422}:
                raise ValueError("unsupported_historical_query") from None
            raise CollectionStop("http_access_redirect_or_server_stop") from None
        except (OSError, EOFError):
            attempt.update(state="transport_failure")
            raise CollectionStop("transport_failure") from None
        finally:
            self.save()


def collect():
    protocol = load_protocol()
    if OUTPUT.exists():
        raise FileExistsError("Saved collection cannot be overwritten")
    ONCE.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive fixed journal; another output folder cannot reset the allowance.
    with ONCE.open("x", encoding="utf-8") as stream:
        json.dump(dict(protocol=pin(PROTOCOL), output=OUTPUT.as_posix(), state="started_do_not_retry"), stream)
    OUTPUT.mkdir()
    write_json(OUTPUT / "frozen_protocol.json", protocol)
    report = dict(protocol=pin(PROTOCOL), limits=protocol["limits"], attempts=[], candidates=[],
                  stop_reason=None, completed=False, purchases_usd=0, orders=0, account_requests=0,
                  strategy_runs=0, unit_tests_run=0, holdout_candles_read=False)

    def save():
        write_json(OUTPUT / "report.json", report)

    save()
    try:
        client = BoundedClient(report, save)
        for index, probe in enumerate(protocol["queue"]):
            if index and index % protocol["limits"]["max_probe_intervals_per_batch"] == 0:
                client.next_batch()
            folder = OUTPUT / f"{index + 1:03d}"
            folder.mkdir()
            item = dict(instrument_id=probe["instrument_id"], snapshot_alias=probe["snapshot_alias"],
                        bars={"status": "pending"}, actions={"status": "pending"})
            report["candidates"].append(item)
            for resource in ("bars", "actions"):
                cached = probe["cached_bars"] if resource == "bars" else probe["cached_action_queries"]
                if cached:
                    item[resource] = dict(status="reused_pinned_cache", sources=cached)
                    continue
                result = item[resource] = dict(status="collecting", pages=[])
                token, seen = None, set()
                try:
                    for page_number in range(protocol["limits"]["max_pages_per_symbol_resource"]):
                        client.page_path = folder / f"{resource}_{page_number + 1}.json"
                        if resource == "bars":
                            page = client.bars_page(symbol=probe["snapshot_alias"], start=datetime(2016, 1, 1, tzinfo=UTC),
                                                     end_exclusive=datetime(2024, 1, 1, tzinfo=UTC), token=token)
                        else:
                            page = client.actions_page(symbol=probe["snapshot_alias"], token=token)
                        result["pages"].append(pin(client.page_path))
                        token = page.get("next_page_token")
                        if token is None:
                            result["status"] = "downloaded_not_certified"
                            break
                        if not isinstance(token, str) or not token or token in seen:
                            raise ValueError("invalid_or_repeated_pagination")
                        seen.add(token)
                    else:
                        result["status"] = "incomplete_page_cap"
                except CollectionStop as exc:
                    result["status"] = "stopped_globally"
                    report["stop_reason"] = str(exc)
                    raise
                except (ValueError, TypeError, KeyError):
                    result["status"] = "invalid_or_unavailable_saved_source"
                finally:
                    save()
            print(json.dumps(dict(index=index + 1, symbol=probe["snapshot_alias"], bars=item["bars"]["status"],
                                  actions=item["actions"]["status"], http_attempts=len(report["attempts"]))), flush=True)
        report["completed"] = True
    except CollectionStop:
        pass
    except Exception as exc:
        report["stop_reason"] = "local_failure_" + type(exc).__name__  # No credential/error body leak.
    finally:
        save()
    return dict(http_attempts=len(report["attempts"]), completed=report["completed"], stop_reason=report["stop_reason"])


def qualify():
    """Structural qualification offline; absent observations are not fake candles."""
    protocol = load_protocol()
    frozen = json.loads((OUTPUT / "frozen_protocol.json").read_text(encoding="utf-8"))
    if frozen != protocol:
        raise ValueError("Execution protocol changed")
    report = json.loads((OUTPUT / "report.json").read_text(encoding="utf-8"))
    if report["protocol"] != pin(PROTOCOL):
        raise ValueError("Execution protocol checksum mismatch")
    calendar_path = checked_file(Path.cwd(), protocol["calendar"])
    sessions = [TradingSession(pd.Timestamp(s["opens_at"]), pd.Timestamp(s["closes_at"]))
                for s in json.loads(calendar_path.read_text(encoding="utf-8"))]
    calendar = SavedCalendar(sessions)
    scheduled = {s.opens_at.tz_convert("America/New_York").normalize().tz_convert("UTC") for s in sessions}
    collected = {p["instrument_id"]: p for p in report["candidates"]}
    prior = json.loads(checked_file(Path.cwd(), protocol["prior_summary"]).read_text(encoding="utf-8"))
    evidence = json.loads(checked_file(Path.cwd(), protocol["prior_event_review"]).read_text(encoding="utf-8"))
    for entry in evidence["sources"].values():
        checked_file(Path.cwd(), entry)
    rows, source_hashes = [], {}

    def pages(entries):
        values = []
        for entry in entries:
            path = checked_file(Path.cwd(), entry)
            source_hashes[entry["path"]] = digest(path)
            values.append(json.loads(path.read_text(encoding="utf-8")))
        return values

    for index, probe in enumerate(protocol["queue"], 1):
        item = collected.get(probe["instrument_id"], {})
        row = dict(instrument_id=probe["instrument_id"], snapshot_alias=probe["snapshot_alias"],
                   price_status="not_requested_after_stop", rows=0, full_calendar_observed=False,
                   action_status="not_requested_after_stop", provider_event_count=0,
                   identity_verified=False, actions_certified_complete=False, ready_for_broad_scoring=False)
        blockers = ["Dated issuer/class/alias review and complete event/entitlement evidence required; query ticker is not identity"]
        folder = OUTPUT / f"{index:03d}"
        try:
            if probe["cached_bars"]:
                path = checked_file(Path.cwd(), probe["cached_bars"])
                source_hashes[pin(path)["path"]] = digest(path)
                frame = pd.read_csv(path)
                row["price_status"] = "reused_full_raw_observation"
            elif item.get("bars", {}).get("status") == "downloaded_not_certified":
                payloads = pages(item["bars"]["pages"])
                if any("bars" not in p for p in payloads):
                    raise ValueError("missing_bars_payload")
                frame = raw_candles(payloads, probe["snapshot_alias"])
                row["price_status"] = "downloaded_raw_observation"
            else:
                row["price_status"] = item.get("bars", {}).get("status", row["price_status"])
                frame = None
            if frame is not None:
                stamps = pd.to_datetime(frame["timestamp"], utc=True)
                if not ((stamps >= pd.Timestamp("2016-01-01", tz="UTC")) & (stamps < pd.Timestamp("2024-01-01", tz="UTC"))).all():
                    raise ValueError("price_outside_development_bounds")
                validation = None if frame.empty else validate_candles(frame, config=ValidationConfig(timeframe=TimeFrame.Day), calendar=calendar)
                observed = set(stamps)
                if not stamps.is_monotonic_increasing:
                    raise ValueError("unordered_candles")
                row.update(rows=len(frame), full_calendar_observed=observed == scheduled,
                           first_session=None if frame.empty else min(observed).date().isoformat(),
                           last_session=None if frame.empty else max(observed).date().isoformat(),
                           unobserved_calendar_sessions=len(scheduled - observed),
                           volume_warnings=json.dumps([] if validation is None else [asdict(w) for w in validation.warnings]))
                if folder.exists():
                    path = folder / "qualified_observations.csv"
                    frame.to_csv(path, index=False, lineterminator="\n")
                    compare_bars(pd.read_csv(path), frame)
                    row.update(observation_csv=path.as_posix(), observation_sha256=digest(path))
                if observed != scheduled:
                    blockers.append("Absent calendar observations need dated listing/delisting/alias/feed evidence; not automatically missing candles")
        except (ValueError, TypeError, KeyError) as exc:
            row.update(price_status="hard_price_validation_error", full_calendar_observed=False,
                       validation_error_codes=json.dumps([i.code for i in getattr(exc, "issues", ())]) or type(exc).__name__)
            blockers.append("Hard price validation error; original payload retained")
        queries = probe["cached_action_queries"]
        if not queries and item.get("actions", {}).get("status") == "downloaded_not_certified":
            queries = [dict(symbol=probe["snapshot_alias"], pages=item["actions"]["pages"])]
        if queries:
            try:
                events = [dict(query_symbol=q["symbol"], **event) for q in queries for event in action_inventory(pages(q["pages"]))]
                row.update(action_status="provider_inventory_not_certified", provider_event_count=len(events),
                           event_categories=json.dumps(dict(Counter(e["category"] for e in events)), sort_keys=True))
                if folder.exists():
                    write_json(folder / "event_inventory.json", events)
                    row["event_inventory_sha256"] = digest(folder / "event_inventory.json")
                material = sorted({e["category"] for e in events} - {"cash_dividends"})
                if material:
                    blockers.append("Review provider non-cash/action categories: " + ", ".join(material))
                if not events:
                    blockers.append("Empty provider action inventory is not evidence of no company events")
            except (ValueError, TypeError, KeyError):
                row["action_status"] = "hard_action_inventory_error"
                blockers.append("Malformed/conflicting action evidence")
        else:
            row["action_status"] = item.get("actions", {}).get("status", row["action_status"])
        relevant_probes = {"UA": {"ua_class_a_old", "ua_class_c_old", "ua_class_a_new"}, "CBG": {"cbre_new"}}.get(probe["snapshot_alias"], set())
        known = [check for check in prior["required_event_checks"] if check["probe"] in relevant_probes]
        row["saved_primary_event_checks"] = json.dumps(known)
        for check in known:
            if not check["execution_ready"]:
                blockers.append("Saved primary evidence requires supported ownership/timing terms: " + check["name"])
        row["blockers"] = json.dumps(blockers)
        rows.append(row)
    attempts = report["attempts"]
    if len(attempts) > protocol["limits"]["global_http_attempt_limit"] or [a["number"] for a in attempts] != list(range(1, len(attempts) + 1)):
        raise ValueError("Cumulative request ledger invalid")
    for a in attempts:
        if a.get("sha256"):
            checked_file(Path.cwd(), dict(path=(OUTPUT / a["page"]).as_posix(), sha256=a["sha256"]))
    summary = dict(date="2026-10-29", protocol=pin(PROTOCOL), report=pin(OUTPUT / "report.json"),
        selected_count=len(rows), http_attempts=len(attempts), batches_started=max((a["batch"] for a in attempts), default=0),
        completed=report["completed"], stop_reason=report["stop_reason"],
        price_statuses=dict(Counter(r["price_status"] for r in rows)),
        action_statuses=dict(Counter(r["action_status"] for r in rows)),
        selected_with_valid_raw_observations=sum(r["rows"] > 0 and r["price_status"] != "hard_price_validation_error" for r in rows),
        selected_full_raw_calendar_observed=sum(r["full_calendar_observed"] for r in rows),
        candle_rows=sum(r["rows"] for r in rows), provider_events=sum(r["provider_event_count"] for r in rows),
        source_sha256=source_hashes, saved_primary_sources_checked=len(evidence["sources"]),
        all_selected_retained=len(rows) == 100, new_stocks_admitted=0, ready_for_broad_scoring=False,
        purchases_usd=0, orders=0, account_requests=0, strategy_runs=0, unit_tests_run=0,
        holdout_candles_read=False, no_forward_fill=True, no_aliases_stitched=True,
        limitations="Coverage is observation only; independently review lifetimes, reused tickers, corporate actions, cash/share availability and successor branches before a frozen broader performance run.")
    write_csv(OUTPUT / "qualification.csv", rows)
    write_json(OUTPUT / "qualification.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "collect", "qualify"))
    args = parser.parse_args()
    if args.action == "qualify":
        with offline_only():
            result = qualify()
        print(json.dumps({k: v for k, v in result.items() if k != "source_sha256"}, indent=2))
    else:
        print(json.dumps(prepare() if args.action == "prepare" else collect(), indent=2))


if __name__ == "__main__":
    main()

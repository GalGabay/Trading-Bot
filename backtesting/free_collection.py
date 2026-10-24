"""Collect a frozen 24-case historical raw-data/action sample, without purchases.

Not a performance runner or executable historical universe. Numeric filenames
and repository-relative configuration work on Windows and Raspberry Pi.
"""

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

import pandas as pd
from alpaca.data.timeframe import TimeFrame

from app.broker.research_client import HistoricalResearchClient
from app.data.market_calendar import TradingSession
from app.data.market_data import CANONICAL_CANDLE_COLUMNS, ValidationConfig, validate_candles
from backtesting.cohort_audit import SavedCalendar

PLAN = Path("docs/free_collection_plan.json")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_plan(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    fixed = {"schema_version": 1, "new_purchases_budget_usd": 0,
             "subscription_changes_authorized": False, "feed": "sip", "adjustment": "raw",
             "timeframe": "1Day", "asof": "-", "max_probes": 24,
             "max_pages_per_resource": 4, "max_http_attempts": 192,
             "minimum_request_spacing_seconds": .4, "automatic_retries": False,
             "automatic_feed_fallback": False, "automatic_paid_upgrade": False}
    if any(value.get(key) != expected for key, expected in fixed.items()):
        raise ValueError("Collection restricted to the declared no-purchase historical protocol")
    probes = value["probes"]
    if len(probes) != 24 or len({p["probe_id"] for p in probes}) != 24:
        raise ValueError("Retain all 24 predeclared interval probes")
    for probe in probes:
        if probe["ready_for_simulation"] or not "2016-01-01" <= probe["start"] < probe["end_exclusive"] <= "2024-01-01":
            raise ValueError("Collection interval exceeds declared bounds/readiness")
        for key in ("start", "end_exclusive"):
            datetime.strptime(probe[key], "%Y-%m-%d")
    for key in ("cohort_review", "calendar_path"):
        expected = value["cohort_review_sha256" if key == "cohort_review" else "calendar_sha256"]
        if digest(value[key]) != expected:
            raise ValueError("Reviewed source membership/calendar checksum changed")
    return value


def raw_candles(pages, symbol):
    rows = []
    fields = {"t": "timestamp", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}
    for page in pages:
        grouped = page.get("bars")
        if grouped is None:
            continue
        if not isinstance(grouped, dict) or set(grouped) - {symbol}:
            raise ValueError("Unexpected returned ticker; do not relabel another security")
        bars = grouped.get(symbol, [])
        if not isinstance(bars, list):
            raise ValueError("Expected a raw candle list")
        for bar in bars:
            if not isinstance(bar, dict) or not set(fields).issubset(bar):
                raise ValueError("Raw candle missing required observed values")
            rows.append({**{name: bar[key] for key, name in fields.items()}, "symbol": symbol})
    frame = pd.DataFrame(rows, columns=CANONICAL_CANDLE_COLUMNS)
    if not frame.empty:
        validate_candles(frame, config=ValidationConfig(timeframe=TimeFrame.Day))
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    return frame


def collect_pages(client, resource, probe, folder):
    pages, metadata, tokens, token = [], [], set(), None
    for index in range(4):
        if resource == "bars":
            page = client.bars_page(symbol=probe["symbol"],
                                    start=datetime.fromisoformat(probe["start"]).replace(tzinfo=UTC),
                                    end_exclusive=datetime.fromisoformat(probe["end_exclusive"]).replace(tzinfo=UTC), token=token)
        else:
            page = client.actions_page(symbol=probe["symbol"], token=token)
        path = folder / f"{resource}_{index + 1}.json"
        write(path, page)  # Preserve evidence even if subsequent validation fails.
        metadata.append({"file": path.name, "sha256": digest(path)})
        pages.append(page)
        token = page.get("next_page_token")
        if token is None:
            return pages, metadata
        if not isinstance(token, str) or not token or token in tokens:
            raise ValueError("Invalid/repeated pagination; incomplete data cannot be accepted")
        tokens.add(token)
    raise ValueError("Incomplete collection: four-page resource budget exhausted")


def action_inventory(pages):
    unique = {}
    for page in pages:
        actions = page.get("corporate_actions")
        if not isinstance(actions, dict):
            raise ValueError("Company-action payload lacks its structured inventory")
        for kind, items in actions.items():
            if not isinstance(items, list):
                raise ValueError("Invalid company-action category")
            for item in items:
                if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
                    raise ValueError("Company-action record lacks an explicit identity")
                key = kind, item["id"]
                if key in unique and unique[key]["source_record"] != item:
                    raise ValueError("Same event identity has contradictory provider terms")
                unique[key] = {"category": kind, "event_id": item["id"], "source_record": item,
                               "historical_known_at": None, "cash_available_session": None,
                               "ready_for_simulation": False}
    return list(unique.values())


def collect(output, *, plan_path=PLAN):
    if output.exists():
        raise FileExistsError("Choose a fresh collection directory; saved evidence cannot be overwritten")
    plan = load_plan(plan_path)
    sessions = [TradingSession(pd.Timestamp(s["opens_at"]), pd.Timestamp(s["closes_at"]))
                for s in json.loads(Path(plan["calendar_path"]).read_text())]
    calendar = SavedCalendar(sessions)
    expected = {s.opens_at.tz_convert("America/New_York").normalize().tz_convert("UTC") for s in sessions}
    output.mkdir(parents=True, exist_ok=False)
    write(output / "frozen_plan.json", plan)
    report = {"scope": plan["purpose"], "plan_sha256": digest(plan_path), "calendar_sha256": plan["calendar_sha256"],
              "source_sha256": {p: digest(p) for p in ("backtesting/free_collection.py", "app/broker/research_client.py")},
              "new_purchases_usd": 0, "account_requests": 0, "orders": 0,
              "subscription_changes": 0, "automatic_paid_fallback": False,
              "adjustment": "raw", "feed": "sip", "asof": "-", "probes": [],
              "performance_scored": False, "ready_for_broad_backtest": False,
              "limitations": plan["limitations"]}
    write(output / "report.json", report)
    client = HistoricalResearchClient()
    action_cache, abort = {}, False
    for number, probe in enumerate(plan["probes"], 1):
        folder = output / f"{number:03d}"
        folder.mkdir()
        item = {**probe, "directory": folder.name}
        report["probes"].append(item)
        for resource in ("bars", "actions"):
            if abort:
                item[resource] = {"status": "not_requested_after_access_or_rate_failure"}
                continue
            if resource == "actions" and probe["symbol"] in action_cache:
                item[resource] = {**action_cache[probe["symbol"]], "status": "reused_saved_symbol_event_query"}
                continue
            try:
                pages, metadata = collect_pages(client, resource, probe, folder)
                result = {"pages": metadata}
                if resource == "bars":
                    if any("bars" not in p for p in pages):
                        raise ValueError("Historical response missing bars")
                    frame = raw_candles(pages, probe["symbol"])
                    start, end = pd.Timestamp(probe["start"], tz="UTC"), pd.Timestamp(probe["end_exclusive"], tz="UTC")
                    if not ((frame["timestamp"] >= start) & (frame["timestamp"] < end)).all():
                        raise ValueError("Source returned prices outside the explicit interval")
                    validation = None if frame.empty else validate_candles(frame, config=ValidationConfig(timeframe=TimeFrame.Day), calendar=calendar)
                    observed = set(frame["timestamp"])
                    scheduled = {t for t in expected if start <= t < end}
                    path = folder / "bars.csv"
                    frame.to_csv(path, index=False)
                    result.update(status=("empty_source_response_not_zero_recovery" if frame.empty else
                                          "complete_observed_interval" if observed == scheduled else "unobserved_intervals_need_evidence"),
                                  csv=path.name, sha256=digest(path), rows=len(frame), expected_sessions=len(scheduled),
                                  unobserved_sessions=len(scheduled - observed),
                                  first_bar=None if frame.empty else min(observed).isoformat(),
                                  last_bar=None if frame.empty else max(observed).isoformat(),
                                  unobserved_dates=[t.date().isoformat() for t in sorted(scheduled - observed)],
                                  warnings=[] if validation is None else [asdict(w) for w in validation.warnings],
                                  identity_verified=False, gap_interpretation="Unobserved; not filled, inferred as an IPO/delisting or valued at zero.")
                else:
                    events = action_inventory(pages)
                    write(folder / "event_candidates.json", events)
                    result.update(status="downloaded_evidence_not_certified_complete", count=len(events),
                                  categories=dict(Counter(e["category"] for e in events)),
                                  candidate_sha256=digest(folder / "event_candidates.json"))
                    action_cache[probe["symbol"]] = {"source_directory": folder.name, **result}
                item[resource] = result
            except Exception as exc:
                status = getattr(exc, "status_code", None)
                item[resource] = {"status": "source_gap_no_paid_fallback", "exception": type(exc).__name__,
                                  "http_status": status if isinstance(status, int) else None}
                # Auth/entitlement/rate denial cannot trigger a subscription
                # change, retry storm or repeated denied requests across probes.
                if status in {401, 403, 429}:
                    abort = True
            report["http_attempts"] = client.request_count
            write(output / "report.json", report)
        print(json.dumps({"probe": probe["probe_id"], "bars": item["bars"]["status"],
                          "rows": item["bars"].get("rows"), "actions": item["actions"]["status"]}), flush=True)
    report["summary"] = {"interval_probes": len(report["probes"]),
                         "rows": sum(p["bars"].get("rows", 0) for p in report["probes"]),
                         "bar_statuses": dict(Counter(p["bars"]["status"] for p in report["probes"])),
                         "action_statuses": dict(Counter(p["actions"]["status"] for p in report["probes"])),
                         "aborted_after_access_or_rate_failure": abort}
    report["http_attempts"] = client.request_count
    write(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = collect(args.output)
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()

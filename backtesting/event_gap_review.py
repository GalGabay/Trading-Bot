"""Offline review of collected history against independent company evidence.

Observed vendor-label translations are journaled without changing prices.
Missing API events stay explicit; no cash/stock outcome is invented and no
unsupported corporate action is admitted to strategy scoring.
"""

import argparse
from collections import Counter
from datetime import date, timedelta
import json
from pathlib import Path
import re

import pandas as pd
from alpaca.data.timeframe import TimeFrame

from app.data.market_calendar import TradingSession
from app.data.market_data import ValidationConfig, validate_candles
from backtesting.cohort_audit import SavedCalendar, checked_file, digest, source_text
from backtesting.free_collection import PLAN, action_inventory, load_plan, raw_candles, write

REVIEW = Path("docs/free_collection_event_review.json")


def review_gaps(output, *, review_path=REVIEW):
    if output.exists():
        raise FileExistsError("Choose a fresh offline review directory")
    review = json.loads(review_path.read_text(encoding="utf-8"))
    root = Path(review["collection_root"])
    if digest(root / "report.json") != review["collection_report_sha256"]:
        raise ValueError("Original collection report changed")
    report = json.loads((root / "report.json").read_text(encoding="utf-8"))
    plan = load_plan(PLAN)
    if digest(PLAN) != report["plan_sha256"] or plan != json.loads((root / "frozen_plan.json").read_text(encoding="utf-8")):
        raise ValueError("Collection differs from its frozen protocol")
    archived = root / "executed_collector.py"
    if digest(archived) != report["source_sha256"]["backtesting/free_collection.py"]:
        raise ValueError("Archived executed collector does not match the original execution hash")
    paths = {key: checked_file(Path.cwd(), entry) for key, entry in review["sources"].items()}
    texts = {key: source_text(path) for key, path in paths.items()}
    for check in review["checks"]:
        if not all(term in texts[check["source_id"]] for term in check["terms"]):
            raise ValueError("Primary evidence does not corroborate the reviewed event facts")
    sessions = [TradingSession(pd.Timestamp(r["opens_at"]), pd.Timestamp(r["closes_at"]))
                for r in json.loads(Path(plan["calendar_path"]).read_text())]
    calendar = SavedCalendar(sessions)
    dates = {s.opens_at.tz_convert("America/New_York").normalize().tz_convert("UTC") for s in sessions}
    probes, frames, events, source_queries = {}, {}, {}, set()
    for probe in report["probes"]:
        key = probe["probe_id"]
        probes[key] = probe
        folder = root / probe["directory"]
        # Preserve the original empty-response finding; no network is needed
        # to correctly inventory BBBYQ as empty instead of as a price failure.
        pages = []
        if probe["bars"].get("pages"):
            for entry in probe["bars"]["pages"]:
                pages.append(json.loads(checked_file(folder, {"path": entry["file"], "sha256": entry["sha256"]}).read_text()))
        else:
            original = folder / "bars_1.json"
            if not original.exists() or key != "bed_bath_otc":
                raise ValueError("Unreviewed failed-price payload cannot enter the analysis")
            page = json.loads(original.read_text())
            if page.get("bars") not in ({}, None) or page.get("next_page_token") is not None:
                raise ValueError("Expected the reviewed empty OTC response")
            pages.append(page)
        frame = raw_candles(pages, probe["symbol"])
        start, end = pd.Timestamp(probe["start"], tz="UTC"), pd.Timestamp(probe["end_exclusive"], tz="UTC")
        if not ((frame["timestamp"] >= start) & (frame["timestamp"] < end)).all():
            raise ValueError("Observed candles exceed the declared alias interval")
        if not frame.empty:
            validate_candles(frame, config=ValidationConfig(timeframe=TimeFrame.Day), calendar=calendar)
        frames[key] = frame
        action_folder = root / probe["actions"].get("source_directory", probe["directory"])
        source_queries.add(str(action_folder))
        pages = [json.loads(checked_file(action_folder, {"path": p["file"], "sha256": p["sha256"]}).read_text())
                 for p in probe["actions"]["pages"]]
        events[key] = action_inventory(pages)
        candidate_path = action_folder / "event_candidates.json"
        if digest(candidate_path) != probe["actions"]["candidate_sha256"]:
            raise ValueError("Saved event candidate checksum changed")
    output.mkdir(parents=True, exist_ok=False)
    # One real candle, supplied under the vendor's old ticker on the official
    # rename date. Identity evidence permits this recorded label translation.
    boundary_path = checked_file(Path.cwd(), review["boundary_response"])
    boundary = raw_candles([json.loads(boundary_path.read_text())], "CBG")
    if len(boundary) != 1 or boundary.iloc[0]["timestamp"].date().isoformat() != "2018-03-19":
        raise ValueError("Boundary correction requires the one actual observed rename-session candle")
    if not all(t in texts["cbre_2018_announcement"] for t in ("March 19", "CBG", "CBRE")):
        raise ValueError("Primary rename evidence is missing")
    boundary["source_symbol"] = "CBG"
    boundary["symbol"] = "CBRE"
    cbre_new = frames["cbre_new"].copy()
    cbre_new["source_symbol"] = cbre_new["symbol"]
    corrected = pd.concat([boundary, cbre_new], ignore_index=True).sort_values("timestamp", ignore_index=True)
    validate_candles(corrected, config=ValidationConfig(timeframe=TimeFrame.Day), calendar=calendar)
    expected = {d for d in dates if pd.Timestamp("2018-03-19", tz="UTC") <= d < pd.Timestamp("2024-01-01", tz="UTC")}
    if set(corrected["timestamp"]) != expected:
        raise ValueError("Observed CBRE boundary candle did not close the exact calendar gap")
    translation = {"date": "2018-03-19", "source_symbol": "CBG", "market_alias": "CBRE",
                   "source_sha256": digest(boundary_path), "primary_rename_source_sha256": digest(paths["cbre_2018_announcement"]),
                   "prices_or_volume_changed": False, "candle_fabricated": False}
    write(output / "cbre_vendor_label_translation.json", translation)
    corrected.to_csv(output / "cbre_new_reviewed.csv", index=False)
    streams = {}
    for name, old, new, instrument in (("ua_class_a", "ua_class_a_old", "ua_class_a_new", "COHORT-2016-0454"),
                                        ("ua_class_c", "ua_class_c_old", "ua_class_c_new", "COHORT-2016-0455"),
                                        ("cbre", "cbre_old", "cbre_new", "COHORT-2016-0088")):
        first, second = frames[old].copy(), corrected.copy() if name == "cbre" else frames[new].copy()
        first["source_symbol"] = first["symbol"]
        if "source_symbol" not in second:
            second["source_symbol"] = second["symbol"]
        stream = pd.concat([first, second], ignore_index=True).sort_values("timestamp", ignore_index=True)
        stream["instrument_id"] = instrument
        if stream["timestamp"].duplicated().any():
            raise ValueError("Alias stream contains overlapping/repeated candles")
        validate_candles(stream, config=ValidationConfig(timeframe=TimeFrame.Day), calendar=calendar)
        beginning = "2016-04-08" if name == "ua_class_c" else "2016-01-01"
        expected = {d for d in dates if pd.Timestamp(beginning, tz="UTC") <= d < pd.Timestamp("2024-01-01", tz="UTC")}
        if set(stream["timestamp"]) != expected:
            raise ValueError("Alias-stream observations do not match the independently reviewed lifetime")
        path = output / f"{name}_observed_alias_stream.csv"
        stream.to_csv(path, index=False)
        streams[name] = {"rows": len(stream), "file": path.name, "sha256": digest(path),
                         "first_bar": stream.iloc[0]["timestamp"].isoformat(),
                         "missing_observations_in_reviewed_interval": 0, "ready_for_simulation": False}
    # Explain genuine pre-listing/non-Nasdaq periods using independent evidence.
    uc = frames["ua_class_c_old"]
    expected_uc = {d for d in dates if pd.Timestamp("2016-01-01", tz="UTC") <= d < pd.Timestamp("2016-12-07", tz="UTC")}
    uc_gap = expected_uc - set(uc["timestamp"])
    if len(uc_gap) != 66 or not all(d < pd.Timestamp("2016-04-08", tz="UTC") for d in uc_gap):
        raise ValueError("Class C gap is not exactly the sourced pre-issuance interval")
    bbb = frames["bed_bath_listed"]
    before_suspension = {d for d in dates if d < pd.Timestamp("2023-05-03", tz="UTC")}
    if set(bbb["timestamp"]) != before_suspension or not frames["bed_bath_otc"].empty:
        raise ValueError("Bankruptcy coverage differs from the reviewed exchange/OTC evidence")
    comparisons = []
    for required in review["expected_events"]:
        matches = []
        for event in events[required["probe"]]:
            if event["category"] not in required["categories"]:
                continue
            record = event["source_record"]
            # A process-only name-change row is a candidate, not proof of its
            # effective date or public availability.
            effective = record.get("ex_date") or record.get("effective_date")
            if effective == required["date"]:
                matches.append(event["event_id"])
        comparisons.append({**required, "provider_matching_ids": matches,
                            "provider_event_present": bool(matches),
                            "primary_evidence_preserved": True, "execution_ready": False})
    publication = []
    for item in review["publication_reviews"]:
        text = texts[item["evidence_source"]]
        day = date.fromisoformat(item["publication_date"])
        if item["date_source"] == "SEC_index":
            match = re.search(r"Filing Date\s+(\d{4}-\d{2}-\d{2})", text)
            if not match or match[1] != item["publication_date"]:
                raise ValueError("SEC index publication date does not match review")
        elif not (f"{day.strftime('%B')} {day.day}, {day.year}" in text or
                  f"{day.strftime('%b')} {day.day}, {day.year}" in text or
                  f"{day.strftime('%b')} {day.day:02d}, {day.year}" in text):
            raise ValueError("Issuer release does not corroborate the dated publication")
        bound = pd.Timestamp(day + timedelta(days=2), tz="UTC")
        available = next(s.opens_at for s in sessions if s.opens_at >= bound)
        effective_open = next(s.opens_at for s in sessions if s.opens_at.tz_convert("America/New_York").date().isoformat() == item["effective_date"])
        publication.append({**item, "conservative_known_at": available.isoformat(),
                            "known_by_effective_open_under_convention": available <= effective_open,
                            "exact_historical_release_time_verified": False,
                            "cash_availability_verified": False})
    quarantined, unique_events = [], {}
    for probe_id, items in events.items():
        probe = probes[probe_id]
        for event in items:
            key = event["category"], event["event_id"]
            if key in unique_events and unique_events[key]["source_record"] != event["source_record"]:
                raise ValueError("Same event ID has contradictory terms across ticker queries")
            unique_events[key] = event
            record = event["source_record"]
            effective = record.get("ex_date") or record.get("effective_date")
            if effective and not probe["start"] <= effective < probe["end_exclusive"]:
                quarantined.append({"probe_id": probe_id, **event,
                                    "reason": "Effective/ex-date outside this alias price interval; do not attach by queried ticker alone."})
    result = {"scope": "offline_source_and_gap_resolution_not_strategy_scoring",
              "collection_report_sha256": digest(root / "report.json"), "review_sha256": digest(review_path),
              "execution_sha256": {p: digest(p) for p in ("backtesting/event_gap_review.py", "backtesting/free_collection.py")},
              "source_sha256": {key: digest(p) for key, p in paths.items()},
              "collected_candle_rows": sum(len(frame) for frame in frames.values()),
              "additional_observed_boundary_candles": len(boundary),
              "data_http_attempts": report["http_attempts"] + 1, "unique_symbol_action_queries": len(source_queries),
              "unique_provider_events": len(unique_events), "provider_categories": dict(Counter(e["category"] for e in unique_events.values())),
              "alias_streams": streams, "resolved_observation_issues": {
                  "ua_class_c_pre_issuance_sessions": len(uc_gap), "cbre_real_boundary_candle_recovered": 1,
                  "bbby_nasdaq_suspension_boundary": "2023-05-03", "bbby_otc_source_status": "genuine_empty_response_still_blocks_valuation"},
              "required_event_checks": comparisons, "publication_reviews": publication,
              "required_events_missing_from_provider": sum(not c["provider_event_present"] for c in comparisons),
              "quarantined_event_references": len(quarantined),
              "new_purchases_usd": 0, "subscription_changes": 0, "account_requests": 0, "orders": 0,
              "offline_review_http_requests": 0, "performance_scored": False, "ready_for_broad_backtest": False,
              "remaining_blockers": [
                  "Primary-confirmed events omitted from API; empty responses do not certify event-free histories.",
                  "UA class distributions, Alcoa/Arconic and Fox distributions require supported share/claim accounting or explicitly reviewed warmup boundaries.",
                  "Mixed cash/stock acquisitions and fractional claims lack an audited adapter.",
                  "WFM/ATVI cash rights need explicit conversion/payment/valuation conventions; payable date is not broker cash availability.",
                  "BBBY OTC quotes and suspension-to-cancellation valuation remain unsupported; no stale mark or assumed early zero.",
                  "Dividend publication and payment evidence require review over the full requested period.",
                  "A representative 24-interval collection is not complete coverage of all 506 retained stocks."]}
    write(output / "event_quarantine.json", quarantined)
    write(output / "provider_event_inventory.json", list(unique_events.values()))
    write(output / "report.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = review_gaps(args.output)
    print(json.dumps({key: report[key] for key in ("collected_candle_rows", "additional_observed_boundary_candles",
                                                 "data_http_attempts", "unique_symbol_action_queries", "unique_provider_events",
                                                 "resolved_observation_issues", "required_events_missing_from_provider",
                                                 "ready_for_broad_backtest")}, indent=2))


if __name__ == "__main__":
    main()

"""Review frozen partial histories against separately recorded primary facts.

No price edits, successor stitching, corporate-action booking or network.
Dates in the output are economic anchors, not invented delivery timestamps.
"""

import argparse
from collections import Counter
import csv
from datetime import date
import json
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from backtesting.broad_collection import pin
from backtesting.cohort_audit import checked_file
from backtesting.pilot_readiness_review import offline_only, write_csv, write_json

FACTS = Path("docs/broad_history_review_facts.json")


def assess(target, frame, fact):
    if fact["snapshot_alias"] != target["snapshot_alias"] or fact.get("execution_ready") is not False:
        raise ValueError("Case identity/readiness changed")
    stamp = fact["event_date"]
    if stamp is not None:
        date.fromisoformat(stamp)
        if not "2016-01-01" <= stamp < "2024-01-01":
            raise ValueError("Case economic anchor outside development window")
    url = fact["primary_source_url"]
    if url is not None and (urlparse(url).scheme != "https" or not urlparse(url).hostname):
        raise ValueError("Evidence reference must be an explicit HTTPS source")
    stamps = pd.to_datetime(frame["timestamp"], utc=True)
    sessions = stamps.dt.tz_convert("America/New_York").dt.date.astype(str)
    if not sessions.between("2016-01-01", "2023-12-31").all():
        raise ValueError("Observed candles outside development window")
    if frame.empty or not stamps.is_monotonic_increasing or stamps.duplicated().any():
        raise ValueError("Expected nonempty ordered unique observations")
    # A count AFTER the economic anchor is evidence triage, not an asserted
    # last trading day. Merger-day market/ownership timing remains separate.
    later = None if stamp is None else int((sessions > stamp).sum())
    conflict = bool(fact["unsegmented_identity_conflict"])
    if conflict and not later:
        raise ValueError("Declared cross-identity history lacks post-event observations")
    tasks = ["Archive/check the original primary document and dated class identity",
             "Reconcile all applicable events and historical availability",
             "Record cash/share/fractional delivery and source every needed valuation branch"]
    if conflict:
        tasks.insert(0, "Quarantine the unsegmented ticker stream; construct dated issuer/class segments from independent evidence")
    if fact["next_alias_candidate"]:
        tasks.append("Exact successor/alias quote scope requires a new bounded acquisition; no current request authorized here")
    return dict(instrument_id=target["instrument_id"], snapshot_alias=target["snapshot_alias"],
        classification=fact["classification"], economic_event_date=stamp,
        observed_first_session=sessions.min(), observed_last_session=sessions.max(),
        observed_rows=len(frame), observed_rows_after_economic_anchor=later,
        unsegmented_identity_conflict=conflict, original_candles_modified=False,
        next_alias_candidate=fact["next_alias_candidate"], cash_per_original_share=fact["cash_per_original_share"],
        share_ratio=fact["share_ratio"], primary_source_url=url, source_access=fact["source_access"],
        review_summary=fact["summary"], required_work=json.dumps(tasks),
        strict_identity_certified=False, full_action_history_certified=False,
        actual_delivery_time_known=False, execution_ready=False)


def review(output):
    if output.exists() or not output.resolve().is_relative_to(Path.cwd().resolve()):
        raise ValueError("Choose a fresh review directory inside the workspace")
    facts = json.loads(FACTS.read_text(encoding="utf-8"))
    for key in ("protocol", "qualification", "evidence"):
        checked_file(Path.cwd(), facts[key])
    protocol = json.loads(checked_file(Path.cwd(), facts["protocol"]).read_text(encoding="utf-8"))
    target_path = checked_file(Path.cwd(), protocol["input"])
    targets = json.loads(target_path.read_text(encoding="utf-8"))
    partial = [t for t in targets if not t["full_calendar_observed"]]
    by_alias = {f["snapshot_alias"]: f for f in facts["facts"]}
    if len(targets) != 100 or len(by_alias) != 17 or {t["snapshot_alias"] for t in partial} != set(by_alias):
        raise ValueError("Retain the exact 17 partial cases and all 100 selected identities")
    public = facts["public_review"]
    if public["search_queries"] > protocol["max_search_queries"] or public["page_opens_dispatched"] > protocol["max_open_pages"] or public["additional_opens_after_barrier_observed"]:
        raise ValueError("Public review exceeded its bounded scope")
    inventory = Path("docs/research_data/broad_100_collected_inventory.csv")
    # The previous evidence summary pins the original qualification CSV.
    evidence = json.loads(checked_file(Path.cwd(), facts["evidence"]).read_text(encoding="utf-8"))
    original_csv = checked_file(Path.cwd(), evidence["qualification_csv"])
    if inventory.read_bytes() != original_csv.read_bytes():
        raise ValueError("Tracked qualification differs from original pinned evidence")
    with inventory.open(encoding="utf-8", newline="") as handle:
        rows = {r["instrument_id"]: r for r in csv.DictReader(handle)}
    cases, source_pins = [], {}
    for target in partial:
        row = rows[target["instrument_id"]]
        path = checked_file(Path.cwd(), dict(path=row["observation_csv"], sha256=row["observation_sha256"]))
        source_pins[row["observation_csv"]] = row["observation_sha256"]
        cases.append(assess(target, pd.read_csv(path), by_alias[target["snapshot_alias"]]))
    output.mkdir(parents=True)
    write_json(output / "cases.json", cases)
    write_csv(output / "cases.csv", cases)
    result = dict(date="2026-10-29", facts=pin(FACTS), protocol=facts["protocol"],
        execution=pin("backtesting/broad_history_review.py"), source_sha256=source_pins,
        selected_count=100, partial_cases_reviewed=len(cases),
        classifications=dict(Counter(c["classification"] for c in cases)),
        unsegmented_identity_conflicts=[c["snapshot_alias"] for c in cases if c["unsegmented_identity_conflict"]],
        primary_reference_not_established=[c["snapshot_alias"] for c in cases if c["primary_source_url"] is None],
        public_review=public, original_candles_modified=False, new_stocks_admitted=0,
        new_price_requests=0, broker_requests=0, orders=0, purchases_usd=0, strategy_runs=0,
        performance_authorized=False, ready_for_broad_scoring=False,
        cases=pin(output / "cases.csv"),
        limitation="Evidence review and discovery only. Full source capture, lifetime segmentation, event ownership, delivery terms and successor prices still gate execution; no alias stitching or strategy run occurred.")
    write_json(output / "report.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    with offline_only():
        print(json.dumps(review(parser.parse_args().output), indent=2))

"""Prepare the separately approved exploratory subset, offline and without fills.

Reuse the original prices and approved diagnostic plans without weakening the
fixed-100 loader or certifying vendor assumptions as independently verified.
Recheck all current event gates and each selected stream's full calendar
coverage. These outputs are research inputs, not an execution universe.
"""

import argparse
from collections import Counter
import csv
from dataclasses import asdict
import json
from pathlib import Path

import pandas as pd
from alpaca.data.timeframe import TimeFrame

from app.data.market_calendar import TradingSession
from app.data.market_data import ValidationConfig, validate_candles
from backtesting.broad_collection import pin
from backtesting.cohort_audit import SavedCalendar, checked_file
from backtesting.diagnostic_preflight import assess, prepare as full_preflight
from backtesting.pilot_readiness_review import offline_only, write_csv, write_json

APPROVAL = Path("docs/faster_research_owner_approval_2026-10-30.json")


def load_approved(approval_path):
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    if (approval.get("owner_approved") is not True or
            approval.get("scope") != "separate_availability_selected_76_root_exploratory_comparison" or
            approval.get("selection_bias_acknowledged") is not True or
            approval.get("performance_authorized_conditionally") is not True or
            approval.get("max_strategy_attempts") != 24 or
            approval.get("original_100_protocol_modified") is not False or
            any(approval.get(k) is not False for k in ("paper_authorized", "broker_requests_authorized",
                "heldout_2024_2025_access", "unknown_economic_facts_may_be_fabricated")) or
            approval.get("purchases_usd") != 0):
        raise ValueError("Require the recorded, conditional approval for this separate research scope")
    review = json.loads(checked_file(Path.cwd(), approval["review_context"]).read_text(encoding="utf-8"))
    if approval["proposal"] != review["proposal"] or approval["acceptance"] != review["acceptance"]:
        raise ValueError("Approval detached from the presented proposal/acceptance criteria")
    for key in ("review_document", "audit", "inventory", "acceptance", "original_protocol"):
        checked_file(Path.cwd(), review[key])
    proposal = json.loads(checked_file(Path.cwd(), approval["proposal"]).read_text(encoding="utf-8"))
    roots, deferred = proposal["proposed_candidate_root_ids"], proposal["proposed_deferred_root_ids"]
    if (len(roots) != 76 or len(set(roots)) != 76 or len(deferred) != 24 or len(set(deferred)) != 24 or
            set(roots) & set(deferred) or not set(proposal["control_root_ids"]) <= set(roots) or
            proposal["max_strategy_attempts"] != approval["max_strategy_attempts"]):
        raise ValueError("Approved membership, controls or attempt cap changed")
    return approval, proposal


def prepare(output, *, approval_path=APPROVAL):
    if output.exists() or not output.resolve().is_relative_to(Path.cwd().resolve()):
        raise ValueError("Choose a fresh subset-preparation directory inside the workspace")
    approval, proposal = load_approved(approval_path)
    preparation_path = checked_file(Path.cwd(), proposal["original_preparation"])
    original_preflight = json.loads(checked_file(Path.cwd(), proposal["original_preflight"]).read_text(encoding="utf-8"))
    preparation = json.loads(preparation_path.read_text(encoding="utf-8"))
    revision = json.loads(checked_file(Path.cwd(), preparation["revision"]).read_text(encoding="utf-8"))
    spec = json.loads(checked_file(Path.cwd(), revision["spec"]).read_text(encoding="utf-8"))
    candidate = json.loads(checked_file(Path.cwd(), revision["candidate_report"]).read_text(encoding="utf-8"))
    manifest_path = checked_file(Path.cwd(), candidate["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["spec"] != revision["spec"] or spec["roster"] != proposal["roster"]:
        raise ValueError("Candidate manifest detached from approved original reconstruction")
    with checked_file(Path.cwd(), proposal["roster"]).open(encoding="utf-8", newline="") as handle:
        roster = list(csv.DictReader(handle))
    roots = set(proposal["proposed_candidate_root_ids"])
    if ({r["instrument_id"] for r in roster} != roots | set(proposal["proposed_deferred_root_ids"]) or
            manifest["selected_original_ids"] != [r["instrument_id"] for r in roster]):
        raise ValueError("All 100 original members must remain accounted for")
    streams = [s for s in manifest["streams"] if s["root_id"] in roots]
    selected_ids = {s["instrument_id"] for s in streams}
    if ([s["instrument_id"] for s in streams] != proposal["proposed_candidate_stream_ids"] or
            len(selected_ids) != len(streams) or
            {s["instrument_id"] for s in streams if s["role"] == "original_member"} != roots):
        raise ValueError("Subset stream membership or descendant mappings changed")
    for entry in revision["inputs"].values():
        checked_file(Path.cwd(), entry)
    mapping = json.loads(checked_file(Path.cwd(), revision["mapping"]).read_text(encoding="utf-8"))
    terms_path = checked_file(Path.cwd(), original_preflight["terms_review"])
    terms = json.loads(terms_path.read_text(encoding="utf-8"))
    output.mkdir(parents=True)
    # Reuse the existing admission rules, including all evidence and source pins.
    # Its full-100 result must stay blocked; only this separate approved scope is narrowed.
    fresh_full = full_preflight(preparation_path.parent, terms_path, output / "full_preflight")
    if (fresh_full["blockers"] != original_preflight["blockers"] or
            fresh_full["effective_feature_resets"] != original_preflight["effective_feature_resets"]):
        raise ValueError("Original admission changed: review the scope again, do not automatically reselect")
    plans = {}
    for key, filename in (("dividends", "dividend_candidates.json"), ("material", "material_candidates.json"),
            ("actions", "corporate_actions.json"), ("elections", "election_candidates.json")):
        rows = json.loads((preparation_path.parent / filename).read_text(encoding="utf-8"))
        plans[key] = [r for r in rows if r.get("root_id", r.get("instrument_id")) in roots or
            r.get("instrument_id") in selected_ids]
    with (preparation_path.parent / "event_routes.csv").open(encoding="utf-8", newline="") as handle:
        routes = [r for r in csv.DictReader(handle) if r["root_id"] in roots]
    feature_events = [r for r in mapping["unresolved_feature_events"] if r["instrument_id"] in selected_ids]
    gates = assess(plans["material"], plans["dividends"], routes, feature_events, terms,
        spec["membership_not_before"], plans["actions"], plans["elections"])
    if not gates["data_gates_clear"] or gates["blockers"]:
        raise ValueError("Selected subset still has an economic-data blocker; do not run or silently drop it")
    for event in plans["material"]:
        if event["parent_id"] not in selected_ids or any(leg["instrument_id"] not in selected_ids for leg in event["share_legs"]):
            raise ValueError("Subset would detach a held right from its parent/received-security prices")
    sessions = [TradingSession(pd.Timestamp(s["opens_at"]), pd.Timestamp(s["closes_at"])) for s in
        json.loads(checked_file(Path.cwd(), spec["calendar"]).read_text(encoding="utf-8"))]
    calendar = SavedCalendar(sessions)
    scheduled = {s.opens_at.tz_convert("America/New_York").normalize().tz_convert("UTC") for s in sessions}
    price_checks = []
    for stream in streams:
        if not stream["full_observed_interval"] or stream["unavailable_parts"] or stream["unobserved_sessions"]:
            raise ValueError("Selected stream lacks its complete configured observed interval")
        expected = set()
        previous = None
        for part in stream["parts"]:
            start, end = pd.Timestamp(part["start"], tz="UTC"), pd.Timestamp(part["end_exclusive"], tz="UTC")
            if not pd.Timestamp("2016-01-01", tz="UTC") <= start < end <= pd.Timestamp("2024-01-01", tz="UTC"):
                raise ValueError("Only development-period stream intervals may be read")
            if previous is not None and start != previous:
                raise ValueError("Stream parts must remain contiguous")
            previous = end
            expected.update(t for t in scheduled if start <= t < end)
        frame = pd.read_csv(checked_file(Path.cwd(), stream["source"]))
        validation = validate_candles(frame, config=ValidationConfig(timeframe=TimeFrame.Day), calendar=calendar)
        timestamps = pd.to_datetime(frame["timestamp"], utc=True)
        observed = set(timestamps)
        if (len(frame) != stream["rows"] or observed != expected or not timestamps.is_monotonic_increasing or
                set(frame["symbol"]) != {stream["instrument_id"]} or set(frame["instrument_id"]) != {stream["instrument_id"]}):
            raise ValueError(f"{stream['instrument_id']}: changed row count, interval, order or identity")
        price_checks.append(dict(instrument_id=stream["instrument_id"], rows=len(frame), source=stream["source"],
            expected_sessions=len(expected), unobserved_sessions=0, warnings=[asdict(w) for w in validation.warnings]))
    # The frozen strategy also needs its original raw SPY price-only context.
    # Follow the presented comparison's pinned lineage rather than discovering
    # a newer context file or applying any fund cash distributions to its EMA.
    comparison = json.loads(checked_file(Path.cwd(), proposal["original_comparison"]).read_text(encoding="utf-8"))
    small = json.loads(checked_file(Path.cwd(), comparison["frozen_small_proposal"]).read_text(encoding="utf-8"))
    pilot_pins = [p for p in small["inputs"] if p["path"] == "docs/free_data_pilot_proposal.json"]
    if len(pilot_pins) != 1:
        raise ValueError("Require the exact previously reviewed SPY context lineage")
    pilot = json.loads(checked_file(Path.cwd(), pilot_pins[0]).read_text(encoding="utf-8"))
    contexts = [s for s in pilot["streams"] if s.get("symbol") == "SPY" and s["role"] == "context_only"]
    if len(contexts) != 1 or pilot["calendar"] != spec["calendar"] or small["adjustment"] != "raw" or small["feed"] != "sip":
        raise ValueError("Frozen context identity, calendar or raw SIP basis differs")
    context = contexts[0]
    context_frame = pd.read_csv(checked_file(Path.cwd(), context["csv"]))
    context_validation = validate_candles(context_frame, calendar=calendar, config=ValidationConfig(timeframe=TimeFrame.Day))
    context_times = pd.to_datetime(context_frame["timestamp"], utc=True)
    if (set(context_times) != scheduled or len(context_frame) != context["observed_rows"] or
            not context_times.is_monotonic_increasing or set(context_frame["symbol"]) != {"SPY"}):
        raise ValueError("Frozen SPY context has a gap, extra date, changed identity or unordered candles")
    context_check = dict(symbol="SPY", source=context["csv"], rows=len(context_frame), context_only=True,
        raw_price_only_no_dividend_credits=True, lineage=pilot_pins[0],
        unobserved_sessions=0, warnings=[asdict(w) for w in context_validation.warnings])
    with checked_file(Path.cwd(), candidate["event_roles"]).open(encoding="utf-8", newline="") as handle:
        provider = [r for r in csv.DictReader(handle) if r["root_id"] in roots]
    for key, rows in plans.items():
        write_json(output / f"{key}.json", rows)
    write_csv(output / "event_routes.csv", routes)
    write_csv(output / "provider_event_roles.csv", provider)
    write_json(output / "price_checks.json", price_checks)
    write_json(output / "context_check.json", context_check)
    write_json(output / "preflight.json", gates)
    subset_manifest = dict(schema_version=1, purpose="approved_exploratory_diagnostic_inputs_not_an_execution_universe",
        approval=pin(approval_path), proposal=approval["proposal"], original_manifest=pin(manifest_path),
        original_spec=revision["spec"], original_preparation=proposal["original_preparation"],
        selected_original_ids=proposal["proposed_candidate_root_ids"],
        deferred_original_ids=proposal["proposed_deferred_root_ids"],
        streams=streams, context=context_check, calendar=spec["calendar"], membership_not_before=spec["membership_not_before"],
        warmup_is_uninvested=True, effective_feature_resets=gates["effective_feature_resets"],
        material_events=[e for e in spec["material_events"] if e["root_id"] in roots],
        source_selection_bias=proposal["known_bias"], independently_verified_entitlement=False,
        strict_evidence_approved=False, engine_adapter_integrated=False, performance_ready=False,
        paper_authorized=False, purchases_usd=0,
        schedules={key: pin(output / f"{key}.json") for key in plans},
        event_routes=pin(output / "event_routes.csv"), provider_event_roles=pin(output / "provider_event_roles.csv"))
    write_json(output / "input_manifest.json", subset_manifest)
    (output / "executed_preparer.py").write_bytes(Path(__file__).read_bytes())
    report = dict(date="2026-10-30", approval=pin(approval_path), proposal=approval["proposal"],
        original_manifest=pin(manifest_path), original_full_preflight=pin(output / "full_preflight/report.json"),
        original_blocking_rows=len(fresh_full["blockers"]), original_100_protocol_modified=False,
        selected_originals=len(roots), deferred_originals=len(proposal["proposed_deferred_root_ids"]),
        candidate_streams=len(streams), observed_rows=sum(s["rows"] for s in streams),
        context_candles_checked=len(context_frame), context_check=pin(output / "context_check.json"),
        provider_dividends=sum(r["category"] == "cash_dividends" for r in provider),
        plan_row_counts={key: len(rows) for key, rows in plans.items()},
        warning_counts=dict(Counter(w["code"] for s in price_checks for w in s["warnings"])),
        input_validation_complete=True, subset_data_gates_clear=True, subset_step1_inputs_prepared=True,
        step2_integration_complete=False, performance_ready=False, strict_flags_promoted=False,
        unit_tests_run=0, strategy_runs=0, network_requests=0, broker_requests=0, orders=0, purchases_usd=0,
        heldout_2024_2025_files_read=0, execution=pin(Path(__file__)),
        executed_source=pin(output / "executed_preparer.py"),
        output_files=[pin(output / name) for name in ("input_manifest.json", "preflight.json", "price_checks.json",
            "event_routes.csv", "provider_event_roles.csv", "dividends.json", "material.json", "actions.json", "elections.json")],
        limitation="Approved vendor-dependent exploratory inputs; subset preparation is not engine verification or full-100 admission")
    write_json(output / "summary.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval", type=Path, default=APPROVAL)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with offline_only():
        print(json.dumps(prepare(args.output, approval_path=args.approval), indent=2))

"""Reconstruct a candidate 100-member input from pinned observed prices.

Pure aliases share an explicit ID; mergers/children have separate IDs. Original
data is retained. No forward fill, inferred receipt times, orders or scores.
The manifest is deliberately not an accepted HistoricalUniverse/OwnershipSchedule.
"""

import argparse
from collections import Counter
import csv
from dataclasses import asdict
from fractions import Fraction
import json
from pathlib import Path

import pandas as pd
from alpaca.data.timeframe import TimeFrame

from app.data.market_calendar import TradingSession
from app.data.market_data import ValidationConfig, validate_candles
from backtesting.broad_collection import pin
from backtesting.cohort_audit import SavedCalendar, checked_file, source_text
from backtesting.free_collection import action_inventory, raw_candles
from backtesting.pilot_qualification import compare_bars
from backtesting.pilot_readiness_review import offline_only, write_csv, write_json

SPEC = Path("docs/broad_historical_input_spec.json")
SUCCESSORS = Path("data/reports/broad_successor_collection_v1")
PUBLIC = Path("data/reports/broad_input_public_sources_v1")


def classify_action(kind, record, source_symbol):
    """A buyer's acquisition is not a cash/share credit to buyer shareholders."""
    if kind in {"cash_mergers", "stock_mergers", "stock_and_cash_mergers"}:
        if record.get("acquiree_symbol")==source_symbol and record.get("acquirer_symbol")==source_symbol:
            return "same_symbol_reorganization_requires_review"
        if record.get("acquiree_symbol") == source_symbol:
            return "holder_outcome_candidate_requires_terms"
        if record.get("acquirer_symbol") == source_symbol:
            return "acquirer_context_only_no_holder_credit"
        return "other_security_unattached"
    if kind == "name_changes":
        if record.get("old_symbol") == source_symbol:
            return "outgoing_alias_requires_identity_review"
        if record.get("new_symbol") == source_symbol:
            return "incoming_alias_requires_identity_review"
        return "other_security_unattached"
    if kind == "spin_offs":
        return "parent_distribution_requires_ownership" if record.get("source_symbol") == source_symbol else "other_security_unattached"
    if kind in {"forward_splits", "reverse_splits"}:
        if record.get("symbol") != source_symbol:
            return "other_security_unattached"
        new, old = Fraction(str(record["new_rate"])), Fraction(str(record["old_rate"]))
        if new <= 0 or old <= 0:
            raise ValueError("Nonpositive split ratio")
        ratio = new / old
        if ratio.denominator != 1:
            return "nonstandard_ratio_requires_primary_economic_review"
        return "provider_split_candidate_not_primary_verified"
    if kind == "cash_dividends":
        return "cash_dividend_candidate_unspendable_without_payable_terms" if record.get("symbol") == source_symbol else "other_security_unattached"
    return "unsupported_category_requires_review"


def build(output):
    if output.exists() or not output.resolve().is_relative_to(Path.cwd().resolve()):
        raise ValueError("Choose a fresh input-package directory within the workspace")
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    for key in ("scope", "roster", "inventory", "prior_evidence", "calendar", "public_queue", "successor_queue"):
        checked_file(Path.cwd(), spec[key])
    if spec["performance_authorized"] or spec["strict_evidence_approved"]:
        raise ValueError("Candidate input cannot promote execution approval")
    prior = json.loads(checked_file(Path.cwd(), spec["prior_evidence"]).read_text(encoding="utf-8"))
    original_inventory = checked_file(Path.cwd(), prior["qualification_csv"])
    if original_inventory.read_bytes() != Path(spec["inventory"]["path"]).read_bytes():
        raise ValueError("Original pinned inventory differs")
    with original_inventory.open(encoding="utf-8", newline="") as handle:
        old_rows = list(csv.DictReader(handle))
    with checked_file(Path.cwd(), spec["roster"]).open(encoding="utf-8", newline="") as handle:
        roster = list(csv.DictReader(handle))
    originals = [s for s in spec["streams"] if s["role"] == "original_member"]
    if (len(originals) != 100 or len({s["instrument_id"] for s in spec["streams"]}) != len(spec["streams"])
            or {s["instrument_id"] for s in originals} != {s["instrument_id"] for s in roster}):
        raise ValueError("Retain all exact100 member IDs; branches need distinct IDs")
    report = json.loads((SUCCESSORS / "report.json").read_text(encoding="utf-8"))
    if report["plan"] != spec["successor_queue"]:
        raise ValueError("Successor execution differs from frozen scope")
    supplement_report=None
    if "supplement_queue" in spec:
        checked_file(Path.cwd(),spec["supplement_queue"])
        supplement_path=Path("data/reports/broad_successor_branch_probe_v1/report.json")
        supplement_report=json.loads(supplement_path.read_text(encoding="utf-8"))
        if supplement_report["plan"]!=spec["supplement_queue"] or supplement_report["parent_report"]!=pin(SUCCESSORS/"report.json"):
            raise ValueError("Child probe detached from original cumulative budget")
        parent_attempts=report["attempts"]
        if supplement_report["attempts"][:len(parent_attempts)]!=parent_attempts:
            raise ValueError("Child probe reset original request accounting")
        report["probes"]+=supplement_report["probes"]
        report["attempts"]=supplement_report["attempts"]
    if len(report["probes"])>32 or len(report["attempts"])>192:
        raise ValueError("Step1 cumulative interval/request scope exceeded")
    public = json.loads((PUBLIC / "report.json").read_text(encoding="utf-8"))
    if public["queue_sha256"] != spec["public_queue"]["sha256"]:
        raise ValueError("Public execution differs from frozen scope")
    sessions = [TradingSession(pd.Timestamp(s["opens_at"]),pd.Timestamp(s["closes_at"])) for s in
                json.loads(checked_file(Path.cwd(),spec["calendar"]).read_text(encoding="utf-8"))]
    calendar = SavedCalendar(sessions)
    scheduled = {s.opens_at.tz_convert("America/New_York").normalize().tz_convert("UTC") for s in sessions}
    frames, source_meta, events, pins = {}, {}, {}, {}

    def read_pages(entries):
        values = []
        for entry in entries:
            path = checked_file(Path.cwd(), entry)
            pins[entry["path"]] = entry["sha256"]
            values.append(json.loads(path.read_text(encoding="utf-8")))
        return values

    for row in old_rows:
        path = checked_file(Path.cwd(),dict(path=row["observation_csv"],sha256=row["observation_sha256"]))
        key = "base:"+row["snapshot_alias"]
        frames[key] = pd.read_csv(path)
        source_meta[key] = pin(path)
        pins[row["observation_csv"]] = row["observation_sha256"]
        index = next(i for i,r in enumerate(old_rows,1) if r["instrument_id"]==row["instrument_id"])
        event_path=Path("data/reports/broad_100_collection_v1") / f"{index:03d}" / "event_inventory.json"
        checked_file(Path.cwd(),dict(path=event_path.as_posix(),sha256=row["event_inventory_sha256"]))
        events[key] = json.loads(event_path.read_text(encoding="utf-8"))
        pins[event_path.as_posix()] = row["event_inventory_sha256"]
    probe_inventory = []
    for probe in report["probes"]:
        key = probe["id"]
        item = dict(id=key,symbol=probe["symbol"],rows=0,status=probe["bars"]["status"])
        if probe["bars"]["status"] == "downloaded_candidate":
            pages = read_pages(probe["bars"]["pages"])
            if any("bars" not in p for p in pages):
                raise ValueError("Missing successor bars payload")
            frame = raw_candles(pages,probe["symbol"])
            stamps = pd.to_datetime(frame["timestamp"],utc=True)
            start,end=pd.Timestamp(probe["start"],tz="UTC"),pd.Timestamp(probe["end_exclusive"],tz="UTC")
            if not ((stamps>=start)&(stamps<end)).all():
                raise ValueError("Successor response outside exact interval")
            if not frame.empty:
                validate_candles(frame,config=ValidationConfig(timeframe=TimeFrame.Day),calendar=calendar)
            frames[key]=frame
            source_meta[key]=dict(payloads=probe["bars"]["pages"],symbol=probe["symbol"])
            item.update(rows=len(frame),status="empty_observed_source" if frame.empty else "validated_observations")
        if probe["actions"]["status"] == "downloaded_candidate":
            events[key]=[dict(query_symbol=probe["symbol"],**e) for e in action_inventory(read_pages(probe["actions"]["pages"]))]
        probe_inventory.append(item)
    source_status = []
    public_by_id={a["id"]:a for a in public["attempts"]}
    public_plan=json.loads(checked_file(Path.cwd(),spec["public_queue"]).read_text(encoding="utf-8"))
    for source in public_plan["documents"]:
        saved=public_by_id.get(source["id"],{})
        row=dict(id=source["id"],url=source["url"],status=saved.get("status","not_requested_after_stop"),content_terms_checked=False)
        if saved.get("status")=="saved_unreviewed":
            path=checked_file(Path.cwd(),dict(path=(PUBLIC/saved["file"]).as_posix(),sha256=saved["sha256"]))
            if path.suffix==".html":
                text=source_text(path).casefold()
                row["content_terms_checked"]=all(term.casefold() in text for term in source["required_terms"])
            row["source"]=pin(path)
        source_status.append(row)
    captured={s["id"] for s in source_status if s["content_terms_checked"]}
    output.mkdir(parents=True)
    (output/"streams").mkdir()
    (output/"frozen_spec.json").write_bytes(SPEC.read_bytes())
    (output/"executed_builder.py").write_bytes(Path(__file__).read_bytes())
    streams, action_rows, quarantine = [], [], []
    for number, stream in enumerate(spec["streams"],1):
        chunks, expected, incomplete, part_rows = [],set(),[],[]
        for part in stream["parts"]:
            key=part["source_key"]
            start,end=pd.Timestamp(part["start"],tz="UTC"),pd.Timestamp(part["end_exclusive"],tz="UTC")
            expected.update(t for t in scheduled if start<=t<end)
            if key not in frames:
                incomplete.append(key); continue
            raw=frames[key].copy()
            if not raw.empty:
                validate_candles(raw,config=ValidationConfig(timeframe=TimeFrame.Day),calendar=calendar)
            stamps=pd.to_datetime(raw["timestamp"],utc=True)
            selected=raw.loc[(stamps>=start)&(stamps<end)].copy()
            excluded=raw.loc[~((stamps>=start)&(stamps<end))]
            part_rows.append(dict(**part,observed_rows=len(selected),source=source_meta[key],
                                  source_terms_captured=bool(part["primary_source_ids"]) and set(part["primary_source_ids"])<=captured))
            if not excluded.empty:
                quarantine.append(dict(instrument_id=stream["instrument_id"],source_key=key,
                    outside_selected_interval_rows=len(excluded),reason="Retained in original source; not attached to this specific issuer/class interval"))
            if selected.empty:
                incomplete.append(key); continue
            selected["source_symbol"]=selected["source_symbol"] if "source_symbol" in selected else selected["symbol"]
            selected["source_key"]=key
            selected["symbol"]=stream["instrument_id"]
            selected["instrument_id"]=stream["instrument_id"]
            selected["timestamp"]=pd.to_datetime(selected["timestamp"],utc=True)
            chunks.append(selected)
            for event in events.get(key,[]):
                record=event["source_record"]
                day=record.get("ex_date") or record.get("effective_date") or record.get("process_date")
                if day is None or not part["start"] <= day < part["end_exclusive"]:
                    continue
                role=classify_action(event["category"],record,event["query_symbol"])
                action_rows.append(dict(instrument_id=stream["instrument_id"],root_id=stream["root_id"],
                    event_id=event["event_id"],category=event["category"],source_key=key,day=day,
                    query_symbol=event["query_symbol"],role=role,record=json.dumps(record,sort_keys=True),
                    provider_payable_date=record.get("payable_date") or record.get("pay_date") or record.get("payment_date"),
                    provider_declaration_date=record.get("declaration_date") or record.get("announcement_date"),
                    ready_for_execution=False,actual_cash_or_share_delivery=None))
        item=dict(stream,parts=part_rows,rows=0,full_observed_interval=False,unobserved_sessions=len(expected),
                  unavailable_parts=incomplete,source_terms_captured=False,ready_for_execution=False)
        if chunks:
            frame=pd.concat(chunks,ignore_index=True)
            # Reject overlaps before sorting; no duplicate candle is silently
            # selected merely because it gives a nicer price history.
            validation=validate_candles(frame,config=ValidationConfig(timeframe=TimeFrame.Day),calendar=calendar)
            frame=frame.sort_values("timestamp",ignore_index=True)
            observed=set(frame["timestamp"])
            missing=sorted(expected-observed)
            path=output/"streams"/f"{number:03d}.csv"
            frame.to_csv(path,index=False,lineterminator="\n")
            compare_bars(pd.read_csv(path),frame)
            item.update(rows=len(frame),full_observed_interval=not missing and not incomplete,
                unobserved_sessions=len(missing),unobserved_dates=[t.date().isoformat() for t in missing],
                first_session=frame["timestamp"].min().date().isoformat(),last_session=frame["timestamp"].max().date().isoformat(),
                source=pin(path),warnings=[asdict(w) for w in validation.warnings],
                source_terms_captured=bool(part_rows) and all(p["source_terms_captured"] for p in part_rows))
        streams.append(item)
    # Deduplicate identical event IDs only within a specific canonical security.
    unique={}
    for event in action_rows:
        key=event["instrument_id"],event["category"],event["event_id"]
        if key in unique and unique[key]["record"] != event["record"]:
            raise ValueError("Contradictory provider terms for the same security/event")
        unique[key]=event
    action_rows=list(unique.values())
    declared_ids={s["instrument_id"] for s in streams}
    for event in spec["material_events"]:
        if event["parent_id"] not in declared_ids or event["root_id"] not in {s["instrument_id"] for s in originals}:
            raise ValueError("Material event consumes an undeclared issuer/class")
        for leg in event["share_legs"]:
            if leg["instrument_id"] not in declared_ids or Fraction(leg["shares_per_parent"])<=0:
                raise ValueError("Material event creates an undeclared/nonpositive share leg")
        if event["execution_ready"] or event["prior_close_entitlement_verified"] or event["actual_delivery_at"] is not None:
            raise ValueError("Candidate material event cannot invent execution verification")
    unresolved=[]
    for event in action_rows:
        if event["role"] in {"nonstandard_ratio_requires_primary_economic_review","same_symbol_reorganization_requires_review","unsupported_category_requires_review"}:
            unresolved.append(dict(instrument_id=event["instrument_id"],event_id=event["event_id"],
                                   category=event["category"],day=event["day"],reason=event["role"],execution_ready=False))
    for event in spec["material_events"]:
        unresolved.append(dict(instrument_id=event["parent_id"],event_id=event["id"],category=event["kind"],
            day=event["economic_date"],reason="Primary terms/entitlement/delivery/fractions remain unapproved; candidate outcomes do not create spendable cash",execution_ready=False))
    manifest=dict(schema_version=1,purpose="candidate_input_not_an_execution_universe",spec=pin(SPEC),
        selected_original_ids=[s["instrument_id"] for s in originals],streams=streams,
        material_events=spec["material_events"],source_capture=source_status,
        membership_not_before=spec["membership_not_before"],warmup_is_uninvested=True,
        readiness_blockers=spec["readiness_blockers"],performance_authorized=False,strict_evidence_approved=False,
        max_total_research_exposure_selected=.70,paper_authorized=False)
    write_json(output/"input_manifest.json",manifest)
    write_csv(output/"stream_inventory.csv",[{k:v if not isinstance(v,(dict,list)) else json.dumps(v) for k,v in s.items()} for s in streams])
    write_csv(output/"provider_event_roles.csv",action_rows)
    write_csv(output/"preserved_outside_interval_rows.csv",quarantine)
    write_csv(output/"successor_probe_inventory.csv",probe_inventory)
    write_json(output/"source_capture.json",source_status)
    write_csv(output/"unresolved_events.csv",unresolved)
    roots=[s for s in streams if s["role"]=="original_member"]
    result=dict(date="2026-10-29",spec=pin(SPEC),execution=pin("backtesting/historical_input.py"),
        successor_report=pin(SUCCESSORS/"report.json"),public_report=pin(PUBLIC/"report.json"),source_sha256=pins,
        child_probe_report=None if supplement_report is None else pin(supplement_path),
        selected_originals=len(roots),candidate_streams=len(streams),
        original_streams_with_complete_candidate_intervals=sum(s["full_observed_interval"] for s in roots),
        original_streams_with_gaps=[dict(alias=s["snapshot_alias"],missing=s.get("unobserved_dates",[]),unavailable=s["unavailable_parts"]) for s in roots if not s["full_observed_interval"]],
        successor_probes=len(probe_inventory),successor_observed_rows=sum(s["rows"] for s in probe_inventory),
        empty_successor_probes=[s["id"] for s in probe_inventory if not s["rows"]],
        material_event_records=len(spec["material_events"]),provider_event_role_counts=dict(Counter(e["role"] for e in action_rows)),
        nonstandard_provider_ratios=sum(e["role"]=="nonstandard_ratio_requires_primary_economic_review" for e in action_rows),
        unresolved_material_and_nonstandard_records=len(unresolved),
        provider_dividends_without_payable_date=sum(e["category"]=="cash_dividends" and not e["provider_payable_date"] for e in action_rows),
        provider_dividends_without_declaration_date=sum(e["category"]=="cash_dividends" and not e["provider_declaration_date"] for e in action_rows),
        independently_captured_source_terms=len(captured),public_capture_stopped=public["stopped"],
        historical_data_http_attempts=len(report["attempts"]),
        price_http_attempts=sum(a["resource"]=="bars" for a in report["attempts"]),
        action_http_attempts=sum(a["resource"]=="actions" for a in report["attempts"]),
        public_document_http_attempts=public["network_http_attempts"],
        original_files_modified=False,no_forward_fill=True,original_members_dropped=0,
        performance_ready=False,new_stocks_admitted=0,strict_flags_promoted=False,step1_fully_complete=False,
        orders=0,account_requests=0,purchases_usd=0,strategy_runs=0,unit_tests_run=0,
        manifest=pin(output/"input_manifest.json"),stream_inventory=pin(output/"stream_inventory.csv"),
        event_roles=pin(output/"provider_event_roles.csv"),
        limitation="Dated stream reconstruction is candidate data preparation. Source-capture barriers, quote gaps, unreviewed material events and actual delivery/known-at evidence still block scoring; do not use the manifest as an approved universe.")
    write_json(output/"report.json",result)
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    with offline_only():
        result=build(parser.parse_args().output)
        print(json.dumps({k:v for k,v in result.items() if k!="source_sha256"},indent=2))

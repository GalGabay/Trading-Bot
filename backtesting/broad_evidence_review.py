"""Offline triage of collected histories and remaining company-event evidence.

Large price changes are investigation flags, not automatic split detection.
Provider process/ex dates are never substituted for missing payable dates.
No network, issuer-document download queue, strategy scores or admissions.
"""

from collections import Counter
import csv
import json
from pathlib import Path

import pandas as pd

from backtesting.broad_collection import OUTPUT, PROTOCOL, load_protocol, pin
from backtesting.cohort_audit import checked_file
from backtesting.pilot_readiness_review import offline_only, write_csv, write_json


def review():
    protocol = load_protocol()
    qualification = OUTPUT / "qualification.json"
    summary = json.loads(qualification.read_text(encoding="utf-8"))
    checked_file(Path.cwd(), summary["report"])
    with (OUTPUT / "qualification.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if [r["instrument_id"] for r in rows] != [p["instrument_id"] for p in protocol["queue"]]:
        raise ValueError("Every frozen candidate must remain in order")
    for path, sha in summary["source_sha256"].items():
        checked_file(Path.cwd(), dict(path=path, sha256=sha))
    calendar = json.loads(checked_file(Path.cwd(), protocol["calendar"]).read_text(encoding="utf-8"))
    scheduled = {pd.Timestamp(s["opens_at"]).tz_convert("America/New_York").date().isoformat() for s in calendar}
    targets, action_rows, jumps = [], [], []
    for index, (row, probe) in enumerate(zip(rows, protocol["queue"]), 1):
        folder = OUTPUT / f"{index:03d}"
        target = dict(instrument_id=row["instrument_id"], snapshot_alias=row["snapshot_alias"],
                      source_name=probe["source_name"], full_calendar_observed=row["full_calendar_observed"] == "True",
                      identity_review_required=True, ready_for_broad_scoring=False,
                      provider_events=0, cash_dividends_without_payable_date=0,
                      cash_dividends_without_announcement_date=0, noncash_categories=[],
                      incoming_alias_events_after_membership=[],
                      large_close_moves=0, interior_unobserved_sessions=None, before_first_observation=None,
                      after_last_observation=None, empty_price_response=int(row["rows"]) == 0,
                      saved_primary_event_checks=json.loads(row["saved_primary_event_checks"]))
        if row.get("observation_csv"):
            path = checked_file(Path.cwd(), dict(path=row["observation_csv"], sha256=row["observation_sha256"]))
            frame = pd.read_csv(path)
            stamps = pd.to_datetime(frame["timestamp"], utc=True)
            dates = {t.tz_convert("America/New_York").date().isoformat() for t in stamps}
            if dates:
                first, last = min(dates), max(dates)
                target.update(first_observed_session=first, last_observed_session=last,
                    before_first_observation=sum(day < first for day in scheduled),
                    after_last_observation=sum(day > last for day in scheduled),
                    interior_unobserved_sessions=sum(first <= day <= last and day not in dates for day in scheduled))
                returns = frame["close"].astype(float).pct_change(fill_method=None)
                for n in returns.index[returns.abs() >= .4]:
                    jumps.append(dict(instrument_id=row["instrument_id"], snapshot_alias=row["snapshot_alias"],
                                      session=stamps[n].date().isoformat(), previous_close=float(frame.loc[n-1, "close"]),
                                      close=float(frame.loc[n, "close"]), close_change=float(returns[n]),
                                      interpretation="Review split/distribution/identity/real move; no automatic correction"))
                    target["large_close_moves"] += 1
        inventory_path = folder / "event_inventory.json"
        if row.get("event_inventory_sha256"):
            checked_file(Path.cwd(), dict(path=inventory_path.as_posix(), sha256=row["event_inventory_sha256"]))
            events = json.loads(inventory_path.read_text(encoding="utf-8"))
            target["provider_events"] = len(events)
            target["noncash_categories"] = sorted({e["category"] for e in events} - {"cash_dividends"})
            for event in events:
                record = event["source_record"]
                payable = next((record[k] for k in ("payable_date", "pay_date", "payment_date") if record.get(k)), None)
                announced = next((record[k] for k in ("declaration_date", "announcement_date") if record.get(k)), None)
                cash = event["category"] == "cash_dividends"
                if (event["category"] == "name_changes" and record.get("new_symbol") == probe["snapshot_alias"]
                        and record.get("old_symbol") != probe["snapshot_alias"]
                        and str(record.get("process_date", "")) > "2016-09-30"):
                    target["incoming_alias_events_after_membership"].append(dict(
                        event_id=event["event_id"], old_symbol=record.get("old_symbol"),
                        new_symbol=record.get("new_symbol"), process_date=record.get("process_date"),
                        interpretation="Incoming historical alias requires issuer continuity/reuse review; not automatic identity evidence"))
                target["cash_dividends_without_payable_date"] += int(cash and not payable)
                target["cash_dividends_without_announcement_date"] += int(cash and not announced)
                action_rows.append(dict(instrument_id=row["instrument_id"], snapshot_alias=row["snapshot_alias"],
                    query_symbol=event["query_symbol"], category=event["category"], event_id=event["event_id"],
                    provider_ex_date=record.get("ex_date"), provider_effective_date=record.get("effective_date"),
                    provider_payable_date=payable, provider_announcement_date=announced,
                    terms_independently_verified=False, cash_available_session=None,
                    ready_for_simulation=False, source_record=json.dumps(record, sort_keys=True)))
        tasks = ["Dated class/issuer identity and alias intervals covering the historical holding, not a current ticker match",
                 "Primary company split/distribution/merger history, reconcile provider inventory and omitted events"]
        if not target["full_calendar_observed"]:
            tasks.append("Explain leading/interior/trailing absent sessions; exact successor/alias intervals and terminal economics before further probes")
        if target["noncash_categories"] or target["large_close_moves"]:
            tasks.append("Review material-event terms and large raw-price moves; verify resulting shares, cash, fractions and valuation streams")
        if target["incoming_alias_events_after_membership"]:
            tasks.append("Priority identity quarantine: provider reports another alias entering the sampled ticker after membership; establish continuity or ticker reuse independently")
        if target["cash_dividends_without_payable_date"]:
            tasks.append("Source payable dates and credit policy; process_date/ex_date are not payment dates")
        if target["cash_dividends_without_announcement_date"]:
            tasks.append("Source dated declarations before historical-known-at certification")
        if not target["provider_events"]:
            tasks.append("Explicit no-event evidence or complete event reconstruction; empty inventory proves neither")
        target["remaining_review_tasks"] = tasks
        targets.append(target)
    result = dict(date="2026-10-29", protocol=pin(PROTOCOL), qualification=pin(qualification),
                  qualification_csv=pin(OUTPUT / "qualification.csv"),
                  execution=pin("backtesting/broad_evidence_review.py"),
                  selected_count=len(targets), partial_or_empty_histories=sum(not t["full_calendar_observed"] for t in targets),
                  histories_with_interior_unobserved_sessions=sum(bool(t["interior_unobserved_sessions"]) for t in targets),
                  empty_price_histories=sum(t["empty_price_response"] for t in targets),
                  histories_with_non_cash_events=sum(bool(t["noncash_categories"]) for t in targets),
                  histories_with_incoming_alias_flags=sum(bool(t["incoming_alias_events_after_membership"]) for t in targets),
                  provider_event_categories=dict(Counter(r["category"] for r in action_rows)),
                  cash_dividends_without_payable_date=sum(t["cash_dividends_without_payable_date"] for t in targets),
                  cash_dividends_without_announcement_date=sum(t["cash_dividends_without_announcement_date"] for t in targets),
                  raw_close_moves_at_least_40_percent=len(jumps),
                  public_document_requests=0, additional_price_requests=0, strategy_runs=0,
                  new_stocks_admitted=0, broad_performance_ready=False,
                  limitation="Raw-price move threshold is triage only. Absent observations and provider events cannot establish identity, delisting terms or completeness. Evidence targets are review tasks, not an executable/public acquisition queue.")
    write_json(OUTPUT / "evidence_review_targets.json", targets)
    write_csv(OUTPUT / "action_evidence_inventory.csv", action_rows)
    if jumps:
        write_csv(OUTPUT / "large_raw_price_moves.csv", jumps)
    for name in ("evidence_review_targets.json", "action_evidence_inventory.csv", "large_raw_price_moves.csv"):
        if (OUTPUT / name).exists():
            result[name] = pin(OUTPUT / name)
    write_json(OUTPUT / "evidence_review.json", result)
    return result


if __name__ == "__main__":
    with offline_only():
        print(json.dumps(review(), indent=2))

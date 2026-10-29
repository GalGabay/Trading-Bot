"""Offline structural checks; these checks never certify economic evidence."""

from datetime import date
from fractions import Fraction
from math import isfinite


def validate_ledger(report, limits, *, require_completed=False):
    attempts = report["attempts"]
    if len(attempts) > limits["max_http_attempts"] or len(report["probes"]) > limits["max_probe_intervals"]:
        raise ValueError("Cumulative collection scope exceeded")
    previous = -1
    for number, attempt in enumerate(attempts, 1):
        elapsed = attempt["elapsed_seconds"]
        if (attempt["number"] != number or not isfinite(elapsed) or
                not previous <= elapsed < limits["max_elapsed_minutes"] * 60 or elapsed < 0 or
                attempt["resource"] not in {"bars", "actions"}):
            raise ValueError("Invalid cumulative request numbering/resource/clock")
        previous = elapsed
        if require_completed and not (attempt["state"] == "response_saved" or
                (attempt["state"] == "http_error" and attempt.get("http_status") in {400, 404, 422})):
            raise ValueError("Unfinished or stopped request cannot authorize a continuation")
    if any(report.get(key, 0) != 0 for key in ("orders", "account_requests", "purchases_usd", "strategy_runs")):
        raise ValueError("Historical-only zero-spending scope changed")
    if require_completed and (report.get("completed") is not True or report.get("stop_reason") is not None):
        raise ValueError("Parent collection stopped or unfinished; do not continue")


def validate_streams(spec, roster):
    streams = spec["streams"]
    roots = {s["instrument_id"]: s for s in streams if s["role"] == "original_member"}
    by_id = {s["instrument_id"]: s for s in streams}
    roster_by_id = {r["instrument_id"]: r for r in roster}
    if (len(roots) != 100 or len(by_id) != len(streams) or len(roster) != 100 or
            len(roster_by_id) != 100 or roots.keys() != roster_by_id.keys()):
        raise ValueError("Retain all exact100 member IDs; branches need distinct IDs")
    for stream in streams:
        if stream["root_id"] not in roots or (stream["role"] == "original_member" and
                (stream["root_id"] != stream["instrument_id"] or
                 stream["snapshot_alias"] != roster_by_id[stream["instrument_id"]]["snapshot_alias"])):
            raise ValueError("Stream root or snapshot identity differs from retained roster")
        if stream.get("strict_identity_verified") or stream.get("ready_for_execution"):
            raise ValueError("Candidate stream cannot promote execution verification")
        previous = None
        if not stream["parts"]:
            raise ValueError("Stream needs an explicit dated interval")
        for part in stream["parts"]:
            start, end = date.fromisoformat(part["start"]), date.fromisoformat(part["end_exclusive"])
            if not date(2016, 1, 1) <= start < end <= date(2024, 1, 1):
                raise ValueError("Stream interval outside development dates")
            if previous is not None and start != previous:
                raise ValueError("Stream parts must be ordered and contiguous; no hidden gaps or overlaps")
            previous = end
    events = spec["material_events"]
    if len({e["id"] for e in events}) != len(events):
        raise ValueError("Duplicate material event ID")
    for event in events:
        root, parent = event["root_id"], event["parent_id"]
        if root not in roots or parent not in by_id or by_id[parent]["root_id"] != root:
            raise ValueError("Material event consumes an undeclared or unrelated issuer/class")
        day = date.fromisoformat(event["economic_date"])
        if not date(2016, 1, 1) <= day < date(2024, 1, 1):
            raise ValueError("Material event outside development dates")
        for leg in event["share_legs"]:
            child = leg["instrument_id"]
            if child not in by_id or by_id[child]["root_id"] != root or Fraction(leg["shares_per_parent"]) <= 0:
                raise ValueError("Material event creates an unrelated/nonpositive share leg")
        cash = event["cash_per_parent"]
        if cash is not None and Fraction(str(cash)) < 0:
            raise ValueError("Material event cash must be finite and nonnegative")
        if (event["execution_ready"] or event["prior_close_entitlement_verified"] or
                event["actual_delivery_at"] is not None or event.get("fractional_cash_fixing") is not None):
            raise ValueError("Candidate material event cannot invent execution verification")


def validate_public_report(report, plan):
    documents = plan["documents"]
    attempts = report["attempts"]
    if len({d["id"] for d in documents}) != len(documents):
        raise ValueError("Duplicate public source ID")
    if report["network_http_attempts"] != len(attempts) or len(attempts) > plan["max_http_attempts"]:
        raise ValueError("Public source request accounting differs")
    stopped = False
    for index, attempt in enumerate(attempts):
        if (stopped or index >= len(documents) or attempt["id"] != documents[index]["id"] or
                attempt["url"] != documents[index]["url"]):
            raise ValueError("Public source queue changed or continued after access stop")
        stopped = attempt["status"] == "access_or_rate_barrier"
    if stopped and not report["stopped"]:
        raise ValueError("Public source stop missing from report")

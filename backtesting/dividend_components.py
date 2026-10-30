"""Explicit source-backed dividend reconciliation; never automatic deduplication.

Raw provider rows stay intact. A component contained in an issuer's total has
zero independent entitlement; genuine separate payouts retain their own IDs.
This review does not establish historical availability or broker receipt.
"""

from collections import defaultdict
import json
from pathlib import Path

from backtesting.claim_accounting import number
from backtesting.cohort_audit import checked_file


def validate_review_evidence(review):
    """Check direct evidence and the source pins nested in its JSON facts.

    Nested pins are checked byte for byte, without recursively interpreting
    other review protocols or making requests to their recorded URLs.
    """
    checked_file(Path.cwd(), review["provider_source"])

    def check_nested(value):
        if isinstance(value, dict):
            if "path" in value and "sha256" in value:
                checked_file(Path.cwd(), value)
            for child in value.values():
                check_nested(child)
        elif isinstance(value, list):
            for child in value:
                check_nested(child)

    for source in review["sources"]:
        evidence = checked_file(Path.cwd(), source["evidence"])
        if evidence.suffix.lower() == ".json":
            check_nested(json.loads(evidence.read_text(encoding="utf-8")))


def load_review(path, rows, source_pin):
    review = json.loads(path.read_text(encoding="utf-8"))
    if review.get("provider_source") != source_pin or review.get("schema_version") != 1:
        raise ValueError("Dividend review is detached from the pinned provider source")
    validate_review_evidence(review)
    sources = {}
    for source in review["sources"]:
        if source["id"] in sources:
            raise ValueError("Repeated dividend evidence ID")
        sources[source["id"]] = source
    groups = defaultdict(dict)
    for row in rows:
        if row["category"] == "cash_dividends":
            record = json.loads(row["record"], parse_float=str)
            group = groups[(row["instrument_id"], row["day"])]
            if row["event_id"] in group or record.get("id") != row["event_id"]:
                raise ValueError("Duplicate or inconsistent provider dividend identity")
            group[row["event_id"]] = record
    resolved = {}
    for decision in review["decisions"]:
        key = decision["instrument_id"], decision["ex_date"]
        records = groups.get(key, {})
        ids = decision["provider_event_ids"]
        if len(ids) < 2 or len(set(ids)) != len(ids) or set(ids) != set(records):
            raise ValueError("Dividend decision must cover the complete observed group")
        if not decision["source_ids"] or any(s not in sources for s in decision["source_ids"]):
            raise ValueError("Dividend decision requires pinned reviewed evidence")
        if any(records[i].get("ex_date") != key[1] or
               records[i].get("record_date") != decision["record_date"] or
               records[i].get("payable_date") != decision["payable_date"] for i in ids):
            raise ValueError("Reviewed dividend dates disagree with the provider group")
        kind = decision["kind"]
        if kind == "separate_cash_components":
            rates = decision["rates_by_event_id"]
            if set(rates) != set(ids) or any(number(str(records[i]["rate"]), positive=True) !=
                    number(rates[i], positive=True) for i in ids):
                raise ValueError("Separate dividend components disagree with reviewed nominal rates")
        elif kind == "aggregate_includes_component":
            total, component = decision["total_event_id"], decision["component_event_id"]
            if set(ids) != {total, component} or total == component:
                raise ValueError("Aggregate review requires distinct total and component records")
            if (number(str(records[total]["rate"]), positive=True) != number(decision["total_rate"], positive=True) or
                    number(str(records[component]["rate"]), positive=True) != number(decision["component_rate"], positive=True) or
                    number(decision["total_rate"]) != number(decision["component_rate"]) + number(decision["other_component_rate"], positive=True)):
                raise ValueError("Reviewed total does not reconcile to its components")
        elif kind == "same_cash_payment_representations":
            if (decision["representative_event_id"] not in ids or
                    any(number(str(records[i]["rate"]), positive=True) !=
                        number(decision["cash_rate"], positive=True) for i in ids)):
                raise ValueError("Duplicate payment representations require matching nominal rates")
            if decision.get("ex_date_basis") != "provider_metadata_assumption_not_independently_verified":
                raise ValueError("Payment evidence does not establish an independently verified ex-date")
        elif kind != "cash_stock_election_unresolved":
            raise ValueError("Unsupported dividend review decision")
        for event_id in ids:
            identity = key[0], event_id
            if identity in resolved:
                raise ValueError("Overlapping dividend decisions")
            resolved[identity] = decision
    return resolved


def apply_review(item, decision):
    """Annotate one audit row; unrelated blockers are retained by the caller."""
    if (item["instrument_id"] != decision["instrument_id"] or
            item["event_id"] not in decision["provider_event_ids"] or
            item["provider_record"].get("ex_date") != decision["ex_date"]):
        raise ValueError("Dividend decision does not belong to this audit row")
    item["component_review"] = decision
    kind = decision["kind"]
    represented_by = None
    if kind == "aggregate_includes_component" and item["event_id"] == decision["component_event_id"]:
        represented_by = decision["total_event_id"]
    elif kind == "same_cash_payment_representations" and item["event_id"] != decision["representative_event_id"]:
        represented_by = decision["representative_event_id"]
    if represented_by is not None:
        item.update(status="reviewed_component_in_total_no_independent_right",
                    cash_per_eligible_share="0", modeled_release_at=None,
                    independent_entitlement=False, represented_by_event_id=represented_by)
    elif kind == "cash_stock_election_unresolved":
        item["blockers"].append("reviewed_cash_stock_election_requires_holder_allocation_and_exact_share_terms")
        item.update(cash_per_eligible_share=None, modeled_release_at=None,
                    category="diagnostic_cash_stock_election_candidate")
    item["blockers"].extend(decision.get("remaining_blockers", []))

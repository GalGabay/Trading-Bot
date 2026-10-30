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


def load_review(path, rows, source_pin):
    review = json.loads(path.read_text(encoding="utf-8"))
    if review.get("provider_source") != source_pin or review.get("schema_version") != 1:
        raise ValueError("Dividend review is detached from the pinned provider source")
    checked_file(Path.cwd(), review["provider_source"])
    sources = {}
    for source in review["sources"]:
        if source["id"] in sources:
            raise ValueError("Repeated dividend evidence ID")
        checked_file(Path.cwd(), source["evidence"])
        sources[source["id"]] = source
    groups = defaultdict(dict)
    for row in rows:
        if row["category"] == "cash_dividends":
            groups[(row["instrument_id"], row["day"])][row["event_id"]] = json.loads(row["record"], parse_float=str)
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
    item["component_review"] = decision
    kind = decision["kind"]
    if kind == "aggregate_includes_component" and item["event_id"] == decision["component_event_id"]:
        item.update(status="reviewed_component_in_total_no_independent_right",
                    cash_per_eligible_share="0", modeled_release_at=None,
                    independent_entitlement=False, represented_by_event_id=decision["total_event_id"])
    elif kind == "cash_stock_election_unresolved":
        item["blockers"].append("reviewed_cash_stock_election_requires_holder_allocation_and_exact_share_terms")
        item.update(cash_per_eligible_share=None, modeled_release_at=None,
                    category="diagnostic_cash_stock_election_candidate")

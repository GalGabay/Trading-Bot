"""Reconcile reviewed event interpretations without admitting or booking them.

The review is an offline overlay. Frozen candidate inputs and provider records
are retained. A primary-supported interpretation is not a settlement timestamp,
an election allocation, a complete security master, or approval to score returns.
"""

import argparse
from collections import Counter
import csv
from fractions import Fraction
import json
from pathlib import Path

from backtesting.broad_collection import pin
from backtesting.cohort_audit import checked_file
from backtesting.pilot_readiness_review import offline_only, write_csv, write_json


def review_rows(rows, decisions, material_events, provider_rows, sources):
    def unique(values, key):
        result = {key(v): v for v in values}
        if len(result) != len(values):
            raise ValueError("Duplicate review/event identity")
        return result

    key = lambda r: (r["instrument_id"], r["event_id"])
    queue = unique(rows, key)
    providers = unique(provider_rows, lambda r: (r["instrument_id"], r["category"], r["event_id"]))
    material = unique(material_events, lambda e: (e["parent_id"], e["id"]))
    reviewed = unique(decisions, key)
    primary = unique(sources, lambda s: s["id"])
    if reviewed.keys() != queue.keys() - material.keys() or not material.keys() <= queue.keys():
        raise ValueError("Review must retain each material record and cover every ambiguous provider record exactly once")
    result = []
    for identity, row in queue.items():
        item = dict(row, economic_interpretation_primary_supported=False, execution_ready=False,
                    actual_delivery_at=None, fractional_cash_fixing=None, known_at_verified=False)
        if identity in material:
            item.update(review_status="candidate_event_requires_admission", related_material_events=[identity[1]],
                        remaining="Primary terms, holder entitlement, delivery and fractional handling remain admission gates")
            if identity[1] == "bwa_phin_distribution":
                source = primary["phin_2023"]
                if source["access"] != "primary_browser_text_reviewed":
                    raise ValueError("PHIN economic correction requires directly reviewed source")
                item.update(review_status="candidate_distribution_date_correction_required", primary_source_id="phin_2023",
                    proposed_economic_date=source["facts"]["distribution_effective_at"][:10],
                    quote_start_date=source["facts"]["first_regular_session"],
                    remaining="Create a new spec separating July 3 distribution and July 5 regular trading; ratio/entitlement/delivery remain unverified")
        else:
            decision = reviewed[identity]
            if row["day"] != decision["day"] or row["category"] != decision["category"]:
                raise ValueError("Reviewed event date/category changed")
            provider = providers[(identity[0], row["category"], identity[1])]
            record = json.loads(provider["record"])
            item.update(review_status=decision["status"], remaining=decision["remaining"],
                        related_material_events=decision.get("related_material_events", []),
                        primary_source_id=decision.get("primary_source_id"))
            for related in item["related_material_events"]:
                candidates = [e for e in material_events if e["id"] == related]
                if len(candidates) != 1 or candidates[0]["root_id"] != provider["root_id"]:
                    raise ValueError("Event cross-reference points to an unrelated security")
            if row["category"] in {"forward_splits", "reverse_splits"}:
                observed = Fraction(str(record["new_rate"])) / Fraction(str(record["old_rate"]))
                if observed != Fraction(decision["observed_new_shares_per_old"]):
                    raise ValueError("Provider ratio changed since economic review")
            if decision.get("primary_source_id"):
                source = primary[decision["primary_source_id"]]
                item["primary_source_url"] = source["url"]
                supported = source["access"] in {"primary_browser_text_reviewed", "primary_clearinghouse_browser_pdf_text_reviewed"}
                if decision["primary_interpretation_supported"] and not supported:
                    raise ValueError("Search-only discovery cannot become direct primary evidence")
                item["economic_interpretation_primary_supported"] = decision["primary_interpretation_supported"]
                if decision["status"] in {"reverse_split_with_election_dividend", "genuine_fractional_stock_split"}:
                    if observed != Fraction(source["facts"]["new_shares_per_old"]):
                        raise ValueError("Primary-supported split ratio disagrees with provider")
            if decision.get("execution_ready") or decision.get("actual_delivery_at") is not None:
                raise ValueError("Review cannot invent execution admission or broker delivery")
        result.append(item)
    return result


def build(review_path, output):
    if output.exists() or not output.resolve().is_relative_to(Path.cwd().resolve()):
        raise ValueError("Choose a fresh review directory within the workspace")
    plan = json.loads(review_path.read_text(encoding="utf-8"))
    paths = {k: checked_file(Path.cwd(), v) for k, v in plan["inputs"].items()}
    if plan["performance_authorized"] or plan["purchases_usd"] != 0:
        raise ValueError("Review-only zero-spending scope changed")
    def read_csv(name):
        with paths[name].open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    spec = json.loads(paths["spec"].read_text(encoding="utf-8"))
    facts = json.loads(paths["primary_review"].read_text(encoding="utf-8"))
    decisions = json.loads(paths["decisions"].read_text(encoding="utf-8"))
    rows = review_rows(read_csv("queue"), decisions, spec["material_events"], read_csv("provider_roles"), facts["sources"])
    output.mkdir(parents=True)
    write_csv(output / "event_review.csv", [{k: json.dumps(v) if isinstance(v, list) else v for k, v in r.items()} for r in rows])
    summary = dict(review=pin(review_path), execution=pin("backtesting/event_review.py"), inputs=plan["inputs"],
        records_retained=len(rows), review_status_counts=dict(Counter(r["review_status"] for r in rows)),
        provider_interpretations_primary_supported=sum(r["economic_interpretation_primary_supported"] for r in rows),
        unresolved_execution_records=len(rows), original_records_rewritten=0,
        performance_ready=False, step1_complete=False, strict_flags_promoted=False,
        purchases_usd=0, orders=0, account_requests=0, strategy_runs=0,
        result=pin(output / "event_review.csv"))
    write_json(output / "summary.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=Path("docs/broad_event_review_plan.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with offline_only():
        print(json.dumps(build(args.review, args.output), indent=2))

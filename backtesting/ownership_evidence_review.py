"""Offline review of the remaining historical gates, without event approval.

Revalidates the saved collection and pinned primary files. Advance planned
terms are separated from executed delivery, spendable cash and price coverage.
Unavailable sources remain gaps; no downloader or broker is instantiated.
"""

import argparse
from datetime import date, timedelta
from fractions import Fraction
import json
from pathlib import Path

import pandas as pd

from backtesting.cohort_audit import checked_file, digest, source_text
from backtesting.event_gap_review import review_gaps

REVIEW = Path("docs/ownership_evidence_review.json")


def advance_terms(checks, texts, sessions):
    """Verify reviewed literal terms and compute the declared publication bound."""
    rows = []
    seen = set()
    for check in checks:
        if check["case_name"] in seen:
            raise ValueError("Duplicate advance-terms review")
        seen.add(check["case_name"])
        if not all(term in texts[check["source_id"]] for term in check["terms"]):
            raise ValueError("Advance planned terms do not match their pinned source")
        publication = date.fromisoformat(check["publication_date"])
        rendered_date = f"{publication.strftime('%B')} {publication.day}, {publication.year}"
        if rendered_date not in texts[check["source_id"]]:
            raise ValueError("Publication date is absent from the pinned source")
        if Fraction(check["shares_per_parent"]) <= 0:
            raise ValueError("Advance share ratio must be positive")
        bound = pd.Timestamp(publication + timedelta(days=2), tz="UTC")
        known = next((s for s in sessions if s >= bound), None)
        effective = next((s for s in sessions if s.date().isoformat() == check["recognition_session"]), None)
        if known is None or effective is None:
            raise ValueError("Publication/effective date is outside the saved development calendar")
        rows.append({**check, "conservative_known_at": known.isoformat(),
                     "planned_terms_known_by_recognition_open": known <= effective,
                     "actual_delivery_verified": False, "approved_for_strategy_scoring": False})
    return rows


def match_mechanics(checks, cases):
    """Keep the reviewed advance terms consistent with the mechanics protocol."""
    by_name = {case["name"]: case for case in cases}
    for check in checks:
        case = by_name[check["case_name"]]
        if (case["session"] != check["recognition_session"] or len(case["shares"]) != 1
                or Fraction(case["shares"][0]["ratio"]) != Fraction(check["shares_per_parent"])):
            raise ValueError("Advance terms disagree with the saved mechanics case")


def classify_cases(cases, advances, event_checks):
    by_name = {row["case_name"]: row for row in advances}
    provider_names = {
        "whole_foods_delayed_cash_right": "wfm_cash_merger",
        "activision_delayed_cash_right": "activision_cash_merger",
        "aetna_cash_and_cvs_successor": "aetna_mixed_merger",
        "level3_cash_and_ctl_successor": "level3_mixed_merger",
        "alcoa_retained_parent_and_distinct_child": "alcoa_distribution",
        "arconic_howmet_and_new_arconic_branch": "arconic_2020_distribution",
        "under_armour_distinct_class_c_ownership": "ua_class_c_issuance",
    }
    provider = {row["name"]: row["provider_event_present"] for row in event_checks}
    result = []
    for case in cases:
        advanced = by_name.get(case["name"])
        shares = bool(case["shares"])
        cash = float(case["cash_per_parent"]) > 0
        synthetic = any("synthetic_close" in leg for leg in case["shares"])
        result.append(dict(
            name=case["name"], primary_terms_corroborated=True,
            provider_event_present=provider[provider_names[case["name"]]],
            advance_planned_terms_supported=bool(advanced and advanced["planned_terms_known_by_recognition_open"]),
            event_quotes="missing_child_quote_synthetic_mechanics_only" if synthetic else "saved_event_quotes_or_cash_only",
            prior_close_entitlement_verified=False,
            share_delivery_verified=False if shares else None,
            spendable_cash_availability_verified=False if cash else None,
            fractional_allocation_verified=False if shares and any(leg["ratio"] != "1" for leg in case["shares"]) else None,
            full_lifecycle_price_and_action_coverage_certified=False,
            primary_evidence_is_not_broker_credit_proof=True,
            approved_for_strategy_scoring=False,
        ))
    return result


def run_review(output, *, review_path=REVIEW):
    if output.exists():
        raise FileExistsError("Choose a fresh evidence-review directory")
    protocol = json.loads(review_path.read_text(encoding="utf-8"))
    if (type(protocol["schema_version"]) is not int or protocol["schema_version"] != 1
            or protocol["approved_for_strategy_scoring"] is not False
            or protocol["new_purchases_usd"] != 0 or protocol["automatic_paid_fallback"] is not False):
        raise ValueError("Only the non-scoring, no-purchase review protocol is supported")
    root = Path.cwd()
    parent_path, cases_path, cohort_path = [checked_file(root, protocol[key])
                                            for key in ("parent_review", "mechanics_cases", "cohort_review")]
    parent, cases, cohort = [json.loads(path.read_text(encoding="utf-8")) for path in (parent_path, cases_path, cohort_path)]
    paths = {key: checked_file(root, entry) for key, entry in parent["sources"].items()}
    source = protocol["undated_source_check"]["source_id"]
    paths[source] = checked_file(root / cohort["source_root"], cohort["sources"][source])
    texts = {key: source_text(path) for key, path in paths.items()}
    for case in cases["cases"]:
        if not all(term in texts[case["source_id"]] for term in case["source_terms"]):
            raise ValueError("Saved mechanics case terms no longer match their primary source")
    undated = protocol["undated_source_check"]
    if not all(term in texts[undated["source_id"]] for term in undated["terms"]):
        raise ValueError("Undated Alcoa cover-letter review no longer matches its source")
    plan_path = Path("docs/free_collection_plan.json")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    calendar_path = checked_file(root, {"path": plan["calendar_path"], "sha256": plan["calendar_sha256"]})
    sessions = [pd.Timestamp(item["opens_at"]) for item in json.loads(calendar_path.read_text())]
    if any(s.tzinfo is None or s >= pd.Timestamp("2024-01-01", tz="UTC") for s in sessions) or sessions != sorted(set(sessions)):
        raise ValueError("Evidence review requires ordered aware development sessions only")
    advances = advance_terms(protocol["advance_terms_checks"], texts, sessions)
    match_mechanics(advances, cases["cases"])
    # The collection reviewer validates all raw payload hashes/calendar coverage
    # before writing its new inventory. It never refreshes market data.
    inventory = review_gaps(output / "collection_review", review_path=parent_path)
    result = dict(
        scope=protocol["purpose"], primary_sources_revalidated=len(paths),
        input_sha256={str(path): digest(path) for path in (review_path, parent_path, cases_path, cohort_path, plan_path, calendar_path)},
        primary_source_sha256={key: digest(path) for key, path in paths.items()},
        code_sha256={name: digest(name) for name in ("backtesting/ownership_evidence_review.py", "backtesting/event_gap_review.py")},
        inventory_report_sha256=digest(output / "collection_review/report.json"),
        required_provider_events_missing=inventory["required_events_missing_from_provider"],
        quarantined_event_references=inventory["quarantined_event_references"],
        advance_planned_terms=advances, undated_source_review=undated,
        cases=classify_cases(cases["cases"], advances, inventory["required_event_checks"]),
        unresolved_cases=cases["blocked_cases"],
        data_gaps=dict(new_arconic_child_quote_missing=True, bed_bath_otc_quotes_unavailable=True,
                       additional_class_c_per_unit_ratio_not_certified=True, fox_election_and_proration_unresolved=True,
                       full_506_security_coverage_certified=False),
        cash_availability_convention=parent["cash_availability_convention"],
        free_public_lookup_attempts=protocol["free_public_lookup_attempts"],
        public_web_tool_calls_recorded=len(protocol["free_public_lookup_attempts"]),
        offline_review_network_requests=0, broker_data_requests=0, account_requests=0,
        orders=0, new_purchases_usd=0, subscriptions_changed=0, strategy_simulations=0,
        reserved_holdout_prices_read=False, events_automatically_approved=0,
        ready_for_broad_backtest=False,
    )
    (output / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_review(args.output)
    print(json.dumps({key: report[key] for key in ("primary_sources_revalidated", "required_provider_events_missing",
                     "events_automatically_approved", "new_purchases_usd", "ready_for_broad_backtest")}))


if __name__ == "__main__":
    main()

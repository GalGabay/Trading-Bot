"""Offline scope proposal from existing gates; never a performance admission.

Stocks are classified only by saved data blockers. No prices, strategy results,
credentials or broker services are read. Selecting a subset after inspecting
historical data availability changes the research scope and may bias returns.
The original fixed basket and its admission rules remain unchanged.
"""

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path

from backtesting.broad_collection import pin
from backtesting.cohort_audit import checked_file
from backtesting.pilot_readiness_review import offline_only, write_csv, write_json


def audit(preparation_path, preflight_path, comparison_path, output):
    if output.exists() or not output.resolve().is_relative_to(Path.cwd().resolve()):
        raise ValueError("Choose a fresh scope-audit output directory inside the workspace")
    preparation = json.loads(preparation_path.read_text(encoding="utf-8"))
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    if (preflight["preparation"] != pin(preparation_path) or preflight["selected_originals"] != preparation["selected_originals"] or
            preflight.get("original_members_dropped") != 0 or preparation.get("strategy_runs") != 0):
        raise ValueError("Scope audit requires the unchanged, matching original preparation and preflight")
    for source in preparation["execution"] + preparation["output_files"]:
        checked_file(Path.cwd(), source)
    checked_file(Path.cwd(), preflight["execution"])
    revision = json.loads(checked_file(Path.cwd(), preparation["revision"]).read_text(encoding="utf-8"))
    spec = json.loads(checked_file(Path.cwd(), revision["spec"]).read_text(encoding="utf-8"))
    if comparison["roster"] != spec["roster"]:
        raise ValueError("Comparison and corrected input must use the same frozen original roster")
    with checked_file(Path.cwd(), spec["roster"]).open(encoding="utf-8", newline="") as handle:
        roster = list(csv.DictReader(handle))
    roots = {row["instrument_id"] for row in roster}
    streams = {s["instrument_id"]: s for s in spec["streams"]}
    if (len(roots) != len(roster) or len(roster) != preparation["selected_originals"] or
            len(streams) != len(spec["streams"]) or any(s["root_id"] not in roots for s in streams.values())):
        raise ValueError("Require unique original roots and explicit descendant root mappings")
    blocked = defaultdict(list)
    for gate in preflight["blockers"]:
        instrument = streams.get(gate["instrument_id"])
        if instrument is None:
            raise ValueError("Cannot classify an unmapped blocker as harmless")
        blocked[instrument["root_id"]].append(gate)
    eligible = [r["instrument_id"] for r in roster if r["instrument_id"] not in blocked]
    excluded = [r["instrument_id"] for r in roster if r["instrument_id"] in blocked]
    controls = comparison["selection"]["nested_existing_control_ids"]
    if not set(controls) <= set(eligible) or len(eligible) + len(excluded) != len(roster):
        raise ValueError("Existing controls must remain in the candidate scope; every original must be accounted for")
    inventory = []
    for row in roster:
        counts = Counter(g["kind"] for g in blocked.get(row["instrument_id"], []))
        inventory.append(dict(selection_order=int(row["selection_order"]), instrument_id=row["instrument_id"],
            snapshot_alias=row["snapshot_alias"], source_name=row["source_name"],
            proposed_scope="candidate_currently_unflagged" if not counts else "deferred_in_separate_proposal_only",
            reported_blocking_rows=sum(counts.values()), material_rows=counts["material_terms"],
            dividend_rows=counts["dividend_terms"], provider_rows=counts["provider_terms"], election_rows=counts["election_schedule"]))
    output.mkdir(parents=True)
    write_csv(output/"all_originals.csv", inventory)
    candidate_streams = [s["instrument_id"] for s in spec["streams"] if s["root_id"] in set(eligible)]
    proposal = dict(schema_version=1, date="2026-10-30", status="concrete_separate_scope_proposal_not_approved",
        original_preparation=pin(preparation_path), original_preflight=pin(preflight_path), original_comparison=pin(comparison_path),
        roster=spec["roster"], original_members_retained_in_inventory=len(roster), original_protocol_modified=False,
        proposed_candidate_root_ids=eligible, proposed_deferred_root_ids=excluded,
        proposed_candidate_stream_ids=candidate_streams, control_root_ids=controls,
        selection_basis="all_original_roots_without_current_reported_preflight_blockers_no_rerolls",
        selection_uses_returns=False, selection_uses_future_data_availability=True,
        known_bias="ex_post_data_availability_selection_may_distort_returns_and_does_not_establish_survivorship_control",
        scope_limit="exploratory_subset_comparison_not_full_original_basket_not_paper_acceptance_evidence",
        account_sizes_usd=[10000], allocation=dict(total_entry_exposure=.70,per_stock_entry_cap=.05,max_positions=20),
        frozen_strategy=dict(comparison["frozen_strategy"],portfolio_cap=.70,max_positions=20),
        windows=comparison["windows"], costs=comparison["costs"], scenarios=["base","delayed_five_sessions","no_credit"],
        proposed_arms=[dict(id="matched_two_stock_control",root_ids=controls),dict(id="availability_selected_subset",root_ids=eligible)],
        max_strategy_attempts=24,max_total_wall_clock_minutes=120,max_case_wall_clock_minutes=10,max_concurrent_workers=1,
        extra_parameter_searches=0,ml=False,heldout_2024_2025_access=False,
        prerequisites=["Explicit owner approval of changed scope and its selection bias",
            "Prepare and validate a separately pinned subset input without changing the original basket",
            "Implement and verify Step 2 pending-rights/portfolio bridge and control accounting reconciliation",
            "Profile the runner and enforce finite wall-clock/attempt caps before Step 3"],
        owner_approved=False,performance_authorized=False,paper_authorized=False,
        purchases_usd=0,broker_requests_authorized=False,max_currently_authorized_strategy_runs=0)
    write_json(output/"proposal.json", proposal)
    report = dict(date="2026-10-30", current_step=1, original_member_count=len(roster), candidate_root_count=len(eligible),
        deferred_root_count=len(excluded), candidate_stream_count=len(candidate_streams),
        original_blocking_rows=len(preflight["blockers"]), candidate_reported_blocking_rows=0,
        qualification_limit="No blockers in the existing report only; not fresh price/action/source certification",
        all_originals_accounted_for=True, original_protocol_modified=False, step1_full_basket_complete=False,
        subset_scope_owner_approved=False, engine_adapter_integrated=False, performance_ready=False,
        proposal=pin(output/"proposal.json"), inventory=pin(output/"all_originals.csv"), execution=pin(Path(__file__)),
        tests_run=0,price_files_read=0,credentials_read=False,network_requests=0,orders=0,purchases_usd=0,strategy_runs=0)
    write_json(output/"summary.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparation",type=Path,required=True)
    parser.add_argument("--preflight",type=Path,required=True)
    parser.add_argument("--comparison",type=Path,default=Path("docs/broad_100_comparison_plan.json"))
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    with offline_only():
        print(json.dumps(audit(args.preparation,args.preflight,args.comparison,args.output),indent=2))

"""Create a new candidate revision from the pinned Step 1 review, offline.

No source approvals, known-at timestamps, entitlement, payments or returns are
inferred. Every old observation and original selected member remains accounted
for, including the JCI predecessor reference excluded from active features.
"""

import argparse
from copy import deepcopy
import json
from pathlib import Path

from backtesting.broad_collection import pin
from backtesting.cohort_audit import checked_file
from backtesting.historical_input import build as build_input
from backtesting.pilot_readiness_review import offline_only, write_json

PROPOSAL = Path("docs/broad_mapping_revision_plan.json")


def revised_spec(original, facts, primary_pin):
    spec = deepcopy(original)
    by_source = {s["id"]: s for s in facts["sources"]}
    for key in ("jci_2016", "peak_2023", "phin_2023"):
        if by_source[key]["access"] != "primary_browser_text_reviewed":
            raise ValueError("Mapping corrections require directly reviewed primary text")
    streams = spec["streams"]
    by_id = {s["instrument_id"]: s for s in streams}
    jci = by_id["COHORT-2016-0258"]
    if jci["parts"] != [dict(source_key="base:JCI", start="2016-01-01", end_exclusive="2024-01-01", primary_source_ids=[])]:
        raise ValueError("Original JCI binding changed; review predecessor mapping again")
    boundary = by_source["jci_2016"]["facts"]["new_JCI_first_session"]
    predecessor = deepcopy(jci)
    predecessor.update(instrument_id=jci["instrument_id"]+".PREMERGER-REFERENCE",
        role="preinvestable_warmup_reference_only", eligible_for_new_entries_candidate=False,
        feature_use_prohibited=True, mapping_evidence=dict(source=primary_pin, source_id="jci_2016"))
    predecessor["parts"][0]["end_exclusive"] = boundary
    jci["parts"][0]["start"] = boundary
    jci.update(feature_history_starts_at=boundary, predecessor_features_may_carry=False,
        mapping_evidence=dict(source=primary_pin, source_id="jci_2016"))
    streams.append(predecessor)

    hcp = by_id["COHORT-2016-0227"]
    last = hcp["parts"][-1]
    if last["source_key"] != "hcp_peak" or last["end_exclusive"] != "2024-01-01":
        raise ValueError("Original PEAK binding changed; review legal-parent mapping again")
    peak_day = by_source["peak_2023"]["facts"]["effective_date"]
    new_id = hcp["instrument_id"]+".PEAK-HOLDCO-2023"
    successor = dict(instrument_id=new_id, root_id=hcp["root_id"], snapshot_alias="HCP",
        role="received_security", parts=[dict(last, start=peak_day)],
        eligible_for_new_entries_candidate=True, entry_role="continuation_of_selected_member",
        strict_identity_verified=False, predecessor_id=hcp["instrument_id"],
        mapping_evidence=dict(source=primary_pin, source_id="peak_2023"))
    last["end_exclusive"] = peak_day
    streams.append(successor)
    spec["material_events"].append(dict(id="peak_holding_company_reorganization",
        root_id=hcp["root_id"], parent_id=hcp["instrument_id"], parent_alias="PEAK",
        kind="stock_merger", economic_date=peak_day,
        share_legs=[dict(instrument_id=new_id, shares_per_parent="1")], cash_per_parent="0",
        primary_source_ids=[], mapping_evidence=dict(source=primary_pin, source_id="peak_2023"),
        note="One-for-one legal parent exchange; candidate daily boundary, exact time unverified",
        prior_close_entitlement_verified=False, actual_delivery_at=None,
        fractional_cash_fixing=None, execution_ready=False))
    phin = next(e for e in spec["material_events"] if e["id"] == "bwa_phin_distribution")
    if phin["economic_date"] != "2023-07-05":
        raise ValueError("Original PHIN candidate changed")
    phin.update(economic_date=by_source["phin_2023"]["facts"]["distribution_effective_at"][:10],
        economic_effective_at=by_source["phin_2023"]["facts"]["distribution_effective_at"],
        first_regular_session=by_source["phin_2023"]["facts"]["first_regular_session"],
        mapping_evidence=dict(source=primary_pin, source_id="phin_2023"),
        note="Distribution precedes first regular quotes; ratio remains provider-dependent and delivery unknown")
    spec["diagnostic_mapping"] = dict(primary_review=primary_pin, feature_resets=[jci["instrument_id"]],
        unresolved_feature_events=[dict(instrument_id=jci["instrument_id"],date="2016-11-01",
            reason="ADNT distribution economics still require review; do not warm through an unresolved price discontinuity")],
        feature_continuity_candidates=[dict(parent_id=hcp["instrument_id"], successor_id=new_id,
            first_session=peak_day, shares_per_parent="1", owner_approved=False)],
        provider_overrides=[
            dict(event_id="72ae5eb0-9663-42fe-bd68-50644e3c2a10", instrument_id=jci["instrument_id"],
                 disposition="wrong_predecessor_ratio_do_not_apply", source_id="jci_2016"),
            dict(event_id="4c93ce12-023e-4a00-9f1a-d0ce3b50d5eb", instrument_id=new_id,
                 disposition="represented_by_peak_holding_company_reorganization_do_not_apply_twice", source_id="peak_2023")],
        research_entry_continuity_approved=False, performance_authorized=False)
    spec["readiness_blockers"] += [
        "Mapping revision is candidate only; PEAK daily transition/feature continuity needs diagnostic policy approval",
        "JCI starts fresh history on 2016-09-06; ADNT warmup distribution remains unresolved",
        "PHIN right may exist before any regular quote; missing value must remain unknown, not zero"]
    return spec


def prepare(output, *, plan_path=PROPOSAL):
    if output.exists() or not output.resolve().is_relative_to(Path.cwd().resolve()):
        raise ValueError("Choose a fresh mapping revision directory inside the workspace")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    paths = {k: checked_file(Path.cwd(), v) for k,v in plan["inputs"].items()}
    if plan["performance_authorized"] or plan["purchases_usd"] != 0:
        raise ValueError("Only offline candidate revision is authorized")
    original = json.loads(paths["spec"].read_text(encoding="utf-8"))
    facts = json.loads(paths["primary_review"].read_text(encoding="utf-8"))
    spec = revised_spec(original, facts, plan["inputs"]["primary_review"])
    output.mkdir(parents=True)
    spec_path = output/"corrected_spec.json"
    write_json(spec_path, spec)
    result = build_input(output/"candidate", spec_path=spec_path)
    manifest = json.loads((output/"candidate/input_manifest.json").read_text(encoding="utf-8"))
    # The original builder intentionally has a small manifest schema; carry the
    # revision's additional feature/entry rules in an explicitly separate file.
    mapping = spec["diagnostic_mapping"]
    write_json(output/"mapping_rules.json", mapping)
    summary = dict(plan=pin(plan_path), inputs=plan["inputs"], spec=pin(spec_path),
        execution=pin("backtesting/corrected_input.py"), builder=pin("backtesting/historical_input.py"),
        candidate_report=pin(output/"candidate/report.json"), mapping=pin(output/"mapping_rules.json"),
        candidate_streams=len(manifest["streams"]), selected_originals=result["selected_originals"],
        output_rows=sum(s["rows"] for s in manifest["streams"]), material_events=len(spec["material_events"]),
        new_legal_or_reference_streams=2, original_members_dropped=0,
        feature_reset_ids=mapping["feature_resets"], original_source_files_modified=False,
        performance_ready=False, strict_flags_promoted=False, step1_complete=False,
        paper_authorized=False, purchases_usd=0, broker_requests=0, strategy_runs=0, unit_tests_run=0)
    write_json(output/"summary.json", summary)
    return summary


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args=parser.parse_args()
    with offline_only():
        print(json.dumps(prepare(args.output), indent=2))

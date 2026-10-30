"""Compile a proposed accounting schedule for corrected cached candidates.

No holdings are simulated. Output rows describe conditional rights if a future
simulation owns eligible shares. Missing terms remain blockers and all execution
and approval flags stay false. The strict ownership adapter is unchanged.
"""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path

from backtesting.broad_collection import pin
from backtesting.claim_accounting import exact, instant, number
from backtesting.cohort_audit import checked_file
from backtesting.diagnostic_accounting import DiagnosticClock, SCENARIOS, plan_dividend
from backtesting.diagnostic_approval import validate_approval
from backtesting.dividend_components import apply_review, load_review
from backtesting.diagnostic_event_terms import apply_material_terms, load_event_terms
from backtesting.corporate_action_terms import load_actions
from backtesting.election_schedule import compile_schedules, load_holder_policy
from backtesting.pilot_readiness_review import offline_only, write_csv, write_json


def validate_policy(policy):
    if (policy.get("schema_version") != 1 or type(policy.get("owner_approved")) is not bool or
            policy.get("performance_authorized") is not False or policy.get("paper_authorized") is not False or
            policy.get("purchases_usd") != 0 or policy.get("max_strategy_runs") != 0 or
            policy.get("scenarios") != list(SCENARIOS) or
            policy.get("unknown_payable_policy") != "unspendable_receivable_no_invented_date" or
            policy.get("unknown_value_policy") != "incomplete_equity_blocks_scoring" or
            policy.get("election_policy") != "block_until_holder_terms_resolved" or
            policy.get("fractional_policy") != "pending_share_claim_no_automatic_cash" or
            policy.get("selected_total_entry_exposure") != .70):
        raise ValueError("Only the bounded, zero-run diagnostic policy is supported")
    if policy["owner_approved"]:
        validate_approval(policy)
    supported = dict(
        ordinary_entitlement_policy="assumed_prior_session_close_whole_shares_before_ex_open_fills",
        metadata_policy="retrospective_vendor_accounting_at_event_boundary_never_an_entry_feature",
        missing_declaration_policy="historical_known_at_stays_null_modeled_observed_at_is_explicit_assumption",
        known_cash_policy="provider_payable_date_plus_next_saved_open_base_plus_five_more_sessions_delayed",
        share_release_policy="first_saved_open_at_or_after_economic_instant_and_regular_trading_start_plus_five_sessions_delayed",
        no_credit_policy="retain_and_value_known_rights_but_release_neither_cash_nor_shares_within_window",
        valuation_policy="fixed_cash_face_and_exact_current_session_share_close_no_stale_or_future_marks",
        currency_policy="assumed_gross_usd_for_provider_nonforeign_cash_records_no_tax_or_fx_model",
        share_basis_policy="assumed_post_split_block_same_boundary_until_order_reviewed")
    if any(policy.get(k) != v for k,v in supported.items()):
        raise ValueError("Policy labels disagree with the implemented diagnostic mechanics")
    for key in ("original_members_may_be_dropped","unknown_rights_may_fund_buys"):
        if policy.get(key) is not False:
            raise ValueError("Diagnostic policy cannot drop members or spend unknown rights")
    if policy.get("pending_rights_count_toward_exposure") is not True or policy.get("unresolved_risk_marks_block_new_entries") is not True:
        raise ValueError("Pending-right exposure and unknown-mark gates must remain explicit")


def material_plan(event, clock, scenario, streams):
    economic_at = event.get("economic_effective_at")
    opens = [o for d,o in zip(clock.days,clock.opens) if d.isoformat() >= event["economic_date"]]
    accounting_at = opens[0] if opens else None
    if economic_at:
        # The distribution may occur after a close or on a nontrading date.
        # Do not relabel a regular quote open as its economic instant.
        effective = instant(economic_at)
        accounting_at = next((o for o in clock.opens if o >= effective),None)
    else:
        effective = accounting_at
    legs = []
    for leg in event["share_legs"]:
        # Respect each child's configured regular quote interval, including
        # distributions whose economic date precedes regular-way trading.
        stream_start = streams[leg["instrument_id"]]["parts"][0]["start"]
        first = max(stream_start,event.get("first_regular_session") or event["economic_date"])
        release = None if effective is None else clock.share_release(effective,first,scenario)
        legs.append(dict(instrument_id=leg["instrument_id"],shares_per_parent=exact(number(leg["shares_per_parent"],positive=True)),
            modeled_release_at=None if release is None else release.isoformat(),
            actual_broker_received_at=None,can_release_before_terms_review=False))
    return dict(event_id=event["id"],parent_id=event["parent_id"],root_id=event["root_id"],kind=event["kind"],
        scenario=scenario,economic_date=event["economic_date"],economic_effective_at=economic_at,
        modeled_accounting_at=None if accounting_at is None else accounting_at.isoformat(),
        cash_per_parent=event["cash_per_parent"],modeled_cash_release_at=None,
        share_legs=legs,status="candidate_terms_and_policy_unapproved",
        prior_close_entitlement_verified=False,historical_known_at=None,actual_delivery_at=None,
        execution_ready=False,source_terms=event.get("mapping_evidence") or event.get("primary_source_ids",[]),
        blockers=["Unapproved entitlement and timing assumptions", "Cash payable/fractional terms need per-event support",
                  "Source review required before any proposed share release can execute"])


def validate_peak_continuity(event,evidence):
    root="COHORT-2016-0227"
    if (event["id"]!="peak_holding_company_reorganization" or evidence["id"]!="peak_2023" or
            evidence["access"]!="primary_browser_text_reviewed" or
            evidence["facts"]["new_shares_per_old"]!="1" or
            evidence["facts"]["effective_date"]!=event["economic_date"] or
            event["parent_id"]!=root or event["root_id"]!=root or event["cash_per_parent"]!="0" or
            event["share_legs"]!=[dict(instrument_id=root+".PEAK-HOLDCO-2023",shares_per_parent="1")]):
        raise ValueError("PEAK continuity differs from directly reviewed one-for-one terms")


def dividend_multiplicity(rows):
    groups={}
    for row in rows:
        if row["category"]=="cash_dividends":
            key=row["instrument_id"],row["day"]
            groups.setdefault(key,set()).add(row["event_id"])
    return {key:sorted(ids) for key,ids in groups.items() if len(ids)>1}


def prepare(revision_dir, policy_path, output, dividend_review_path=None, event_terms_path=None,
            corporate_review_path=None, election_inputs_path=None):
    if output.exists() or not output.resolve().is_relative_to(Path.cwd().resolve()):
        raise ValueError("Choose a fresh policy-preparation directory in the workspace")
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    validate_policy(policy)
    for entry in policy["implementation"]:
        checked_file(Path.cwd(),entry)
    revision = json.loads((revision_dir/"summary.json").read_text(encoding="utf-8"))
    for entry in revision["inputs"].values():
        checked_file(Path.cwd(),entry)
    spec_path = checked_file(Path.cwd(),revision["spec"])
    mapping_path = checked_file(Path.cwd(),revision["mapping"])
    report = json.loads(checked_file(Path.cwd(),revision["candidate_report"]).read_text(encoding="utf-8"))
    if revision["performance_ready"] or revision["strict_flags_promoted"] or revision["strategy_runs"]:
        raise ValueError("Require a candidate-only mapping revision")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    calendar = json.loads(checked_file(Path.cwd(),spec["calendar"]).read_text(encoding="utf-8"))
    clock = DiagnosticClock(calendar)
    with checked_file(Path.cwd(),report["event_roles"]).open(encoding="utf-8",newline="") as handle:
        provider_rows = list(csv.DictReader(handle))
    decisions = json.loads(checked_file(Path.cwd(),policy["event_decisions"]).read_text(encoding="utf-8"))
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    overrides = {(r["instrument_id"],r["event_id"]):r for r in mapping["provider_overrides"]}
    ambiguous = {(r["instrument_id"],r["event_id"]):r for r in decisions}
    event_routes, dividends = [], []
    boundary_actions = {(r["instrument_id"],r["day"]) for r in provider_rows if r["category"] in {"forward_splits","reverse_splits"}}
    election_roots = {r["instrument_id"] for r in decisions if r["status"] in {"reverse_split_with_election_dividend","search_only_reverse_split_election"}}
    feature_excluded = {s["instrument_id"] for s in spec["streams"] if s.get("feature_use_prohibited")}
    multiple_dividends=dividend_multiplicity(provider_rows)
    component_decisions = {} if dividend_review_path is None else load_review(
        dividend_review_path, provider_rows, report["event_roles"])
    material_decisions, context_decisions = ({}, {}) if event_terms_path is None else load_event_terms(
        event_terms_path, spec, provider_rows, report["event_roles"])
    corporate_actions = {} if corporate_review_path is None else load_actions(
        corporate_review_path, spec, provider_rows, report["event_roles"], clock)
    election_schedules = []
    holder_policy = None
    if election_inputs_path is not None:
        inputs = json.loads(election_inputs_path.read_text(encoding="utf-8"))
        if inputs["provider_source"] != report["event_roles"] or inputs.get("schema_version") != 1:
            raise ValueError("Election inventory must match the pinned provider input")
        holder_policy = load_holder_policy(inputs)
        election_schedules = compile_schedules(provider_rows, clock,
            *(checked_file(Path.cwd(),inputs[k]) for k in ("terms","split_review","resolution","mac_review")),
            holder_policy=holder_policy)
    # An unresolved future election cannot change the number of shares used by
    # an earlier ordinary cash dividend. After the first share-changing event,
    # later dividends and received descendants still depend on its resolution.
    election_cutoffs = {}
    for schedule in election_schedules:
        first = min(schedule["payable_date"], schedule.get("split_first_adjusted_session") or schedule["payable_date"])
        root = schedule["instrument_id"]
        election_cutoffs[root] = min(first, election_cutoffs.get(root, first))
    # MAC has an election without a linked reverse split. Its later dividends
    # also depend on the unallocated stock issue, so include every schedule root.
    election_roots.update(election_cutoffs)
    for row in provider_rows:
        identity = row["instrument_id"],row["event_id"]
        if row["category"] == "cash_dividends":
            for scenario in SCENARIOS:
                item = plan_dividend(row,clock,scenario)
                component_decision = component_decisions.get(identity)
                if component_decision is not None:
                    apply_review(item, component_decision)
                elif (row["instrument_id"],row["day"]) in multiple_dividends:
                    item["blockers"].append("multiple_records_same_security_ex_date_require_component_review")
                if row["instrument_id"] in feature_excluded:
                    item["blockers"].append("reference_only_predecessor_never_earns_a_portfolio_right")
                if (row["instrument_id"],row["day"]) in boundary_actions:
                    item["blockers"].append("same_boundary_split_dividend_order_and_share_basis_require_review")
                cutoff = election_cutoffs.get(row["root_id"])
                if row["root_id"] in election_roots and (cutoff is None or row["day"] >= cutoff):
                    item["blockers"].append("lineage_contains_unresolved_special_election_dividend")
                if row["root_id"] in election_roots:
                    item["lineage_dependency_starts_on"] = cutoff
                if item["blockers"]:
                    item.update(status="blocked_terms",modeled_release_at=None)
                dividends.append(item)
            continue
        disposition = "requires_identity_or_economic_review"
        related = ambiguous.get(identity,{}).get("related_material_events",[])
        if identity in overrides:
            disposition = overrides[identity]["disposition"]
        elif identity in corporate_actions:
            disposition = "handled_by_reviewed_corporate_action"
        elif identity in context_decisions:
            disposition = "context_only_no_portfolio_credit"
        elif identity in ambiguous:
            disposition = ambiguous[identity]["status"]
        elif row["role"] == "acquirer_context_only_no_holder_credit":
            disposition = "context_only_no_portfolio_credit"
        elif row["category"] == "cash_mergers":
            record = json.loads(row["record"],parse_float=str)
            matches = [e for e in spec["material_events"] if e["parent_id"]==row["instrument_id"] and
                e["economic_date"]==row["day"] and e["kind"]=="cash_merger" and
                material_decisions.get(e["id"],{}).get("kind")=="primary_cash_consideration_reviewed" and
                number(str(record["rate"]),positive=True)==number(e["cash_per_parent"],positive=True)]
            if len(matches)==1:
                disposition="represented_by_reviewed_cash_merger"
                related=[matches[0]["id"]]
        event_routes.append(dict(instrument_id=row["instrument_id"],root_id=row["root_id"],event_id=row["event_id"],
            category=row["category"],day=row["day"],disposition=disposition,
            related_material_events=related,
            execution_ready=False,provider_record_preserved=True))
    streams = {s["instrument_id"]:s for s in spec["streams"]}
    material = [material_plan(e,clock,s,streams) for e in spec["material_events"] for s in SCENARIOS]
    if policy["owner_approved"]:
        for item in material:
            item["status"]="candidate_economic_terms_unresolved"
            item["accounting_assumptions_owner_approved"]=True
            item["blockers"]=[b for b in item["blockers"] if b!="Unapproved entitlement and timing assumptions"]
            if item["event_id"]=="peak_holding_company_reorganization":
                event=next(e for e in spec["material_events"] if e["id"]==item["event_id"])
                source=event["mapping_evidence"]
                facts=json.loads(checked_file(Path.cwd(),source["source"]).read_text(encoding="utf-8"))
                evidence=next(s for s in facts["sources"] if s["id"]==source["source_id"])
                validate_peak_continuity(event,evidence)
                item.update(status="admitted_diagnostic_continuity",diagnostic_terms_admitted=True,
                    blockers=[],actual_delivery_at=None,execution_ready=False)
    for item in dividends:
        item["accounting_assumptions_owner_approved"]=policy["owner_approved"]
    for item in material:
        if item["event_id"] in material_decisions:
            apply_material_terms(item, material_decisions[item["event_id"]], clock)
    output.mkdir(parents=True)
    write_json(output/"frozen_policy.json",policy)
    write_json(output/"dividend_candidates.json",dividends)
    write_json(output/"material_candidates.json",material)
    write_json(output/"corporate_actions.json",list(corporate_actions.values()))
    write_json(output/"election_candidates.json",election_schedules)
    write_csv(output/"event_routes.csv",[{k:json.dumps(v) if isinstance(v,list) else v for k,v in r.items()} for r in event_routes])
    summary = dict(revision=pin(revision_dir/"summary.json"),policy=pin(policy_path),
        execution=[pin("backtesting/diagnostic_preparation.py"),pin("backtesting/diagnostic_accounting.py"),
                   pin("backtesting/dividend_components.py"),pin("backtesting/diagnostic_event_terms.py"),
                   pin("backtesting/corporate_action_terms.py"),pin("backtesting/election_schedule.py"),pin("backtesting/election_terms.py")],
        dividend_component_review=None if dividend_review_path is None else pin(dividend_review_path),
        event_terms_review=None if event_terms_path is None else pin(event_terms_path),
        corporate_action_review=None if corporate_review_path is None else pin(corporate_review_path),
        election_schedule_inputs=None if election_inputs_path is None else pin(election_inputs_path),
        reviewed_corporate_actions=len(corporate_actions),election_schedules=len(election_schedules),
        holder_election_policy=None if holder_policy is None else holder_policy["choice"],
        holder_election_approval=None if holder_policy is None else holder_policy["approval"],
        election_lineage_dependency_cutoffs=election_cutoffs,
        reviewed_material_events=len(material_decisions),reviewed_context_only_records=len(context_decisions),
        reviewed_dividend_component_groups=len({(d["instrument_id"],d["ex_date"]) for d in component_decisions.values()}),
        selected_originals=revision["selected_originals"],candidate_streams=revision["candidate_streams"],
        provider_dividend_records=len(dividends)//len(SCENARIOS),dividend_plan_rows=len(dividends),
        base_dividend_status_counts=dict(Counter(d["status"] for d in dividends if d["scenario"]=="base")),
        base_blocker_counts=dict(Counter(b for d in dividends if d["scenario"]=="base" for b in d["blockers"])),
        base_dividends_missing_payable_date=sum(not d["provider_payable_date"] for d in dividends if d["scenario"]=="base"),
        multiple_dividend_groups=len(multiple_dividends),multiple_dividend_records=sum(len(ids) for ids in multiple_dividends.values()),
        material_event_records=len(spec["material_events"]),material_plan_rows=len(material),
        unresolved_feature_events=mapping["unresolved_feature_events"],
        event_route_counts=dict(Counter(r["disposition"] for r in event_routes)),
        output_files=[pin(output/n) for n in ("dividend_candidates.json","material_candidates.json","event_routes.csv",
                                            "corporate_actions.json","election_candidates.json")],
        owner_approved=policy["owner_approved"],performance_ready=False,step1_complete=False,strict_flags_promoted=False,
        paper_authorized=False,purchases_usd=0,broker_requests=0,orders=0,strategy_runs=0,unit_tests_run=0)
    write_json(output/"summary.json",summary)
    return summary


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision",type=Path,required=True)
    parser.add_argument("--policy",type=Path,required=True,help="Explicit versioned proposal/approved policy; execution pins must match")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--dividend-review",type=Path,help="Explicit pinned dividend component decisions; no automatic deduplication")
    parser.add_argument("--event-terms",type=Path,help="Explicit warmup exclusions, primary ratio facts and incoming-context review")
    parser.add_argument("--corporate-actions",type=Path,help="Pinned same-instrument aliases, split and preinvestment review")
    parser.add_argument("--election-inputs",type=Path,help="Conditional election inventory; no investor choice is inferred")
    args=parser.parse_args()
    with offline_only():
        print(json.dumps(prepare(args.revision,args.policy,args.output,args.dividend_review,args.event_terms,
                                 args.corporate_actions,args.election_inputs),indent=2))

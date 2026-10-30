"""Offline Step 2 admission gate for approved diagnostics and unresolved data.

Owner assent clears the modeling-choice gate. Every unresolved economic input
continues to block engine handoff. This module never instantiates a strategy,
relabels assumptions as strict evidence, or drops difficult instruments.
"""

import argparse
import csv
import json
from pathlib import Path

from backtesting.broad_collection import pin
from backtesting.cohort_audit import checked_file
from backtesting.diagnostic_preparation import validate_policy
from backtesting.pilot_readiness_review import offline_only, write_csv, write_json
from backtesting.dividend_components import validate_review_evidence
from backtesting.corporate_action_terms import gate_action
from backtesting.claim_accounting import number


class DiagnosticIntegrationBlocked(ValueError):
    pass


def assess(material,dividends,routes,feature_events,terms_review,membership_not_before,
           corporate_actions=(),election_schedules=()):
    blockers=[]
    resets=[]
    admitted_cash=set()
    corrections={e["instrument_id"]:e for e in terms_review["feature_corrections"]}
    for event in feature_events:
        correction=corrections.get(event["instrument_id"])
        if correction and correction["economic_date"] < membership_not_before and correction["no_pre_reset_feature_history"] is True:
            resets.append(dict(instrument_id=event["instrument_id"],from_session=correction["first_regular_session"],
                reason="Reviewed ADNT warmup distribution: reset features, no invested entitlement",source=correction["source"]))
        else:
            blockers.append(dict(kind="feature_event",instrument_id=event["instrument_id"],event_id="",reason=event["reason"]))
    for event in material:
        if event["scenario"]=="base":
            reset=event.get("required_feature_reset")
            if (event.get("status")=="inapplicable_preinvestable_event" and
                    event.get("no_portfolio_entitlement") is True and reset and
                    event["economic_date"] <= reset["from_session"] < membership_not_before and
                    reset["instrument_id"]==event["parent_id"]):
                resets.append(reset)
                continue
            if (event["event_id"]=="peak_holding_company_reorganization" and
                    event.get("diagnostic_terms_admitted") is True):
                continue
            if (event.get("status")=="admitted_diagnostic_cash_receivable" and event.get("kind")=="cash_merger" and
                    event.get("data_terms_resolved") is True and event.get("execution_ready") is False and
                    not event.get("share_legs") and not event.get("blockers") and
                    number(event["cash_per_parent"],positive=True)>0 and
                    event.get("cash_availability_policy")=="unspendable_receivable_no_invented_date" and
                    event.get("modeled_cash_release_at") is None and event.get("actual_delivery_at") is None and
                    event.get("required_ownership_snapshot_at") and event.get("consume_parent_once") is True and
                    event.get("invalidate_pending_orders_and_stops") is True):
                admitted_cash.add((event["parent_id"],event["event_id"]))
                continue
            blockers.append(dict(kind="material_terms",instrument_id=event["parent_id"],event_id=event["event_id"],
                reason="Conditional economic terms/holder entitlement/order not yet admitted; owner timing approval does not fill them"))
    for event in dividends:
        if event["scenario"]=="base" and event["blockers"]:
            # The separate predecessor reference can never be a portfolio
            # holding; retain the row as inapplicable rather than a run blocker.
            if "reference_only_predecessor_never_earns_a_portfolio_right" in event["blockers"]:
                continue
            blockers.append(dict(kind="dividend_terms",instrument_id=event["instrument_id"],event_id=event["event_id"],
                reason="; ".join(event["blockers"])))
    harmless={"context_only_no_portfolio_credit","wrong_predecessor_ratio_do_not_apply",
              "represented_by_peak_holding_company_reorganization_do_not_apply_twice"}
    reviewed_actions={(a["instrument_id"],a["event_id"]):a for a in corporate_actions}
    if len(reviewed_actions)!=len(corporate_actions):
        raise ValueError("Repeated corporate-action instruction identity")
    for event in routes:
        if event["disposition"]=="represented_by_reviewed_cash_merger":
            related=event.get("related_material_events",[])
            if isinstance(related,str):
                related=json.loads(related)
            if len(related)==1 and (event["instrument_id"],related[0]) in admitted_cash:
                continue
        if event["disposition"]=="handled_by_reviewed_corporate_action":
            action=reviewed_actions.get((event["instrument_id"],event["event_id"]))
            if action is not None and gate_action(action,membership_not_before):
                if action.get("required_feature_reset"):
                    resets.append(action["required_feature_reset"])
                continue
        if event["disposition"] not in harmless:
            blockers.append(dict(kind="provider_terms",instrument_id=event["instrument_id"],event_id=event["event_id"],reason=event["disposition"]))
    for event in election_schedules:
        if event["blockers"] or event.get("selected_holder_election") is None:
            blockers.append(dict(kind="election_schedule",instrument_id=event["instrument_id"],event_id=event["event_id"],
                reason="; ".join(event["blockers"]) or "Holder election remains unspecified"))
    resets=list({(r["instrument_id"],r["from_session"]):r for r in resets}.values())
    return dict(data_gates_clear=not blockers,blockers=blockers,effective_feature_resets=resets)


def require_data_ready(report):
    if report.get("owner_assumptions_approved") is not True or not report.get("data_gates_clear") or report.get("blockers"):
        raise DiagnosticIntegrationBlocked("Step 2 handoff blocked: unresolved input terms; no strategy or performance run started")


def prepare(preparation_dir,terms_review_path,output):
    if output.exists() or not output.resolve().is_relative_to(Path.cwd().resolve()):
        raise ValueError("Choose a fresh preflight directory in the workspace")
    preparation=json.loads((preparation_dir/"summary.json").read_text(encoding="utf-8"))
    policy=json.loads(checked_file(Path.cwd(),preparation["policy"]).read_text(encoding="utf-8"))
    validate_policy(policy)
    if policy["owner_approved"] is not True or preparation["owner_approved"] is not True:
        raise ValueError("Step 2 preflight requires recorded owner assent")
    for source in preparation["execution"]+preparation["output_files"]:
        checked_file(Path.cwd(),source)
    if preparation.get("dividend_component_review") is not None:
        review=json.loads(checked_file(Path.cwd(),preparation["dividend_component_review"]).read_text(encoding="utf-8"))
        validate_review_evidence(review)
    if preparation.get("event_terms_review") is not None:
        review=json.loads(checked_file(Path.cwd(),preparation["event_terms_review"]).read_text(encoding="utf-8"))
        checked_file(Path.cwd(),review["spec"])
        validate_review_evidence(review)
    if preparation.get("corporate_action_review") is not None:
        review=json.loads(checked_file(Path.cwd(),preparation["corporate_action_review"]).read_text(encoding="utf-8"))
        checked_file(Path.cwd(),review["spec"])
        validate_review_evidence(review)
    if preparation.get("election_schedule_inputs") is not None:
        inputs=json.loads(checked_file(Path.cwd(),preparation["election_schedule_inputs"]).read_text(encoding="utf-8"))
        for key in ("terms","split_review","resolution","mac_review","provider_source"):
            checked_file(Path.cwd(),inputs[key])
    revision=json.loads(checked_file(Path.cwd(),preparation["revision"]).read_text(encoding="utf-8"))
    spec=json.loads(checked_file(Path.cwd(),revision["spec"]).read_text(encoding="utf-8"))
    mapping=json.loads(checked_file(Path.cwd(),revision["mapping"]).read_text(encoding="utf-8"))
    terms=json.loads(terms_review_path.read_text(encoding="utf-8"))
    for source in terms["sources"]:
        checked_file(Path.cwd(),source["browser_text"])
    material=json.loads((preparation_dir/"material_candidates.json").read_text(encoding="utf-8"))
    dividends=json.loads((preparation_dir/"dividend_candidates.json").read_text(encoding="utf-8"))
    with (preparation_dir/"event_routes.csv").open(encoding="utf-8",newline="") as handle:
        routes=list(csv.DictReader(handle))
    actions_path=preparation_dir/"corporate_actions.json"
    elections_path=preparation_dir/"election_candidates.json"
    actions=json.loads(actions_path.read_text(encoding="utf-8")) if actions_path.exists() else []
    elections=json.loads(elections_path.read_text(encoding="utf-8")) if elections_path.exists() else []
    result=assess(material,dividends,routes,mapping["unresolved_feature_events"],terms,spec["membership_not_before"],actions,elections)
    result.update(date="2026-10-30",owner_assumptions_approved=True,approval=policy["approval"],
        allocation=dict(total_entry_exposure=.70,per_stock_entry_cap=.05,max_positions=20),
        preparation=pin(preparation_dir/"summary.json"),terms_review=pin(terms_review_path),
        execution=pin("backtesting/diagnostic_preflight.py"),selected_originals=preparation["selected_originals"],
        original_members_dropped=0,strict_flags_promoted=False,engine_handoff_ready=False,
        engine_adapter_integrated=False,performance_authorized=False,paper_authorized=False,
        purchases_usd=0,broker_requests=0,orders=0,strategy_runs=0)
    output.mkdir(parents=True)
    write_csv(output/"remaining_gates.csv",result["blockers"])
    write_json(output/"report.json",result)
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparation",type=Path,required=True)
    parser.add_argument("--terms-review",type=Path,default=Path("docs/broad_remaining_terms_review_2026-10-30.json"))
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    with offline_only():
        r=prepare(args.preparation,args.terms_review,args.output)
        print(json.dumps({k:v for k,v in r.items() if k!="blockers"},indent=2))
        print(json.dumps(dict(remaining_gates=len(r["blockers"]))))

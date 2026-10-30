"""Bind approved research defaults to their immutable proposal and owner record."""

from copy import deepcopy
import json
from pathlib import Path

from backtesting.broad_collection import pin
from backtesting.cohort_audit import checked_file


def validate_approval(policy):
    record=json.loads(checked_file(Path.cwd(),policy["approval"]).read_text(encoding="utf-8"))
    proposal=json.loads(checked_file(Path.cwd(),record["proposed_policy"]).read_text(encoding="utf-8"))
    checked_file(Path.cwd(),record["resolved_document"])
    if (record.get("owner_approved") is not True or record.get("diagnostic_accounting_defaults_approved") is not True or
            record.get("allocation") != dict(total_entry_exposure=.70,per_stock_entry_cap=.05,max_positions=20,scope="historical_research_only") or
            record.get("new_performance_batch_authorized") is not False or record.get("paper_authorized") is not False or
            record.get("max_strategy_runs") != 0 or record.get("purchases_usd") != 0):
        raise ValueError("Owner record does not approve these bounded research defaults")
    if policy.get("source_proposal") != record["proposed_policy"]:
        raise ValueError("Approved policy detached from frozen proposal")
    if policy.get("position_parameters_owner_approved") is not True:
        raise ValueError("Approved position settings must be marked as accepted")
    mutable={"owner_approved","position_parameters_owner_approved","implementation","approval","source_proposal"}
    if {k:v for k,v in policy.items() if k not in mutable} != {k:v for k,v in proposal.items() if k not in mutable}:
        raise ValueError("Research assumptions changed after owner approval")
    return record


def approved_policy(proposal_path,approval_path):
    policy=deepcopy(json.loads(proposal_path.read_text(encoding="utf-8")))
    policy.update(owner_approved=True,position_parameters_owner_approved=True,
                  approval=pin(approval_path),source_proposal=pin(proposal_path))
    policy["implementation"]=[pin("backtesting/"+n+".py") for n in
        ("diagnostic_accounting","diagnostic_preparation","diagnostic_approval")]
    validate_approval(policy)
    return policy

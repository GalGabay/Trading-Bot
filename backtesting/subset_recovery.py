"""One approved recovery segment; preserve all attempts in the stopped original."""

import argparse
from copy import deepcopy
from pathlib import Path
import sys
import time

from backtesting import subset_runner as runner

OWNER=Path("docs/subset_recovery_owner_approval_2026-10-30.json")
SCOPE=Path("docs/subset_recovery_proposal_2026-10-30.json")
PROOF=Path("docs/subset_recovery_driver_verification_2026-10-30.json")
OUTPUT=Path("data/reports/approved_subset_recovery_v1")
REPORT=Path("data/reports/approved_subset_combined_results_v1")


def approved_scope(owner, scope, cases):
    """Validate the exact exception, not a general permission to retry."""
    expected=dict(additional_attempts_limit=21,lifetime_attempts_limit=25,
        case_seconds=600,recovery_segment_seconds=3600)
    if (owner.get("owner_approved") is not True or
            any(owner.get(k)!=v or scope.get(k)!=v for k,v in expected.items()) or
            owner.get("max_workers")!=1 or scope.get("worker_limit")!=1 or
            scope.get("original_attempts_consumed")!=4 or scope.get("completed_unique_cases_retained")!=3 or
            scope.get("remaining_ordered_cases")!=cases[3:] or scope.get("one_retry_case")!=cases[3] or
            scope.get("stop_on_failure") is not True or scope.get("automatic_retry") is not False or
            scope.get("original_ledger_may_be_reset") is not False or
            owner.get("purchases_usd")!=0 or owner.get("broker_requests_authorized") is not False or
            owner.get("paper_authorized") is not False or owner.get("heldout_2024_2025_access") is not False):
        raise ValueError("Only the approved 21-attempt/25-lifetime bounded recovery is supported")


def original_state(scope):
    protocol=runner.read(runner.checked(scope["original_protocol"]))
    original=runner.read(runner.checked(scope["original_ledger"]))
    ids=[c["id"] for c in protocol["ordered_cases"]]
    if (original["scope"]!=runner.pin(runner.APPROVAL) or original["status"]!="stopped" or
            original["case_ids"]!=ids or len(original["attempts"])!=4 or len(original["completed"])!=3 or
            [a["id"] for a in original["attempts"]]!=ids[:4] or
            [a["id"] for a in original["completed"]]!=ids[:3] or
            original["attempts"][-1]["status"]!="failed_or_interrupted_no_retry"):
        raise ValueError("Original stopped batch/attempt lineage differs")
    for item in original["completed"]:
        result=runner.read(runner.checked(item["result_file"]))
        runner.checked(result["case_file"])
        if any(result[k]!=item[k] for k in result):
            raise ValueError("Original accepted result changed")
    return protocol,original


def authority(verification_path=PROOF):
    owner=runner.read(OWNER)
    if owner["proposal"]!=runner.pin(SCOPE) or owner["original_approval"]!=runner.pin(runner.APPROVAL):
        raise ValueError("Recovery detached from original approval/proposal")
    runner.checked(owner["review_document"])
    scope=runner.read(runner.checked(owner["proposal"]))
    protocol,original=original_state(scope)
    approved_scope(owner,scope,protocol["ordered_cases"])
    prior_owner=runner.read(runner.APPROVAL)
    for key in ("proposal","acceptance","review_context"):
        runner.checked(prior_owner[key])
    if protocol["ordered_cases"]!=runner.cases_for(runner.read(prior_owner["proposal"]["path"])):
        raise ValueError("Frozen strategy case order changed")

    # Historical source identities may only be resolved by the recorded exact
    # snapshots; current sources require a separate passing verification below.
    engineering=runner.read(runner.checked(scope["engineering_verification"]))
    snapshots={s["original"]["sha256"]:s["tracked_snapshot"] for s in engineering["archived_executed_sources"]}
    required=set()
    step2=runner.read(runner.STEP2)
    if step2["step2_integration_complete"] is not True or step2["approval"]!=runner.pin(runner.APPROVAL):
        raise ValueError("Historical Step 2 proof is missing")
    runner.checked(step2["saved_accounting_audit"])
    for field,entries in (("compilation","executions"),("unit_verification","execution"),
                          ("synthetic_control_comparisons","execution")):
        historical=runner.read(runner.checked(step2[field]))
        for entry in historical[entries]:
            required.add(entry["path"])
            runner.checked(snapshots.get(entry["sha256"],entry))
    proof=runner.read(verification_path)
    required.update({"backtesting/subset_recovery.py","backtesting/subset_runner.py",
        "backtesting/subset_results.py","tests/test_subset_recovery.py",
        "tests/test_subset_runner.py","tests/test_subset_results.py"})
    if (proof.get("passed") is not True or proof.get("tests_run",0)<280 or
            any(proof.get(k)!=0 for k in ("failures","errors","skipped")) or
            proof.get("approval")!=runner.pin(OWNER) or proof.get("proposal")!=runner.pin(SCOPE) or
            not required.issubset({p["path"] for p in proof["execution"]}) or
            proof.get("saved_case_reports_exactly_match")!=3 or proof.get("synthetic_control_checks")!=6):
        raise ValueError("Current passing recovery-driver verification required")
    for entry in proof["execution"]:
        runner.checked(entry)
    for key in ("log","saved_replay","synthetic_controls"):
        runner.checked(proof[key])
    return scope,original,proof


def validate_ledger(ledger,scope):
    ids=[c["id"] for c in scope["remaining_ordered_cases"]]
    attempts=ledger["attempts"]
    completed=ledger["completed"]
    if (ledger["status"] not in {"profiling","running","stopped","completed"} or
            ledger["case_ids"]!=ids or ledger["scope"]!=runner.pin(OWNER) or
            ledger.get("original_attempts_consumed")!=4 or ledger.get("lifetime_attempts_limit")!=25 or
            ledger.get("original_ledger")!=scope["original_ledger"] or
            ledger["total_seconds"]!=3600 or ledger["case_seconds"]!=600 or ledger["max_workers"]!=1 or
            len(attempts)>21 or len(completed)>len(attempts) or
            [a["id"] for a in attempts]!=ids[:len(attempts)] or
            [a["number"] for a in attempts]!=list(range(1,len(attempts)+1)) or
            [a["id"] for a in completed]!=ids[:len(completed)] or
            ledger["research_strategy_attempts"]!=len(attempts) or
            (ledger["status"]=="completed" and (len(attempts)!=21 or len(completed)!=21))):
        raise ValueError("Recovery budget/order/lifetime lineage differs")


def worker(task_path):
    scope,_,proof=authority()
    path=Path(task_path).resolve()
    if not path.is_relative_to(OUTPUT.resolve()) or path.name!="task.json":
        raise ValueError("Recovery worker requires its fixed execution directory")
    task=runner.read(path)
    if task["execution"]!=proof["execution"]:
        raise ValueError("Recovery task source pins differ from verified code")
    ledger=runner.read(OUTPUT/"budget/ledger.json")
    validate_ledger(ledger,scope)
    expected="profile" if task["kind"]=="profile" else f"case-{len(ledger['attempts']):02d}"
    if path.parent.name!=expected:
        raise ValueError("Recovery task directory differs from reservation")
    if task["kind"]=="case" and task["case"]!=scope["remaining_ordered_cases"][len(ledger["attempts"])-1]:
        raise ValueError("Recovery task differs from the exact approved case")
    runner.worker(path,run_directory=OUTPUT,budget_scope=runner.pin(OWNER))


def run():
    scope,original,proof=authority()
    if OUTPUT.exists():
        raise ValueError("Recovery already has state; no retry, resume or budget reset")
    OUTPUT.mkdir(parents=True,exist_ok=False)
    cases=scope["remaining_ordered_cases"]
    budget=runner.Budget(OUTPUT/"budget",runner.pin(OWNER),[c["id"] for c in cases],total_seconds=3600,case_seconds=600)
    budget.state.update(original_attempts_consumed=4,lifetime_attempts_limit=25,original_ledger=scope["original_ledger"])
    budget.save()
    def task(kind,case=None):
        folder=OUTPUT/("profile" if kind=="profile" else f"case-{len(budget.state['attempts'])+1:02d}")
        folder.mkdir()
        path=folder/"task.json"
        runner.atomic_json(path,dict(kind=kind,case=case,execution=proof["execution"]))
        return path
    def execute(path,allowance):
        return runner.supervise([sys.executable,"-m","backtesting.subset_recovery","--worker",str(path)],
            path.parent/"process",allowance)
    try:
        path=task("profile")
        elapsed=execute(path,min(600,budget.remaining()))
        profile=runner.read(path.parent/"result.json")
        if profile.get("passed") is not True or profile.get("research_strategy_runs")!=0:
            raise ValueError("Successful zero-strategy recovery profile required")
        budget.profile_passed(dict(result=runner.pin(path.parent/"result.json"),elapsed_seconds=elapsed))
        print(f"Recovery profile passed in {elapsed:.1f}s; original 4 attempts remain counted.",flush=True)
        for case in cases:
            authority()
            validate_ledger(budget.state,scope)
            path=task("case",case)
            allowance=budget.reserve(case["id"],runner.pin(path))
            print(f"Starting lifetime attempt {4+len(budget.state['attempts'])}/25: {case['id']}",flush=True)
            elapsed=execute(path,allowance)
            authority()
            result=runner.read(path.parent/"result.json")
            runner.checked(result["case_file"])
            if (any(result[k]!=case[k] for k in case) or result.get("ledger_reconciled") is not True or
                    result.get("external_source_prices_verified") is not True):
                raise ValueError("Recovery result identity or reconciliation differs")
            budget.finish(dict(**result,result_file=runner.pin(path.parent/"result.json"),elapsed_seconds=elapsed))
            print(f"Completed {3+len(budget.state['completed'])}/24 distinct cases: "
                f"return {result['metrics']['net_marked_return_after_estimated_whole_share_exits']:.4%}",flush=True)
        budget.state.update(status="completed",completed_at_epoch=time.time())
        validate_ledger(budget.state,scope)
        budget.save()
    except BaseException as exc:
        budget.stop(f"{type(exc).__name__}: {exc}")
        raise
    finally:
        runner.atomic_json(OUTPUT/"summary.json",dict(status=budget.state["status"],approval=runner.pin(OWNER),
            verification=runner.pin(PROOF),ledger=runner.pin(budget.path),original_ledger=scope["original_ledger"],
            original_attempts=4,attempts=len(budget.state["attempts"]),
            lifetime_attempts=4+len(budget.state["attempts"]),completed=len(budget.state["completed"]),
            completed_unique_cases=3+len(budget.state["completed"]),stop_reason=budget.state.get("stop_reason"),
            purchases_usd=0,broker_requests=0,orders=0,heldout_2024_2025_files_read=0,paper_authorized=False))
    return budget.state


def combine(original,ledger,execution,cases):
    combined=deepcopy(ledger)
    combined["completed"]=original["completed"]+ledger["completed"]
    ids=[r["id"] for r in combined["completed"]]
    if len(set(ids))!=len(ids) or ids!=[c["id"] for c in cases][:len(ids)]:
        raise ValueError("Combined cases are duplicated or out of original order")
    result=dict(execution,approval=runner.pin(runner.APPROVAL),
        attempts=4+len(ledger["attempts"]),completed=len(ids))
    if result["attempts"]>25 or (result["status"]=="completed" and len(ids)!=24):
        raise ValueError("Combined case/attempt completion differs")
    return result,combined


def report_evidence(run_directory,execution,ledger):
    if Path(run_directory).resolve()!=OUTPUT.resolve():
        raise ValueError("Only the approved recovery directory may be combined")
    scope,original,_=authority()
    validate_ledger(ledger,scope)
    if (execution["approval"]!=runner.pin(OWNER) or execution["original_ledger"]!=scope["original_ledger"] or
            execution["status"]!=ledger["status"] or
            execution["lifetime_attempts"]!=4+len(ledger["attempts"]) or
            execution["attempts"]!=len(ledger["attempts"]) or execution["completed"]!=len(ledger["completed"])):
        raise ValueError("Recovery summary and ledger differ")
    protocol=runner.read(runner.checked(scope["original_protocol"]))
    combined_execution,combined=combine(original,ledger,execution,protocol["ordered_cases"])
    evidence=dict(recovery_approval=runner.pin(OWNER),original_ledger=scope["original_ledger"],
        recovery_ledger=runner.pin(OUTPUT/"budget/ledger.json"),original_attempts=4,
        recovery_attempts=len(ledger["attempts"]),lifetime_attempts=4+len(ledger["attempts"]))
    return combined_execution,combined,evidence


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker",type=Path)
    parser.add_argument("--report",action="store_true")
    args=parser.parse_args()
    if args.worker is not None and args.report:
        parser.error("Choose worker or report")
    if args.worker is not None:
        worker(args.worker)
    elif args.report:
        from backtesting.subset_results import summarize
        print(summarize(REPORT,OUTPUT,recovery=True)["step3_complete"])
    else:
        run()

"""One explicitly reviewed child probe using the SAME cumulative Step1 budget."""

from copy import deepcopy
from datetime import UTC, datetime
import json
from pathlib import Path
import time

from app.broker.research_client import HistoricalResearchClient
from backtesting.broad_collection import pin
from backtesting.cohort_audit import checked_file
from backtesting.pilot_readiness_review import write_json
from backtesting.successor_collection import RecordedOpener, load_plan

PLAN=Path("docs/broad_successor_branch_probe.json")
OUTPUT=Path("data/reports/broad_successor_branch_probe_v1")
JOURNAL=Path("data/reports/broad_successor_branch_probe_execution.json")


def collect():
    parent_plan=load_plan()
    plan=json.loads(PLAN.read_text(encoding="utf-8"))
    parent=json.loads(checked_file(Path.cwd(),plan["parent_report"]).read_text(encoding="utf-8"))
    checked_file(Path.cwd(),plan["provider_evidence"])
    for path,sha in plan["execution_sha256"].items():
        checked_file(Path.cwd(),dict(path=path,sha256=sha))
    if len(parent["probes"])+1>parent_plan["limits"]["max_probe_intervals"] or plan["purchases_usd"]!=0:
        raise ValueError("Cumulative probe/spending scope exceeded")
    probe=plan["probe"]
    if probe!={"id":"bwa_phin","symbol":"PHIN","start":"2023-07-05","end_exclusive":"2024-01-01","readiness":False}:
        raise ValueError("Only the newly identified frozen PHIN branch is authorized")
    origin=datetime.fromisoformat(plan["conservative_budget_origin_utc"]).timestamp()
    age=time.time()-origin
    if age<0 or age>=900:
        raise ValueError("Original Step1 elapsed allowance is exhausted; do not reset")
    if OUTPUT.exists(): raise FileExistsError("Preserve original branch probe")
    with JOURNAL.open("x",encoding="utf-8") as handle: json.dump(dict(plan=pin(PLAN),state="started_do_not_retry"),handle)
    OUTPUT.mkdir()
    report=dict(plan=pin(PLAN),parent_report=plan["parent_report"],attempts=deepcopy(parent["attempts"]),
                probes=[],completed=False,stop_reason=None,purchases_usd=0,orders=0,account_requests=0)
    def save(): write_json(OUTPUT/"report.json",report)
    save()
    client=HistoricalResearchClient()
    client.request_count=len(parent["attempts"])
    recorder=RecordedOpener(report,save,parent_plan["limits"])
    recorder.started=time.monotonic()-age
    client._opener=recorder
    item=dict(probe)
    report["probes"].append(item)
    try:
        for resource in ("bars","actions"):
            recorder.page_path=OUTPUT/f"{resource}_1.json"
            recorder.probe_id,recorder.resource=probe["id"],resource
            if resource=="bars":
                page=client.bars_page(symbol=probe["symbol"],start=datetime(2023,7,5,tzinfo=UTC),end_exclusive=datetime(2024,1,1,tzinfo=UTC))
            else: page=client.actions_page(symbol=probe["symbol"])
            item[resource]=dict(status="downloaded_candidate" if page.get("next_page_token") is None else "incomplete_no_followup",pages=[pin(recorder.page_path)])
        report["completed"]=True
    except Exception as exc:
        report["stop_reason"]="stopped_no_retry_"+type(exc).__name__
    finally:
        save()
        write_json(JOURNAL,dict(plan=pin(PLAN),report=pin(OUTPUT/"report.json"),state="closed_do_not_restart"))
    return dict(completed=report["completed"],new_attempts=len(report["attempts"])-len(parent["attempts"]),cumulative_attempts=len(report["attempts"]))


if __name__=="__main__": print(json.dumps(collect(),indent=2))

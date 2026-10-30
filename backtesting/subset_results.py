"""Summarize saved approved comparison cases; no signals, prices or new runs."""

import argparse
from collections import Counter
import csv
from fractions import Fraction
import gzip
from math import isclose
from pathlib import Path
from statistics import median

from backtesting.subset_runner import APPROVAL,OUTPUT,checked,pin,read,atomic_json


def contributions(case):
    report=case["diagnostic_accounting"]
    streams=report["universe"]["streams"]
    roots={s["instrument_id"]:s["root_id"] for s in streams}
    names={s["root_id"]:s["snapshot_alias"] for s in streams if s.get("role")=="original_member"}
    values=Counter()
    for row in report["journal"]:
        if row["kind"]=="simulated_sell":
            values[roots[row["instrument_id"]]]+=float(Fraction(row["proceeds"])-Fraction(row["basis"]))
        elif row["kind"]=="diagnostic_cash_release":
            claim=row["claim_id"]
            if claim.startswith("dividend:"):
                event=next(d for d in report["schedule"]["dividends"] if claim==f"dividend:{d['event_id']}")
                key=event["instrument_id"]
            else:
                event=next(e for e in report["schedule"]["material"] if claim.startswith(f"diagnostic:{e['event_id']}:"))
                key=event["parent_id"]
            values[roots[key]]+=float(Fraction(row["amount"])-Fraction(row["basis"]))
    final=report["marks"][-1]
    quotes=report["days"][-1]["quotes"]
    for lot in final["lots"]:
        key=lot["instrument_id"]
        values[roots[key]]+=lot["quantity"]*float(quotes[key]["close"])-float(Fraction(lot["basis"]))
    for claim in final["claims"]:
        key=claim["instrument_id"]
        value=float(Fraction(claim["amount"])) if claim["kind"]=="cash" else float(Fraction(claim["units"]))*float(quotes[key]["close"])
        values[roots[key]]+=value-float(Fraction(claim["basis"]))
    profit=case["metrics"]["final_equity"]-case["metrics"]["initial_cash"]
    if not isclose(sum(values.values()),profit,abs_tol=1e-6):
        raise ValueError("Per-root P&L does not reconcile with marked account profit")
    return [dict(root_id=key,snapshot_alias=names.get(key,key),marked_profit_before_estimated_final_exits=values[key]) for key in sorted(set(roots.values()))]


def summarize(output, run_directory=OUTPUT, *, recovery=False):
    if output.exists() or not output.resolve().is_relative_to(Path.cwd().resolve()):
        raise ValueError("Choose a fresh result-report directory inside the workspace")
    execution=read(run_directory/"summary.json")
    ledger=read(checked(execution["ledger"]))
    recovery_evidence={}
    if recovery:
        from backtesting.subset_recovery import report_evidence
        execution,ledger,recovery_evidence=report_evidence(run_directory,execution,ledger)
    if execution["status"] not in {"completed","stopped"} or ledger["status"]!=execution["status"]:
        raise ValueError("Wait for the batch to finish or stop before a final result report")
    if execution["approval"]!=pin(APPROVAL) or execution["attempts"]>(25 if recovery else 24) or execution["completed"]>execution["attempts"]:
        raise ValueError("Execution exceeds or differs from the approved scope")
    rows=[]
    per_root=[]
    for item in ledger["completed"]:
        result=read(checked(item["result_file"]))
        if result["id"]!=item["id"] or result["metrics"]!=item["metrics"]:
            raise ValueError("Accepted result differs from the persistent ledger")
        with gzip.open(checked(result["case_file"]),"rt",encoding="utf-8") as handle:
            import json
            case=json.load(handle)
        if case["research_case"]["id"]!=result["id"]:
            raise ValueError("Full case identity differs from the accepted result")
        metrics=result["metrics"]
        curve=case["equity_curve"]
        stock_use=sum(p["exposure"]-(p["dividend_receivable"]+p["ownership_cash_receivable"])/p["equity"] for p in curve)/len(curve)
        exits=[r["holding_days"] for r in case["diagnostic_accounting"]["fill_details"] if r["side"]=="SELL"]
        rows.append(dict(id=result["id"],arm=result["arm"],window=result["window"],cost=result["cost"],scenario=result["scenario"],
            net_marked_return=metrics["net_marked_return_after_estimated_whole_share_exits"],net_marked_cagr=metrics["net_marked_cagr"],
            net_marked_profit=metrics["net_marked_profit_after_estimated_whole_share_exits"],final_cash=metrics["final_spendable_cash"],
            unpaid_right_value=metrics["outstanding_claim_value"],closing_drawdown=metrics["max_drawdown"],
            conservative_drawdown_bound=metrics["conservative_drawdown_bound"],
            mean_closing_exposure=metrics["mean_closing_exposure"],mean_stock_and_share_claim_exposure=stock_use,
            mean_cash_fraction=metrics["mean_cash_fraction"],completed_trades=metrics["completed_trades"],
            closed_instruments=metrics["instruments_with_closed_trades"],profit_factor=metrics["profit_factor"],
            average_holding_calendar_days=metrics["average_holding_days"],median_holding_calendar_days=median(exits) if exits else None,
            max_holding_calendar_days=max(exits,default=None),mean_position_count=metrics["mean_position_count"],
            max_positions=metrics["max_observed_positions"],max_root_exposure=metrics["maximum_single_root_exposure"],
            modeled_trade_cost=metrics["total_modeled_trade_cost"],turnover_notional_over_initial_capital=metrics["traded_notional"]/metrics["initial_cash"],
            evaluation_checks=metrics["evaluation_checks"],elapsed_seconds=item["elapsed_seconds"]))
        per_root.extend(dict(case_id=result["id"],**row) for row in contributions(case))
    output.mkdir(parents=True)
    with (output/"all_cases.csv").open("w",encoding="utf-8",newline="") as handle:
        fields=[k for k in rows[0] if k!="evaluation_checks"] if rows else ["id"]
        writer=csv.DictWriter(handle,fieldnames=fields)
        writer.writeheader()
        writer.writerows({k:r[k] for k in fields} for r in rows)
    with (output/"root_contributions.csv").open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=["case_id","root_id","snapshot_alias","marked_profit_before_estimated_final_exits"])
        writer.writeheader()
        writer.writerows(per_root)
    primary=[r for r in rows if r["cost"]=="pessimistic" and r["scenario"]=="base"]
    summary=dict(date="2026-10-30",status=execution["status"],current_step=3,
        step3_complete=execution["status"]=="completed" and len(rows)==24,
        strategy_attempts=execution["attempts"],completed_strategy_runs=len(rows),stop_reason=execution["stop_reason"],
        execution_summary=pin(run_directory/"summary.json"),ledger=execution["ledger"],approval=pin(APPROVAL),
        report_execution=pin(Path(__file__)),all_cases=rows,primary_pessimistic_base_availability=primary,
        all_case_rows=pin(output/"all_cases.csv"),root_contributions=pin(output/"root_contributions.csv"),
        per_root_marked_pnl_reconciled=True,paper_authorized=False,purchases_usd=0,broker_requests=0,orders=0,
        limitations=["Historical data-availability-selected exploratory subset; not all-market or paper acceptance evidence",
            "2017-2021 and 2022-2023 start separate simulated accounts; do not compound them into one continuous result",
            "Net marked returns include nominal unpaid rights and estimated exits of whole shares, not settled cash profit",
            "Daily OHLC risk bounds are conservative; exact intraday drawdown/exit time is unobserved"])
    summary.update(recovery_evidence)
    atomic_json(output/"summary.json",summary)
    return summary


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=summarize(args.output)
    print({k:result[k] for k in ("status","strategy_attempts","completed_strategy_runs","step3_complete")})

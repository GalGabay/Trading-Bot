"""Validate and summarize an existing 24-run diagnostic; never run a strategy."""

import argparse
from itertools import product
import json
from math import isclose
from pathlib import Path

from backtesting.cohort_audit import digest, checked_file
from backtesting.pilot_readiness_review import offline_only, write_csv, write_json
from backtesting.pilot_diagnostic import APPROVAL, execution_hashes, POLICIES

SOURCE = Path("data/reports/limited_pilot_experiment_v1")


def summarize(output):
    if output.exists():
        raise FileExistsError("Choose a fresh summary directory")
    approval=json.loads(APPROVAL.read_text(encoding="utf-8"))
    proposal=json.loads(checked_file(Path.cwd(),approval["proposal"]).read_text(encoding="utf-8"))
    report=json.loads((SOURCE/"report.json").read_text(encoding="utf-8"))
    verification_path=Path("data/reports/limited_pilot_verification_v1/verification.json")
    verification=json.loads(verification_path.read_text(encoding="utf-8"))
    expected={f"{w['id']}_{capital}_{cost['id']}_{p}" for w,capital,cost,p in product(
        proposal["windows"],proposal["account_sizes_usd"],proposal["costs"],POLICIES)}
    if (report["status"]!="completed" or set(report["attempts"])!=expected or len(report["attempts"])!=24
            or {r["id"] for r in report["runs"]}!=expected or len(report["runs"])!=24
            or report["approval_sha256"]!=digest(APPROVAL) or report["execution_sha256"]!=execution_hashes()
            or report["verification_sha256"]!=digest(verification_path) or not verification["passed"]):
        raise ValueError("Execution budget, scope, approval or verification mismatch")
    if digest(verification_path.parent/"unittest.log")!=verification["log_sha256"]:
        raise ValueError("Unit verification log changed")
    rows, cases, pins = [], {}, {}
    for run in report["runs"]:
        path=checked_file(Path.cwd(),dict(path=(SOURCE/run["file"]).as_posix(),sha256=run["sha256"]))
        case=json.loads(path.read_text(encoding="utf-8"))
        m=case["metrics"]
        if m!=run["metrics"] or not case["diagnostic_risk"]["ledger_reconciled"]:
            raise ValueError("Case summary or ledger differs")
        mode=case["universe_metadata"]["diagnostic_research"]
        if mode["cash_policy"]!=run["cash_policy"] or mode["broker_cash_credit_verified"] is not False:
            raise ValueError("Diagnostic flags or policy differ")
        if len({e["event_id"] for e in case["dividend_entitlements"]})!=len(case["dividend_entitlements"]):
            raise ValueError("Duplicate earned cash right")
        expected_pnl=m["realized_trading_pnl"]+m["marked_unrealized_pnl"]+m["dividend_income_earned"]
        if not isclose(expected_pnl,m["final_equity"]-run["capital"],abs_tol=1e-6):
            raise ValueError("Diagnostic P&L fails independent summary check")
        if run["cash_policy"]=="no_credit" and case["dividend_payments"]:
            raise ValueError("No-credit scenario paid cash")
        if run["cash_policy"]=="no_credit" and not isclose(m["dividend_income_earned"],m["final_receivable"],abs_tol=1e-6):
            raise ValueError("No-credit scenario lost an earned right")
        if m["final_receivable"] and m["hypothetical_liquidated_return"] is not None:
            raise ValueError("Unpaid rights mislabeled as liquidated return")
        if not isclose(sum(v["net_marked_profit"] for v in case["instrument_contributions"].values()),expected_pnl,abs_tol=1e-6):
            raise ValueError("Contribution totals differ")
        rows.append(dict(window=run["window"],capital=run["capital"],cost=run["cost"],cash_policy=run["cash_policy"],
            net_marked_profit=m["net_account_profit"],net_marked_profit_after_estimated_share_exits=run["capital"]*m["net_marked_return_after_estimated_share_exits"],
            total_marked_return=m["total_return"],marked_return_after_estimated_share_exits=m["net_marked_return_after_estimated_share_exits"],
            annualized_marked_return_after_estimated_share_exits=m["net_marked_cagr_after_estimated_share_exits"],
            max_closing_drawdown=m["max_drawdown"],daily_ohlc_drawdown_lower_bound=case["diagnostic_risk"]["conservative_drawdown_bound"],
            completed_trades=m["completed_trades"],closed_instruments=m["instruments_with_closed_trades"],
            dividend_income_earned=m["dividend_income_earned"],cash_dividends_received=m["dividend_cash_received"],
            final_receivable=m["final_receivable"],final_spendable_cash=m["final_spendable_cash"],
            realized_trading_pnl=m["realized_trading_pnl"],open_marked_pnl=m["marked_unrealized_pnl"],
            estimated_share_exit_cost=m["hypothetical_exit_cost"],commissions=m["commissions_paid"],
            slippage_cost=m["modeled_slippage_cost"],spread_cost=m["modeled_spread_cost"],
            mean_closing_exposure=m["mean_closing_exposure"],mean_spendable_cash_fraction=m["mean_cash_fraction"],
            mean_completed_holding_sessions=case["holding_statistics"]["completed_holding_sessions_mean"],
            longest_completed_holding_sessions=case["holding_statistics"]["completed_holding_sessions_max"],
            return_hurdle_met=m["net_marked_cagr_after_estimated_share_exits"]>=.06,
            enough_closed_trades=m["completed_trades"]>=30,enough_instruments=m["instruments_with_closed_trades"]>=5,
            eligible_for_paper=False))
        cases[run["id"]]=case
        pins[path.relative_to(Path.cwd()).as_posix()]=digest(path)
    sensitivities=[]
    for w,capital,cost in product(proposal["windows"],proposal["account_sizes_usd"],proposal["costs"]):
        group=[r for r in rows if (r["window"],r["capital"],r["cost"])==(w["id"],capital,cost["id"])]
        prefix=f"{w['id']}_{capital}_{cost['id']}_"
        fill_lists=[cases[prefix+p]["fills"] for p in POLICIES]
        if not all(fills==fill_lists[0] for fills in fill_lists):
            same=False
        else:
            same=True
        sensitivities.append(dict(window=w["id"],capital=capital,cost=cost["id"],same_fills=same,
            marked_return_min=min(v["total_marked_return"] for v in group),marked_return_max=max(v["total_marked_return"] for v in group),
            cash_delay_changes_trade_path=not same,no_credit_rights=cases[prefix+"no_credit"]["final_dividend_receivables"]))
    output.mkdir(parents=True,exist_ok=False)
    write_csv(output/"all_runs.csv",rows)
    write_json(output/"cash_sensitivity.json",sensitivities)
    summary=dict(schema_version=1,completed_on="2026-10-29",status="completed_exploratory_not_a_paper_candidate",
        owner_approval=dict(path=APPROVAL.as_posix(),sha256=digest(APPROVAL)),
        frozen_proposal=approval["proposal"],execution_report=dict(path=(SOURCE/"report.json").as_posix(),sha256=digest(SOURCE/"report.json")),
        verification=dict(path=verification_path.as_posix(),sha256=digest(verification_path),tests_run=verification["tests_run"],
            failures=verification["failures"],errors=verification["errors"],skipped=verification["skipped"],
            real_schedule_checks=len(verification["schedule_checks"]),legacy_accounting_checks=len(verification["legacy_accounting_replay"]["checks"])),
        code_sha256={**execution_hashes(),"backtesting/pilot_diagnostic_report.py":digest("backtesting/pilot_diagnostic_report.py")},
        case_sha256=pins,strategy_attempts=len(report["attempts"]),completed_strategy_runs=len(rows),
        all_24_risk_and_financial_ledgers_reconciled=True,all_run_rows=rows,cash_sensitivity=sensitivities,
        primary_pessimistic=[r for r in rows if r["capital"]==10000 and r["cost"]=="pessimistic" and r["cash_policy"]=="base"],
        all_cagr_below_six_percent=all(not r["return_hurdle_met"] for r in rows),
        all_cash_scenarios_same_fills=all(r["same_fills"] for r in sensitivities),
        original_strict_evidence_flags_unchanged=True,independently_verified_entitlement=False,
        broker_cash_credit_verified=False,investment_criteria_changed=False,broader_universe_qualified=False,
        original_506_register_preserved=True,registered_nine_stock_control_unchanged=True,jpm_collection_parked=True,
        network_requests=0,new_price_requests=0,broker_account_requests=0,orders=0,purchases_usd=0,
        reserved_candles_read=False,paper_authorized=False,dependency_installations=0,raspberry_pi_verified=False,
        outputs={p.name:digest(p) for p in output.iterdir()},
        limitations=["Two surviving stocks chosen for engineering availability, not an unbiased investment universe",
            "Provider-dependent ex-dates, clipped identity coverage and action completeness remain exploratory assumptions",
            "Marked returns can contain unpaid nominal rights; estimated share exits do not settle those rights",
            "Daily-OHLC risk bounds do not measure actual intraday paths; taxes and idle-cash yield omitted",
            "Frozen small allocations and two names leave most capital idle; this experiment cannot meet five-instrument acceptance",
            "No claim of improvement versus old different-universe/all-adjusted studies; no new rule comparison"])
    write_json(output/"summary.json",summary)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    with offline_only():
        r=summarize(args.output)
    print(json.dumps(dict(completed_runs=r["completed_strategy_runs"],all_ledgers_reconcile=True,
        all_cagr_below_six_percent=r["all_cagr_below_six_percent"],cash_scenario_fills_identical=r["all_cash_scenarios_same_fills"])))


if __name__=="__main__":
    main()

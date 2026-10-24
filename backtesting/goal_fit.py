"""Offline owner-goal audit. Frozen pre-2024 inputs only; no broker calls.

Run: python -m backtesting.goal_fit --output-dir data/reports/study_c_goal_fit
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import replace
from math import isclose, isfinite
from pathlib import Path, PureWindowsPath
from importlib.metadata import version

import numpy as np
import pandas as pd

from backtesting.allocation_research import ARMS, simulate_policy
from backtesting.daily_research import SYMBOLS, assert_baseline_matches, load_study_data, passive_spy
from backtesting.earlier_history import CALENDAR_NAME, SnapshotCalendar, _pack_window, join_history, load_extension
from backtesting.research import COST_SCENARIOS
from backtesting.risk_diagnostics import daily_risk_envelope

POLICY = Path("config/research_acceptance.json")
PROTOCOL = Path("docs/study_c_goal_fit_protocol.md")
R3 = Path("data/reports/study_c_r3_final/report.json")
R4 = Path("data/reports/study_c_r4/report.json")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def frozen_source_path(name):
    """Resolve legacy Windows report paths against the current repo on Pi too."""
    parts = PureWindowsPath(name).parts
    for index, part in enumerate(parts):
        if part in {"backtesting", "app"}:
            candidate = Path(*parts[index:])
            if ".." in candidate.parts or candidate.suffix != ".py":
                continue
            if candidate.is_file() and candidate.resolve().is_relative_to(Path(part).resolve()):
                return candidate
    raise ValueError(f"Cannot resolve frozen repository source: {name}")


def load_policy(path):
    policy = json.loads(path.read_text(encoding="utf-8"))
    if policy.get("approved_for_development_audit") is not True:
        raise ValueError("Development audit criteria require recorded approval")
    if policy.get("approved_for_final_evaluation") is not False or policy.get("approved_for_paper") is not False:
        raise ValueError("This research record must not authorize holdout or paper orders")
    if policy["reserved_start"] != "2024-01-01" or policy["drawdown_basis"] != "running_account_equity_peak":
        raise ValueError("Unexpected holdout boundary or drawdown convention")
    for key in ("annual_return_cagr_minimum", "drawdown_rejection_level", "drawdown_review_level", "daily_loss_rejection_level"):
        if isinstance(policy[key], bool) or not isinstance(policy[key], (int, float)) or not isfinite(policy[key]) or not 0 < policy[key] < 1:
            raise ValueError(f"Invalid research fraction: {key}")
    if not policy["drawdown_review_level"] < policy["drawdown_rejection_level"]:
        raise ValueError("Review drawdown must be below the rejection level")
    for key in ("minimum_completed_trades", "minimum_instruments"):
        if type(policy[key]) is not int or policy[key] < 1:
            raise ValueError(f"Invalid evidence floor: {key}")
    if isinstance(policy["minimum_profit_factor"], bool) or not isinstance(policy["minimum_profit_factor"], (int, float)) or not isfinite(policy["minimum_profit_factor"]) or policy["minimum_profit_factor"] <= 1:
        raise ValueError("Profit factor threshold must be finite and greater than one")
    if policy["audit_account_sizes"] != [100000, 10000]:
        raise ValueError("Account sizes differ from the registered audit")
    return policy


def above_loss_limit(value, limit):
    return value > -limit and not isclose(value, -limit, rel_tol=0, abs_tol=1e-12)


def checks_for(metrics, years, policy):
    cagr = (1 + metrics["hypothetical_liquidated_return"]) ** (1 / years) - 1
    pf = metrics["profit_factor"]
    checks = {
        "net_cagr_meets_minimum": "pass" if cagr >= policy["annual_return_cagr_minimum"] or isclose(cagr, policy["annual_return_cagr_minimum"], rel_tol=0, abs_tol=1e-12) else "fail",
        "closing_drawdown_below_rejection_level": "pass" if above_loss_limit(metrics["max_drawdown"], policy["drawdown_rejection_level"]) else "fail",
        "daily_closing_loss_below_rejection_level": "pass" if above_loss_limit(metrics["worst_closing_daily_return"], policy["daily_loss_rejection_level"]) else "fail",
        "sufficient_closed_trades": "pass" if metrics["completed_trades"] >= policy["minimum_completed_trades"] else "inconclusive",
        "sufficient_closed_instruments": "pass" if metrics["instruments_with_closed_trades"] >= policy["minimum_instruments"] else "inconclusive",
        "positive_realized_profit": "pass" if metrics["realized_pnl"] > 0 else "fail",
        "profit_factor_meets_minimum": "inconclusive" if pf is None or not isfinite(pf) else "pass" if pf >= policy["minimum_profit_factor"] else "fail",
        "no_permanent_halt": "pass" if metrics["permanent_halt_reason"] is None else "fail",
        "actual_intraday_drawdown_measured": "inconclusive",
    }
    return {"net_liquidated_cagr": cagr, "checks": checks,
            "closing_drawdown_review_flag": not above_loss_limit(metrics["max_drawdown"], policy["drawdown_review_level"]),
            "decision": "does_not_qualify" if "fail" in checks.values() else "inconclusive"}


def cost_attribution(case, risk, years, policy):
    costs, m = case["costs"], case["metrics"]
    multiplier = (costs["slippage_bps"] + costs["spread_bps"] / 2) / 10000
    slippage = spread = 0.0
    for fill in case["fills"]:
        # Stop reference_open is the session open, not the stop trigger price.
        # Recover the actual stop reference from this fixed candidate's
        # known adverse multiplier; no extra stop stress is in these runs.
        reference = (fill["fill_price"] / (1 - multiplier)
                     if fill["signal_reason"].startswith("PROTECTIVE_STOP_") else fill["reference_open"])
        expected = reference * (1 + multiplier if fill["side"] == "BUY" else 1 - multiplier)
        if not isclose(expected, fill["fill_price"], abs_tol=1e-8):
            raise ValueError("Cost attribution differs from declared fill model")
        slippage += reference * fill["quantity"] * costs["slippage_bps"] / 10000
        spread += reference * fill["quantity"] * costs["spread_bps"] / 20000
    commission = sum(fill["commission"] for fill in case["fills"])
    pnl = m["realized_pnl"] + m["marked_unrealized_pnl"]
    if not isclose(pnl, m["final_equity"] - costs["initial_cash"], abs_tol=1e-6):
        raise ValueError("Realized/unrealized P&L does not reconcile")
    total_cost = slippage + spread + commission
    exposures = [point["exposure"] for point in case["equity_curve"]]
    return {
        "realized_pnl": m["realized_pnl"], "open_marked_pnl": m["marked_unrealized_pnl"],
        "net_account_profit": pnl, "commissions": commission, "modeled_slippage_cost": slippage,
        "modeled_half_spread_cost": spread, "modeled_cost_total": total_cost,
        "fixed_fill_path_profit_before_cost_addback": pnl + total_cost,
        "hypothetical_final_exit_cost": m["hypothetical_exit_cost"],
        "net_profit_after_estimated_final_exits": pnl - m["hypothetical_exit_cost"],
        "profit_required_for_goal": costs["initial_cash"] * ((1 + policy["annual_return_cagr_minimum"]) ** years - 1),
        "goal_shortfall_dollars": costs["initial_cash"] * (1 + policy["annual_return_cagr_minimum"]) ** years - (m["final_equity"] - m["hypothetical_exit_cost"]),
        "mean_closing_exposure": sum(exposures) / len(exposures),
        "mean_closing_cash_fraction": 1 - sum(exposures) / len(exposures),
        "mean_cash_dollars": sum(row["cash_at_close"] for row in risk["daily_envelopes"]) / len(exposures),
        "fully_in_cash_sessions": sum(value == 0 for value in exposures), "sessions": len(exposures),
        "cash_interest_credited": 0.0,
        "limitation": "Costs added back on unchanged fills are not a zero-cost strategy simulation. Cash yield eligibility/rates were not established.",
    }


def assess_saved_stresses(diag, policy, *, neighbors):
    cases = {"reverse_priority": diag["reverse_priority"]["metrics"],
             "delay_and_stop_cost": diag["extra_session_delay_and_50bps_stops"]["metrics"],
             **{f"remove_{symbol}": m for symbol, m in diag["leave_one_symbol_out"].items()}}
    if neighbors:
        cases.update({f"channel_{name}": case["metrics"] for name, case in diag["channel_neighbors"].items()})
    return {"account_size": 100000, "results": {
        name: {"total_return": m["total_return"], "max_closing_drawdown": m["max_drawdown"],
               "status": "pass" if m["total_return"] > 0 and above_loss_limit(m["max_drawdown"], policy["drawdown_rejection_level"]) else "fail"}
        for name, m in cases.items()},
        "channel_neighbor_coverage": "not_available_for_recent_selected_sizing" if not neighbors else "2017_2018_window_only",
        "intraday_risk": "not_measured", "ten_thousand_dollar_stresses": "not_run_no_extrapolation"}


def run_audit(output_dir, data_dir=Path("data/historical")):
    if output_dir.exists():
        raise FileExistsError("Choose a fresh audit output directory")
    policy = load_policy(POLICY)
    r3, r4 = (json.loads(path.read_text(encoding="utf-8")) for path in (R3, R4))
    if r4["reference_sha256"] != digest(R3) or r3["selected_on_earlier_years"] != "vol_latched":
        raise ValueError("Original reference chain or selected policy differs")
    if r4["coverage_mode"] != "primary":
        raise ValueError("This audit requires the complete registered primary history")
    for path, sha in r4["source_sha256"].items():
        if digest(frozen_source_path(path)) != sha:
            raise ValueError(f"Frozen candidate source changed: {path}")
    if digest(Path("docs/study_c_earlier_history_protocol.md")) != r4["protocol_sha256"]:
        raise ValueError("Earlier-history protocol changed")
    calendar_path = data_dir / CALENDAR_NAME
    if digest(calendar_path) != r4["calendar_sha256"]:
        raise ValueError("Historical session calendar changed")
    calendar = SnapshotCalendar(calendar_path)
    earlier = {}
    for symbol in SYMBOLS:
        bars, manifest = load_extension(data_dir / f"{symbol}_1Day_2016_2018_study_c_r4.csv", symbol, "2016-01-01", calendar)
        if manifest["sha256"] != r4["provenance"][symbol]["sha256"]:
            raise ValueError("Earlier dataset changed")
        earlier[symbol] = bars
    later, manifests = load_study_data(data_dir)
    for symbol, manifest in manifests.items():
        if not manifest["sha256"] == r4["old_provenance"][symbol]["sha256"] == r3["provenance"][symbol]["sha256"]:
            raise ValueError("Later dataset changed")
    combined = join_history(earlier, later, "2016-01-01", calendar)
    candidate = next(arm for arm in ARMS if arm.id == "vol_latched")
    report = {"study": "C-goal-fit", "policy": policy, "policy_sha256": digest(POLICY),
              "protocol_sha256": digest(PROTOCOL), "reference_sha256": {str(p): digest(p) for p in (R3, R4)},
              "source_sha256": {str(p): digest(p) for p in (Path("backtesting/goal_fit.py"), Path("backtesting/risk_diagnostics.py"))},
              "candidate_source_sha256": r4["source_sha256"],
              "environment": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__, "alpaca-py": version("alpaca-py")},
              "dataset_provenance": {"earlier": r4["provenance"], "later": manifests},
              "calendar_sha256": r4["calendar_sha256"], "accounts": {}, "simulation_count": 0,
              "paper_authorized": False, "holdout_opened": False}
    output_dir.mkdir(parents=True)
    windows = (("full_2017_2023", combined, "2017-01-01", 7), ("recent_2022_2023", later, "2022-01-01", 2))
    for initial_cash in policy["audit_account_sizes"]:
        accounts = report["accounts"][str(initial_cash)] = {}
        for window, data, start, years in windows:
            cases, assessments = {}, {}
            for name, scenario in COST_SCENARIOS.items():
                costs = replace(scenario, initial_cash=initial_cash, periods_per_year=252)
                result = simulate_policy(candidate, data, data["SPY"], costs, start=start, end="2024-01-01")
                report["simulation_count"] += 1
                packed = _pack_window(result, start, "2024-01-01")
                risk = daily_risk_envelope(packed, data)
                goals = checks_for(packed["metrics"], years, policy)
                assessments[name] = {"goal_fit": goals, "risk_diagnostics": risk,
                                     "attribution": cost_attribution(packed, risk, years, policy)}
                cases[name] = packed
                print(f"{initial_cash}/{window}/{name}: {goals['decision']}", flush=True)
            if initial_cash == 100000:
                old_cases = (r4["windows"]["continuous"]["arms"]["candidate"] if years == 7 else r3["development"]["vol_latched"])
                assert_baseline_matches(cases, {"cost_scenarios": old_cases})
            benchmark = {str(fraction): {name: passive_spy(data["SPY"], replace(config, initial_cash=initial_cash),
                                                         start=start, end="2024-01-01", initial_fraction=fraction)
                                           for name, config in COST_SCENARIOS.items()} for fraction in (.20, .35)}
            accounts[window] = {"start": start, "end_exclusive": "2024-01-01", "years": years,
                                "cases": cases, "audit": assessments, "passive_spy": benchmark}
            write(output_dir / f"account_{initial_cash}_{window}.json", accounts[window])
    report["reference_replay"] = "Both $100,000 reference windows match all original metrics and fills exactly under all three costs; all twelve ledgers reconcile."
    report["saved_stress_review"] = {
        "2017_2018_r4": assess_saved_stresses(r4["diagnostics"], policy, neighbors=True),
        "2022_2023_r3": assess_saved_stresses(r3["diagnostics"]["vol_latched"], policy, neighbors=False)}
    report["decision"] = "does_not_qualify" if any(
        account["audit"]["pessimistic"]["goal_fit"]["decision"] == "does_not_qualify"
        for account_windows in report["accounts"].values() for account in account_windows.values()
    ) or any(case["status"] == "fail" for review in report["saved_stress_review"].values()
             for case in review["results"].values()) else "inconclusive"
    write(output_dir / "report.json", report)
    print(json.dumps({"report": str(output_dir / "report.json"), "decision": report["decision"],
                      "simulations": report["simulation_count"], "holdout_opened": False}, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=Path("data/historical"))
    args = parser.parse_args()
    run_audit(args.output_dir, args.data_dir)


if __name__ == "__main__":
    main()

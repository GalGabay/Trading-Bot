"""Approved three-arm holding-time study. Offline, fixed pre-2024 inputs."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, replace
import json
from pathlib import Path, PureWindowsPath
from statistics import mean, median
import sys
from importlib.metadata import version

import numpy as np
import pandas as pd

from backtesting.allocation_research import ARMS, simulate_policy
from backtesting.daily_research import assert_baseline_matches, SYMBOLS
from backtesting.daily_strategies import DailyRuleConfig
from backtesting.earlier_history import CALENDAR_NAME, SnapshotCalendar, join_history, load_extension, _pack_window
from backtesting.goal_fit import POLICY, digest, load_policy, checks_for, cost_attribution, above_loss_limit
from backtesting.holding_policy import HoldingPolicy
from backtesting.research import COST_SCENARIOS, load_dataset
from backtesting.risk_diagnostics import daily_risk_envelope

PROTOCOL = Path("docs/holding_period_study_protocol.md")
REFERENCE = Path("data/reports/study_c_goal_fit_final/report.json")
POLICIES = {"control": None, "maximum_30": HoldingPolicy("maximum"), "continuation_30": HoldingPolicy("continuation")}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_history(directory, reference):
    """Validate original manifests and reference chain, without API clients."""
    for name, sha in reference["reference_sha256"].items():
        if digest(Path(*PureWindowsPath(name).parts)) != sha:
            raise ValueError("Original reference chain changed")
    calendar_path = directory / CALENDAR_NAME
    if digest(calendar_path) != reference["calendar_sha256"]:
        raise ValueError("Saved calendar changed")
    calendar = SnapshotCalendar(calendar_path)
    earlier, later = {}, {}
    for symbol in SYMBOLS:
        bars, provenance = load_extension(directory / f"{symbol}_1Day_2016_2018_study_c_r4.csv", symbol, "2016-01-01", calendar)
        if provenance["sha256"] != reference["dataset_provenance"]["earlier"][symbol]["sha256"]:
            raise ValueError(f"{symbol}: earlier data changed")
        earlier[symbol] = bars
        path = directory / f"{symbol}_1Day_2019_2023_study_c.csv"
        bars, provenance = load_dataset(path)
        expected = (symbol, "1Day", "sip", "all", "2019-01-01", "2024-01-01")
        if tuple(provenance[key] for key in ("symbol", "timeframe", "feed", "adjustment", "start_utc", "end_exclusive_utc")) != expected:
            raise ValueError("Later data conventions changed")
        if provenance["sha256"] != reference["dataset_provenance"]["later"][symbol]["sha256"]:
            raise ValueError(f"{symbol}: later data changed")
        later[symbol] = bars.sort_values("timestamp", ignore_index=True)
    return join_history(earlier, later, "2016-01-01", calendar), later


def capacity_summary(result):
    decisions = result.buy_decisions
    opened = [row for row in decisions if row["phase"] == "open"]
    blocked = [row for row in opened if row["status"] == "blocked"]
    return {"open_attempts": len(opened), "filled_open_attempts": sum(row["status"] == "filled" for row in opened),
            "blocked_open_attempts": len(blocked),
            "open_blockers": dict(Counter(reason for row in blocked for reason in row["blockers"])),
            "planning_blockers": dict(Counter(reason for row in decisions if row["phase"] == "close" and row["status"] == "blocked" for reason in row["blockers"])),
            "blocked_with_holding_at_least_30_sessions": sum(any(age >= 30 for age in row["held_ages"].values()) for row in blocked),
            "position_count_blocks_with_positive_cash": sum("position_count" in row["blockers"] and row["cash"] > 0 for row in blocked),
            "sessions_at_seven_position_limit": sum(point.position_count == 7 for point in result.equity_curve),
            "mean_position_count": mean(point.position_count for point in result.equity_curve),
            "limitation": "First rejecting check, not every possible blocker. Daily repeated attempts are not independent trades or proven missed profits."}


def holding_summary(result):
    dates = [point.timestamp for point in result.equity_curve]
    indices = {day: index for index, day in enumerate(dates)}
    entries, durations, time_exits = {}, [], []
    reasons = Counter()
    buys = [fill for fill in result.fills if fill.side.value == "BUY"]
    for fill in result.fills:
        if fill.side.value == "BUY":
            entries[fill.symbol] = fill
            continue
        entry = entries.pop(fill.symbol)
        duration = indices[fill.timestamp] - indices[entry.timestamp]
        durations.append(max(1, duration + int(fill.signal_reason.startswith("PROTECTIVE_STOP_TOUCH:"))))
        kind = "holding_time" if fill.signal_reason.startswith("HOLDING_") else "stop" if fill.signal_reason.startswith("PROTECTIVE_STOP_") else "natural"
        reasons[kind] += 1
        if kind == "holding_time":
            index = indices[fill.timestamp]
            next_buys = [buy for buy in buys if buy.symbol != fill.symbol and index <= indices[buy.timestamp] <= index + 5]
            time_exits.append({"timestamp": fill.timestamp.isoformat(), "symbol": fill.symbol,
                               "different_buy_same_open": any(buy.timestamp == fill.timestamp for buy in next_buys),
                               "different_buy_within_five_sessions": bool(next_buys),
                               "complete_five_session_followup": index + 5 < len(dates)})
    return {"completed_holding_sessions_mean": None if not durations else mean(durations),
            "completed_holding_sessions_median": None if not durations else median(durations),
            "completed_holding_sessions_max": None if not durations else max(durations),
            "exit_kinds": dict(reasons), "review_count": len(result.holding_reviews),
            "retained_reviews_at_or_beyond_60": sum(row["age_sessions"] >= 60 and row["decision"] == "retain" for row in result.holding_reviews),
            "open_position_ages": {symbol: len(dates) - indices[entry.timestamp] for symbol, entry in entries.items()},
            "time_exit_reuse": time_exits,
            "time_exit_with_different_buy_same_open": sum(row["different_buy_same_open"] for row in time_exits),
            "time_exit_with_different_buy_within_five_sessions": sum(row["different_buy_within_five_sessions"] and row["complete_five_session_followup"] for row in time_exits),
            "complete_five_session_followups": sum(row["complete_five_session_followup"] for row in time_exits),
            "right_censored_five_session_followups": sum(not row["complete_five_session_followup"] for row in time_exits),
            "limitation": "Followup is ex-post utilization, not proof of funding necessity. Open exits count prior held sessions; same-day touches count one."}


def run_study(output_dir, data_dir=Path("data/historical")):
    if output_dir.exists():
        raise FileExistsError("Choose a new holding-study output directory")
    policy = load_policy(POLICY)
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    if reference["policy_sha256"] != digest(POLICY):
        raise ValueError("Approved criteria differ from the reference audit")
    combined, later = load_history(data_dir, reference)
    allocation = next(arm for arm in ARMS if arm.id == "vol_latched")
    if (allocation.position_cap, allocation.total_cap, allocation.stop_risk_cap, allocation.volatility_contribution, allocation.pause_sessions) != (.05, .35, .005, .01, None):
        raise ValueError("Frozen allocation settings changed")
    windows = (("full_2017_2023", combined, "2017-01-01", 7), ("recent_2022_2023", later, "2022-01-01", 2))
    output_dir.mkdir(parents=True)
    report = {"study": "holding_time", "protocol_sha256": digest(PROTOCOL), "policy": policy, "policy_sha256": digest(POLICY),
              "reference_sha256": digest(REFERENCE), "dataset_provenance": reference["dataset_provenance"],
              "calendar_sha256": reference["calendar_sha256"], "environment": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__, "alpaca-py": version("alpaca-py")},
              "source_sha256": {str(path): digest(path) for path in (
                  Path("backtesting/holding_research.py"), Path("backtesting/holding_policy.py"), Path("backtesting/portfolio_engine.py"),
                  Path("backtesting/allocation_research.py"), Path("backtesting/daily_strategies.py"), Path("backtesting/protective_exits.py"),
                  Path("backtesting/research_policy.py"), Path("backtesting/goal_fit.py"), Path("backtesting/risk_diagnostics.py"), Path("app/ai/features.py"))},
              "holding_policies": {name: None if value is None else asdict(value) for name, value in POLICIES.items()},
              "arms": {}, "conditional_diagnostics": {}, "simulation_count": 0, "paper_authorized": False, "holdout_opened": False}
    for arm, holding_policy in POLICIES.items():
        report["arms"][arm] = {}
        for capital in policy["audit_account_sizes"]:
            accounts = report["arms"][arm][str(capital)] = {}
            for window, data, start, years in windows:
                cases = accounts[window] = {}
                for cost_name, base_cost in COST_SCENARIOS.items():
                    costs = replace(base_cost, initial_cash=capital, periods_per_year=252)
                    result = simulate_policy(allocation, data, data["SPY"], costs, start=start, end="2024-01-01", holding_policy=holding_policy, record_decisions=True)
                    report["simulation_count"] += 1
                    packed = _pack_window(result, start, "2024-01-01")
                    if arm == "control":
                        old = reference["accounts"][str(capital)][window]["cases"][cost_name]
                        assert_baseline_matches({cost_name: packed}, {"cost_scenarios": {cost_name: old}})
                    risk = daily_risk_envelope(packed, data)
                    audit = {"goal_fit": checks_for(packed["metrics"], years, policy),
                             "risk": {key: value for key, value in risk.items() if key != "daily_envelopes"},
                             "attribution": cost_attribution(packed, risk, years, policy),
                             "capacity": capacity_summary(result), "holding": holding_summary(result)}
                    filename = f"{arm}_{capital}_{window}_{cost_name}.json"
                    write(output_dir / filename, {"financial": packed, "audit": audit, "daily_risk_envelopes": risk["daily_envelopes"],
                                                   "holding_reviews": list(result.holding_reviews), "buy_decisions": list(result.buy_decisions)})
                    cases[cost_name] = {"metrics": packed["metrics"], "audit": audit, "artifact": filename, "artifact_sha256": digest(output_dir / filename)}
                    print(f"{arm}/{capital}/{window}/{cost_name}: {audit['goal_fit']['decision']}", flush=True)
        if arm == "control":
            print("All twelve controls match original metrics and fills exactly before variant scoring", flush=True)
    report["reference_replay"] = "All twelve original goal-fit controls reproduced exactly, including event counts and fills; every main ledger reconciled."
    promising = [name for name in POLICIES if name != "control" and all(
        all(status == "pass" for key, status in report["arms"][name]["10000"][window]["pessimistic"]["audit"]["goal_fit"]["checks"].items()
            if key != "actual_intraday_drawdown_measured") for window, _, _, _ in windows)]
    report["promising_for_development_diagnostics"] = promising
    for arm in promising:
        report["conditional_diagnostics"][arm] = {}
        for window, data, start, years in windows:
            variants = [("reverse_priority", data, {"priority": "reverse"}),
                        ("delay_and_stop_cost", data, {"delay": 2, "extra_stop_bps": 50})]
            variants.extend((f"remove_{symbol}", {name: frame for name, frame in data.items() if name != symbol}, {}) for symbol in SYMBOLS)
            variants.extend((f"channel_{entry}_{exit_}", data, {"rule_config": DailyRuleConfig("breakout", entry, exit_)}) for entry, exit_ in ((40, 15), (70, 25)))
            checks = report["conditional_diagnostics"][arm][window] = {}
            for name, datasets, kwargs in variants:
                result = simulate_policy(allocation, datasets, data["SPY"], replace(COST_SCENARIOS["pessimistic"], initial_cash=10000, periods_per_year=252),
                                         start=start, end="2024-01-01", holding_policy=POLICIES[arm], **kwargs)
                report["simulation_count"] += 1
                packed = _pack_window(result, start, "2024-01-01")
                checks[name] = {"metrics": packed["metrics"], "profitable_and_closing_drawdown_below_5_percent": packed["metrics"]["total_return"] > 0 and above_loss_limit(packed["metrics"]["max_drawdown"], policy["drawdown_rejection_level"])}
                write(output_dir / f"diagnostic_{arm}_{window}_{name}.json", packed)
    report["benchmarks"] = {capital: {window: account["passive_spy"] for window, account in accounts.items()} for capital, accounts in reference["accounts"].items()}
    passed = [arm for arm in promising if all(case["profitable_and_closing_drawdown_below_5_percent"] for window in report["conditional_diagnostics"][arm].values() for case in window.values())]
    report["measured_development_diagnostics_passed"] = passed
    report["decision"] = ("no_new_arm_qualifies" if not promising else "all_promising_arms_failed_stress" if not passed else "development_only_review_required_intraday_risk_unmeasured")
    write(output_dir / "report.json", report)
    print(json.dumps({"report": str(output_dir / "report.json"), "simulations": report["simulation_count"], "decision": report["decision"]}, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=Path("data/historical"))
    args = parser.parse_args()
    run_study(args.output_dir, args.data_dir)


if __name__ == "__main__":
    main()

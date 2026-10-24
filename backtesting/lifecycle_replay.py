"""Replay all 36 saved holding-study cases without changing their provenance.

Offline regression evidence only: no search, fresh prices, paid data or orders.
Reference artifact/data hashes are checked before exact financial comparison.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from backtesting.allocation_research import ARMS, simulate_policy
from backtesting.earlier_history import _pack_window
from backtesting.holding_research import load_history, POLICIES
from backtesting.research import COST_SCENARIOS
from backtesting.risk_diagnostics import daily_risk_envelope


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_risk_replay(output: Path, *, data_dir=Path("data/historical"), reference=Path("data/reports/study_c_holding/report.json")):
    """Recompute all old daily envelopes without rerunning strategy selection."""
    if output.exists():
        raise FileExistsError("Choose a fresh risk replay evidence directory")
    original = json.loads(reference.read_text(encoding="utf-8"))
    goal_path = Path("data/reports/study_c_goal_fit_final/report.json")
    combined, later = load_history(data_dir, json.loads(goal_path.read_text(encoding="utf-8")))
    report = {"purpose": "exact_legacy_daily_risk_regression_not_strategy_search",
              "reference_sha256": digest(reference), "goal_reference_sha256": digest(goal_path),
              "source_sha256": {name: digest(name) for name in ("backtesting/risk_diagnostics.py", "backtesting/lifecycle_replay.py")},
              "cases": [], "holdout_opened": False, "orders_placed": False}
    output.mkdir(parents=True, exist_ok=False)
    for policy, accounts in original["arms"].items():
        for capital, windows in accounts.items():
            for window, scenarios in windows.items():
                datasets = combined if window == "full_2017_2023" else later
                for name, expected in scenarios.items():
                    path = reference.parent / expected["artifact"]
                    if path.resolve().parent != reference.parent.resolve() or digest(path) != expected["artifact_sha256"]:
                        raise ValueError("Saved holding reference artifact checksum/path changed")
                    artifact = json.loads(path.read_text(encoding="utf-8"))
                    risk = daily_risk_envelope(artifact["financial"], datasets)
                    exact = risk["daily_envelopes"] == artifact["daily_risk_envelopes"]
                    report["cases"].append({"policy": policy, "capital": capital, "window": window, "costs": name,
                                            "artifact_sha256": digest(path), "all_daily_envelopes_exact": exact})
                    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
                    if not exact:
                        raise ValueError("Historical daily-risk envelope changed; original evidence preserved")
    report["all_36_cases_match"] = len(report["cases"]) == 36
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"{len(report['cases'])}/36 saved daily-risk cases match exactly", flush=True)
    return report


def run_replay(output: Path, *, data_dir=Path("data/historical"), reference=Path("data/reports/study_c_holding/report.json")):
    if output.exists():
        raise FileExistsError("Choose a fresh replay evidence directory")
    output.mkdir(parents=True)
    original = json.loads(reference.read_text(encoding="utf-8"))
    goal_path = Path("data/reports/study_c_goal_fit_final/report.json")
    goal = json.loads(goal_path.read_text(encoding="utf-8"))
    combined, later = load_history(data_dir, goal)
    report = {
        "purpose": "exact_regression_replay_not_new_strategy_research",
        "reference_sha256": digest(reference), "goal_fit_reference_sha256": digest(goal_path),
        "source_sha256": {name: digest(name) for name in (
            "backtesting/lifecycle_replay.py", "backtesting/portfolio_engine.py",
            "backtesting/universe.py", "backtesting/corporate_actions.py",
            "backtesting/daily_research.py", "backtesting/risk_diagnostics.py",
        )},
        "cases": [], "holdout_opened": False, "orders_placed": False,
    }
    arm = next(a for a in ARMS if a.id == "vol_latched")
    for policy, accounts in original["arms"].items():
        for capital, windows in accounts.items():
            for window, scenarios in windows.items():
                start, datasets = ("2017-01-01", combined) if window == "full_2017_2023" else ("2022-01-01", later)
                for name, expected in scenarios.items():
                    path = reference.parent / expected["artifact"]
                    if path.resolve().parent != reference.parent.resolve() or digest(path) != expected["artifact_sha256"]:
                        raise ValueError("Saved holding reference artifact checksum/path changed")
                    saved = json.loads(path.read_text(encoding="utf-8"))["financial"]
                    result = simulate_policy(
                        arm, datasets, datasets["SPY"],
                        replace(COST_SCENARIOS[name], initial_cash=int(capital), periods_per_year=252),
                        start=start, end="2024-01-01", holding_policy=POLICIES[policy], record_decisions=True,
                    )
                    current = _pack_window(result, start, "2024-01-01")
                    checks = {key: current[key] == saved[key] for key in ("metrics", "costs", "fills", "equity_curve", "events", "risk_events")}
                    case = {"policy": policy, "capital": capital, "window": window, "costs": name, "exact_matches": checks}
                    report["cases"].append(case)
                    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
                    print(f"{policy}/{capital}/{window}/{name}: {'MATCH' if all(checks.values()) else 'MISMATCH'}", flush=True)
                    if not all(checks.values()):
                        (output / "mismatched_current.json").write_text(json.dumps(current, indent=2, allow_nan=False) + "\n", encoding="utf-8")
                        raise ValueError("Historical regression replay differs; old reports are unchanged")
    report["all_36_cases_match"] = len(report["cases"]) == 36
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--risk-only", action="store_true", help="Reconcile saved fills and compare every daily envelope")
    args = parser.parse_args()
    (run_risk_replay if args.risk_only else run_replay)(args.output)


if __name__ == "__main__":
    main()

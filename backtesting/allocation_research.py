"""Offline Study C-R3: fixed breakout signals, allocation and halt policies.

Run ``python -m backtesting.allocation_research --output-dir data/reports/study_c_r3``.
Requires the existing Study C SIP/IEX CSVs and the C-R2 reference report.
No API clients are constructed and no data beyond 2023 is read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass, replace
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

from backtesting.daily_research import (
    SYMBOLS, assert_baseline_matches, bootstrap_difference, enriched_metrics,
    load_study_data, pack, passive_spy,
)
from backtesting.daily_strategies import DailyResearchStrategy, DailyRuleConfig, market_regime
from backtesting.portfolio_engine import PortfolioBacktestEngine, ResearchPortfolioLimits
from backtesting.protective_exits import ProtectiveExitConfig
from backtesting.research import COST_SCENARIOS, _utc_date
from backtesting.research_policy import AllocationPolicy, HaltPolicy

PROTOCOL = Path("docs/study_c_allocation_protocol.md")


@dataclass(frozen=True)
class AllocationArm:
    id: str
    position_cap: float
    total_cap: float
    stop_risk_cap: float
    volatility_contribution: float | None = None
    pause_sessions: int | None = None
    eligible: bool = True


ARMS = (
    AllocationArm("full_latched", .10, .70, .01, eligible=False),
    AllocationArm("full_pause", .10, .70, .01, pause_sessions=5, eligible=False),
    AllocationArm("half_latched", .05, .35, .005),
    AllocationArm("half_pause", .05, .35, .005, pause_sessions=5),
    AllocationArm("vol_latched", .05, .35, .005, volatility_contribution=.01),
    AllocationArm("vol_pause", .05, .35, .005, volatility_contribution=.01, pause_sessions=5),
)


def simulate_policy(arm, data, context, costs, *, start, end, priority="alphabetical", delay=1, extra_stop_bps=0, signal_data=None, rule_config=None, holding_policy=None, record_decisions=False):
    if end > "2024-01-01":
        raise ValueError("Reserved holdout cannot enter allocation research")
    regime = market_regime(context)
    rule_config = rule_config or DailyRuleConfig("breakout")
    if rule_config.style != "breakout":
        raise ValueError("Allocation-policy research requires breakout rules")
    return PortfolioBacktestEngine(
        DailyResearchStrategy(rule_config, regime=regime),
        costs=replace(costs, position_fraction=arm.position_cap),
        limits=ResearchPortfolioLimits(max_single_position=arm.position_cap, max_portfolio_exposure=arm.total_cap),
        protection=ProtectiveExitConfig(atr_multiple=3, max_risk_per_trade=arm.stop_risk_cap, trailing=False, extra_stop_slippage_bps=extra_stop_bps),
        reentry_cooldown_sessions=10, execution_delay_sessions=delay, buy_priority=priority,
        allocation=AllocationPolicy(arm.volatility_contribution),
        halt_policy=HaltPolicy(arm.pause_sessions), restart_review=regime if arm.pause_sessions is not None else None,
        holding_policy=holding_policy, holding_market_review=regime if holding_policy is not None else None,
        record_decisions=record_decisions,
    ).run(data, trade_start=_utc_date(start), trade_end=_utc_date(end), signal_datasets=signal_data)


def policy_metrics(result):
    metrics = enriched_metrics(result)
    equity = np.r_[result.costs.initial_cash, [point.equity for point in result.equity_curve]]
    daily_returns = equity[1:] / equity[:-1] - 1
    return {
        **metrics, "worst_closing_daily_return": float(daily_returns.min()),
        "daily_halt_count": sum(event["kind"] == "daily_halt" for event in result.risk_events),
        "drawdown_halt_count": sum(event["kind"] == "drawdown_halt" for event in result.risk_events),
        "restart_count": sum(event["kind"] == "restart" for event in result.risk_events),
        "restart_dates": [event["timestamp"] for event in result.risk_events if event["kind"] == "restart"],
        "sessions_blocked_at_open": result.blocked_sessions_at_open,
        "permanent_halt_reason": result.permanent_halt_reason,
        "halt_active_at_end": result.halt_active_at_end,
    }


def pack_policy(result):
    return {**pack(result), "metrics": policy_metrics(result), "risk_events": list(result.risk_events)}


def select_earlier(training):
    assessments, eligible = {}, []
    for arm in ARMS:
        if not arm.eligible:
            continue
        m = training[arm.id]["pessimistic"]["metrics"]
        checks = {
            "both_earlier_years_positive": all(m["annual_returns"].get(year, -1) > 0 for year in ("2020", "2021")),
            "at_least_20_completed_trades": m["completed_trades"] >= 20,
            "at_least_five_instruments": m["instruments_with_closed_trades"] >= 5,
            "drawdown_below_10_percent": m["max_drawdown"] > -.10,
            "worst_closing_day_within_3_percent": m["worst_closing_daily_return"] >= -.03,
            "no_permanent_halt": m["permanent_halt_reason"] is None,
        }
        assessments[arm.id] = checks
        if all(checks.values()):
            eligible.append((min(m["annual_returns"].values()), m["max_drawdown"], m["completed_trades"], arm.id))
    eligible.sort(key=lambda item: (-item[0], -item[1], item[2], item[3]))
    return (eligible[0][3] if eligible else None), assessments


def _write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run_study(output_dir, data_dir=Path("data/historical"), reference=Path("data/reports/study_c_r2_final/report.json")):
    output_dir.mkdir(parents=True, exist_ok=False)
    data, provenance = load_study_data(data_dir)
    iex, iex_provenance = load_study_data(data_dir, feed="iex")
    old = json.loads(reference.read_text(encoding="utf-8"))
    costs = {name: replace(config, periods_per_year=252) for name, config in COST_SCENARIOS.items()}
    counter = 0

    def run(arm, *, datasets=None, context=None, **kwargs):
        nonlocal counter
        counter += 1
        return simulate_policy(arm, data if datasets is None else datasets,
                               data["SPY"] if context is None else context, **kwargs)

    report = {
        "study": "C-R3", "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "source_sha256": {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in (
            Path(__file__), Path("backtesting/research_policy.py"), Path("backtesting/portfolio_engine.py"),
            Path("backtesting/daily_research.py"), Path("backtesting/daily_strategies.py"),
            Path("backtesting/protective_exits.py"), Path("app/ai/features.py"),
        )},
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__, "alpaca-py": version("alpaca-py")},
        "arms": [asdict(arm) for arm in ARMS], "provenance": provenance, "iex_provenance": iex_provenance,
        "reference_path": str(reference), "reference_sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
        "training": {}, "development": {}, "diagnostics": {}, "paper_authorized": False,
    }
    cached = {}
    for window, start, end in (("training", "2020-01-01", "2022-01-01"), ("development", "2022-01-01", "2024-01-01")):
        cached[window] = {}
        for name, config in costs.items():
            cached[window][name] = run(ARMS[0], costs=config, start=start, end=end)
        current = {name: pack_policy(result) for name, result in cached[window].items()}
        assert_baseline_matches(current, {"cost_scenarios": old[window]["regime_breakout"]})
    report["reference_replay"] = "All C-R2 fixed-stop breakout metric fields and fills match exactly in both windows and all three costs."
    print("C-R2 breakout reference verified in both windows and all costs", flush=True)

    for arm in ARMS:
        report["training"][arm.id] = {}
        for name, config in costs.items():
            result = cached["training"][name] if arm.id == "full_latched" else run(arm, costs=config, start="2020-01-01", end="2022-01-01")
            report["training"][arm.id][name] = pack_policy(result)
        print(f"Earlier allocation window complete: {arm.id}", flush=True)
    selected, checks = select_earlier(report["training"])
    report["selected_on_earlier_years"], report["earlier_selection_checks"] = selected, checks
    _write(output_dir / "earlier_selection.json", {key: report[key] for key in (
        "protocol_sha256", "arms", "training", "selected_on_earlier_years", "earlier_selection_checks",
    )})
    print(f"Earlier selection frozen before new 2022-23 scores: {selected}", flush=True)

    dev_results = {}
    for arm in ARMS:
        report["development"][arm.id] = {}
        for name, config in costs.items():
            result = cached["development"][name] if arm.id == "full_latched" else run(arm, costs=config, start="2022-01-01", end="2024-01-01")
            report["development"][arm.id][name] = pack_policy(result)
            if name == "pessimistic":
                dev_results[arm.id] = result
        _write(output_dir / f"{arm.id}_development.json", report["development"][arm.id])
        print(f"Later allocation window complete: {arm.id}", flush=True)

    diagnostic_arms = [arm for arm in ARMS if arm.eligible and (selected is None or arm.id == selected)]
    for arm in diagnostic_arms:
        def score(test_arm=arm, **kwargs):
            return run(test_arm, costs=costs["pessimistic"], start="2022-01-01", end="2024-01-01", **kwargs)
        diag = {
            "reverse_priority": pack_policy(score(priority="reverse")),
            "extra_session_delay_and_50bps_stops": pack_policy(score(delay=2, extra_stop_bps=50)),
            "leave_one_symbol_out": {}, "pause_neighbors": {}, "volatility_neighbors": {},
        }
        for symbol in SYMBOLS:
            reduced = {name: frame for name, frame in data.items() if name != symbol}
            diag["leave_one_symbol_out"][symbol] = policy_metrics(score(datasets=reduced))
        if selected == arm.id and arm.pause_sessions is not None:
            for pause in (1, 10):
                diag["pause_neighbors"][str(pause)] = pack_policy(score(replace(arm, pause_sessions=pause)))
        if selected == arm.id and arm.volatility_contribution is not None:
            for contribution in (.0075, .0125):
                diag["volatility_neighbors"][str(contribution)] = pack_policy(score(replace(arm, volatility_contribution=contribution)))
        diag["paired_bootstrap"] = bootstrap_difference(
            [point.equity for point in dev_results[arm.id].equity_curve],
            [point.equity for point in dev_results["full_latched"].equity_curve],
        )
        report["diagnostics"][arm.id] = diag
        _write(output_dir / f"{arm.id}_diagnostics.json", diag)
        print(f"Allocation robustness complete: {arm.id}", flush=True)

    sip_short = {symbol: frame.loc[frame["timestamp"] >= _utc_date("2022-03-09")].reset_index(drop=True) for symbol, frame in data.items()}
    report["feed_comparison"] = {"scope": "Fresh 2023 account, matching March 2022 warmup; SIP execution for both signal feeds", "arms": {}}
    for arm in ARMS:
        report["feed_comparison"]["arms"][arm.id] = {}
        for feed, signal_data in (("sip", sip_short), ("iex", iex)):
            result = run(arm, datasets=sip_short, context=signal_data["SPY"], signal_data=signal_data,
                         costs=costs["pessimistic"], start="2023-01-01", end="2024-01-01")
            report["feed_comparison"]["arms"][arm.id][feed] = pack_policy(result)
    report["benchmarks"] = {
        window: {str(fraction): {name: passive_spy(data["SPY"], config, start=start, end=end, initial_fraction=fraction)
                                for name, config in costs.items()} for fraction in (.35, .70)}
        for window, start, end in (("training", "2020-01-01", "2022-01-01"), ("development", "2022-01-01", "2024-01-01"))
    }
    baseline = policy_metrics(dev_results["full_latched"])
    report["development_checks"] = {}
    for arm in diagnostic_arms:
        m, diag = policy_metrics(dev_results[arm.id]), report["diagnostics"][arm.id]
        stresses = [diag["reverse_priority"]["metrics"], diag["extra_session_delay_and_50bps_stops"]["metrics"],
                    *diag["leave_one_symbol_out"].values(),
                    *[value["metrics"] for value in diag["pause_neighbors"].values()],
                    *[value["metrics"] for value in diag["volatility_neighbors"].values()]]
        checks = {
            "positive_pessimistic_return_after_exit_estimate": m["hypothetical_liquidated_return"] > 0,
            "improved_drawdown": m["max_drawdown"] > baseline["max_drawdown"],
            "improved_worst_closing_day": m["worst_closing_daily_return"] > baseline["worst_closing_daily_return"],
            "no_permanent_halt": m["permanent_halt_reason"] is None,
            "at_least_20_closed_trades": m["completed_trades"] >= 20,
            "at_least_five_instruments": m["instruments_with_closed_trades"] >= 5,
            "all_stress_returns_positive": all(value["total_return"] > 0 for value in stresses),
            "all_stress_drawdowns_below_10_percent": all(value["max_drawdown"] > -.10 for value in stresses),
        }
        report["development_checks"][arm.id] = {"checks": checks, "passes_allocation_screen": all(checks.values())}
    report["simulation_count"] = counter
    report["selected_for_further_allocation_research"] = selected if selected is not None and report["development_checks"][selected]["passes_allocation_screen"] else None
    _write(output_dir / "report.json", report)
    print(json.dumps({"report": str(output_dir / "report.json"), "simulations": counter,
                      "selected_on_earlier_years": selected, "development_checks": report["development_checks"],
                      "paper_authorized": False}, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=Path("data/historical"))
    parser.add_argument("--reference", type=Path, default=Path("data/reports/study_c_r2_final/report.json"))
    args = parser.parse_args()
    run_study(args.output_dir, args.data_dir, args.reference)


if __name__ == "__main__":
    main()

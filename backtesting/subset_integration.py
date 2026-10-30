"""Load and compile approved subset inputs for the diagnostic simulator path.

The CLI performs input/schedule checks only: zero strategy calls or fills. A
performance runner must separately enforce the approved attempt/time budgets
and require current accounting/control verification before starting a case.
"""

import argparse
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path

import pandas as pd

from app.data.market_calendar import TradingSession
from backtesting.broad_collection import pin
from backtesting.cohort_audit import checked_file
from backtesting.diagnostic_bridge import DiagnosticSchedule, DiagnosticUniverse
from backtesting.pilot_readiness_review import offline_only, write_json
from backtesting.subset_preparation import APPROVAL, load_approved
from backtesting.universe import SplitAction, UniverseDataError

PREPARATION = Path("docs/approved_subset_preparation_summary.json")


def load_inputs(preparation_path=PREPARATION):
    approval, proposal = load_approved(APPROVAL)
    summary = json.loads(preparation_path.read_text(encoding="utf-8"))
    if (summary["approval"] != pin(APPROVAL) or summary["proposal"] != approval["proposal"] or
            summary.get("subset_data_gates_clear") is not True or summary.get("input_validation_complete") is not True or
            summary.get("selected_originals") != 76 or summary.get("deferred_originals") != 24 or
            summary.get("strategy_runs") != 0 or summary.get("strict_flags_promoted") is not False):
        raise UniverseDataError("Require the approved, validated subset preparation with unchanged scope")
    checked_file(Path.cwd(), summary["execution"])
    checked_file(Path.cwd(), summary["executed_source"])
    outputs = {Path(item["path"]).name: checked_file(Path.cwd(), item) for item in summary["output_files"]}
    context_check = json.loads(checked_file(Path.cwd(), summary["context_check"]).read_text(encoding="utf-8"))
    manifest = json.loads(outputs["input_manifest.json"].read_text(encoding="utf-8"))
    gates = json.loads(outputs["preflight.json"].read_text(encoding="utf-8"))
    if not gates["data_gates_clear"] or gates["blockers"]:
        raise UniverseDataError("Remaining subset economic-data gates cannot be bypassed")
    if (manifest["selected_original_ids"] != proposal["proposed_candidate_root_ids"] or
            manifest["deferred_original_ids"] != proposal["proposed_deferred_root_ids"] or
            [s["instrument_id"] for s in manifest["streams"]] != proposal["proposed_candidate_stream_ids"] or
            manifest["approval"] != pin(APPROVAL) or manifest["proposal"] != approval["proposal"] or
            manifest["strict_evidence_approved"] is not False or manifest["paper_authorized"] is not False or
            manifest["context"] != context_check):
        raise UniverseDataError("Subset manifest scope, approval, diagnostic flags or context changed")
    sessions = [TradingSession(pd.Timestamp(s["opens_at"]), pd.Timestamp(s["closes_at"])) for s in
        json.loads(checked_file(Path.cwd(), manifest["calendar"]).read_text(encoding="utf-8"))]
    full_universe = DiagnosticUniverse(sessions, manifest["streams"])
    data = {}
    for stream in manifest["streams"]:
        for part in stream["parts"]:
            if not "2016-01-01" <= part["start"] < part["end_exclusive"] <= "2024-01-01":
                raise UniverseDataError("Only the frozen development price intervals may be read")
        frame = pd.read_csv(checked_file(Path.cwd(), stream["source"]))
        # Match full coverage before any clipping. Empty or extra source rows
        # cannot disappear just because one evaluation window does not use them.
        full_universe.prepare(stream["instrument_id"], frame)
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        data[stream["instrument_id"]] = frame
    context = pd.read_csv(checked_file(Path.cwd(), context_check["source"]))
    context["timestamp"] = pd.to_datetime(context["timestamp"], utc=True)
    from app.data.market_data import validate_candles, ValidationConfig
    from alpaca.data.timeframe import TimeFrame
    from backtesting.cohort_audit import SavedCalendar
    validate_candles(context, config=ValidationConfig(timeframe=TimeFrame.Day), calendar=SavedCalendar(sessions))
    if set(context["timestamp"]) != set(full_universe.dates) or set(context["symbol"]) != {"SPY"}:
        raise UniverseDataError("Frozen raw SPY context has changed coverage or identity")
    schedules = {key: json.loads(checked_file(Path.cwd(), entry).read_text(encoding="utf-8"))
                 for key, entry in manifest["schedules"].items()}
    return dict(approval=approval, proposal=proposal, preparation=pin(preparation_path), manifest=manifest,
        manifest_pin=pin(outputs["input_manifest.json"]), sessions=sessions, data=data, context=context, schedules=schedules)


def build_window(inputs, arm_id, window_id, scenario):
    proposal, manifest = inputs["proposal"], inputs["manifest"]
    arms = [a for a in proposal["proposed_arms"] if a["id"] == arm_id]
    windows = [w for w in proposal["windows"] if w["id"] == window_id]
    if len(arms) != 1 or len(windows) != 1 or scenario not in proposal["scenarios"]:
        raise UniverseDataError("Only the exact approved arms/windows/scenarios may be compiled")
    arm, window = arms[0], windows[0]
    begin, end = window["warmup_start"], window["end_exclusive"]
    if not "2016-01-01" <= begin < window["evaluation_start"] < end <= "2024-01-01":
        raise UniverseDataError("Invalid development window")
    roots = set(arm["root_ids"])
    streams = [s for s in manifest["streams"] if s["root_id"] in roots]
    ids = {s["instrument_id"] for s in streams}
    sessions = [s for s in inputs["sessions"] if begin <= s.opens_at.date().isoformat() < end]
    opens = {s.opens_at.isoformat() for s in sessions}
    source = inputs["schedules"]
    actions = [a for a in source["actions"] if a["instrument_id"] in ids and a["effective_at"] in opens]
    splits = []
    for action in actions:
        if action["kind"] == "ordinary_split":
            ratio = Fraction(action["share_multiplier"])
            splits.append(SplitAction(action["event_id"], action["instrument_id"], action["effective_at"][:10],
                ratio.numerator, ratio.denominator, action["effective_at"],
                "modeled retrospective diagnostic split observation; not verified historical known-at"))
    universe = DiagnosticUniverse(sessions, streams, splits, provenance=dict(
        approval=pin(APPROVAL), manifest=inputs["manifest_pin"], arm=arm_id, window=window_id,
        selection_bias=manifest["source_selection_bias"], split_known_at_is_modeled_not_verified=True))
    material = [deepcopy(r) for r in source["material"] if r["root_id"] in roots and r["scenario"] == scenario and
        r["modeled_accounting_at"] in opens and r["status"] != "inapplicable_preinvestable_event"]
    dividends = [deepcopy(r) for r in source["dividends"] if r["instrument_id"] in ids and r["scenario"] == scenario and r["economic_at"] in opens]
    for row in dividends:
        if row["modeled_release_at"] is not None and row["modeled_release_at"] not in opens:
            row["release_outside_window"] = row["modeled_release_at"]
            row["modeled_release_at"] = None
    for row in material:
        for leg in row["share_legs"]:
            if leg["modeled_release_at"] is not None and leg["modeled_release_at"] not in opens:
                leg["release_outside_window"] = leg["modeled_release_at"]
                leg["modeled_release_at"] = None
    entry_ids = [s["instrument_id"] for s in streams if s["eligible_for_new_entries_candidate"]]
    if set(entry_ids) != roots:
        raise UniverseDataError("Only original roots may receive new entries in this approved subset")
    schedule = DiagnosticSchedule(entry_instrument_ids=entry_ids, dividends=dividends, material=material,
        actions=actions, resets=[r for r in manifest["effective_feature_resets"] if r["instrument_id"] in ids],
        scenario=scenario, approval_sha256=pin(APPROVAL)["sha256"], membership_not_before=manifest["membership_not_before"])
    schedule.bind(universe)
    data = {}
    for key in ids:
        frame = inputs["data"][key]
        frame = frame.loc[(frame["timestamp"] >= pd.Timestamp(begin, tz="UTC")) & (frame["timestamp"] < pd.Timestamp(end, tz="UTC"))].reset_index(drop=True)
        universe.prepare(key, frame)
        data[key] = frame
    context = inputs["context"]
    context = context.loc[(context["timestamp"] >= pd.Timestamp(begin, tz="UTC")) & (context["timestamp"] < pd.Timestamp(end, tz="UTC"))].reset_index(drop=True)
    return universe, schedule, data, context


def make_engine(inputs, context, cost_id):
    """Construct the frozen research engine; never run a strategy here.

    Execution belongs to the separately verified/budgeted Step 3 runner.
    """
    from backtesting.daily_strategies import DailyResearchStrategy, DailyRuleConfig, market_regime
    from backtesting.engine import BacktestConfig
    from backtesting.holding_policy import HoldingPolicy
    from backtesting.portfolio_engine import PortfolioBacktestEngine, ResearchPortfolioLimits
    from backtesting.protective_exits import ProtectiveExitConfig
    from backtesting.research_policy import AllocationPolicy, HaltPolicy
    proposal = inputs["proposal"]
    matches = [c for c in proposal["costs"] if c["id"] == cost_id]
    if len(matches) != 1 or proposal["account_sizes_usd"] != [10000]:
        raise UniverseDataError("Only the approved cost case and simulated account size may be constructed")
    costs, settings = matches[0], proposal["frozen_strategy"]
    regime = market_regime(context)
    return PortfolioBacktestEngine(
        DailyResearchStrategy(DailyRuleConfig("breakout",settings["entry_sessions"],settings["exit_sessions"]),regime=regime),
        costs=BacktestConfig(initial_cash=10000,position_fraction=settings["position_cap"],periods_per_year=252,
            slippage_bps=costs["slippage_bps_per_side"],spread_bps=costs["full_spread_bps"],commission_per_order=costs["commission_per_order_usd"]),
        limits=ResearchPortfolioLimits(max_single_position=settings["position_cap"],max_portfolio_exposure=settings["portfolio_cap"],
            max_positions=settings["max_positions"],max_daily_loss=settings["daily_loss_latched_halt"],max_drawdown=settings["drawdown_latched_halt"]),
        protection=ProtectiveExitConfig(atr_multiple=settings["initial_fixed_stop_atr14_multiple"],max_risk_per_trade=settings["stop_risk_cap"],trailing=False),
        reentry_cooldown_sessions=settings["reentry_cooldown_sessions"],allocation=AllocationPolicy(settings["annualized_volatility_contribution"]),
        halt_policy=HaltPolicy(),holding_policy=HoldingPolicy("continuation"),holding_market_review=regime,
        buy_priority=settings["buy_priority"],record_decisions=True)


def compile_inputs(output, *, preparation_path=PREPARATION):
    if output.exists() or not output.resolve().is_relative_to(Path.cwd().resolve()):
        raise ValueError("Choose a fresh integration compilation path inside the workspace")
    inputs = load_inputs(preparation_path)
    output.mkdir(parents=True)
    cases = []
    for arm in inputs["proposal"]["proposed_arms"]:
        for window in inputs["proposal"]["windows"]:
            for scenario in inputs["proposal"]["scenarios"]:
                universe, schedule, data, context = build_window(inputs, arm["id"], window["id"], scenario)
                name = f"{arm['id']}__{window['id']}__{scenario}.json"
                write_json(output/name, dict(universe=universe.metadata(), schedule=schedule.metadata(),
                    input_rows={key: len(frame) for key, frame in data.items()}, context_rows=len(context),
                    warmup_is_uninvested=True, strategy_runs=0, verification_pending=True))
                cases.append(pin(output/name))
                for cost in inputs["proposal"]["costs"]:
                    make_engine(inputs, context, cost["id"])  # Construct only; no calls to run/generate_signal.
    from backtesting.subset_accounting_audit import audit_saved_accounting
    saved_accounting = audit_saved_accounting(inputs)
    write_json(output/"saved_accounting_audit.json", saved_accounting)
    sources = [Path("backtesting")/f"{n}.py" for n in
        ("diagnostic_bridge", "subset_integration", "subset_accounting_audit", "portfolio_engine", "daily_research", "risk_diagnostics",
         "claim_accounting", "diagnostic_accounting", "ownership_adapter", "corporate_actions", "subset_preparation")]
    snapshots = output/"executed_sources"
    snapshots.mkdir()
    for path in sources:
        (snapshots/path.name).write_bytes(path.read_bytes())
    report = dict(date="2026-10-30", preparation=inputs["preparation"], approval=pin(APPROVAL),
        compiled_cases=cases, compiled_arm_window_scenarios=len(cases),
        saved_accounting_audit=pin(output/"saved_accounting_audit.json"),saved_accounting_checks=saved_accounting["checks_passed"],
        frozen_engine_constructions=24, strategy_calls=0,
        economic_data_gates_clear=True, runtime_integration_implemented=True,
        accounting_and_control_verification_complete=False, performance_ready=False,
        strategy_runs=0, unit_tests_run=0, network_requests=0, broker_requests=0, orders=0,
        purchases_usd=0, heldout_2024_2025_files_read=0, paper_authorized=False,
        executions=[pin(path) for path in sources], snapshots=[pin(snapshots/path.name) for path in sources])
    write_json(output/"summary.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparation", type=Path, default=PREPARATION)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with offline_only():
        result=compile_inputs(args.output, preparation_path=args.preparation)
        print(json.dumps({k:result[k] for k in ("compiled_arm_window_scenarios","saved_accounting_checks",
            "runtime_integration_implemented","accounting_and_control_verification_complete","strategy_runs","purchases_usd")},indent=2))

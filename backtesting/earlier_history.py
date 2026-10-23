"""Study C-R4: audit pre-2019 coverage, then evaluate frozen daily rules.

Download is read-only at Alpaca; run is entirely offline. Neither command
requests price data from 2024 onward or calls an order endpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from importlib.metadata import version

import pandas as pd
import numpy as np
from alpaca.data.timeframe import TimeFrame

from app.data.market_calendar import AlpacaMarketCalendar, TradingSession
from app.data.market_data import ValidationConfig, validate_candles
from backtesting.allocation_research import ARMS as ALLOCATION_ARMS, pack_policy, simulate_policy
from backtesting.daily_research import (
    ARMS as RULE_ARMS, SYMBOLS, assert_baseline_matches, bootstrap_difference,
    load_study_data, passive_spy, simulate,
)
from backtesting.daily_strategies import DailyRuleConfig
from backtesting.research import COST_SCENARIOS, _utc_date, download_dataset, load_dataset

PROTOCOL = Path("docs/study_c_earlier_history_protocol.md")
CALENDAR_NAME = "calendar_2016_2023_study_c_r4.json"
MODES = {
    "primary": {"start": "2016-01-01", "score_start": "2017-01-01", "suffix": "2016_2018_study_c_r4"},
    "fallback": {"start": "2017-01-01", "score_start": "2018-01-01", "suffix": "2017_2018_study_c_r4_fallback"},
}


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


class SnapshotCalendar:
    """Actual broker sessions saved for repeatable offline calendar checks."""

    def __init__(self, path: Path):
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.start, self.end = date.fromisoformat(raw["start"]), date.fromisoformat(raw["end"])
        self.rows = tuple(TradingSession(pd.Timestamp(row["opens_at"]), pd.Timestamp(row["closes_at"])) for row in raw["sessions"])
        dates = [session.opens_at.tz_convert("America/New_York").date() for session in self.rows]
        if not self.rows or len(set(dates)) != len(dates) or dates != sorted(dates):
            raise ValueError("Calendar snapshot must contain unique ordered sessions")
        if dates[0] < self.start or dates[-1] > self.end:
            raise ValueError("Calendar session lies outside snapshot bounds")

    def sessions(self, start: date, end: date):
        if start < self.start or end > self.end:
            raise ValueError("Requested calendar range exceeds saved coverage")
        return [session for session in self.rows if start <= session.opens_at.tz_convert("America/New_York").date() <= end]


def _validate_range(bars, start, end, calendar):
    if not (bars["timestamp"].ge(_utc_date(start)) & bars["timestamp"].lt(_utc_date(end))).all():
        raise ValueError("Dataset contains candles outside its exclusive date range")
    return validate_candles(
        bars, config=ValidationConfig(timeframe=TimeFrame.Day, require_all_scheduled_bars=True),
        calendar=calendar, requested_start=_utc_date(start), requested_end=_utc_date(end) - timedelta(microseconds=1),
    )


def load_extension(path, symbol, start, calendar):
    bars, manifest = load_dataset(path)
    fields = ("symbol", "timeframe", "feed", "adjustment", "start_utc", "end_exclusive_utc")
    if tuple(manifest[key] for key in fields) != (symbol, "1Day", "sip", "all", start, "2019-01-01"):
        raise ValueError(f"{symbol}: extension conventions differ from the frozen scope")
    bars = bars.sort_values("timestamp", ignore_index=True)
    validation = _validate_range(bars, start, "2019-01-01", calendar)
    return bars, {**manifest, "path": str(path), "revalidated_warnings": [asdict(issue) for issue in validation.warnings]}


def download_coverage(data_dir: Path, output: Path) -> dict:
    """Choose a fallback by coverage only; no strategy is scored here."""
    if output.exists():
        raise FileExistsError("Coverage report exists; choose a new report path")
    from app.broker.alpaca_client import AlpacaClient
    data_dir.mkdir(parents=True, exist_ok=True)
    calendar_path = data_dir / CALENDAR_NAME
    if not calendar_path.exists():
        sessions = AlpacaMarketCalendar(AlpacaClient()).sessions(date(2016, 1, 1), date(2023, 12, 31))
        _write(calendar_path, {
            "start": "2016-01-01", "end": "2023-12-31", "downloaded_at_utc": datetime.now(UTC).isoformat(),
            "sessions": [{"opens_at": row.opens_at.isoformat(), "closes_at": row.closes_at.isoformat()} for row in sessions],
        })
    calendar = SnapshotCalendar(calendar_path)
    report = {"protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
              "calendar": str(calendar_path), "calendar_sha256": hashlib.sha256(calendar_path.read_bytes()).hexdigest(),
              "attempts": {}, "selected_mode": None, "coverage_complete": False}
    for mode, scope in MODES.items():
        outcomes = {}
        for symbol in SYMBOLS:
            path = data_dir / f"{symbol}_1Day_{scope['suffix']}.csv"
            try:
                if not path.exists():
                    download_dataset(symbol=symbol, start=scope["start"], end="2019-01-01", timeframe="1Day",
                                     destination=path, feed="sip", adjustment="all")
                bars, manifest = load_extension(path, symbol, scope["start"], calendar)
                outcomes[symbol] = {"accepted": True, "manifest": manifest}
                print(f"{mode} {symbol}: {len(bars)} validated daily bars", flush=True)
            except Exception as exc:
                outcomes[symbol] = {"accepted": False, "error_type": type(exc).__name__, "message": str(exc)[:600]}
                print(f"{mode} {symbol}: rejected ({type(exc).__name__})", flush=True)
        report["attempts"][mode] = outcomes
        if all(outcome["accepted"] for outcome in outcomes.values()):
            report["selected_mode"], report["coverage_complete"] = mode, True
            break
    _write(output, report)
    print(f"Coverage report: {output}; mode: {report['selected_mode']}")
    return report


def join_history(earlier, later, start, calendar):
    if set(earlier) != set(SYMBOLS) or set(later) != set(SYMBOLS):
        raise ValueError("Both history segments must contain all twelve declared symbols")
    joined = {}
    for symbol in SYMBOLS:
        frame = pd.concat([earlier[symbol], later[symbol]], ignore_index=True).sort_values("timestamp", ignore_index=True)
        _validate_range(frame, start, "2024-01-01", calendar)
        joined[symbol] = frame
    first_dates = joined[SYMBOLS[0]]["timestamp"]
    if any(not frame["timestamp"].equals(first_dates) for frame in joined.values()):
        raise ValueError("Joined basket session timestamps do not match")
    return joined


def _pack_window(result, start, end):
    packed = pack_policy(result)
    years = int(end[:4]) - int(start[:4])  # Frozen windows are full Jan-1 calendar years.
    m = packed["metrics"]
    m["annualized_return_cagr"] = (1 + m["total_return"]) ** (1 / years) - 1
    halt_year = None if result.permanent_halt_reason is None else int(result.halted_at[:4])
    m["annual_entry_halt_status"] = {
        year: ("not_halted" if halt_year is None or int(year) < halt_year else
               "halt_reached_in_year" if int(year) == halt_year else "halt_already_active_at_year_start")
        for year in m["annual_returns"]
    }
    return packed


def _data_summary(frame):
    positive = frame.loc[frame["volume"] > 0, "volume"]
    median = None if positive.empty else float(positive.median())
    anomalies = frame.loc[frame["volume"] > 10 * median] if median is not None else frame.iloc[:0]
    returns = frame["close"].pct_change(fill_method=None).abs()
    largest = returns.idxmax()
    return {"rows": len(frame), "first": frame["timestamp"].min().isoformat(), "last": frame["timestamp"].max().isoformat(),
            "yearly_rows": {str(year): int(count) for year, count in frame.groupby(frame["timestamp"].dt.year).size().items()},
            "volume_warning_dates": [{"date": row.timestamp.isoformat(), "volume": float(row.volume)} for row in anomalies.itertuples()],
            "largest_absolute_close_change": float(returns.loc[largest]),
            "largest_absolute_close_change_date": frame.loc[largest, "timestamp"].isoformat()}


def run_study(data_dir: Path, coverage_path: Path, output_dir: Path, reference: Path):
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != coverage["protocol_sha256"]:
        raise ValueError("Coverage audit and current study protocol hashes differ")
    output_dir.mkdir(parents=True, exist_ok=False)
    mode = coverage["selected_mode"]
    if not coverage["coverage_complete"] or mode not in MODES:
        report = {"status": "incomplete_coverage_no_basket_scored", "coverage": coverage, "paper_authorized": False}
        _write(output_dir / "report.json", report)
        print("No basket scored: neither frozen coverage window is complete")
        return report
    scope = MODES[mode]
    calendar_path = data_dir / CALENDAR_NAME
    if hashlib.sha256(calendar_path.read_bytes()).hexdigest() != coverage["calendar_sha256"]:
        raise ValueError("Calendar differs from the coverage audit")
    calendar = SnapshotCalendar(calendar_path)
    earlier, provenance = {}, {}
    for symbol in SYMBOLS:
        outcome = coverage["attempts"][mode][symbol]
        if not outcome["accepted"]:
            raise ValueError(f"{symbol}: selected coverage window was rejected")
        path = data_dir / f"{symbol}_1Day_{scope['suffix']}.csv"
        bars, manifest = load_extension(path, symbol, scope["start"], calendar)
        if manifest["sha256"] != outcome["manifest"]["sha256"]:
            raise ValueError(f"{symbol}: dataset changed after coverage selection")
        if int((bars["timestamp"] < _utc_date(scope["score_start"])).sum()) < 200:
            raise ValueError(f"{symbol}: fewer than 200 warmup sessions")
        earlier[symbol], provenance[symbol] = bars, manifest
    later, old_provenance = load_study_data(data_dir)
    combined = join_history(earlier, later, scope["start"], calendar)
    old_report = json.loads(reference.read_text(encoding="utf-8"))
    if old_report["selected_on_earlier_years"] != "vol_latched":
        raise ValueError("Reference does not contain the frozen C-R3 selection")
    candidate = next(arm for arm in ALLOCATION_ARMS if arm.id == "vol_latched")
    full = next(arm for arm in ALLOCATION_ARMS if arm.id == "full_latched")
    if (candidate.position_cap, candidate.total_cap, candidate.stop_risk_cap, candidate.volatility_contribution, candidate.pause_sessions) != (.05, .35, .005, .01, None):
        raise ValueError("Candidate policy no longer matches the frozen settings")
    costs = {name: replace(config, periods_per_year=252) for name, config in COST_SCENARIOS.items()}
    report = {
        "study": "C-R4", "status": "backward_historical_robustness", "coverage_mode": mode,
        "primary_coverage_complete": mode == "primary", "protocol_sha256": coverage["protocol_sha256"],
        "coverage_sha256": hashlib.sha256(coverage_path.read_bytes()).hexdigest(),
        "calendar_sha256": coverage["calendar_sha256"], "reference_sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
        "source_sha256": {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in (
            Path(__file__), Path("backtesting/allocation_research.py"), Path("backtesting/daily_strategies.py"),
            Path("backtesting/portfolio_engine.py"), Path("backtesting/protective_exits.py"),
            Path("backtesting/research_policy.py"), Path("backtesting/daily_research.py"), Path("app/ai/features.py"),
        )},
        "candidate": asdict(candidate), "provenance": provenance, "old_provenance": old_provenance,
        "environment": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__, "alpaca-py": version("alpaca-py")},
        "data_summary": {symbol: _data_summary(frame) for symbol, frame in earlier.items()},
        "joined_rows": {symbol: len(frame) for symbol, frame in combined.items()},
        "windows": {}, "diagnostics": {}, "paper_authorized": False,
    }
    count = 0
    for window, start, end in (("training", "2020-01-01", "2022-01-01"), ("development", "2022-01-01", "2024-01-01")):
        replay = {}
        for name, config in costs.items():
            result = simulate_policy(candidate, later, later["SPY"], config, start=start, end=end)
            replay[name] = pack_policy(result)
            count += 1
        assert_baseline_matches(replay, {"cost_scenarios": old_report[window]["vol_latched"]})
    report["reference_replay"] = "C-R3 candidate metrics and fills match exactly in both old windows and every cost case."
    print("C-R3 candidate reference reproduced exactly before new history scoring", flush=True)
    new_runs = {}
    for window, datasets, end in (("new_only", earlier, "2019-01-01"), ("continuous", combined, "2024-01-01")):
        start = scope["score_start"]
        report["windows"][window] = {"start": start, "end_exclusive": end, "arms": {}}
        for arm_name, policy in (("candidate", candidate), ("full_breakout_reference", full), ("original_rule_reference", None)):
            report["windows"][window]["arms"][arm_name] = {}
            for name, config in costs.items():
                result = (
                    simulate_policy(policy, datasets, datasets["SPY"], config, start=start, end=end)
                    if policy is not None else simulate(RULE_ARMS[0], datasets, datasets["SPY"], config, start=start, end=end)
                )
                count += 1
                report["windows"][window]["arms"][arm_name][name] = _pack_window(result, start, end)
                if window == "new_only" and name == "pessimistic":
                    new_runs[arm_name] = result
                print(f"{window}: {arm_name}/{name} complete", flush=True)
            _write(output_dir / f"{window}_{arm_name}.json", report["windows"][window]["arms"][arm_name])

    def score(*, datasets=earlier, **kwargs):
        nonlocal count
        count += 1
        result = simulate_policy(candidate, datasets, earlier["SPY"], costs["pessimistic"],
                                 start=scope["score_start"], end="2019-01-01", **kwargs)
        return _pack_window(result, scope["score_start"], "2019-01-01")

    diag = {"reverse_priority": score(priority="reverse"),
            "extra_session_delay_and_50bps_stops": score(delay=2, extra_stop_bps=50),
            "leave_one_symbol_out": {}, "channel_neighbors": {}}
    for symbol in SYMBOLS:
        diag["leave_one_symbol_out"][symbol] = score(datasets={name: frame for name, frame in earlier.items() if name != symbol})["metrics"]
    for entry, exit_ in ((40, 15), (70, 25)):
        diag["channel_neighbors"][f"{entry}_{exit_}"] = score(rule_config=DailyRuleConfig("breakout", entry, exit_))
    curve = [point.equity for point in new_runs["candidate"].equity_curve]
    diag["bootstrap_vs_cash"] = bootstrap_difference(curve, [100_000.0] * len(curve))
    diag["bootstrap_vs_full_breakout"] = bootstrap_difference(curve, [point.equity for point in new_runs["full_breakout_reference"].equity_curve])
    report["diagnostics"] = diag
    report["benchmarks"] = {
        window: {str(fraction): {name: passive_spy(datasets["SPY"], config, start=scope["score_start"], end=end, initial_fraction=fraction)
                                for name, config in costs.items()} for fraction in (.35, .70)}
        for window, datasets, end in (("new_only", earlier, "2019-01-01"), ("continuous", combined, "2024-01-01"))
    }
    new = report["windows"]["new_only"]["arms"]["candidate"]["pessimistic"]["metrics"]
    long = report["windows"]["continuous"]["arms"]["candidate"]["pessimistic"]["metrics"]
    stresses = [diag["reverse_priority"]["metrics"], diag["extra_session_delay_and_50bps_stops"]["metrics"], *diag["leave_one_symbol_out"].values()]
    checks = {
        "new_return_positive_after_estimated_exits": new["hypothetical_liquidated_return"] > 0,
        "new_drawdown_below_10_percent": new["max_drawdown"] > -.10 and new["drawdown_halt_count"] == 0,
        "new_no_permanent_halt": new["permanent_halt_reason"] is None,
        "new_at_least_20_closed_trades": new["completed_trades"] >= 20,
        "new_at_least_five_instruments": new["instruments_with_closed_trades"] >= 5,
        "all_priority_delay_removal_returns_positive": all(m["total_return"] > 0 for m in stresses),
        "all_priority_delay_removal_drawdowns_below_10_percent": all(m["max_drawdown"] > -.10 and m["drawdown_halt_count"] == 0 for m in stresses),
        "both_channel_neighbors_positive": all(case["metrics"]["total_return"] > 0 for case in diag["channel_neighbors"].values()),
        "continuous_return_positive_after_estimated_exits": long["hypothetical_liquidated_return"] > 0,
        "continuous_no_permanent_halt": long["permanent_halt_reason"] is None,
    }
    report["screen_checks"] = checks
    report["passes_primary_history_screen"] = mode == "primary" and all(checks.values())
    report["simulation_count"] = count
    _write(output_dir / "report.json", report)
    print(json.dumps({"report": str(output_dir / "report.json"), "simulations": count,
                      "passes_primary_history_screen": report["passes_primary_history_screen"], "checks": checks}, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download")
    download.add_argument("--data-dir", type=Path, default=Path("data/historical"))
    download.add_argument("--output", type=Path, required=True)
    run = commands.add_parser("run")
    run.add_argument("--data-dir", type=Path, default=Path("data/historical"))
    run.add_argument("--coverage", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--reference", type=Path, default=Path("data/reports/study_c_r3_final/report.json"))
    args = parser.parse_args()
    if args.command == "download":
        download_coverage(args.data_dir, args.output)
    else:
        run_study(args.data_dir, args.coverage, args.output_dir, args.reference)


if __name__ == "__main__":
    main()

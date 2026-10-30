"""Finite, offline Study C-R2 study. Never reads data from 2024 onward.

Run ``python -m backtesting.daily_research --output-dir data/reports/study_c_r2``
after downloading the predeclared SIP datasets. Add ``--iex-dir data/historical``
for the separate, complete-window 2023 signal-feed comparison.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

from app.strategy.base import SignalAction
from app.strategy.strategy_v1 import TrendFollowingV1
from backtesting.daily_strategies import DailyResearchStrategy, DailyRuleConfig, market_regime
from backtesting.engine import BacktestConfig
from backtesting.portfolio_engine import PortfolioBacktestEngine, PortfolioBacktestResult, summarize_portfolio
from backtesting.protective_exits import ProtectiveExitConfig
from backtesting.research import COST_SCENARIOS, _utc_date, load_dataset

SYMBOLS = ("AAPL", "MSFT", "JPM", "JNJ", "XOM", "WMT", "CAT", "PG", "NEE", "SPY", "QQQ", "IWM")
PROTOCOL = Path("docs/study_c_daily_improvements.md")


@dataclass(frozen=True)
class ResearchArm:
    id: str
    style: str | None = None
    protection: ProtectiveExitConfig | None = None
    cooldown: int = 0
    eligible: bool = False
    entry_sessions: int = 55
    exit_sessions: int = 20


ARMS = (
    ResearchArm("baseline"),
    ResearchArm("no_volume", "no_volume"),
    ResearchArm("regime_trend", "trend", ProtectiveExitConfig(atr_multiple=3, trailing=False), 10, True),
    ResearchArm("regime_breakout", "breakout", ProtectiveExitConfig(atr_multiple=3, trailing=False), 10, True),
    ResearchArm("regime_breakout_trail", "breakout", ProtectiveExitConfig(atr_multiple=3, trailing_atr_multiple=4), 10, True),
)


def load_study_data(directory: Path, *, feed: str = "sip") -> tuple[dict, dict]:
    """Load only explicit pre-2024 filenames; require matching conventions."""
    if feed not in {"sip", "iex"}:
        raise ValueError("Expected sip or iex")
    suffix = "2019_2023_study_c" if feed == "sip" else "2022_2023_study_c_r2_iex"
    start = "2019-01-01" if feed == "sip" else "2022-03-09"
    datasets, provenance = {}, {}
    for symbol in SYMBOLS:
        path = directory / f"{symbol}_1Day_{suffix}.csv"
        bars, manifest = load_dataset(path)
        expected = (symbol, "1Day", feed, "all", start, "2024-01-01")
        actual = tuple(manifest[name] for name in ("symbol", "timeframe", "feed", "adjustment", "start_utc", "end_exclusive_utc"))
        if actual != expected:
            raise ValueError(f"{symbol}: dataset conventions differ from frozen study scope")
        if (bars["timestamp"] >= _utc_date("2024-01-01")).any():
            raise ValueError("Reserved holdout data must not enter this study")
        datasets[symbol] = bars.sort_values("timestamp", ignore_index=True)
        provenance[symbol] = {"path": str(path), **manifest}
    dates = datasets[SYMBOLS[0]]["timestamp"]
    if any(not bars["timestamp"].equals(dates) for bars in datasets.values()):
        raise ValueError("All study symbols must have matching session timestamps; no filling")
    return datasets, provenance


def simulate(
    arm: ResearchArm, data: dict, context: pd.DataFrame, costs: BacktestConfig,
    *, start: str, end: str, priority: str = "alphabetical", delay: int = 1,
    signal_data: dict | None = None,
) -> PortfolioBacktestResult:
    if end > "2024-01-01":
        raise ValueError("Study end cannot open the reserved holdout")
    strategy = TrendFollowingV1() if arm.style is None else DailyResearchStrategy(
        DailyRuleConfig(arm.style, arm.entry_sessions, arm.exit_sessions),
        regime=market_regime(context) if arm.style != "no_volume" else None,
    )
    return PortfolioBacktestEngine(
        strategy, costs=costs, protection=arm.protection, buy_priority=priority,
        reentry_cooldown_sessions=arm.cooldown, execution_delay_sessions=delay,
    ).run(data, trade_start=_utc_date(start), trade_end=_utc_date(end), signal_datasets=signal_data)


def enriched_metrics(result: PortfolioBacktestResult) -> dict:
    metrics = summarize_portfolio(result)
    multiplier = (result.costs.slippage_bps + result.costs.spread_bps / 2) / 10_000
    liquidation_cost = sum(
        quantity * result.final_closes[symbol] * multiplier + result.costs.commission_per_order
        for symbol, quantity in result.final_positions.items()
    )
    values = {
        **metrics,
        "mean_closing_exposure": float(np.mean([point.gross_exposure for point in result.equity_curve])),
        "commissions_paid": sum(fill.commission for fill in result.fills),
        "traded_notional": sum(fill.quantity * fill.fill_price for fill in result.fills),
        "realized_pnl": metrics["total_realized_pnl"] if result.ownership_accounting is not None else sum(metrics["realized_pnl_by_symbol"].values()),
        "marked_unrealized_pnl": metrics["marked_unrealized_pnl_including_claims"] if result.ownership_accounting is not None else sum(position["marked_unrealized_pnl"] for position in metrics["open_positions"].values()),
        "instruments_with_closed_trades": len({fill.symbol for fill in result.fills if fill.side.value == "SELL"}),
        "hypothetical_exit_cost": liquidation_cost,
        "hypothetical_liquidated_return": (metrics["final_equity"] - liquidation_cost) / result.costs.initial_cash - 1,
    }
    if result.ownership_accounting is not None and metrics["ownership_claims"]:
        values["hypothetical_whole_share_exit_marked_return"] = values["hypothetical_liquidated_return"]
        values["hypothetical_liquidated_return"] = None
        values["claims_not_liquidated"] = True
    return values


def pack(result: PortfolioBacktestResult) -> dict:
    packed = {
        "metrics": enriched_metrics(result), "costs": asdict(result.costs),
        "equity_curve": [{"timestamp": point.timestamp.isoformat(), "equity": point.equity,
                          "exposure": point.gross_exposure} for point in result.equity_curve],
        "fills": [{**asdict(fill), "timestamp": fill.timestamp.isoformat(),
                   "signal_timestamp": fill.signal_timestamp.isoformat(), "side": fill.side.value}
                  for fill in result.fills],
        "events": list(result.events),
    }
    if result.universe_metadata is not None:
        packed["universe_metadata"] = result.universe_metadata
        if result.ownership_accounting is None:
            packed["cash_settlements"] = list(result.cash_settlements)
            packed["share_actions"] = list(result.share_actions)
            packed["dividend_entitlements"] = list(result.dividend_entitlements)
            packed["dividend_payments"] = list(result.dividend_payments)
            packed["final_dividend_receivables"] = list(result.final_dividend_receivables)
        for point, value in zip(result.equity_curve, packed["equity_curve"]):
            value.update(cash=point.cash, dividend_receivable=point.dividend_receivable)
            if result.ownership_accounting is not None:
                value.update(ownership_cash_receivable=point.ownership_cash_receivable, fractional_claim_value=point.fractional_claim_value)
    if result.ownership_accounting is not None:
        packed["accounting_ledger_version"] = 1
        packed["ownership_accounting"] = result.ownership_accounting
    return packed


def select_on_earlier_years(training: dict[str, dict]) -> tuple[str | None, dict]:
    assessments = {}
    eligible = []
    for arm in ARMS:
        if not arm.eligible:
            continue
        metrics = training[arm.id]["pessimistic"]["metrics"]
        checks = {
            "both_earlier_years_positive": all(metrics["annual_returns"].get(year, -1) > 0 for year in ("2020", "2021")),
            "drawdown_within_10_percent": metrics["max_drawdown"] >= -0.10,
            "no_entry_halt": metrics["entry_halted_at"] is None,
            "at_least_20_closed_trades": metrics["completed_trades"] >= 20,
            "at_least_five_instruments": metrics["instruments_with_closed_trades"] >= 5,
        }
        assessments[arm.id] = checks
        if all(checks.values()):
            eligible.append((min(metrics["annual_returns"].values()), -metrics["completed_trades"], arm.id))
    eligible.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return (eligible[0][2] if eligible else None), assessments


def passive_spy(data: pd.DataFrame, costs: BacktestConfig, *, start: str, end: str, initial_fraction: float = 0.70) -> dict:
    if isinstance(initial_fraction, bool) or not np.isfinite(initial_fraction) or not 0 < initial_fraction <= 1:
        raise ValueError("initial_fraction must be in (0, 1]")
    dates = data["timestamp"]
    indices = list(data.index[(dates >= _utc_date(start)) & (dates < _utc_date(end))])
    first = indices[0]
    if first < 1:
        raise ValueError("SPY allocation needs a prior completed close")
    multiplier = (costs.slippage_bps + costs.spread_bps / 2) / 10_000
    budget = costs.initial_cash * initial_fraction
    planned = int((budget - costs.commission_per_order) // (float(data.iloc[first - 1]["close"]) * (1 + multiplier)))
    price = float(data.iloc[first]["open"]) * (1 + multiplier)
    quantity = min(planned, int((budget - costs.commission_per_order) // price))
    cash = costs.initial_cash - quantity * price - costs.commission_per_order
    equity = cash + quantity * data.iloc[indices]["close"].to_numpy()
    peak = np.maximum.accumulate(np.r_[costs.initial_cash, equity])[1:]
    exit_cost = quantity * float(data.iloc[indices[-1]]["close"]) * multiplier + costs.commission_per_order
    return {"quantity": quantity, "total_return": float(equity[-1] / costs.initial_cash - 1),
            "hypothetical_liquidated_return": float((equity[-1] - exit_cost) / costs.initial_cash - 1),
            "max_drawdown": float(np.min(equity / peak - 1)),
            "mean_closing_exposure": float(np.mean((equity - cash) / equity)),
            "assumption": f"{initial_fraction:.0%} initial SPY allocation, remaining zero-yield cash; no risk halt or 10% single-position cap."}


def bootstrap_difference(candidate: list[float], baseline: list[float], *, seed: int = 20261023, draws: int = 2000, block: int = 20) -> dict:
    a, b = np.asarray(candidate, dtype=float), np.asarray(baseline, dtype=float)
    if len(a) != len(b) or len(a) < block or not np.isfinite(a).all() or not np.isfinite(b).all() or (a <= 0).any() or (b <= 0).any():
        raise ValueError("Bootstrap needs aligned positive finite equity curves and sufficient observations")
    ar = np.diff(np.log(np.r_[100_000.0, a]))
    br = np.diff(np.log(np.r_[100_000.0, b]))
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, len(a), size=(draws, int(np.ceil(len(a) / block))))
    indices = ((starts[:, :, None] + np.arange(block)) % len(a)).reshape(draws, -1)[:, :len(a)]
    differences = np.expm1(ar[indices].sum(axis=1)) - np.expm1(br[indices].sum(axis=1))
    return {"method": "paired_circular_20_session_blocks", "draws": draws, "seed": seed,
            "observed_return_difference": float(a[-1] / 100_000 - b[-1] / 100_000),
            "percentile_2_5": float(np.quantile(differences, 0.025)),
            "percentile_97_5": float(np.quantile(differences, 0.975)),
            "limitation": "Exploratory sample uncertainty, not selection-adjusted evidence or a formal significance test."}


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def assert_baseline_matches(current: dict, original: dict) -> None:
    """Check all old metric values and fills, allowing only absent null stops."""
    for name, previous in original["cost_scenarios"].items():
        for key, value in previous["metrics"].items():
            actual = current[name]["metrics"][key]
            if key == "open_positions":
                actual = {symbol: dict(position) for symbol, position in actual.items()}
                for symbol, position in actual.items():
                    if "stop_price" not in value.get(symbol, {}) and position.get("stop_price") is None:
                        position.pop("stop_price", None)
            if actual != value:
                raise ValueError(f"Baseline replay differs on {name}/{key}")
        if current[name]["fills"] != previous["fills"]:
            raise ValueError(f"Baseline fill replay differs on {name}")


def run_study(output_dir: Path, *, data_dir: Path, iex_dir: Path | None = None) -> dict:
    output_dir.mkdir(parents=True, exist_ok=False)
    data, provenance = load_study_data(data_dir)
    context = data["SPY"]
    costs = {name: replace(case, periods_per_year=252) for name, case in COST_SCENARIOS.items()}
    report = {
        "study": "C-R2", "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "arms": [asdict(arm) for arm in ARMS], "provenance": provenance,
        "code_sha256": {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in (
            Path(__file__), Path("backtesting/daily_strategies.py"), Path("backtesting/portfolio_engine.py"),
            Path("backtesting/protective_exits.py"), Path("app/ai/features.py"), Path("app/strategy/strategy_v1.py"),
        )},
        "training": {}, "development": {}, "diagnostics": {}, "paper_authorized": False,
    }
    original_path = Path("data/reports/study_c_shared_cash_close_planned.json")
    original = json.loads(original_path.read_text(encoding="utf-8"))
    baseline_runs = {name: simulate(ARMS[0], data, context, case, start="2022-01-01", end="2024-01-01")
                     for name, case in costs.items()}
    report["development"]["baseline"] = {name: pack(result) for name, result in baseline_runs.items()}
    assert_baseline_matches(report["development"]["baseline"], original)
    report["baseline_replay"] = "All original metric fields and fills match exactly in all three cost cases; missing null stop metadata normalized."
    _write(output_dir / "baseline_regression.json", report["development"]["baseline"])
    print("Original baseline regression verified before scoring new arms", flush=True)
    for arm in ARMS:
        report["training"][arm.id] = {}
        for name, case in costs.items():
            result = simulate(arm, data, context, case, start="2020-01-01", end="2022-01-01")
            report["training"][arm.id][name] = pack(result)
        print(f"Earlier-period results complete: {arm.id}", flush=True)
    selected, assessments = select_on_earlier_years(report["training"])
    report["selected_on_2020_2021"] = selected
    report["selection_checks"] = assessments
    _write(output_dir / "earlier_period_selection.json", {key: report[key] for key in (
        "protocol_sha256", "arms", "training", "selected_on_2020_2021", "selection_checks",
    )})
    print(f"Selection frozen before 2022-23 scoring: {selected}", flush=True)

    runs = {}
    for arm in ARMS:
        if arm.id != "baseline":
            report["development"][arm.id] = {}
        for name, case in costs.items():
            result = baseline_runs[name] if arm.id == "baseline" else simulate(
                arm, data, context, case, start="2022-01-01", end="2024-01-01",
            )
            report["development"][arm.id][name] = pack(result)
            if name == "pessimistic":
                runs[arm.id] = result
        print(f"Later development results complete: {arm.id}", flush=True)
        _write(output_dir / f"{arm.id}_development.json", report["development"][arm.id])

    diagnostic_arms = [arm for arm in ARMS if arm.eligible and (selected is None or arm.id == selected)]
    for arm in diagnostic_arms:
        diagnostics = {}
        reverse = simulate(arm, data, context, costs["pessimistic"], start="2022-01-01", end="2024-01-01", priority="reverse")
        diagnostics["reverse_priority"] = pack(reverse)
        stressed = replace(arm, protection=replace(arm.protection, extra_stop_slippage_bps=50))
        diagnostics["extra_session_delay_and_50bps_stops"] = pack(simulate(
            stressed, data, context, costs["pessimistic"], start="2022-01-01", end="2024-01-01", delay=2,
        ))
        diagnostics["leave_one_symbol_out"] = {}
        for symbol in SYMBOLS:
            reduced = {name: bars for name, bars in data.items() if name != symbol}
            result = simulate(arm, reduced, context, costs["pessimistic"], start="2022-01-01", end="2024-01-01")
            diagnostics["leave_one_symbol_out"][symbol] = enriched_metrics(result)
        diagnostics["channel_neighbors"] = {}
        if arm.style == "breakout":
            for entry, exit_ in ((40, 15), (70, 25)):
                neighbor = replace(arm, entry_sessions=entry, exit_sessions=exit_)
                diagnostics["channel_neighbors"][f"{entry}_{exit_}"] = pack(simulate(
                    neighbor, data, context, costs["pessimistic"], start="2022-01-01", end="2024-01-01",
                ))
        diagnostics["paired_bootstrap"] = bootstrap_difference(
            [point.equity for point in runs[arm.id].equity_curve],
            [point.equity for point in runs["baseline"].equity_curve],
        )
        report["diagnostics"][arm.id] = diagnostics
        _write(output_dir / f"{arm.id}_diagnostics.json", diagnostics)
        print(f"Robustness checks complete: {arm.id}", flush=True)

    report["benchmark"] = {name: passive_spy(context, case, start="2022-01-01", end="2024-01-01") for name, case in costs.items()}
    report["cash_benchmark"] = {"return": 0.0, "assumptions": "Zero interest, inflation and taxes omitted"}
    report["feed_comparison"] = {"status": "Not run; pass --iex-dir after obtaining complete short-window IEX datasets."}
    if iex_dir is not None:
        iex, iex_provenance = load_study_data(iex_dir, feed="iex")
        sip = {symbol: bars.loc[bars["timestamp"] >= _utc_date("2022-03-09")].reset_index(drop=True)
               for symbol, bars in data.items()}
        feed_result = {"status": "2023-only fresh account; same SIP execution for both signal feeds.", "iex_provenance": iex_provenance,
                       "warmup_start": "2022-03-09", "start": "2023-01-01", "end_exclusive": "2024-01-01", "arms": {}}
        for arm in ARMS:
            feed_result["arms"][arm.id] = {}
            for feed, signals in (("sip", sip), ("iex", iex)):
                result = simulate(arm, sip, signals["SPY"], costs["pessimistic"], start="2023-01-01", end="2024-01-01", signal_data=signals)
                feed_result["arms"][arm.id][feed] = pack(result)
        report["feed_comparison"] = feed_result

    baseline = enriched_metrics(runs["baseline"])
    report["development_checks"] = {}
    for arm in diagnostic_arms:
        metrics = enriched_metrics(runs[arm.id])
        diag = report["diagnostics"][arm.id]
        sensitivity_metrics = [diag["reverse_priority"]["metrics"], diag["extra_session_delay_and_50bps_stops"]["metrics"],
                               *diag["leave_one_symbol_out"].values(), *[x["metrics"] for x in diag["channel_neighbors"].values()]]
        checks = {
            "positive_pessimistic_return": metrics["total_return"] > 0,
            "beats_baseline_return": metrics["total_return"] > baseline["total_return"],
            "drawdown_not_worse_than_baseline": metrics["max_drawdown"] >= baseline["max_drawdown"],
            "both_later_years_nonnegative": all(metrics["annual_returns"].get(year, -1) >= 0 for year in ("2022", "2023")),
            "no_entry_halt": metrics["entry_halted_at"] is None,
            "at_least_20_closed_trades": metrics["completed_trades"] >= 20,
            "at_least_five_instruments": metrics["instruments_with_closed_trades"] >= 5,
            "positive_hypothetical_liquidation": metrics["hypothetical_liquidated_return"] > 0,
            "all_sensitivity_returns_positive": all(x["total_return"] > 0 for x in sensitivity_metrics),
            "all_sensitivity_drawdowns_within_10_percent": all(x["max_drawdown"] >= -0.10 for x in sensitivity_metrics),
        }
        report["development_checks"][arm.id] = {"checks": checks, "passes_development_screen": all(checks.values())}
    report["simulation_count"] = 30 + sum(14 + (2 if arm.style == "breakout" else 0) for arm in diagnostic_arms) + (10 if iex_dir else 0)
    _write(output_dir / "report.json", report)
    print(json.dumps({"report": str(output_dir / "report.json"), "selected_on_earlier_years": selected,
                      "baseline_replay": report["baseline_replay"], "development_checks": report["development_checks"]}, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--data-dir", default=Path("data/historical"), type=Path)
    parser.add_argument("--iex-dir", type=Path)
    args = parser.parse_args()
    run_study(args.output_dir, data_dir=args.data_dir, iex_dir=args.iex_dir)


if __name__ == "__main__":
    main()

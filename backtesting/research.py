"""Download an auditable historical dataset and run local cost scenarios.

Usage: ``python -m backtesting.research --help``. This module reads market
data only; it never calls Alpaca's order endpoints.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, replace
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import pandas as pd
from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from app.broker.alpaca_client import AlpacaClient
from app.ai.features import FEATURE_VERSION
from app.data.market_data import MarketDataService, validate_candles
from app.strategy.strategy_v1 import TrendFollowingV1
from backtesting.engine import BacktestConfig, BacktestEngine
from backtesting.metrics import calculate_metrics

TIMEFRAMES = {"15Min": TimeFrame(15, TimeFrameUnit.Minute), "1Hour": TimeFrame.Hour, "1Day": TimeFrame.Day}
PERIODS_PER_YEAR = {"15Min": 252 * 26, "1Hour": 252 * 7, "1Day": 252}
COST_SCENARIOS = {
    "optimistic": BacktestConfig(slippage_bps=0, spread_bps=0),
    "base": BacktestConfig(slippage_bps=5, spread_bps=2),
    "pessimistic": BacktestConfig(slippage_bps=20, spread_bps=10, commission_per_order=1),
}


def _utc_date(value: str) -> datetime:
    """Turn a YYYY-MM-DD research boundary into midnight UTC."""
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC)


def _manifest_path(dataset_path: Path) -> Path:
    return dataset_path.with_suffix(".manifest.json")


def download_dataset(
    *, symbol: str, start: str, end: str, timeframe: str, destination: Path,
    feed: str = "sip", adjustment: str = "all",
) -> dict[str, object]:
    """Fetch all SDK pages, validate complete sessions, then save CSV + manifest."""
    if _utc_date(start) >= _utc_date(end):
        raise ValueError("end must be after start; end is an exclusive UTC date")
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"timeframe must be one of {', '.join(TIMEFRAMES)}")
    if destination.exists() or _manifest_path(destination).exists():
        raise FileExistsError("Dataset or manifest already exists; choose a fresh destination")
    client = AlpacaClient()
    service = MarketDataService(client)
    bars, report = service.get_historical_candles(
        symbol, start=_utc_date(start), end=_utc_date(end),
        timeframe=TIMEFRAMES[timeframe],
        adjustment=Adjustment(adjustment), feed=DataFeed(feed),
    )
    if report.time_gaps:
        raise ValueError(
            f"{report.time_gaps} scheduled intervals have no bar. Investigate feed coverage or no-trade intervals before research."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    bars.to_csv(destination, index=False, date_format="%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "symbol": symbol.strip().upper(), "start_utc": start, "end_exclusive_utc": end,
        "timeframe": timeframe, "feed": feed, "adjustment": adjustment,
        "row_count": len(bars), "first_bar_utc": bars["timestamp"].min().isoformat(),
        "last_bar_utc": bars["timestamp"].max().isoformat(),
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "downloaded_at_utc": datetime.now(UTC).isoformat(),
        "alpaca_sdk_version": version("alpaca-py"),
        "universe_scope": "single_symbol_case_study",
        "validation_warnings": [asdict(issue) for issue in report.warnings],
    }
    _manifest_path(destination).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def load_dataset(dataset_path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    """Verify provenance and content before any performance calculation."""
    manifest = json.loads(_manifest_path(dataset_path).read_text(encoding="utf-8"))
    digest = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    if digest != manifest["sha256"]:
        raise ValueError("Dataset checksum differs from its download manifest")
    bars = pd.read_csv(dataset_path)
    # Validate the raw timestamp strings before normalizing. Passing utc=True
    # first would silently accept a dataset whose timestamps lost their zone.
    validate_candles(bars)
    bars["timestamp"] = pd.to_datetime(bars["timestamp"], utc=True)
    if len(bars) != manifest["row_count"]:
        raise ValueError("Dataset row count differs from its download manifest")
    if set(bars["symbol"].str.upper()) != {manifest["symbol"]}:
        raise ValueError("Dataset symbol differs from its download manifest")
    if manifest["universe_scope"] != "single_symbol_case_study":
        raise ValueError("This runner only supports a single-symbol case study")
    return bars, manifest


def run_scenarios(
    dataset_path: Path, *, trade_start: str, trade_end: str,
) -> dict[str, object]:
    """Compare cost assumptions on the same untouched historical dataset."""
    bars, manifest = load_dataset(dataset_path)
    start, end = _utc_date(trade_start), _utc_date(trade_end)
    if not (manifest["start_utc"] <= trade_start < trade_end <= manifest["end_exclusive_utc"]):
        raise ValueError("Trade window must lie inside the downloaded dataset range")
    results = {}
    for name, scenario in COST_SCENARIOS.items():
        config = replace(scenario, periods_per_year=PERIODS_PER_YEAR[manifest["timeframe"]])
        run = BacktestEngine(TrendFollowingV1(), config=config).run(
            bars, trade_start=pd.Timestamp(start), trade_end=pd.Timestamp(end)
        )
        metrics = calculate_metrics(run, periods_per_year=config.periods_per_year)
        results[name] = {
            "assumptions": asdict(config), "metrics": asdict(metrics),
            "signal_count": len(run.signals), "fill_count": len(run.fills),
            "last_equity": run.final_equity, "events": list(run.events),
        }
    return {
        "dataset": str(dataset_path), "dataset_sha256": manifest["sha256"],
        "symbol": manifest["symbol"], "timeframe": manifest["timeframe"],
        "strategy": TrendFollowingV1.name, "feature_version": FEATURE_VERSION,
        "feed": manifest["feed"], "adjustment": manifest["adjustment"],
        "trade_start_utc": trade_start, "trade_end_exclusive_utc": trade_end,
        "scope": manifest["universe_scope"],
        "scope_limit": "Single current-symbol case study; does not remove survivorship or universe-selection bias.",
        "cost_scenarios": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download", help="Download and validate Alpaca historical bars")
    download.add_argument("--symbol", required=True)
    download.add_argument("--start", required=True, help="YYYY-MM-DD UTC; inclusive")
    download.add_argument("--end", required=True, help="YYYY-MM-DD UTC; exclusive")
    download.add_argument("--timeframe", choices=TIMEFRAMES, default="15Min")
    download.add_argument("--feed", choices=["sip", "iex"], default="sip")
    download.add_argument("--adjustment", choices=["all", "split", "raw"], default="all")
    download.add_argument("--output", type=Path, required=True)
    backtest = commands.add_parser("backtest", help="Run local cost scenarios on a downloaded dataset")
    backtest.add_argument("--dataset", type=Path, required=True)
    backtest.add_argument("--trade-start", required=True, help="YYYY-MM-DD UTC; inclusive")
    backtest.add_argument("--trade-end", required=True, help="YYYY-MM-DD UTC; exclusive")
    backtest.add_argument("--output", type=Path, help="Optional JSON report path")
    arguments = parser.parse_args()
    if arguments.command == "download":
        result = download_dataset(
            symbol=arguments.symbol, start=arguments.start, end=arguments.end,
            timeframe=arguments.timeframe, feed=arguments.feed,
            adjustment=arguments.adjustment, destination=arguments.output,
        )
    else:
        result = run_scenarios(arguments.dataset, trade_start=arguments.trade_start, trade_end=arguments.trade_end)
        if arguments.output:
            if arguments.output.exists():
                raise FileExistsError("Report already exists; choose a fresh output path")
            arguments.output.parent.mkdir(parents=True, exist_ok=True)
            arguments.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

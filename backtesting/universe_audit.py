"""Read-only broad-universe coverage audit; never a performance backtest.

Run from either Windows or Linux with a fresh output directory. Raw public
catalogs and bars are local research artifacts, not broker/account snapshots.
The fixed date bounds deliberately exclude the reserved 2024-2025 prices.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import time
from collections import Counter
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from importlib.metadata import version
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import pandas as pd
from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.timeframe import TimeFrame

from app.broker.alpaca_client import AlpacaClient
from app.data.market_calendar import AlpacaMarketCalendar, TradingSession
from app.data.market_data import (
    CANONICAL_CANDLE_COLUMNS, CandleValidationError, ValidationConfig,
    _barset_to_candles, validate_candles,
)

START = datetime(2016, 1, 1, tzinfo=UTC)
END_EXCLUSIVE = datetime(2024, 1, 1, tzinfo=UTC)
EXCHANGES = ("NYSE", "NASDAQ", "AMEX", "ARCA", "BATS")
LIFECYCLE_PROBES = ("META", "FB", "TWTR", "ATVI", "SIVB", "FRC", "ABNB", "UBER")
DIRECTORIES = {
    "nasdaqlisted": "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt",
    "otherlisted": "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt",
}


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False, default=str) + "\n", encoding="utf-8")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _failure(exc: Exception) -> dict[str, object]:
    # HTTP exception messages can contain request context. Do not save them.
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    return {"exception": type(exc).__name__, "http_status": status if isinstance(status, int) else None}


def select_sample(assets: list[dict]) -> list[dict]:
    """Freeze metadata-only, deterministic coverage probes before prices."""
    def rank(asset: dict) -> str:
        key = f"broad-universe-audit-v1|{asset['id']}|{asset['symbol']}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    selected: dict[str, dict] = {}

    def add(symbol: str, reason: str, asset: dict | None = None) -> None:
        probe = selected.setdefault(symbol, {"symbol": symbol, "reasons": [], "asset": asset})
        probe["reasons"].append(reason)

    for exchange in EXCHANGES:
        pool = [a for a in assets if a["exchange"] == exchange and a["status"] == "active" and a["tradable"]]
        for asset in sorted(pool, key=rank)[:8]:
            add(asset["symbol"], f"active_{exchange}", asset)
    for asset in sorted([a for a in assets if a["status"] == "inactive"], key=rank)[:8]:
        add(asset["symbol"], "inactive_sample", asset)
    by_symbol = {a["symbol"]: a for a in assets}
    for symbol in LIFECYCLE_PROBES:
        add(symbol, "lifecycle_probe", by_symbol.get(symbol))
    return list(selected.values())


class _SavedCalendar:
    def __init__(self, sessions: list[TradingSession]):
        self._sessions = sessions

    def sessions(self, start: date, end: date) -> list[TradingSession]:
        return [s for s in self._sessions if start <= s.opens_at.date() <= end]


def analyze_coverage(candles: pd.DataFrame, *, symbol: str, sessions: list[TradingSession]) -> dict:
    """Separate lifecycle edges from internal unobserved scheduled intervals.

    Counts describe observations, never guessed listing dates or fabricated
    fills. Structural errors are retained even if coverage counts are useful.
    """
    expected = {
        s.opens_at.tz_convert(ZoneInfo("America/New_York")).normalize().tz_convert("UTC")
        for s in sessions
    }
    result: dict = {"rows": len(candles), "expected_sessions": len(expected), "hard_errors": [], "warnings": []}
    if candles.empty:
        result.update(status="empty", unobserved_sessions=len(expected), before_first=None,
                      internal_unobserved=None, after_last=None, first_bar=None, last_bar=None)
        return result
    try:
        validation = validate_candles(
            candles, config=ValidationConfig(timeframe=TimeFrame.Day),
            calendar=_SavedCalendar(sessions), requested_start=START,
            requested_end=END_EXCLUSIVE - timedelta(microseconds=1),
        )
        result["warnings"] = [asdict(issue) for issue in validation.warnings]
    except CandleValidationError as exc:
        result["hard_errors"] = [asdict(issue) for issue in exc.issues]
    if set(candles["symbol"]) != {symbol}:
        result["hard_errors"].append({"code": "unexpected_symbol", "message": "Returned symbols differ from requested identity."})
    observed = set(pd.to_datetime(candles["timestamp"], errors="coerce", utc=True).dropna())
    outside = observed - expected
    missing = expected - observed
    first, last = min(observed, default=None), max(observed, default=None)
    if outside and not result["hard_errors"]:
        result["hard_errors"].append({"code": "unexpected_timestamp", "row_count": len(outside)})
    result.update(
        status="invalid" if result["hard_errors"] else ("complete" if not missing else "incomplete_unexplained"),
        first_bar=str(first) if first is not None else None,
        last_bar=str(last) if last is not None else None,
        unobserved_sessions=len(missing), unexpected_timestamps=len(outside),
        before_first=sum(t < first for t in missing) if first is not None else None,
        internal_unobserved=sum(first <= t <= last for t in missing) if first is not None else None,
        after_last=sum(t > last for t in missing) if last is not None else None,
        unobserved_dates=[t.date().isoformat() for t in sorted(missing)],
        unexpected_dates=[str(t) for t in sorted(outside)],
    )
    return result


def _directory_snapshot(output: Path) -> tuple[dict, dict]:
    metadata, flags = {}, {}
    for name, url in DIRECTORIES.items():
        try:
            request = Request(url, headers={"User-Agent": "TradingBot-ReadOnlyResearch/1.0"})
            with urlopen(request, timeout=30) as response:
                payload = response.read(10_000_001)
            if len(payload) > 10_000_000:
                raise ValueError("Directory exceeds audit size budget")
            path = output / f"{name}.txt"
            path.write_bytes(payload)
            rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig")), delimiter="|"))
            symbol_field = "Symbol" if name == "nasdaqlisted" else "ACT Symbol"
            if not rows or not {symbol_field, "ETF", "Test Issue"}.issubset(rows[0]):
                raise ValueError("Unexpected public directory schema")
            count = 0
            for row in rows:
                symbol = row[symbol_field]
                if not symbol or symbol.startswith("File Creation Time"):
                    continue
                flags[symbol] = {"etf": row["ETF"], "test_issue": row["Test Issue"], "source": name}
                count += 1
            metadata[name] = {"status": "downloaded", "url": url, "rows": count, "sha256": _digest(path)}
        except Exception as exc:
            metadata[name] = {"status": "error", "url": url, **_failure(exc)}
    return metadata, flags


def run_audit(output: Path) -> dict:
    """Execute the fixed protocol. Failures remain evidence, not exclusions."""
    if output.exists():
        raise FileExistsError("Choose a fresh audit directory; existing evidence is never overwritten")
    output.mkdir(parents=True)
    started = time.monotonic()
    root = Path(__file__).resolve().parents[1]
    report: dict = {
        "scope": "current_catalog_and_fixed_historical_coverage_sample_not_performance",
        "started_at_utc": datetime.now(UTC).isoformat(), "start_utc": START.isoformat(),
        "end_exclusive_utc": END_EXCLUSIVE.isoformat(), "feed": "sip", "adjustment": "all",
        "timeframe": "1Day", "symbol_asof": "API default current mapping; installed SDK lacks asof field",
        "alpaca_sdk_version": version("alpaca-py"), "probes": [],
        "source_hashes": {name: _digest(root / name) for name in (
            "backtesting/universe_audit.py", "app/broker/alpaca_client.py",
            "app/data/market_data.py", "docs/broad_universe_audit_protocol.md",
        )},
        "market_wide_backtest_ready": False,
        "blockers": [
            "Current catalog does not establish complete dated historical membership or common-stock classification.",
            "Stable historical identity/aliases and delisting terminal outcomes are not independently audited.",
            "Current portfolio engine requires identical dates; dynamic universes need explicit lifecycle support.",
            "Today's adjusted data and symbol mapping are not point-in-time snapshots.",
        ],
    }
    _write(output / "report.json", report)
    client = AlpacaClient()
    try:
        assets = client.get_assets()
        if not assets:
            raise ValueError("Empty asset catalog")
        _write(output / "assets.json", assets)
        report["catalog"] = {
            "count": len(assets), "sha256": _digest(output / "assets.json"),
            "statuses": dict(Counter(a["status"] for a in assets)),
            "exchanges": dict(Counter(a["exchange"] for a in assets)),
            "active_tradable": sum(a["status"] == "active" and a["tradable"] for a in assets),
            "available_fields": sorted(set().union(*(a.keys() for a in assets))),
            "duplicate_symbols": [s for s, n in Counter(a["symbol"] for a in assets).items() if n > 1],
        }
        sample = select_sample(assets)
        _write(output / "sample.json", sample)  # Frozen before any new price request.
        report["sample_sha256"] = _digest(output / "sample.json")
        report["directories"], flags = _directory_snapshot(output)
        _write(output / "directory_flags.json", flags)
        sessions = AlpacaMarketCalendar(client).sessions(START.date(), (END_EXCLUSIVE - timedelta(days=1)).date())
        if not sessions or len({s.opens_at for s in sessions}) != len(sessions):
            raise ValueError("Empty or duplicated exchange calendar")
        _write(output / "calendar.json", [asdict(s) for s in sessions])
        report["calendar"] = {"sessions": len(sessions), "sha256": _digest(output / "calendar.json")}
    except Exception as exc:
        report["setup_failure"] = _failure(exc)
        _write(output / "report.json", report)
        return report
    (output / "bars").mkdir()
    for index, probe in enumerate(sample, 1):
        symbol = probe["symbol"]
        before = time.monotonic()
        item: dict = {"symbol": symbol, "reasons": probe["reasons"], "directory": flags.get(symbol)}
        try:
            response = client.get_market_data_batch(
                [symbol], start=START, end=END_EXCLUSIVE - timedelta(seconds=1),
                timeframe=TimeFrame.Day, feed=DataFeed.SIP, adjustment=Adjustment.ALL,
            )
            if not any(response.data.values()):
                candles = pd.DataFrame(columns=CANONICAL_CANDLE_COLUMNS)
            else:
                candles = _barset_to_candles(response, symbol)
            # Numeric filenames avoid OS-specific symbol/path characters.
            path = output / "bars" / f"{index:03d}.csv"
            candles.to_csv(path, index=False)
            item.update(csv=str(path.relative_to(output)), sha256=_digest(path), bytes=path.stat().st_size)
            item.update(analyze_coverage(candles, symbol=symbol, sessions=sessions))
        except Exception as exc:
            item.update(status="request_or_analysis_error", **_failure(exc))
        item["elapsed_seconds"] = round(time.monotonic() - before, 3)
        report["probes"].append(item)
        _write(output / "report.json", report)
        print(json.dumps({"probe": index, "of": len(sample), "symbol": symbol,
                          "status": item["status"], "rows": item.get("rows")}), flush=True)
    report["summary"] = {
        "probed_symbols": len(sample), "statuses": dict(Counter(p["status"] for p in report["probes"])),
        "rows": sum(p.get("rows", 0) for p in report["probes"]),
        "csv_bytes": sum(p.get("bytes", 0) for p in report["probes"]),
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    report["finished_at_utc"] = datetime.now(UTC).isoformat()
    _write(output / "report.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    result = run_audit(arguments.output)
    print(json.dumps({k: result.get(k) for k in ("summary", "setup_failure", "market_wide_backtest_ready", "blockers")}, indent=2))
    if "setup_failure" in result:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

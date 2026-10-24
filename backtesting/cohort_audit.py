"""Offline identity/coverage audit for the retained September 2016 cohort.

No HTTP, brokerage clients, credentials, payments or simulations. Only explicitly
reviewed public downloads and saved pre-2024 candles enter this command. A
dated ticker crosswalk is not a complete historical security master.
"""

import argparse
from collections import Counter, defaultdict
import csv
from dataclasses import asdict
from datetime import date
import hashlib
import io
import json
from math import isfinite
from pathlib import Path, PureWindowsPath
import re

import pandas as pd
from alpaca.data.timeframe import TimeFrame

from app.data.market_calendar import TradingSession
from app.data.market_data import ValidationConfig, validate_candles
from backtesting.historical_holdings import FilingRows, require_available

REVIEW = Path("docs/2016_cohort_source_review.json")
START = pd.Timestamp("2016-01-01", tz="UTC")  # Includes the proposed warmup.
END = pd.Timestamp("2024-01-01", tz="UTC")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# Keep this offline command independent of research runners that import broker
# clients. Reading a public snapshot never requires loading account settings.
def checked_file(root: Path, entry: dict) -> Path:
    path = (root / entry["path"]).resolve()
    if not path.is_relative_to(root.resolve()) or digest(path) != entry["sha256"]:
        raise ValueError("Reviewed source path/checksum changed")
    return path


def source_text(path: Path) -> str:
    parser = FilingRows()
    parser.feed(path.read_text(encoding="utf-8"))
    return " ".join(" ".join(parser.text).split())


def normalized_name(name: str) -> str:
    """Exact comparison after a small declared spelling/footnote cleanup.

    Class letters and all other identifying words remain. No fuzzy scores or
    current-company-name matches can automatically assign a historical ticker.
    """
    name = re.sub(r"\([a-z]+\)", "", name, flags=re.I).upper().replace("&", " AND ")
    name = re.sub(r"\b(CORPORATION|CORP|CO|COMPANY|INCORPORATED|INC|PLC|LTD|LIMITED|REIT)\b", "", name)
    return re.sub(r"[^A-Z0-9]", "", name)


def read_issuer_snapshot(path: Path, *, asof: str) -> tuple[list[dict], dict]:
    text = path.read_text(encoding="utf-8-sig")
    if text.lstrip().startswith("<"):
        raise ValueError("Holdings download is HTML, not an historical CSV")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or rows[0] != ["iShares Core S&P 500 ETF"]:
        raise ValueError("Historical CSV identifies the wrong fund")
    day = date.fromisoformat(asof)
    expected = f"{day.strftime('%b')} {day.day:02d}, {day.year}"
    if len(rows) < 2 or rows[1] != ["Fund Holdings as of", expected]:
        raise ValueError("Download did not honor the exact requested historical date")
    headers = next((i for i, row in enumerate(rows) if row[:2] == ["Ticker", "Name"]), None)
    required = {"Ticker", "Name", "Asset Class", "Exchange", "Price", "Currency", "Market Currency"}
    if headers is None or not required.issubset(rows[headers]):
        raise ValueError("Unexpected historical holdings schema")
    body = [row for row in rows[headers + 1:] if row]
    if any(len(row) != len(rows[headers]) for row in body):
        raise ValueError("Malformed holdings row; do not silently drop a security")
    records = [dict(zip(rows[headers], row)) for row in body]
    equities = [row for row in records if row["Asset Class"] == "Equity"]
    if not 400 <= len(equities) <= 600 or len({row["Ticker"] for row in equities}) != len(equities):
        raise ValueError("Historical holdings have missing/duplicate/unexpected equity rows")
    for row in equities:
        price = float(row["Price"].replace(",", ""))
        if not row["Ticker"].strip() or not row["Name"].strip() or not isfinite(price) or price <= 0:
            raise ValueError("Invalid dated security name/ticker/price")
        if row["Currency"] != "USD" or row["Market Currency"] != "USD":
            raise ValueError("Currency conversion requires explicit review")
    return equities, {"fund": rows[0][0], "asof": asof, "equity_rows": len(equities),
                      "non_equity_rows_not_used_for_identity": dict(Counter(r["Asset Class"] for r in records if r["Asset Class"] != "Equity")),
                      "historical_publication_time_verified": False}


def map_cohort(rows: list[dict], equities: list[dict], crosswalk: dict, *, texts: dict) -> list[dict]:
    by_name, by_ticker = defaultdict(list), {}
    for equity in equities:
        by_name[normalized_name(equity["Name"])].append(equity)
        by_ticker[equity["Ticker"]] = equity
    manual = {r["membership_key"]: r for r in crosswalk["manual_pairs"]}
    if len(manual) != len(crosswalk["manual_pairs"]):
        raise ValueError("Duplicate manual source-name mapping")
    keys = {r["membership_key"] for r in rows}
    if len(keys) != len(rows) or not set(manual).issubset(keys):
        raise ValueError("Invalid/repeated cohort row keys or extraneous review rows")
    extra = crosswalk["extra_primary_identity"]
    if extra["membership_key"] not in keys or extra["membership_key"] in manual:
        raise ValueError("Independent identity review is outside the original cohort")
    result, assigned = [], set()
    for row in rows:
        key = row["membership_key"]
        common = {**row, "instrument_id": "COHORT-2016-" + key.rsplit("-", 1)[1],
                  "instrument_id_scope": "local_retained_security_row_not_permanent_market_identifier",
                  "identity_asof": "2016-09-30", "full_alias_history_verified": False,
                  "historical_known_at": None, "ready_for_simulation": False}
        if key == extra["membership_key"]:
            if "Class V" not in row["source_name"] or not all(s in texts[extra["source_id"]] for s in ("DVMT", "tracking stock")):
                raise ValueError("Independent tracking-stock identity is not corroborated")
            result.append({**common, "issuer_ticker": extra["issuer_ticker"], "issuer_name": row["source_name"],
                           "mapping_method": "independent_SEC_identity_review", "security_type": extra["security_type"],
                           "mapping_source_id": extra["source_id"], "same_date_price_difference": None,
                           "unsupported_tracking_class": True})
            continue
        pair = manual.get(key)
        if pair:
            if pair["source_name"] != row["source_name"]:
                raise ValueError("Manual mapping's original security name changed")
            equity = by_ticker.get(pair["issuer_ticker"])
            if equity is None or equity["Name"] != pair["issuer_name"]:
                raise ValueError("Manual mapping does not match the issuer's dated ticker/name")
            method = "explicit_reviewed_name_pair"
        else:
            candidates = by_name.get(normalized_name(row["source_name"]), [])
            if len(candidates) != 1:
                raise ValueError(f"{key}: name ambiguous/unresolved; do not drop or guess this row")
            equity, method = candidates[0], "unique_normalized_name_and_same_date_price"
        if equity["Ticker"] in assigned:
            raise ValueError("Two cohort securities mapped to the same dated ticker")
        assigned.add(equity["Ticker"])
        # This one-date price comparison only corroborates identity; no returns
        # or favorable future performance enter the name/alias decisions.
        difference = abs(int(row["reported_market_value_usd"]) / int(row["reported_shares"])
                         - float(equity["Price"].replace(",", "")))
        if difference > .015:
            raise ValueError(f"{key}: same-date prices disagree; class/identity requires review")
        result.append({**common, "issuer_ticker": equity["Ticker"], "issuer_name": equity["Name"],
                       "mapping_method": method, "mapping_source_id": "ivv_20160930",
                       "snapshot_exchange": equity["Exchange"], "snapshot_location": equity["Location"],
                       "security_type": "reit_common" if "REIT" in row["source_name"] else "common_stock_source_schedule",
                       "same_date_price_difference": difference,
                       "vendor_alias_spelling_review_required": equity["Ticker"] in {"BRKB", "UAC/C"}})
    if len(result) != len(rows) or assigned != set(by_ticker):
        raise ValueError("Cohort or corroborating equity roster is not completely accounted for")
    return result


class SavedCalendar:
    def __init__(self, sessions):
        self.rows = sessions

    def sessions(self, start, end):
        return [s for s in self.rows if start <= s.opens_at.tz_convert("America/New_York").date() <= end]


def read_cached_prices(path: Path, metadata: dict, calendar: SavedCalendar) -> tuple[dict, set]:
    """Checksum/calendar audit only. Never infer liquidity or an event from a gap."""
    if digest(path) != metadata["sha256"]:
        raise ValueError(f"Saved candle checksum changed: {path}")
    frame = pd.read_csv(path)
    validation = validate_candles(frame, config=ValidationConfig(timeframe=TimeFrame.Day), calendar=calendar)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    if not frame.empty and not ((frame["timestamp"] >= START) & (frame["timestamp"] < END)).all():
        raise ValueError("Cached candles exceed declared pre-2024 audit bounds")
    if not frame.empty and set(frame["symbol"]) != {metadata["symbol"]}:
        raise ValueError("Cached candle symbol does not match source metadata")
    dates = set(frame["timestamp"])
    return {"path": str(path), "sha256": metadata["sha256"], "symbol": metadata["symbol"],
            "adjustment": metadata["adjustment"], "feed": metadata["feed"], "rows": len(frame),
            "first_bar": None if frame.empty else min(dates).isoformat(),
            "last_bar": None if frame.empty else max(dates).isoformat(),
            "warnings": [asdict(w) for w in validation.warnings],
            "historical_identity_continuity_verified": False}, dates


def audit_cache(review: dict, cohort: list[dict], events: list[dict], *, historical_dir: Path) -> tuple[list[dict], dict]:
    root = Path(review["cached_audit_root"])
    report_path = root / "report.json"
    if digest(report_path) != review["cached_audit_report_sha256"]:
        raise ValueError("Original broad coverage audit checksum changed")
    prior = json.loads(report_path.read_text(encoding="utf-8"))
    cal_path = root / "calendar.json"
    if digest(cal_path) != prior["calendar"]["sha256"]:
        raise ValueError("Saved market calendar checksum changed")
    sessions = [TradingSession(pd.Timestamp(s["opens_at"]), pd.Timestamp(s["closes_at"])) for s in json.loads(cal_path.read_text())]
    expected = {s.opens_at.tz_convert("America/New_York").normalize().tz_convert("UTC") for s in sessions}
    if len(expected) != len(sessions) or len(sessions) != prior["calendar"]["sessions"]:
        raise ValueError("Saved exchange calendar has duplicate/missing sessions")
    if not expected or min(expected) < START or max(expected) >= END:
        raise ValueError("Calendar exceeds the pre-2024 audit window")
    calendar = SavedCalendar(sessions)
    symbols = {r["issuer_ticker"] for r in cohort}
    symbols.update(e[k] for e in events for k in ("from_symbol", "to_symbol") if k in e)
    candidates, skipped = [], []
    for entry in prior["probes"]:
        if entry["symbol"] in symbols and "csv" in entry:
            path = root.joinpath(*PureWindowsPath(entry["csv"]).parts).resolve()
            if not path.is_relative_to(root.resolve()):
                raise ValueError("Cached audit candle path escapes its source directory")
            candidates.append((path, {**entry, "adjustment": prior["adjustment"], "feed": prior["feed"]}))
    for manifest_path in sorted(historical_dir.glob("*.manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("timeframe") != "1Day" or manifest.get("symbol") not in symbols:
            continue
        if manifest["start_utc"] < "2016-01-01" or manifest["end_exclusive_utc"] > "2024-01-01":
            skipped.append({"manifest": str(manifest_path), "reason": "outside_pre_2024_window; candles_not_read"})
            continue
        candidates.append((manifest_path.with_name(manifest_path.name.removesuffix(".manifest.json") + ".csv"), manifest))
    pilot = json.loads(Path(review["price_pilot_review"]).read_text(encoding="utf-8"))
    candidates.append((checked_file(Path(pilot["source_root"]), pilot["prices"]), pilot["prices"]))
    records, available, seen = [], defaultdict(lambda: defaultdict(set)), set()
    for path, metadata in candidates:
        path = path.resolve()
        if path in seen:
            continue
        seen.add(path)
        record, dates = read_cached_prices(path, metadata, calendar)
        records.append(record)
        # Coverage under a ticker is only an observation; a reused ticker is
        # not automatically attached to the old company or its successor.
        available[metadata["symbol"]][metadata["adjustment"]].update(dates)
    known_events = defaultdict(list)
    for event in events:
        known_events[event["membership_key"]].append(event)
    for row in cohort:
        relevant = known_events[row["membership_key"]]
        aliases = {row["issuer_ticker"]}
        aliases.update(e[k] for e in relevant for k in ("from_symbol", "to_symbol") if k in e)
        raw = set().union(*(available[s]["raw"] for s in aliases))
        adjusted = set().union(*(dates for s in aliases for basis, dates in available[s].items() if basis != "raw"))
        row["cached_observations"] = {
            "candidate_aliases_only_not_certified_price_attachment": sorted(aliases),
            "raw_session_count": len(raw), "raw_unobserved_session_count": len(expected - raw),
            "adjusted_session_count": len(adjusted), "required_calendar_sessions": len(expected),
            "raw_calendar_coverage_complete": bool(raw) and not (expected - raw),
            "events_reviewed": len(relevant), "event_history_complete": False,
            "gap_interpretation": "Unobserved sessions; not assumed missing, IPOs, holidays or zero-value outcomes."}
    return records, {"required_calendar_sessions": len(expected), "calendar_sha256": digest(cal_path),
                     "cached_daily_files_checked": len(records), "skipped_manifest_ranges": skipped,
                     "cohort_rows_with_candidate_raw_observations": sum(r["cached_observations"]["raw_session_count"] > 0 for r in cohort),
                     "cohort_rows_with_candidate_adjusted_observations": sum(r["cached_observations"]["adjusted_session_count"] > 0 for r in cohort),
                     "cohort_rows_with_complete_raw_calendar_observations": sum(r["cached_observations"]["raw_calendar_coverage_complete"] for r in cohort),
                     "observations_certify_security_identity_or_event_completeness": False}


def run_audit(output: Path, *, review_path: Path = REVIEW, historical_dir=Path("data/historical")) -> dict:
    if output.exists():
        raise FileExistsError("Choose a fresh cohort-audit output directory")
    review = json.loads(review_path.read_text(encoding="utf-8"))
    if review["spending_budget_usd"] != 0 or review["asof"] != "2016-09-30":
        raise ValueError("This audit is restricted to the no-purchase September 2016 cohort")
    root = Path(review["source_root"])
    paths = {key: checked_file(root, entry) for key, entry in review["sources"].items()}
    texts = {key: source_text(path) for key, path in paths.items() if path.suffix == ".html"}
    for check in review["class_identity_checks"]:
        if not all(term.lower() in texts[check["source_id"]].lower() for term in check["terms"]):
            raise ValueError("Primary share-class identity evidence does not corroborate review")
    source_review_path = Path(review["original_membership_review"])
    basket = next(b for b in json.loads(source_review_path.read_text())["baskets"] if b["asof"] == review["asof"])
    require_available(basket, "2017-01-01T00:00:00Z")
    roster_path = Path(basket["holding_rows_csv"])
    if digest(roster_path) != basket["holding_rows_sha256"]:
        raise ValueError("Original retained stock roster checksum changed")
    with roster_path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    if len(rows) != 506 or sum(int(r["reported_market_value_usd"]) for r in rows) != basket["common_stock_market_value_usd"]:
        raise ValueError("Original 506 security rows and disclosed total must remain intact")
    equities, snapshot = read_issuer_snapshot(paths["ivv_20160930"], asof=review["asof"])
    crosswalk_path = Path(review["crosswalk_review"])
    crosswalk = json.loads(crosswalk_path.read_text(encoding="utf-8"))
    if crosswalk["schema_version"] != 1 or crosswalk["asof"] != review["asof"]:
        raise ValueError("Crosswalk review must match the dated historical source")
    cohort = map_cohort(rows, equities, crosswalk, texts=texts)
    keys, events = {r["membership_key"] for r in cohort}, review["events"]
    for event in events:
        if event["membership_key"] not in keys or event["effective_date"] >= "2024-01-01":
            raise ValueError("Event exceeds the declared development cohort/window")
        if event["ready_for_simulation"] or event["historical_known_at"] is not None or event["cash_available_session"] is not None:
            raise ValueError("Review candidates cannot be silently promoted to execution events")
        if not all(term.lower() in texts[event["source_id"]].lower() for term in event["required_source_terms"]):
            raise ValueError(f"Source does not corroborate event review: {event['membership_key']}/{event['kind']}")
    files, coverage = audit_cache(review, cohort, events, historical_dir=historical_dir)
    checks = {"all_506_original_rows_retained": len(cohort) == 506,
              "all_505_issuer_equities_accounted_for": len(equities) == 505,
              "dated_aliases_distinct": len({r["issuer_ticker"] for r in cohort}) == 506,
              "no_row_silently_execution_ready": not any(r["ready_for_simulation"] for r in cohort)}
    report = {"scope": "offline_dated_alias_and_saved_data_audit_not_strategy_performance",
              "spending": {"new_purchases_usd": 0, "broker_requests": 0, "account_requests": 0,
                           "network_requests_by_audit_runner": 0, "orders_submitted": 0,
                           "source_acquisition": "Unauthenticated free public issuer/SEC GET downloads saved separately; no purchases or upgrades."},
              "review_sha256": digest(review_path), "source_review_sha256": digest(source_review_path),
              "crosswalk_sha256": digest(crosswalk_path), "roster_sha256": digest(roster_path),
              "source_sha256": {key: digest(path) for key, path in paths.items()},
              "execution_sha256": {name: digest(name) for name in ("backtesting/cohort_audit.py", "backtesting/raw_action_pilot.py", "backtesting/historical_holdings.py", "app/data/market_data.py")},
              "snapshot": snapshot, "checks": checks, "all_checks_passed": all(checks.values()),
              "mapping_counts": dict(Counter(row["mapping_method"] for row in cohort)),
              "event_counts": dict(Counter(e["kind"] for e in events)), "coverage": coverage,
              "market_wide_ready": False, "cohort_backtest_ready": False, "performance_scored": False,
              "holdout_prices_opened": False, "limitations": [
                  "Snapshot aliases do not certify full dated alias history, permanent IDs, or original publication times.",
                  "Fund holdings publication timing is not inferred from holdings date; membership remains anchored to the SEC filing bound.",
                  "No event evidence means unknown coverage, not an event-free security.",
                  "Adjusted cached candles cannot substitute for a raw corporate-action-aware run.",
                  "Known spin-offs/share mergers/OTC life and actual terminal cash availability need further adapters/evidence.",
                  "Ticker reuse prevents automatic attachment of current/adjusted quote series to old securities."]}
    output.mkdir(parents=True, exist_ok=False)
    for name, value in (("report.json", report), ("cohort.json", cohort), ("events.json", events), ("cached_files.json", files)):
        (output / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with (output / "cohort.csv").open("x", encoding="utf-8", newline="") as target:
        fields = ("membership_key", "source_name", "instrument_id", "issuer_ticker", "issuer_name",
                  "mapping_method", "security_type", "raw_cached_sessions", "adjusted_candidate_sessions",
                  "reviewed_event_count", "ready_for_simulation")
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        for row in cohort:
            writer.writerow({**{key: row[key] for key in fields if key in row},
                             "raw_cached_sessions": row["cached_observations"]["raw_session_count"],
                             "adjusted_candidate_sessions": row["cached_observations"]["adjusted_session_count"],
                             "reviewed_event_count": row["cached_observations"]["events_reviewed"]})
    if not report["all_checks_passed"]:
        raise ValueError("Cohort audit failed a declared integrity check")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--review", type=Path, default=REVIEW)
    args = parser.parse_args()
    report = run_audit(args.output, review_path=args.review)
    print(json.dumps({key: report[key] for key in ("checks", "mapping_counts", "event_counts", "coverage", "cohort_backtest_ready", "spending")}, indent=2))


if __name__ == "__main__":
    main()

"""Offline cache qualification for a fixed 100-name historical candidate sample.

No strategy scores, purchases, data collection or automatic admission. A
candidate alias and an observed full calendar are not complete identity/action
evidence. Known branch/reuse cases never join merely by ticker spelling.
"""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

import pandas as pd
from alpaca.data.timeframe import TimeFrame

from app.data.market_data import ValidationConfig, validate_candles
from backtesting.cohort_audit import checked_file, digest, run_audit
from backtesting.event_gap_review import review_gaps
from backtesting.free_collection import raw_candles
from backtesting.pilot_qualification import compare_bars
from backtesting.pilot_readiness_review import offline_only, write_csv, write_json

REVIEW = Path("docs/broad_sample_qualification_review.json")


def qualify(output):
    if output.exists() or not output.resolve().is_relative_to(Path.cwd().resolve()):
        raise ValueError("Choose a fresh output directory within the workspace")
    root, inputs = Path.cwd(), {REVIEW.as_posix(): digest(REVIEW)}

    def load(entry):
        path = checked_file(root, entry)
        inputs[path.relative_to(root).as_posix()] = digest(path)
        return path

    protocol = json.loads(REVIEW.read_text(encoding="utf-8"))
    metadata = {key: load(value) for key, value in protocol["inputs"].items()}
    with metadata["source_register"].open(encoding="utf-8", newline="") as handle:
        register = list(csv.DictReader(handle))
    with load(protocol["selected_roster"]).open(encoding="utf-8", newline="") as handle:
        selected = list(csv.DictReader(handle))
    if len(register) != 506 or len(selected) != 100 or len({r["instrument_id"] for r in selected}) != 100:
        raise ValueError("Frozen historical population/sample changed")
    forced = protocol["forced_control_ids"]
    rank = lambda r: (hashlib.sha256((protocol["selection_seed"] + "|" + r["instrument_id"]).encode("utf-8")).hexdigest(), r["instrument_id"])
    pool = [r for r in register if r["instrument_id"] not in forced and r["issuer_ticker"] != "DVMT"]
    expected = forced + [r["instrument_id"] for r in sorted(pool, key=rank)[:98]]
    if [r["instrument_id"] for r in selected] != expected or protocol["performance_scope_approved"] is not False:
        raise ValueError("Sample was rerolled or research approval silently changed")
    # Reuse existing offline readers and preserve all 506 original rows. The
    # legacy reader screens metadata dates before opening candidate prices.
    legacy = run_audit(output / "legacy_cache", review_path=metadata["cohort_review"])
    collection = review_gaps(output / "collection_replay", review_path=metadata["collection_review"])
    cohort = json.loads((output / "legacy_cache/cohort.json").read_text(encoding="utf-8"))
    inventory = json.loads((output / "legacy_cache/cached_files.json").read_text(encoding="utf-8"))
    for row in inventory:
        path = Path(row["path"])
        inputs[path.relative_to(root).as_posix()] = digest(path)
        row["path"] = path.relative_to(root).as_posix()
        row["source_kind"] = "legacy_raw_or_adjusted_observation"
        row["qualifies_as_raw_broad_input"] = False
    old = {r["instrument_id"]: r for r in cohort}
    by_alias = {r["issuer_ticker"]: r for r in register}
    selected_ids = {r["instrument_id"] for r in selected}
    candidates = defaultdict(list)
    plan = json.loads(Path("docs/free_collection_plan.json").read_text(encoding="utf-8"))
    data_report = json.loads(metadata["collection_report"].read_text(encoding="utf-8"))
    collection_root = Path("data/reports/free_collection_v1")
    if data_report["plan_sha256"] != digest("docs/free_collection_plan.json"):
        raise ValueError("Saved data collection differs from its pinned plan")
    inputs["docs/free_collection_plan.json"] = digest("docs/free_collection_plan.json")
    # Only these explicitly identified original-issuer intervals may become
    # observations under the 2016 row. Parent/child reused aliases stay separate.
    direct = {"ordinary_aapl": "AAPL", "ordinary_jpm": "JPM", "whole_foods": "WFM",
              "activision": "ATVI", "aetna": "AET", "level3": "LVLT", "cvs_reference": "CVS",
              "ctl_reference": "CTL", "alcoa_original": "AA", "fox_original_a": "FOXA",
              "bed_bath_listed": "BBBY"}
    for probe in data_report["probes"]:
        if "csv" not in probe["bars"]:
            inventory.append(dict(path="", symbol=probe["symbol"], source_kind="empty_or_unavailable_source",
                                  rows=0, probe_id=probe["probe_id"], adjustment="raw", qualifies_as_raw_broad_input=False))
            continue
        path = load(dict(path=(collection_root / probe["directory"] / probe["bars"]["csv"]).as_posix(), sha256=probe["bars"]["sha256"]))
        frame = pd.read_csv(path)
        pages = [json.loads(load(dict(path=(collection_root / probe["directory"] / p["file"]).as_posix(), sha256=p["sha256"])).read_text(encoding="utf-8"))
                 for p in probe["bars"]["pages"]]
        compare_bars(frame, raw_candles(pages, probe["symbol"]))
        validate_candles(frame, config=ValidationConfig(timeframe=TimeFrame.Day))
        stamps = pd.to_datetime(frame["timestamp"], utc=True)
        if len(frame) != probe["bars"]["rows"] or not ((stamps >= pd.Timestamp("2016-01-01", tz="UTC")) & (stamps < pd.Timestamp("2024-01-01", tz="UTC"))).all():
            raise ValueError("Saved probe row count/development dates changed")
        item = dict(path=path.relative_to(root).as_posix(), sha256=digest(path), symbol=probe["symbol"],
                    source_kind="raw_probe_not_certified_attachment", probe_id=probe["probe_id"],
                    rows=len(frame), adjustment="raw", first_session=stamps.min().date().isoformat(),
                    last_session=stamps.max().date().isoformat(), qualifies_as_raw_broad_input=False)
        inventory.append(item)
        if probe["probe_id"] in direct:
            alias = direct[probe["probe_id"]]
            if alias in by_alias:
                candidates[by_alias[alias]["instrument_id"]].append(item)
    # These aliases were reconstructed from actual candles by the saved
    # independent event review. Do not construct any other concatenated stream.
    free_summary = json.loads(metadata["collection_summary"].read_text(encoding="utf-8"))
    for key, stable in (("ua_class_a", "COHORT-2016-0454"), ("ua_class_c", "COHORT-2016-0455"), ("cbre", "COHORT-2016-0088")):
        info = free_summary["alias_streams"][key]
        original = load(dict(path=(Path(free_summary["evidence_directory"]) / info["file"]).as_posix(), sha256=info["sha256"]))
        frame, reconstructed = pd.read_csv(original), pd.read_csv(output / "collection_replay" / info["file"])
        compare_bars(frame, reconstructed)
        stamps = pd.to_datetime(frame["timestamp"], utc=True)
        item = dict(path=original.relative_to(root).as_posix(), sha256=digest(original), symbol=key,
            source_kind="reviewed_observed_alias_stream", rows=len(frame), adjustment="raw",
            first_session=stamps.min().date().isoformat(), last_session=stamps.max().date().isoformat(),
            qualifies_as_raw_broad_input=False)
        inventory.append(item)
        candidates[stable].append(item)
    audited_control = {"COHORT-2016-0047", "COHORT-2016-0088"}
    stock_rows = []
    for row in register:
        stable, alias = row["instrument_id"], row["issuer_ticker"]
        streams = candidates[stable]
        largest = max(streams, key=lambda r: r["rows"], default=None)
        raw_count = 0 if largest is None else largest["rows"]
        observed_full = bool(largest and raw_count == 2012 and largest["first_session"] == "2016-01-04" and largest["last_session"] == "2023-12-29")
        diagnostic_control = stable in audited_control
        issues = []
        if not streams:
            issues.append("No bound raw stream cached")
        elif not observed_full:
            issues.append("Only partial/full-lifetime-interval observations; historical listing/action boundaries still govern required coverage")
        if stable not in audited_control:
            issues.append("No approved complete identity/action/entitlement/payment input for broader scoring")
        if alias == "JPM":
            issues.append("JPM collection parked; no new follow-up")
        if alias in {"UA", "UA.C"}:
            issues.append("Class issuance/distribution or alias-reuse accounting/evidence remains blocked")
        if alias == "DVMT":
            issues.append("Tracking-share class outside predeclared candidate eligibility; retained in parent register")
        if stable in audited_control:
            issues.append("Admitted only to completed two-stock diagnostic under approved assumptions; broader scope approval still required")
        stock_rows.append(dict(instrument_id=stable, membership_key=row["membership_key"], snapshot_alias=alias,
            source_name=row["source_name"], selected_for_100=stable in selected_ids,
            largest_bound_raw_stream_sessions=raw_count, full_2016_2023_raw_calendar_observed=observed_full,
            raw_observations_do_not_certify_identity=True,
            legacy_adjusted_candidate_sessions=old[stable]["cached_observations"]["adjusted_session_count"],
            raw_candidate_paths=json.dumps([r["path"] for r in streams]),
            approved_in_completed_two_stock_diagnostic=diagnostic_control,
            ready_for_broad_strategy_scoring=False, blockers=json.dumps(issues)))
    active = [r for r in stock_rows if r["selected_for_100"]]
    for name, rows in (("all_506_inventory", stock_rows), ("selected_100_inventory", active), ("cached_files", inventory)):
        write_json(output / f"{name}.json", rows)
        write_csv(output / f"{name}.csv", rows)
    result = dict(schema_version=1, date="2026-10-29", scope="Fixed 100-name cached-data qualification; no strategy returns",
        protocol_sha256=digest(REVIEW), input_sha256=inputs,
        execution_sha256={name:digest(name) for name in ("backtesting/broad_sample_qualification.py", "backtesting/cohort_audit.py", "backtesting/event_gap_review.py", "backtesting/pilot_qualification.py")},
        all_506_retained=True, selected_count=100, selection_seed=protocol["selection_seed"],
        selected_roster=protocol["selected_roster"], jpm_selected=any(r["snapshot_alias"] == "JPM" for r in active),
        cached_file_inventory_rows=len(inventory), legacy_files_rechecked=legacy["coverage"]["cached_daily_files_checked"],
        raw_collection_rows_rechecked=collection["collected_candle_rows"], boundary_candles_rechecked=collection["additional_observed_boundary_candles"],
        selected_with_bound_raw_observations=sum(r["largest_bound_raw_stream_sessions"]>0 for r in active),
        selected_full_raw_calendar_observed=sum(r["full_2016_2023_raw_calendar_observed"] for r in active),
        selected_without_full_raw_calendar=sum(not r["full_2016_2023_raw_calendar_observed"] for r in active),
        selected_with_adjusted_candidates=sum(r["legacy_adjusted_candidate_sessions"]>0 for r in active),
        selected_approved_only_in_old_diagnostic=sum(r["approved_in_completed_two_stock_diagnostic"] for r in active),
        selected_ready_for_broad_scoring=0, new_stocks_admitted=0,
        all_cohort_with_bound_raw_observations=sum(r["largest_bound_raw_stream_sessions"]>0 for r in stock_rows),
        all_cohort_full_raw_calendar_observed=sum(r["full_2016_2023_raw_calendar_observed"] for r in stock_rows),
        selected_full_raw_aliases=[r["snapshot_alias"] for r in active if r["full_2016_2023_raw_calendar_observed"]],
        selected_partial_raw_aliases=[r["snapshot_alias"] for r in active if r["largest_bound_raw_stream_sessions"]>0 and not r["full_2016_2023_raw_calendar_observed"]],
        no_adjusted_prices_substituted=True, no_aliases_silently_stitched=True, no_missing_data_filled=True,
        jpm_collection_parked=True, original_control_and_acceptance_unchanged=True,
        network_requests=0,new_price_requests=0,broker_account_requests=0,orders=0,purchases_usd=0,
        strategy_simulations=0,unit_tests_run=0,holdout_candles_read=False,raspberry_pi_verified=False,
        comparison_ready=False, performance_scope_approved=False,
        outputs={p.name:digest(p) for p in output.iterdir() if p.is_file()},
        limitation="Largest bound raw stream and candidate adjusted timestamps describe observations, not independent full identity/action certification. Lifetimes must explain absent sessions; counts are not missing-candle charges.")
    write_json(output / "report.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with offline_only():
        r = qualify(args.output)
    print(json.dumps({k:r[k] for k in ("selected_count", "selected_with_bound_raw_observations", "selected_full_raw_calendar_observed", "selected_without_full_raw_calendar", "selected_with_adjusted_candidates", "selected_full_raw_aliases", "selected_partial_raw_aliases", "comparison_ready")}))


if __name__ == "__main__":
    main()

"""Review three cached pilot histories without collecting data or scoring trades.

Outputs are evidence inventories, not executable universes. Source facts,
vendor cross-references and unapproved timing assumptions remain distinct.
"""

import argparse
from collections import Counter
from contextlib import contextmanager
import csv
from dataclasses import asdict
from decimal import Decimal
import json
from pathlib import Path
import socket

import pandas as pd
from alpaca.data.timeframe import TimeFrame

from app.data.market_calendar import TradingSession
from app.data.market_data import ValidationConfig, validate_candles
from backtesting.cohort_audit import SavedCalendar, checked_file, digest, source_text
from backtesting.pilot_qualification import after, compare_bars, raw_bars
from backtesting.public_source_review import review_sources

REVIEW = Path("docs/remaining_pilot_review.json")


@contextmanager
def offline_only():
    """Reject socket connection calls during the cached review."""
    connect, connect_ex, create = socket.socket.connect, socket.socket.connect_ex, socket.create_connection

    def deny(*args, **kwargs):
        raise RuntimeError("This cached evidence review cannot access the network")

    socket.socket.connect = socket.socket.connect_ex = socket.create_connection = deny
    try:
        yield
    finally:
        socket.socket.connect, socket.socket.connect_ex, socket.create_connection = connect, connect_ex, create


def write_json(path, value):
    path.write_bytes((json.dumps(value, indent=2, allow_nan=False) + "\n").encode("utf-8"))


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=sorted({key for row in rows for key in row}), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def review(output, *, protocol_path=REVIEW):
    root, inputs = Path.cwd(), {}
    output = output.resolve()
    if not output.is_relative_to(root.resolve()) or output.exists():
        raise ValueError("Choose a fresh output directory inside this workspace")

    def load(entry):
        path = checked_file(root, entry)
        inputs[path.relative_to(root).as_posix()] = digest(path)
        return path

    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    inputs[protocol_path.as_posix()] = digest(protocol_path)
    if (protocol["schema_version"] != 1 or protocol["active_symbols"] != ["AAPL", "CBRE", "SPY"]
            or protocol["assumptions_owner_approved"] is not False
            or protocol["ready_for_strategy_scoring"] is not False
            or (protocol["start_inclusive"], protocol["end_exclusive"]) != ("2016-01-01", "2024-01-01")):
        raise ValueError("Only the frozen unapproved three-stream review is supported")
    loaded = {key: json.loads(load(entry).read_text(encoding="utf-8"))
              for key, entry in protocol["inputs"].items() if entry["path"].endswith(".json")}
    for entry in protocol["inputs"].values():
        load(entry)
    proposal, qreview = loaded["proposal"], loaded["qualification_review"]
    if (loaded["jpm_outcome"]["status"] != "executed_partial_jpm_parked"
            or loaded["acceptance"]["minimum_instruments"] != 5
            or loaded["acceptance"]["minimum_completed_trades"] != 30):
        raise ValueError("JPM parking or unchanged research acceptance does not match")
    for item in loaded["qualification_summary"]["input_sha256"].items():
        # Revalidate the old frozen input pins; JPM price files need not be read.
        name, sha = item
        if name not in {"data/reports/free_collection_v1/002/bars.csv", "data/reports/free_collection_v1/002/bars_1.json"}:
            load(dict(path=name, sha256=sha))
    public = loaded["primary_review"]
    sources = {key: load(entry) for key, entry in qreview["sources"].items()}
    texts = {key: source_text(path) for key, path in sources.items()}
    facts = []
    for check in qreview["source_checks"]:
        if not all(term in texts[check["source"]] for term in check["terms"]):
            raise ValueError(f"Saved source no longer supports {check['name']}")
        facts.append(dict(fact=check["name"], source_path=sources[check["source"]].relative_to(root).as_posix(),
                          supported=True, scope=check["supports"], full_period_certified=False))
    for key in ("cbre_2016_10k", "cbre_2023_10k"):
        path = load(public["sources"][key])
        text = source_text(path)
        if not all(term in text for term in ("Class A", "New York Stock Exchange", "not declared or paid any cash dividends")):
            raise ValueError("CBRE class/listing/no-cash-dividend evidence changed")
        facts.append(dict(fact=key, source_path=path.relative_to(root).as_posix(), supported=True,
                          scope="Issuer common Class A/listing and no common cash dividends since inception; retrospective, not an all-action certificate",
                          full_period_certified=False))
    event_review = json.loads(load(qreview["event_review"]).read_text(encoding="utf-8"))
    collection_path = Path(event_review["collection_root"]) / "report.json"
    collection = json.loads(load(dict(path=collection_path.as_posix(), sha256=event_review["collection_report_sha256"])).read_text(encoding="utf-8"))
    probes = {row["probe_id"]: row for row in collection["probes"]}

    def original(probe_id, resource):
        probe = probes[probe_id]
        folder = Path(event_review["collection_root"], probe[resource].get("source_directory", probe["directory"]))
        return [json.loads(load(dict(path=(folder / item["file"]).as_posix(), sha256=item["sha256"])).read_text(encoding="utf-8"))
                for item in probe[resource]["pages"]]

    calendar_rows = json.loads(load(proposal["calendar"]).read_text(encoding="utf-8"))
    sessions = [TradingSession(pd.Timestamp(r["opens_at"]), pd.Timestamp(r["closes_at"])) for r in calendar_rows]
    if len(sessions) != 2012 or any(not pd.Timestamp("2016-01-01", tz="UTC") <= s.opens_at < pd.Timestamp("2024-01-01", tz="UTC") for s in sessions):
        raise ValueError("Unexpected development calendar")
    calendar = SavedCalendar(sessions)
    streams, years, provider_events = [], [], {}
    selected = [s for s in proposal["streams"] if s.get("symbol", "CBRE") in protocol["active_symbols"]]
    if len(selected) != 3:
        raise ValueError("Unexpected remaining pilot streams")
    for stream in selected:
        symbol = stream.get("symbol", "CBRE")
        frame = pd.read_csv(load(stream["csv"]))
        if symbol == "CBRE":
            load(stream["derivation_report"])
            boundary = raw_bars([json.loads(load(event_review["boundary_response"]).read_text(encoding="utf-8"))], "CBG")
            if len(boundary) != 1 or not boundary.iloc[0]["timestamp"].startswith("2018-03-19"):
                raise ValueError("Expected the genuine recovered CBRE boundary candle")
            old, new = raw_bars(original("cbre_old", "bars"), "CBG"), raw_bars(original("cbre_new", "bars"), "CBRE")
            old["source_symbol"], new["source_symbol"] = "CBG", "CBRE"
            boundary["source_symbol"], boundary["symbol"] = "CBG", "CBRE"
            reconstructed = pd.concat([old, boundary, new], ignore_index=True)
            stamps = pd.to_datetime(frame["timestamp"], utc=True)
            prior = stamps < pd.Timestamp("2018-03-19", tz="UTC")
            if not (frame.loc[prior, "symbol"].eq("CBG").all() and frame.loc[~prior, "symbol"].eq("CBRE").all()
                    and frame["instrument_id"].eq(stream["instrument_id"]).all()):
                raise ValueError("Dated CBRE aliases/identity changed")
            pages = original("cbre_old", "actions") + original("cbre_new", "actions")
        else:
            reconstructed = raw_bars([json.loads(load(e).read_text(encoding="utf-8")) for e in stream["raw_bar_pages"]], symbol)
            pages = [json.loads(load(e).read_text(encoding="utf-8")) for e in stream["raw_action_pages"]]
        compare_bars(frame, reconstructed)
        logical = frame.copy()
        logical["symbol"] = stream["instrument_id"]
        validation = validate_candles(logical, calendar=calendar,
            config=ValidationConfig(timeframe=TimeFrame.Day, require_all_scheduled_bars=True),
            requested_start=pd.Timestamp("2016-01-01", tz="UTC"), requested_end=pd.Timestamp("2023-12-31T23:59:59Z"))
        stamps = pd.to_datetime(frame["timestamp"], utc=True)
        if len(frame) != 2012 or not stamps.is_monotonic_increasing:
            raise ValueError("Unexpected row count/order")
        records = []
        for page in pages:
            if page.get("next_page_token") is not None:
                raise ValueError("Incomplete saved action response")
            records.extend((category, r) for category, items in page["corporate_actions"].items() for r in items)
        if len({r["id"] for _, r in records}) != len(records):
            raise ValueError("Duplicate provider actions require explicit review")
        provider_events[symbol] = records
        streams.append(dict(symbol=symbol, rows=len(frame), first_session=stamps.iloc[0].date().isoformat(),
            last_session=stamps.iloc[-1].date().isoformat(), calendar_ohlcv_pass=True,
            raw_reconstruction_matches=True, warnings=[asdict(w) for w in validation.warnings],
            source_alias_rows=dict(Counter(frame.get("source_symbol", frame["symbol"]))),
            provider_action_counts=dict(Counter(k for k, _ in records)),
            full_period_identity_action_certified=False, ready_for_strict_scoring=False))
        for year in range(2016, 2024):
            subset = stamps[stamps.dt.year == year]
            years.append(dict(symbol=symbol, year=year, candles=len(subset), first_session=subset.iloc[0].date().isoformat(),
                              last_session=subset.iloc[-1].date().isoformat(), calendar_ohlcv_pass=True,
                              ready_for_strict_scoring=False))

    # Replay the original catalog, including its two archived JPM declarations;
    # this does not reopen acquisition or read JPM price histories.
    source_result = review_sources(output / "primary_replay")
    replay_csv = output / "primary_replay/dividend_reconciliation.csv"
    if digest(replay_csv) != loaded["primary_summary"]["tracked_dividend_matrix"]["sha256"]:
        raise ValueError("Replayed primary-source comparison changed")
    comparisons = json.loads((output / "primary_replay/dividend_reconciliation.json").read_text(encoding="utf-8"))
    events = []
    for row in comparisons:
        if row["symbol"] not in {"AAPL", "SPY"}:
            continue
        symbol = row["symbol"]
        entry = public["sources"][row["source"]]
        load(entry)
        ex = row.get("ex_date") or row["provider_ex_date"]
        if not "2016-01-01" <= ex < "2024-01-01":
            raise ValueError("Event exceeds development scope")
        known = after(sessions, row["declared"], 2) if row.get("declared") else None
        base, later = after(sessions, row["payable"], 1), after(sessions, row["payable"], 6)
        events.append(dict(symbol=symbol, event_id=row.get("provider_event_id") or f"PRIMARY-SPY-{ex}",
            kind="cash_dividend", ex_or_effective_date=ex,
            ex_date_basis="primary_fund_schedule" if row["ex_date_independently_supplied"] else "provider_only_cross_reference",
            nominal_amount=row["amount"], provider_amount=row.get("provider_amount"),
            declared=row.get("declared"), record=row["record"], payable=row["payable"],
            source_only_event=row["source_only_event"], source_url=entry["url"], source_sha256=entry["sha256"],
            amount_precision_warning=row["amount_exact_match"] is False,
            short_term_gain=row.get("short_term_gain"), long_term_gain=row.get("long_term_gain"),
            source_terms_supported=True, proposed_known_at=known, proposed_cash_available_at=base,
            proposed_delayed_cash_at=later, no_credit_scenario="Retain earned right outstanding; never fabricate credit",
            known_before_ex_open=None,
            cash_outside_saved_calendar=base is None, historical_publication_time_verified=False,
            entitlement_verified=False, broker_credit_verified=False, assumptions_approved=False,
            ready_for_strict_scoring=False))
    opens_by_day = {s.opens_at.tz_convert("America/New_York").date().isoformat(): s.opens_at for s in sessions}
    for event in events:
        known = event["proposed_known_at"]
        event["known_before_ex_open"] = pd.Timestamp(known) <= opens_by_day[event["ex_or_effective_date"]] if known else None
        if event["known_before_ex_open"] is False:
            raise ValueError("Proposed knowledge bound falls after the required boundary")
    splits = [r for kind, r in provider_events["AAPL"] if kind == "forward_splits"]
    if (len(splits) != 1 or (splits[0].get("ex_date") or splits[0].get("effective_date")) != "2020-08-31"
            or (Decimal(str(splits[0]["new_rate"])), Decimal(str(splits[0]["old_rate"]))) != (4, 1)
            or not all(term in texts["aapl_july"] for term in ("four-for-one", "August 31, 2020"))):
        raise ValueError("Apple split evidence differs")
    for symbol, kind, event_id, effective, announced, source in [
        ("AAPL", "split_4_for_1", splits[0]["id"], "2020-08-31", "2020-07-30", "aapl_july"),
        ("CBRE", "alias_change_no_automatic_quantity_change", "PRIMARY-CBRE-RENAME-2018-03-19", "2018-03-19", "2018-03-08", "cbre_2018_announcement")]:
        events.append(dict(symbol=symbol, event_id=event_id, kind=kind, ex_or_effective_date=effective,
            ex_date_basis="primary_issuer_effective_boundary", declared=announced,
            source_url=qreview["sources"][source]["url"], source_sha256=qreview["sources"][source]["sha256"],
            source_terms_supported=True, proposed_known_at=after(sessions, announced, 2),
            assumptions_approved=False, ready_for_strict_scoring=False))
    counts = dict(Counter(e["symbol"] for e in events))
    if counts != protocol["event_counts"] or len(events) != 66:
        raise ValueError("Unexpected reviewed event inventory")
    output.mkdir(parents=True, exist_ok=True)
    for name, rows in (("events", events), ("identity_facts", facts), ("year_coverage", years)):
        write_json(output / f"{name}.json", rows)
        write_csv(output / f"{name}.csv", rows)
    gaps = {
        "AAPL": ["32 provider-only dividend ex-dates; no independent ex-date column in issuer table",
                 "Full-period identity/action completeness not independently certified",
                 "Knowledge/payment conventions and any labeled vendor-reliance diagnostic remain unapproved"],
        "CBRE": ["Class A/NYSE aliases and no-cash-dividend policy supported; other action categories not certified complete",
                 "Imported REIT label retained; historical tax subtype unresolved, not required merely to read common-share prices",
                 "A scope that filters by REIT status cannot silently treat this unknown label as false"],
        "SPY_context": ["Raw completed prices and 2016/2020 fund identity anchors supported; full-period identity/action certificate absent",
                        "Distribution knowledge times, capital-gain blanks and amount precision do not enter a raw price-only regime calculation",
                        "Price-only market context still requires explicit scope/vendor-reliance review before a new performance study"],
        "SPY_total_return": ["No declaration/publication times in the retrospective distribution table",
                            "Blank capital-gain cells are not zero; one shared amount precision warning",
                            "2023-12-15 distribution is payable 2024-01-31, outside the saved cash calendar"],
        "investment_acceptance": ["Only two candidate stocks; SPY is context, not a third traded stock",
                                  "Five instruments and 30 completed trades remain required; larger historical universe remains blocked"],
        "implementation": ["Strict ownership evidence flags cannot be set from modeling assumptions",
                           "An explicitly labeled assumption-based diagnostic mode needs implementation/verification before new raw-data returns"]}
    write_json(output / "gaps.json", gaps)
    for name, sha in source_result["input_sha256"].items():
        if name in inputs and inputs[name] != sha:
            raise ValueError("Source replay input mismatch")
        inputs[name] = sha
    result = dict(schema_version=1, purpose=protocol["purpose"], input_sha256=inputs,
        code_sha256={p: digest(p) for p in ("backtesting/pilot_readiness_review.py", "backtesting/pilot_qualification.py",
                     "backtesting/public_source_review.py", "app/data/market_data.py", "backtesting/cohort_audit.py")},
        streams=streams, total_active_candles=sum(s["rows"] for s in streams), event_counts=counts,
        identity_facts_checked=len(facts), years_reviewed=len(years),
        primary_replay_matches_frozen_csv=True, total_source_replay_rows=source_result["primary_dividend_rows"],
        aapl_dividends=32, aapl_split_events=1, cbre_alias_events=1, spy_dividends=32,
        aapl_independent_dividend_ex_dates=0,
        spy_source_only_events=sum(e.get("source_only_event", False) for e in events),
        spy_precision_warnings=sum(e.get("amount_precision_warning", False) for e in events),
        spy_short_term_gain_blanks=sum(e["symbol"] == "SPY" and e.get("short_term_gain") == "" for e in events),
        spy_long_term_gain_blanks=sum(e["symbol"] == "SPY" and e.get("long_term_gain") == "" for e in events),
        cash_dates_outside_saved_calendar=[e["event_id"] for e in events if e.get("cash_outside_saved_calendar")],
        gaps=gaps, existing_506_register_preserved=True, registered_control_unchanged=True, jpm_collection_parked=True,
        assumptions_owner_approved=False, new_performance_scope_approved=False, ready_for_strategy_scoring=False,
        paper_activation_approved=False, network_requests=0, purchases_usd=0, broker_requests=0, account_requests=0,
        orders=0, strategy_simulations=0, unit_tests_run=0, dependency_installations=0, holdout_candles_read=False,
        verification_scope="Saved-input hash checks, actual candle/calendar validation, raw response reconstruction and source/date/amount reconciliation; not unit tests or performance acceptance",
        output_sha256={p.name: digest(p) for p in output.iterdir() if p.is_file()})
    write_json(output / "report.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with offline_only():
        report = review(args.output)
    print(json.dumps({key: report[key] for key in ("total_active_candles", "event_counts", "identity_facts_checked",
        "spy_precision_warnings", "spy_short_term_gain_blanks", "spy_long_term_gain_blanks", "ready_for_strategy_scoring")}))


if __name__ == "__main__":
    main()

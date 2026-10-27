"""Qualify saved pilot facts without downloading data or simulating trades.

Event rows distinguish provider fields, corroborated issuer terms, proposed
research timestamps and unverified entitlement/credit. No output is an
executable universe or an approval of the underlying source declarations.
"""

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import date
from fractions import Fraction
import json
from pathlib import Path

import pandas as pd
from alpaca.data.timeframe import TimeFrame

from app.data.market_calendar import TradingSession
from app.data.market_data import CANONICAL_CANDLE_COLUMNS, CandleValidationError, ValidationConfig, validate_candles
from backtesting.cohort_audit import SavedCalendar, checked_file, digest, source_text

REVIEW = Path("docs/free_data_pilot_review.json")
NUMERIC = ["open", "high", "low", "close", "volume"]


def raw_bars(pages, symbol):
    """Read actual saved payloads, without mapping aliases or filling rows."""
    fields = dict(t="timestamp", o="open", h="high", l="low", c="close", v="volume")
    rows = []
    for page in pages:
        if set(page.get("bars", {})) - {symbol}:
            raise ValueError("Unexpected source ticker in pinned pilot payload")
        rows.extend({**{target: bar[key] for key, target in fields.items()}, "symbol": symbol}
                    for bar in page["bars"][symbol])
    if pages[-1].get("next_page_token") is not None:
        raise ValueError("Incomplete pilot price pagination")
    return pd.DataFrame(rows, columns=CANONICAL_CANDLE_COLUMNS)


def compare_bars(saved, reconstructed):
    left, right = saved.copy(), reconstructed.copy()
    for frame in (left, right):
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        frame.sort_values("timestamp", inplace=True, ignore_index=True)
    if len(left) != len(right) or not left[["timestamp", "symbol"]].equals(right[["timestamp", "symbol"]]):
        raise ValueError("Saved stream differs from its raw payload identity/timestamps")
    for name in NUMERIC:
        a, b = left[name].astype(float), right[name].astype(float)
        if not ((a - b).abs() <= 1e-8 + 1e-12 * b.abs()).all():
            raise ValueError("Saved OHLCV differs from its raw payload")
    if "source_symbol" in right and not left["source_symbol"].equals(right["source_symbol"]):
        raise ValueError("Derived alias stream lost its source-label provenance")


def after(sessions, day, offset):
    matches = [s for s in sessions if s.opens_at.tz_convert("America/New_York").date() > date.fromisoformat(day)]
    return matches[offset - 1].opens_at.isoformat() if len(matches) >= offset else None


def collection_targets(events):
    """Finite discovery targets; these are not invented download URLs."""
    targets = []
    domains = dict(AAPL=["apple.com", "investor.apple.com", "sec.gov"],
                   JPM=["jpmorganchase.com", "sec.gov"],
                   CBRE=["cbre.com", "ir.cbre.com", "sec.gov"],
                   SPY=["ssga.com", "sec.gov"])
    for symbol in domains:
        selected = [e for e in events if e["symbol"] == symbol]
        targets.extend([
            dict(target_id=f"{symbol}-identity", symbol=symbol, domains=domains[symbol],
                 target="Dated listing/class/alias evidence covering 2016-2023; reconcile earlier and later anchors",
                 missing_event_ids=[], exact_download_url=None),
            dict(target_id=f"{symbol}-complete-actions", symbol=symbol, domains=domains[symbol],
                 target="Issuer/fund full-period split/distribution/rename history; include explicit no-dividend evidence where applicable",
                 missing_event_ids=[], exact_download_url=None),
            dict(target_id=f"{symbol}-dated-terms", symbol=symbol, domains=domains[symbol],
                 target="Dated primary terms for uncorroborated events: ex/effective date, amount/basis, payable date and announcement; reconcile records without guessing",
                 missing_event_ids=[e["event_id"] for e in selected if not e["primary_economic_terms_corroborated"]
                                    or not e["primary_ex_or_effective_date_corroborated"]], exact_download_url=None),
        ])
    return dict(status="proposed_not_executed", targets=targets, target_count=len(targets),
                max_public_discovery_tool_calls=12, max_public_document_get_attempts=40,
                automatic_retries=False, redirects_require_review=True, leaf_urls_require_primary_domain_review=True,
                exact_source_urls_not_yet_established=True, unbounded_link_following=False,
                new_price_requests=0, broker_or_account_requests=0, credentials_required=False,
                purchases_budget_usd=0, paid_fallback=False, performance_runs=0,
                stop="Stop at the first access/payment requirement or request cap; remaining targets stay blocked. A provider count or payment pattern cannot supply absent terms.")


def qualify(output, *, review_path=REVIEW):
    if output.exists():
        raise FileExistsError("Choose a fresh pilot qualification directory")
    root, inputs = Path.cwd(), {}

    def load(entry):
        path = checked_file(root, entry)
        inputs[path.relative_to(root).as_posix()] = digest(path)
        return path

    review = json.loads(review_path.read_text(encoding="utf-8"))
    inputs[review_path.as_posix()] = digest(review_path)
    if (type(review["schema_version"]) is not int or review["schema_version"] != 1
            or review["ready_for_strategy_scoring"] is not False
            or review["research_assumptions_owner_approved"] is not False):
        raise ValueError("Only the unapproved offline qualification protocol is supported")
    proposal, apple, event_review = [json.loads(load(review[key]).read_text(encoding="utf-8"))
                                    for key in ("proposal", "apple_review", "event_review")]
    for entry in proposal["evidence_inputs"]:
        load(entry)
    scope = proposal["scope"]
    if (scope["start_inclusive"], scope["end_exclusive"], scope["sessions_per_stream"], len(proposal["streams"])) != (
            "2016-01-01", "2024-01-01", 2012, 4):
        raise ValueError("Frozen four-stream development scope changed")
    sources = {key: source_text(load(entry)) for key, entry in review["sources"].items()}
    facts = []
    for check in review["source_checks"]:
        if not all(term in sources[check["source"]] for term in check["terms"]):
            raise ValueError(f"Pinned primary source does not corroborate {check['name']}")
        facts.append({**check, "literal_terms_match": True, "full_period_identity_certified": False})
    sessions = [TradingSession(pd.Timestamp(r["opens_at"]), pd.Timestamp(r["closes_at"]))
                for r in json.loads(load(proposal["calendar"]).read_text())]
    opens = [s.opens_at for s in sessions]
    if (any(t.tzinfo is None or not pd.Timestamp("2016-01-01", tz="UTC") <= t < pd.Timestamp("2024-01-01", tz="UTC") for t in opens)
            or opens != sorted(set(opens)) or len(sessions) != 2012):
        raise ValueError("Pilot calendar must contain unique ordered development exchange sessions")
    calendar = SavedCalendar(sessions)
    collection = json.loads(Path(event_review["collection_root"], "report.json").read_text())
    if digest(Path(event_review["collection_root"], "report.json")) != event_review["collection_report_sha256"]:
        raise ValueError("Original collection report changed")
    probes = {p["probe_id"]: p for p in collection["probes"]}

    def original(probe_id, resource):
        probe = probes[probe_id]
        folder = Path(event_review["collection_root"], probe[resource].get("source_directory", probe["directory"]))
        return [json.loads(load(dict(path=(folder / item["file"]).as_posix(), sha256=item["sha256"])).read_text())
                for item in probe[resource]["pages"]]

    streams, events = [], []
    for stream in proposal["streams"]:
        symbol = stream.get("symbol", "CBRE")
        frame = pd.read_csv(load(stream["csv"]))
        if symbol == "CBRE":
            load(stream["derivation_report"])
            boundary = raw_bars([json.loads(load(event_review["boundary_response"]).read_text())], "CBG")
            if len(boundary) != 1 or not boundary.iloc[0]["timestamp"].startswith("2018-03-19"):
                raise ValueError("CBRE translation requires its actual pinned boundary candle")
            boundary["source_symbol"], boundary["symbol"] = "CBG", "CBRE"
            old, new = raw_bars(original("cbre_old", "bars"), "CBG"), raw_bars(original("cbre_new", "bars"), "CBRE")
            old["source_symbol"], new["source_symbol"] = "CBG", "CBRE"
            reconstructed = pd.concat([old, boundary, new], ignore_index=True)
            stamp = pd.to_datetime(frame["timestamp"], utc=True)
            expected_alias = stamp < pd.Timestamp("2018-03-19", tz="UTC")
            if not (frame.loc[expected_alias, "symbol"].eq("CBG").all() and frame.loc[~expected_alias, "symbol"].eq("CBRE").all()
                    and frame["instrument_id"].eq(stream["instrument_id"]).all()):
                raise ValueError("CBRE dated alias or stable identity differs from its reviewed stream")
            action_pages = original("cbre_old", "actions") + original("cbre_new", "actions")
        else:
            pages = [json.loads(load(entry).read_text()) for entry in stream["raw_bar_pages"]]
            reconstructed = raw_bars(pages, symbol)
            action_pages = [json.loads(load(entry).read_text()) for entry in stream["raw_action_pages"]]
        compare_bars(frame, reconstructed)
        logical = frame.copy()
        logical["symbol"] = stream["instrument_id"]  # Validation copy only; check raw aliases above.
        errors, warnings = [], []
        try:
            valid = validate_candles(logical, calendar=calendar,
                config=ValidationConfig(timeframe=TimeFrame.Day, require_all_scheduled_bars=True),
                requested_start=pd.Timestamp("2016-01-01", tz="UTC"), requested_end=pd.Timestamp("2023-12-31T23:59:59Z"))
            warnings = [asdict(w) for w in valid.warnings]
        except CandleValidationError as exc:
            errors = [asdict(issue) for issue in exc.issues]
        timestamps = pd.to_datetime(frame["timestamp"], utc=True)
        if len(frame) != stream["observed_rows"] or not timestamps.is_monotonic_increasing:
            raise ValueError("Pilot stream row count/order differs from its declared observations")
        records = {}
        for page in action_pages:
            if page.get("next_page_token") is not None:
                raise ValueError("Incomplete saved action pagination")
            for category, items in page["corporate_actions"].items():
                for row in items:
                    if row["id"] in records and records[row["id"]] != (category, row):
                        raise ValueError("Conflicting action records with the same ID")
                    records[row["id"]] = (category, row)
        for identifier, (category, row) in records.items():
            if row.get("symbol") != symbol:
                raise ValueError("An action record belongs to a different pilot identity")
            ex = row.get("ex_date") or row.get("effective_date")
            if not ex or not "2016-01-01" <= ex < "2024-01-01":
                raise ValueError("Out-of-scope action requires quarantine, not automatic attachment")
            item = dict(symbol=symbol, instrument_id=stream["instrument_id"], event_id=identifier,
                category=category, provider_record=row, provider_ex_or_effective_date=ex,
                provider_amount_per_share=str(row["rate"]) if "rate" in row else None,
                provider_payable_date=row.get("payable_date"), provider_record_date=row.get("record_date"),
                provider_cusip=row.get("cusip") or None, issuer_amount_per_share=None,
                issuer_payable_date=None, issuer_announcement_date=None, primary_source_ids=[],
                primary_economic_terms_corroborated=False, primary_ex_or_effective_date_corroborated=False,
                entitlement_verified=False, broker_cash_availability_verified=False,
                proposed_known_at=None, proposed_cash_available_at=None, proposed_later_cash_at=None,
                proposed_assumptions_approved=False, ready_for_strategy_scoring=False)
            reviewed = next((d for d in apple["dividends"] if d["event_id"] == identifier), None)
            if symbol == "AAPL" and reviewed is not None:
                release = sources["aapl_" + reviewed["source"]]
                payable, published = date.fromisoformat(reviewed["issuer_payable_date"]), date.fromisoformat(reviewed["announcement"])
                terms = [f"${reviewed['cash_per_share']} per share", f"{payable.strftime('%B')} {payable.day}, {payable.year}",
                         f"{published.strftime('%B')} {published.day}, {published.year}"]
                if (not all(term in release for term in terms) or ex != reviewed["ex_session"]
                        or Fraction(str(row["rate"])) != Fraction(str(reviewed["cash_per_share"]))
                        or row.get("payable_date", reviewed["issuer_payable_date"]) != reviewed["issuer_payable_date"]):
                    raise ValueError("Apple dividend source/provider terms disagree")
                item.update(primary_economic_terms_corroborated=True, issuer_amount_per_share=str(reviewed["cash_per_share"]),
                    issuer_payable_date=reviewed["issuer_payable_date"], issuer_announcement_date=reviewed["announcement"],
                    primary_source_ids=["aapl_" + reviewed["source"]],
                    proposed_known_at=after(sessions, reviewed["announcement"], 2),
                    proposed_cash_available_at=after(sessions, reviewed["issuer_payable_date"], 1),
                    proposed_later_cash_at=after(sessions, reviewed["issuer_payable_date"], 6))
            elif symbol == "AAPL" and identifier == apple["split"]["event_id"]:
                if (category != "forward_splits" or row["new_rate"] != 4 or row["old_rate"] != 1
                        or ex != "2020-08-31" or not all(t in sources["aapl_july"] for t in ["four-for-one", "August 31, 2020"])):
                    raise ValueError("Apple split source/provider terms disagree")
                item.update(primary_economic_terms_corroborated=True, primary_ex_or_effective_date_corroborated=True,
                    issuer_announcement_date="2020-07-30", primary_source_ids=["aapl_july"],
                    proposed_known_at=after(sessions, "2020-07-30", 2))
            item["missing_evidence"] = (["Independent full-period action completeness"]
                + ([] if item["primary_economic_terms_corroborated"] else ["Primary contractual terms and dated announcement"])
                + ([] if item["primary_ex_or_effective_date_corroborated"] else ["Independent ex-date/share-basis/entitlement review"])
                + (["Primary issuer payable terms"] if category == "cash_dividends" and item["issuer_payable_date"] is None else [])
                + (["Modeled cash assumptions unapproved; actual broker credit unverified"] if category == "cash_dividends" else []))
            events.append(item)
        selected = [e for e in events if e["symbol"] == symbol]
        quarters = Counter(f"{e['provider_ex_or_effective_date'][:4]}-Q{(int(e['provider_ex_or_effective_date'][5:7])-1)//3+1}"
                           for e in selected if e["category"] == "cash_dividends")
        streams.append(dict(symbol=symbol, instrument_id=stream["instrument_id"], role=stream["role"],
            rows=len(frame), first_bar=timestamps.iloc[0].isoformat(), last_bar=timestamps.iloc[-1].isoformat(),
            raw_payload_reconstruction_matches=True, errors=errors, warnings=warnings,
            observed_calendar_and_ohlcv_pass=not errors, zero_volume_rows=int(frame["volume"].eq(0).sum()),
            provider_event_counts=dict(Counter(category for category, _ in records.values())),
            provider_missing_payable_date=sum(e["category"] == "cash_dividends" and not e["provider_payable_date"] for e in selected),
            source_supported_provider_events=sum(e["primary_economic_terms_corroborated"] for e in selected),
            independent_source_supported_alias_events=1 if symbol == "CBRE" else 0,
            quarters_without_provider_dividend_record=[f"{year}-Q{q}" for year in range(2016, 2024) for q in range(1, 5) if not quarters[f"{year}-Q{q}"]] if symbol == "SPY" else [],
            missing_quarter_implies_event=False, full_period_identity_certified=False,
            full_period_action_completeness_certified=False, ready_for_context_signals=False,
            ready_for_total_return_benchmark=False, ready_for_strategy_scoring=False))
    events.append(dict(symbol="CBRE", instrument_id="COHORT-2016-0088", event_id="PRIMARY-CBRE-RENAME-2018-03-19",
        category="independent_alias_change", provider_record=None, provider_ex_or_effective_date="2018-03-19",
        primary_source_ids=["cbre_2018_announcement", "cbre_index"], primary_economic_terms_corroborated=True,
        primary_ex_or_effective_date_corroborated=True, issuer_announcement_date="2018-03-08", announcement_basis="SEC filing date",
        proposed_known_at=after(sessions, "2018-03-08", 2), proposed_assumptions_approved=False,
        entitlement_verified=False, broker_cash_availability_verified=False, ready_for_strategy_scoring=False,
        missing_evidence=["Full-period share classification and independent action completeness; absence from API is not absence of an event"]))
    result = dict(scope=review["purpose"], input_sha256=inputs,
        code_sha256={p: digest(p) for p in ["backtesting/pilot_qualification.py", "app/data/market_data.py", "backtesting/cohort_audit.py"]},
        primary_files_revalidated=len(sources), source_checks=facts, streams=streams,
        total_rows=sum(s["rows"] for s in streams), provider_events=len(events)-1, independent_rename_events=1,
        action_matrix_rows=len(events), primary_economic_terms_corroborated=sum(e["primary_economic_terms_corroborated"] for e in events),
        provider_dividends_missing_payable=sum(s["provider_missing_payable_date"] for s in streams),
        full_period_streams_qualified_for_scoring=0, assumptions_owner_approved=False,
        identity_limits=dict(AAPL="2016 basket and 2018 issuer listing anchors, not continuous 2016-2023 certification",
            JPM="Dated 2016 fund holding/crosswalk; no cached JPM issuer listing/action source",
            CBRE="Rename and 2016/2020 Class A source labels; 2016 REIT classification unresolved, no silent correction",
            SPY="2016/2020 fund identity anchors; no complete distribution/ex-date/split review"),
        reconstruction_tolerance=dict(relative=1e-12, absolute=1e-8), volume_warning_scope="Retrospective 10x full-stream positive median; not a causal entry filter",
        no_new_company_events_automatically_approved=True, ready_for_strategy_scoring=False,
        network_requests=0, broker_requests=0, account_requests=0, orders=0, purchases_usd=0,
        strategy_simulations=0, ml_training_runs=0, unit_tests_run=0, holdout_prices_read=False,
        next_work="Review bounded free primary-source discovery targets; no implicit acceptance of modeled timing or narrowed strategy scope")
    output.mkdir(parents=True, exist_ok=False)
    for name, value in [("action_matrix.json", events), ("collection_targets.json", collection_targets(events))]:
        (output / name).write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    result["output_sha256"] = {name: digest(output/name) for name in ["action_matrix.json", "collection_targets.json"]}
    (output/"report.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = qualify(args.output)
    print(json.dumps({k: report[k] for k in ["total_rows", "provider_events", "action_matrix_rows",
                     "primary_economic_terms_corroborated", "provider_dividends_missing_payable", "full_period_streams_qualified_for_scoring", "network_requests", "purchases_usd"]}))


if __name__ == "__main__":
    main()

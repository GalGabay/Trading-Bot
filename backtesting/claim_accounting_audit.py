"""Replay saved corporate-action terms locally, without a strategy or network.

Historical source terms and observed quotes are pinned separately from openly
declared mechanics assumptions. Passing arithmetic never certifies a missing
publication, entitlement, delivery or broker cash-availability date.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path

import pandas as pd

from backtesting.claim_accounting import AccountingError, ClaimLedger, OwnershipEvent, Quote, ShareLeg
from backtesting.cohort_audit import checked_file, digest, source_text

DEFAULT_CASES = Path("docs/claim_accounting_cases.json")


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def run_audit(output: Path, *, cases_path=DEFAULT_CASES) -> dict:
    if output.exists():
        raise FileExistsError("Choose a fresh accounting-check directory; do not replace previous evidence")
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    if (type(cases["schema_version"]) is not int or cases["schema_version"] != 1
            or cases["ready_for_strategy_scoring"] is not False or cases["new_purchases_usd"] != 0):
        raise ValueError("Only the explicit no-purchase mechanics protocol is supported")
    review_path = checked_file(Path.cwd(), {"path": cases["event_review_path"], "sha256": cases["event_review_sha256"]})
    gap_path = checked_file(Path.cwd(), {"path": cases["event_gap_report_path"], "sha256": cases["event_gap_report_sha256"]})
    review = json.loads(review_path.read_text(encoding="utf-8"))
    gap = json.loads(gap_path.read_text(encoding="utf-8"))
    if gap.get("ready_for_strategy_scoring", False) is not False:
        raise ValueError("This check must not promote unresolved collection evidence")
    root = Path(review["collection_root"])
    original = checked_file(Path.cwd(), {"path": str(root / "report.json"), "sha256": review["collection_report_sha256"]})
    collection = json.loads(original.read_text(encoding="utf-8"))
    if collection["adjustment"] != "raw" or collection["new_purchases_usd"] != 0:
        raise ValueError("Accounting requires the original raw, no-purchase collection")
    plan_path = checked_file(Path.cwd(), {"path": "docs/free_collection_plan.json", "sha256": collection["plan_sha256"]})
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    calendar_path = checked_file(Path.cwd(), {"path": plan["calendar_path"], "sha256": collection["calendar_sha256"]})
    sessions = json.loads(calendar_path.read_text(encoding="utf-8"))
    # Session closes are explicit; neither calendar-day gaps nor local midnight
    # labels are treated as event execution times.
    calendar = {pd.Timestamp(row["closes_at"]).date().isoformat(): row for row in sessions}
    probes = {p["probe_id"]: p for p in collection["probes"]}
    pinned = {str(review_path): digest(review_path), str(gap_path): digest(gap_path),
              str(original): digest(original), str(plan_path): digest(plan_path),
              str(calendar_path): digest(calendar_path), str(cases_path): digest(cases_path)}
    texts = {}
    for key in {c["source_id"] for c in cases["cases"] + cases["blocked_cases"]}:
        path = checked_file(Path.cwd(), review["sources"][key])
        pinned[str(path)] = digest(path)
        texts[key] = source_text(path)
    frames = {}

    def observed_quote(probe_id, identity, day, at):
        if probe_id not in frames:
            probe = probes[probe_id]
            bars = probe["bars"]
            path = checked_file(root / probe["directory"], {"path": bars["csv"], "sha256": bars["sha256"]})
            pinned[str(path)] = digest(path)
            frame = pd.read_csv(path, dtype=str)
            dates = pd.to_datetime(frame["timestamp"], utc=True)
            if dates.duplicated().any() or (dates >= pd.Timestamp("2024-01-01", tz="UTC")).any():
                raise ValueError("Duplicate or reserved holdout observations cannot enter accounting checks")
            if set(frame["symbol"]) != {probe["symbol"]}:
                raise ValueError("Saved quote symbols differ from the declared source probe")
            frame["session"] = dates.dt.tz_convert("America/New_York").dt.date.astype(str)
            frames[probe_id] = frame
        rows = frames[probe_id].loc[lambda f: f["session"] == day]
        if len(rows) != 1:
            raise ValueError(f"{probe_id}: require one actual quote for {day}; do not fill")
        row = rows.iloc[0]
        low, high, opening, close = map(Fraction, (row["low"], row["high"], row["open"], row["close"]))
        if not 0 < low <= min(opening, close) <= max(opening, close) <= high or Fraction(row["volume"]) <= 0:
            raise ValueError("Invalid or untradable raw event-session candle")
        return Quote(identity, at, row["low"], row["close"], row["high"])

    checks = []

    def require(condition, name):
        if not condition:
            raise AssertionError(name)
        checks.append(dict(name=name, passed=True))

    def rejected(call, name, ledger):
        before = deepcopy(ledger.__dict__)
        try:
            call()
        except AccountingError:
            require(ledger.__dict__ == before, name + ": rejected without mutation")
        else:
            raise AssertionError(name + ": invalid input was accepted")

    case_reports, artifacts = [], {}
    for case in cases["cases"]:
        name, day = case["name"], case["session"]
        require(all(term in texts[case["source_id"]] for term in case["source_terms"]), name + ": source terms corroborated")
        if day >= "2024-01-01" or day not in calendar:
            raise ValueError("Mechanics case must identify a saved development session")
        at = calendar[day]["closes_at"]
        prior_days = [d for d in calendar if d < day]
        if not prior_days:
            raise ValueError("Need an explicit prior session for hypothetical starting ownership")
        prior = calendar[max(prior_days)]["closes_at"]
        event = OwnershipEvent(name, case["parent_id"], case["kind"], at, prior,
                               review["sources"][case["source_id"]]["url"], case["cash_per_parent"],
                               tuple(ShareLeg(leg["instrument_id"], leg["ratio"]) for leg in case["shares"]),
                               terms_complete=True)
        ledger = ClaimLedger(cases["initial_simulated_cash"])
        ledger.buy("hypothetical_starting_holding", case["parent_id"], case["quantity"],
                   cases["hypothetical_entry_price"], at=prior)
        cash_before, basis_before = ledger.cash, sum(lot.basis for lot in ledger.lots)
        quotes = {}
        if case.get("parent_probe"):
            quotes[event.instrument_id] = observed_quote(case["parent_probe"], event.instrument_id, day, at)
        synthetic = []
        for leg in case["shares"]:
            identity = leg["instrument_id"]
            if "probe" in leg:
                quotes[identity] = observed_quote(leg["probe"], identity, day, at)
            else:
                rejected(lambda: ledger.recognize(event, quotes, at=at), name + ": missing child quote blocked", ledger)
                # This explicit arithmetic-only quote cannot become price data.
                value = leg["synthetic_close"]
                quotes[identity] = Quote(identity, at, value, value, value)
                synthetic.append(identity)
        rejected(lambda: ledger.recognize(replace(event, known_at="2023-12-31T23:59:59Z"), quotes, at=at),
                 name + ": unknown-at-event evidence blocked", ledger)
        rejected(lambda: ledger.recognize(replace(event, terms_complete=False), quotes, at=at),
                 name + ": unresolved ownership terms blocked", ledger)
        ledger.recognize(event, quotes, at=at)
        mark = ledger.mark(quotes, at=at)
        require(ledger.cash == cash_before, name + ": claims do not credit spendable cash")
        expected_parent = case["quantity"] if event.kind != "exchange" else 0
        require(ledger.quantity(event.instrument_id) == expected_parent, name + ": correct parent ownership")
        for leg in event.shares:
            expected = case["quantity"] * leg.shares_per_parent
            whole = expected.numerator // expected.denominator
            fraction = sum((c.units for c in ledger.claims if c.kind == "fractional_shares" and c.instrument_id == leg.instrument_id), Fraction(0))
            require(ledger.quantity(leg.instrument_id) == whole and fraction == expected - whole,
                    name + ": exact successor/child and fractional ownership")
        require(sum((c.amount for c in ledger.claims if c.kind == "cash"), Fraction(0)) == case["quantity"] * event.cash_per_parent,
                name + ": correct cash rights")
        require(sum((lot.basis for lot in ledger.lots), Fraction(0)) + sum((c.basis for c in ledger.claims), Fraction(0)) == basis_before,
                name + ": economic basis conserved")
        require(mark["reconciliation_passed"], name + ": equity and P&L reconcile")
        rejected(lambda: ledger.recognize(event, quotes, at=at), name + ": duplicate event blocked", ledger)
        require(not any(row["kind"] == "claim_paid" for row in ledger.journal), name + ": no invented payment")
        artifacts[f"{name}.json"] = dict(scenario=case, assumptions=cases["mechanics_assumptions"],
                                          mark=mark, journal=ledger.journal, quotes=[
                                              dict(instrument_id=q.instrument_id, timestamp=q.timestamp.isoformat(),
                                                   low=str(q.low), close=str(q.close), high=str(q.high),
                                                   synthetic=q.instrument_id in synthetic) for q in quotes.values()],
                                          ready_for_strategy_scoring=False)
        case_reports.append(dict(name=name, source_terms_corroborated=True, mechanics_checks_passed=True,
                                 price_mode="includes_explicit_synthetic_child_quote" if synthetic else "saved_raw_quotes_or_cash_only",
                                 outstanding_claims=len(ledger.claims), blockers=case["blockers"],
                                 ready_for_strategy_scoring=False))

    # An openly synthetic settlement timeline verifies the production API for
    # delay/fixing/one-time credit. It supplies no missing historical payment.
    ledger = ClaimLedger("1000")
    t0, t1, t2, t3, t4 = ("2018-11-27T21:00:00Z", "2018-11-28T21:00:00Z",
                           "2018-11-29T21:00:00Z", "2018-11-30T21:00:00Z", "2018-12-03T21:00:00Z")
    synthetic_source = "Synthetic settlement check only; not historical broker credit evidence"
    ledger.buy("holding", "PARENT", 3, "200", at=t0)
    event = OwnershipEvent("synthetic_timeline", "PARENT", "exchange", t1, t0, synthetic_source,
                           "145", (ShareLeg("CHILD", "0.8378"),), terms_complete=True)
    q = lambda at: {"CHILD": Quote("CHILD", at, "60", "65", "70")}
    ledger.recognize(event, q(t1), at=t1)
    cash_claim = next(c for c in ledger.claims if c.kind == "cash")
    fractional = next(c for c in ledger.claims if c.kind == "fractional_shares")
    initial_mark = ledger.mark(q(t1), at=t1)
    rejected(lambda: ledger.buy("unfunded", "OTHER", 5, "100", at=t1), "synthetic: claims cannot fund buys", ledger)
    ledger.sell("whole_share_exit", "CHILD", 2, "65", at=t2)
    post_sale = ledger.mark(q(t2), at=t2)
    require(len(ledger.claims) == 2, "synthetic: claims survive whole-share sale")
    require(Fraction(post_sale["stock_and_fraction_value"]) == Fraction("0.5134") * 65, "synthetic: fraction remains price exposed")
    ledger.pay("cash_credit", cash_claim.claim_id, "435", available_at=t3, known_at=t2, at=t3, source=synthetic_source)
    rejected(lambda: ledger.pay("second_credit", cash_claim.claim_id, "435", available_at=t3, known_at=t2, at=t3,
                                source=synthetic_source), "synthetic: duplicate payment blocked", ledger)
    before_fix_cash = ledger.cash
    ledger.fix_fraction("fixing", fractional.claim_id, "33.20", known_at=t3, at=t3, source=synthetic_source)
    require(ledger.cash == before_fix_cash, "synthetic: fixing does not create buying power")
    fixed_mark = ledger.mark({}, at=t3)
    require(Fraction(fixed_mark["stock_and_fraction_value"]) == 0, "synthetic: known cash allocation removes fractional price exposure")
    ledger.pay("fraction_credit", fractional.claim_id, "33.20", available_at=t4, known_at=t3, at=t4, source=synthetic_source)
    final_mark = ledger.mark({}, at=t4)
    require(ledger.cash == Fraction("998.20") and not ledger.claims and not ledger.lots, "synthetic: exact final cash and no remaining rights")
    require(ledger.realized_pnl == Fraction("-1.80") and final_mark["reconciliation_passed"], "synthetic: final realized P&L reconciles")
    artifacts["synthetic_settlement_timeline.json"] = dict(synthetic=True, simulated_money=True,
        initial_mark=initial_mark, after_whole_share_sale=post_sale, after_fixing=fixed_mark,
        final_mark=final_mark, journal=ledger.journal, not_historical_payment_evidence=True)

    report = dict(
        scope=cases["purpose"], accounting_ledger_version=1, simulated_money=True,
        new_purchases_usd=0, network_requests=0, orders=0, subscription_changes=0,
        strategy_simulations=0, reserved_holdout_read=False,
        input_sha256=pinned,
        code_sha256={str(path): digest(path) for path in (
            Path("backtesting/claim_accounting.py"), Path("backtesting/claim_accounting_audit.py"),
            Path("backtesting/risk_diagnostics.py"), Path("backtesting/cohort_audit.py"),
            Path("backtesting/historical_holdings.py"), Path("tests/test_claim_accounting.py"))},
        checks_passed=len(checks), checks_failed=0, checks=checks,
        case_count=len(case_reports), cases=case_reports,
        source_blocked_cases=cases["blocked_cases"],
        settlement_timeline="Explicitly synthetic; no real-case payout/date inferred",
        assumptions=cases["mechanics_assumptions"],
        legacy_strategy_adapter_connected=False, market_wide_performance_ready=False,
        ready_for_strategy_scoring=False,
        next_work="Integrate the checked ledger with explicit universe/feature/order policies; resolve evidence gaps before any larger strategy study",
    )
    # All checks finish before evidence is written. No old artifacts are edited.
    output.mkdir(parents=True, exist_ok=False)
    for filename, value in artifacts.items():
        write(output / filename, value)
    write(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    args = parser.parse_args()
    report = run_audit(args.output, cases_path=args.cases)
    print(json.dumps({key: report[key] for key in ("checks_passed", "checks_failed", "case_count", "new_purchases_usd", "orders", "ready_for_strategy_scoring")}))


if __name__ == "__main__":
    main()

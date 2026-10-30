"""Reviewed daily corporate-action instructions, without portfolio execution.

Ticker changes preserve the same economic instrument. Split ratios are backed
by issuer/clearinghouse evidence; a provider ex-date can be a disclosed daily
convention when it is the first saved open after the issuer distribution date.
Preinvestment actions never change portfolio quantities. Every source row stays
in the audit inventory. These instructions do not certify actual broker receipt.
"""

import json
from pathlib import Path

from backtesting.claim_accounting import exact, number
from backtesting.cohort_audit import checked_file
from backtesting.dividend_components import validate_review_evidence


def load_actions(path, spec, provider_rows, provider_pin, clock):
    review = json.loads(path.read_text(encoding="utf-8"))
    if review.get("schema_version") != 1 or review.get("provider_source") != provider_pin:
        raise ValueError("Corporate-action review is detached from the provider inventory")
    validate_review_evidence(review)
    if json.loads(checked_file(Path.cwd(), review["spec"]).read_text(encoding="utf-8")) != spec:
        raise ValueError("Corporate-action review does not match the historical specification")
    sources = {s["id"]: s for s in review["sources"]}
    if len(sources) != len(review["sources"]):
        raise ValueError("Duplicate corporate-action source identity")
    rows = {}
    for row in provider_rows:
        identity = row["instrument_id"], row["event_id"]
        if row["category"] != "cash_dividends":
            if identity in rows:
                raise ValueError("Duplicate provider corporate-action identity")
            rows[identity] = row
    streams = {s["instrument_id"]: s for s in spec["streams"]}
    actions = {}
    for decision in review["decisions"]:
        identity = decision["instrument_id"], decision["event_id"]
        row = rows.get(identity)
        if row is None or identity in actions:
            raise ValueError("Missing or repeated provider corporate-action decision")
        record = json.loads(row["record"], parse_float=str)
        if record.get("id") != row["event_id"] or row["day"] != decision["provider_day"]:
            raise ValueError("Provider identity/date changed after corporate-action review")
        action = dict(instrument_id=row["instrument_id"], root_id=row["root_id"], event_id=row["event_id"],
            category=row["category"], provider_day=row["day"], provider_record=record,
            kind=decision["kind"], decision=decision, data_terms_resolved=True,
            execution_ready=False, historical_known_at=None, actual_broker_received_at=None,
            strict_identity_verified=False, cash_delta="0", blockers=[])
        if decision["kind"] == "preinvestment_reference_action":
            if row["day"] >= spec["membership_not_before"] or row["category"] not in {"forward_splits", "reverse_splits"}:
                raise ValueError("Only uninvested split-reference boundaries can use this exclusion")
            at = clock.open_on(row["day"])
            if at is None:
                raise ValueError("Preinvestment reference reset requires a saved session")
            action.update(effective_at=at.isoformat(), quantity_effect="none_no_portfolio_holdings",
                required_feature_reset=dict(instrument_id=row["instrument_id"], from_session=row["day"],
                    reason="Preinvestment provider action: start fresh features; no quantity or cash credit"))
        else:
            source = sources[decision["source_id"]]
            evidence = json.loads(checked_file(Path.cwd(), source["evidence"]).read_text(encoding="utf-8"))
            fact = next((f for f in evidence["sources"] if f["id"] == decision["fact_id"]), None)
            if not fact or fact["access"] not in {"primary_browser_text_reviewed", "primary_clearinghouse_browser_pdf_text_reviewed"}:
                raise ValueError("Corporate-action terms need direct primary evidence")
            action["source"] = dict(evidence=source["evidence"], fact_id=fact["id"], url=fact["url"])
            if decision["kind"] == "same_instrument_alias":
                if (row["category"] != "name_changes" or record["old_symbol"] != fact["old_symbol"] or
                        record["new_symbol"] != fact["new_symbol"] or fact.get("same_instrument") is not True):
                    raise ValueError("Reviewed alias is not a same-instrument name change")
                stream = streams[row["instrument_id"]]
                parts = stream["parts"]
                matches = [(a, b) for a, b in zip(parts, parts[1:]) if
                    a["source_key"] == decision["old_source_key"] and b["source_key"] == decision["new_source_key"] and
                    a["end_exclusive"] == b["start"] == fact["first_session"]]
                if len(matches) != 1:
                    raise ValueError("Alias date/source segments disagree with the reviewed stream")
                at = clock.open_on(fact["first_session"])
                if at is None:
                    raise ValueError("Alias boundary is outside the saved calendar")
                action.update(effective_at=at.isoformat(), quantity_effect="preserve_existing_lots", share_multiplier="1",
                    preserve_feature_history=True, preserve_position_age=True, invalidate_symbol_bound_execution_state=True,
                    provider_date_differs_from_effective_session=row["day"] != fact["first_session"],
                    effective_session_basis=fact["session_basis"])
            elif decision["kind"] == "ordinary_split":
                if row["category"] != "forward_splits":
                    raise ValueError("This reviewed split adapter supports forward splits only")
                ratio = number(str(record["new_rate"]), positive=True)/number(str(record["old_rate"]), positive=True)
                if ratio != number(fact["new_shares_per_old"], positive=True):
                    raise ValueError("Provider split ratio disagrees with primary evidence")
                primary_day = fact.get("first_adjusted_session")
                if primary_day:
                    if row["day"] != primary_day:
                        raise ValueError("Provider split session disagrees with primary ex-date")
                    basis = "primary_first_adjusted_session"
                else:
                    reported_day = fact.get("distribution_date") or fact["issuer_split_date"]
                    first_after = next((d.isoformat() for d in clock.days if d.isoformat() > reported_day), None)
                    if row["day"] != first_after:
                        raise ValueError("Provider split ex-date must be first saved session after issuer distribution date")
                    basis = "issuer_ratio_provider_session_after_reported_date_daily_convention"
                at = clock.open_on(row["day"])
                if at is None:
                    raise ValueError("Split boundary is outside the saved calendar")
                action.update(effective_at=at.isoformat(), quantity_effect="multiply_current_lots_by_ratio",
                    share_multiplier=exact(ratio), effective_session_basis=basis, preserve_total_cost_basis=True,
                    rebase_stops_and_per_share_basis=True, invalidate_pending_orders=True,
                    fractional_policy="pending_share_claim_no_automatic_cash", rebase_pending_share_rights=True)
            else:
                raise ValueError("Unsupported corporate-action instruction")
        actions[identity] = action
    return actions


def gate_action(action, membership_not_before):
    """Validate the minimum instruction contract before a route leaves the gate."""
    common = (action.get("data_terms_resolved") is True and action.get("execution_ready") is False and
        action.get("historical_known_at") is None and action.get("actual_broker_received_at") is None and
        action.get("cash_delta") == "0" and not action.get("blockers") and action.get("effective_at"))
    if not common:
        return False
    if action["kind"] == "preinvestment_reference_action":
        reset = action.get("required_feature_reset", {})
        return (reset.get("instrument_id") == action["instrument_id"] and
            action["provider_day"] == reset.get("from_session") and action["provider_day"] < membership_not_before and
            action.get("quantity_effect") == "none_no_portfolio_holdings")
    if action["kind"] == "same_instrument_alias":
        return action.get("share_multiplier") == "1" and action.get("quantity_effect") == "preserve_existing_lots"
    if action["kind"] == "ordinary_split":
        return (number(action["share_multiplier"], positive=True) > 1 and action.get("preserve_total_cost_basis") is True and
            action.get("rebase_stops_and_per_share_basis") is True and action.get("invalidate_pending_orders") is True and
            action.get("fractional_policy") == "pending_share_claim_no_automatic_cash")
    return False

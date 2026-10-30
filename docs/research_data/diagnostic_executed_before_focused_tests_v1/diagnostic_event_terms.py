"""Offline event-term overlay: warmup exclusions and incoming-context routing.

Reviewed spin-off ratios are recorded separately from unresolved entitlement,
receipt and fractional-cash terms. No strict ownership flags are promoted.
"""

import json
from pathlib import Path

from backtesting.claim_accounting import exact, number
from backtesting.cohort_audit import checked_file
from backtesting.dividend_components import validate_review_evidence


def load_event_terms(path, spec, provider_rows, source_pin):
    review = json.loads(path.read_text(encoding="utf-8"))
    if review.get("schema_version") != 1 or review.get("provider_source") != source_pin:
        raise ValueError("Event-term overlay is detached from its provider input")
    validate_review_evidence(review)
    spec_path = checked_file(Path.cwd(), review["spec"])
    if json.loads(spec_path.read_text(encoding="utf-8")) != spec:
        raise ValueError("Event-term overlay does not match the historical spec")
    material = {e["id"]: e for e in spec["material_events"]}
    streams = {s["instrument_id"]: s for s in spec["streams"]}
    providers = {(r["instrument_id"], r["event_id"]): r for r in provider_rows if r["category"] != "cash_dividends"}
    events, routes = {}, {}
    sources = {s["id"]: s for s in review["sources"]}
    for decision in review["material_decisions"]:
        event = material[decision["event_id"]]
        if (decision["event_id"] in events or decision["parent_id"] != event["parent_id"] or
                decision["economic_date"] != event["economic_date"]):
            raise ValueError("Repeated or mismatched material event decision")
        kind = decision["kind"]
        if kind == "uninvested_warmup_event":
            if (event["kind"] != "preinvestable_warmup_spinoff" or
                    event["economic_date"] >= spec["membership_not_before"]):
                raise ValueError("Only events before membership availability are uninvested warmup")
        elif kind == "primary_ratio_reviewed_other_terms_unresolved":
            if (not decision["source_ids"] or any(s not in sources for s in decision["source_ids"]) or
                    len(event["share_legs"]) != 1 or
                    event["share_legs"][0]["instrument_id"] != decision["child_id"] or
                    number(event["share_legs"][0]["shares_per_parent"], positive=True) !=
                    number(decision["shares_per_parent"], positive=True)):
                raise ValueError("Primary ratio review disagrees with the configured child entitlement")
            evidence = json.loads(checked_file(Path.cwd(), sources[decision["source_ids"][0]]["evidence"]).read_text(encoding="utf-8"))
            fact = next((s for s in evidence["sources"] if s["id"] == decision["primary_fact_id"]), None)
            if (not fact or not fact["access"].startswith("primary_") or
                    fact.get("economic_date") != event["economic_date"] or
                    number(fact["shares_per_parent"], positive=True) != number(decision["shares_per_parent"], positive=True)):
                raise ValueError("Reviewed primary fact does not support the event date and ratio")
        elif kind == "primary_cash_consideration_reviewed":
            if (not decision["source_ids"] or any(s not in sources for s in decision["source_ids"]) or
                    event["kind"] != "cash_merger" or event["share_legs"] or
                    number(event["cash_per_parent"], positive=True) != number(decision["cash_per_parent"], positive=True)):
                raise ValueError("Cash-merger decision does not match the configured holder consideration")
            evidence = json.loads(checked_file(Path.cwd(), sources[decision["source_ids"][0]]["evidence"]).read_text(encoding="utf-8"))
            fact = next((s for s in evidence["sources"] if s["id"] == decision["primary_fact_id"]), None)
            boundary = streams[event["parent_id"]]["parts"][-1]["end_exclusive"]
            if (not fact or fact.get("access") != "primary_browser_text_reviewed" or
                    fact.get("all_common_holders_supported") is not True or fact.get("currency") != "USD" or
                    fact["event_id"] != event["id"] or fact["economic_date"] != event["economic_date"] or
                    number(fact["cash_per_parent"], positive=True) != number(decision["cash_per_parent"], positive=True) or
                    decision["first_nontradeable_session"] != boundary or boundary < event["economic_date"] or
                    fact.get("cash_receipt_date") is not None):
                raise ValueError("Cash-merger source, gross USD value or terminal boundary changed")
        else:
            raise ValueError("Unsupported event-term review kind")
        events[decision["event_id"]] = decision
    for decision in review["provider_context_decisions"]:
        identity = decision["instrument_id"], decision["event_id"]
        row = providers[identity]
        record = json.loads(row["record"])
        stream = streams[row["instrument_id"]]
        if (identity in routes or row["category"] != "spin_offs" or row["role"] != "other_security_unattached" or
                record.get("new_symbol") != row["query_symbol"] or
                record.get("source_symbol") != decision["source_symbol"] or
                row["query_symbol"] != decision["received_symbol"] or
                stream["role"] != "received_security" or row["root_id"] != stream["root_id"]):
            raise ValueError("Context decision must describe an incoming record on a received child stream")
        # Owning the child does not earn another distribution from its parent.
        # The real parent event, if present, keeps its independent review gates.
        if decision["source_symbol"] == decision["received_symbol"]:
            raise ValueError("Cannot classify a holder's own event as unrelated context")
        routes[identity] = decision
    return events, routes


def apply_material_terms(item, decision, clock):
    if (item["event_id"] != decision["event_id"] or item["parent_id"] != decision["parent_id"] or
            item["economic_date"] != decision["economic_date"]):
        raise ValueError("Material decision does not belong to this event")
    item["event_term_review"] = decision
    if decision["kind"] == "uninvested_warmup_event":
        reset = next((d.isoformat() for d in clock.days if d.isoformat() >= item["economic_date"]), None)
        if reset is None:
            raise ValueError("Warmup feature reset has no saved session")
        item.update(status="inapplicable_preinvestable_event", no_portfolio_entitlement=True,
                    blockers=[], required_feature_reset=dict(instrument_id=item["parent_id"],
                        from_session=reset, reason="Uninvested warmup distribution; do not carry earlier features"))
        item["modeled_cash_release_at"] = None
        for leg in item["share_legs"]:
            leg["modeled_release_at"] = None
    elif decision["kind"] == "primary_cash_consideration_reviewed":
        at = clock.open_on(decision["first_nontradeable_session"])
        prior_closes = [c for c in clock.closes if at is not None and c < at]
        if at is None or not prior_closes:
            raise ValueError("Cash-merger boundary requires an actual saved open and prior ownership close")
        item.update(status="admitted_diagnostic_cash_receivable", data_terms_resolved=True,
            cash_per_parent=exact(number(decision["cash_per_parent"], positive=True)),
            modeled_accounting_at=at.isoformat(), required_ownership_snapshot_at=prior_closes[-1].isoformat(),
            first_nontradeable_session=decision["first_nontradeable_session"],
            cash_availability_policy="unspendable_receivable_no_invented_date", modeled_cash_release_at=None,
            currency_basis="primary_reported_gross_usd_no_personal_tax_model", actual_delivery_at=None,
            consume_parent_once=True, invalidate_pending_orders_and_stops=True, blockers=[])
    else:
        item.update(primary_share_ratio_reviewed=True,
            blockers=["Distribution record-date/due-bill entitlement requires diagnostic schedule review",
                      "Fractional claim and release schedule require diagnostic admission; actual receipt remains unknown"])

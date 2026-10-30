"""Source-bound holder schedules for daily diagnostic preparation only.

Regular-way due bills follow the buyer until the ex-distribution boundary;
record-date ownership alone is insufficient. Fractional rights remain exact
unspendable share claims under the approved diagnostic convention. No portfolio
transfer, cash fixing, delivery confirmation or strategy execution occurs here.
"""

from copy import deepcopy
import json
from pathlib import Path

from backtesting.claim_accounting import exact, instant, number
from backtesting.cohort_audit import checked_file
from backtesting.dividend_components import validate_review_evidence


def load_holder_terms(path, spec, provider_rows, provider_pin, clock):
    review = json.loads(path.read_text(encoding="utf-8"))
    if review.get("schema_version") != 1 or review.get("provider_source") != provider_pin:
        raise ValueError("Holder review is detached from the provider inventory")
    validate_review_evidence(review)
    if json.loads(checked_file(Path.cwd(), review["spec"]).read_text(encoding="utf-8")) != spec:
        raise ValueError("Holder review does not match the historical specification")
    sources = {}
    for source in review["sources"]:
        if source["id"] in sources:
            raise ValueError("Repeated holder evidence source identity")
        sources[source["id"]] = source

    def fact_for(decision, allowed_access):
        source = sources[decision["source_id"]]
        evidence = json.loads(checked_file(Path.cwd(), source["evidence"]).read_text(encoding="utf-8"))
        matches = [f for f in evidence["sources"] if f["id"] == decision["fact_id"]]
        if len(matches) != 1 or matches[0].get("access") not in allowed_access:
            raise ValueError("Holder schedule requires unique directly reviewed primary terms")
        return matches[0]

    material = {e["id"]: e for e in spec["material_events"]}
    streams = {s["instrument_id"]: s for s in spec["streams"]}
    providers = {}
    for row in provider_rows:
        if row["category"] != "cash_dividends":
            identity = row["instrument_id"], row["event_id"]
            if identity in providers or json.loads(row["record"]).get("id") != row["event_id"]:
                raise ValueError("Repeated or inconsistent holder provider identity")
            providers[identity] = row
    spinoffs, aliases, boundaries = {}, {}, {}
    for decision in review["spinoffs"]:
        event = material[decision["event_id"]]
        fact = fact_for(decision, {"primary_browser_text_reviewed"})
        completion = fact_for(dict(source_id=decision["source_id"], fact_id=decision["completion_fact_id"]),
                              {"primary_audited_plan_filing_browser_text_reviewed", "primary_browser_text_reviewed"})
        ratio = exact(number(fact["shares_per_parent"], positive=True))
        child = streams[decision["child_id"]]
        if (event["id"] in spinoffs or event["kind"] != "retained_parent_spinoff" or
                event["parent_id"] != decision["parent_id"] or event["root_id"] != event["parent_id"] or
                event["economic_date"] != fact["economic_date"] or
                event["share_legs"] != [dict(instrument_id=decision["child_id"], shares_per_parent=ratio)] or
                child["root_id"] != event["root_id"] or child["role"] != "received_security" or
                child.get("eligible_for_new_entries_candidate") is not False or
                completion["economic_date"] != fact["economic_date"] or
                number(completion["shares_per_parent"], positive=True) != number(ratio) or
                completion["record_date"] != fact["record_date"] or
                number(fact["fixed_cash_per_parent"]) != 0 or
                (event["cash_per_parent"] is not None and number(event["cash_per_parent"]) != 0) or
                fact["regular_way_sale_transfers_child_right"] is not True or
                fact["fractional_treatment"] != "aggregate_sell_net_proceeds_actual_price_and_receipt_unknown"):
            raise ValueError("Spin-off identity, ratio or primary holder terms disagree")
        at = clock.open_on(fact["ex_date"])
        prior = [c for c in clock.closes if at is not None and c < at]
        effective = instant(fact["economic_effective_at"])
        if (at is None or not prior or effective > at or fact["ex_date"] != fact["economic_date"] or
                fact["regular_way_due_bills_end"] != prior[-1].date().isoformat() or
                not fact["regular_way_due_bills_start"] <= fact["record_date"] <= fact["regular_way_due_bills_end"] or
                child["parts"][0]["start"] != fact["first_regular_session"] or
                fact["first_regular_session"] != fact["ex_date"]):
            raise ValueError("Due-bill entitlement must use the last regular-way close before the reviewed ex-open")
        identity = event["parent_id"], decision["provider_event_id"]
        row = providers[identity]
        record = json.loads(row["record"], parse_float=str)
        if (row["category"] != "spin_offs" or row["role"] != "parent_distribution_requires_ownership" or
                row["day"] != fact["ex_date"] or record["ex_date"] != fact["ex_date"] or
                record["record_date"] != fact["record_date"] or record["source_symbol"] != fact["parent_symbol"] or
                record["new_symbol"] != fact["child_symbol"] or
                number(str(record["new_rate"]), positive=True) / number(str(record["source_rate"]), positive=True) != number(ratio)):
            raise ValueError("Provider spin-off does not match the reviewed regular-way entitlement")
        plan = dict(decision=deepcopy(decision), source=deepcopy(fact), completion=deepcopy(completion),
            parent_id=event["parent_id"], child_id=decision["child_id"], event_id=event["id"], shares_per_parent=ratio,
            economic_date=fact["economic_date"], economic_effective_at=fact["economic_effective_at"],
            ex_date=fact["ex_date"], record_date=fact["record_date"],
            first_regular_session=fact["first_regular_session"], ownership_snapshot_at=prior[-1].isoformat(),
            ex_open_at=at.isoformat(), provider_event_id=row["event_id"],
            provider_due_bill_redemption_date=record.get("due_bill_redemption_date"),
            regular_start_aliases=[], review_source=deepcopy(review["sources"]))
        spinoffs[event["id"]] = plan
    for decision in review["regular_start_aliases"]:
        plan = spinoffs[decision["event_id"]]
        identity = decision["instrument_id"], decision["provider_event_id"]
        row = providers[identity]
        record = json.loads(row["record"])
        symbol = plan["source"]["child_symbol"]
        if (identity in aliases or decision["instrument_id"] != plan["child_id"] or
                row["category"] != "name_changes" or row["day"] != plan["first_regular_session"] or
                record["old_symbol"] != symbol + ".WI" or record["new_symbol"] != symbol or
                record["old_cusip"] != record["new_cusip"]):
            raise ValueError("Only the unheld when-issued alias at the received stream start is context")
        aliases[identity] = plan["event_id"]
        plan["regular_start_aliases"].append(dict(instrument_id=identity[0], event_id=identity[1],
            old_symbol=record["old_symbol"], new_symbol=symbol, quantity_effect="none_no_when_issued_positions"))
    for decision in review["election_boundaries"]:
        fact = fact_for(decision, {"primary_clearinghouse_browser_pdf_text_reviewed", "primary_browser_text_reviewed"})
        at = clock.open_on(fact["ex_date"])
        prior = [c for c in clock.closes if at is not None and c < at]
        if decision["event_id"] in boundaries or not prior or fact["record_date"] < fact["ex_date"]:
            raise ValueError("Election ex-distribution boundary is missing or repeated")
        boundaries[decision["event_id"]] = dict(source=deepcopy(fact), instrument_id=decision["instrument_id"],
            record_date=fact["record_date"], ex_date=fact["ex_date"], ownership_snapshot_at=prior[-1].isoformat(),
            ex_open_at=at.isoformat(), ownership_basis="regular_way_prior_saved_close_before_reviewed_ex_open")
    return spinoffs, aliases, boundaries


def apply_spinoff_terms(item, plan, clock):
    if (item["event_id"] != plan["event_id"] or item["parent_id"] != plan["parent_id"] or
            item["economic_date"] != plan["economic_date"] or len(item["share_legs"]) != 1 or
            item["share_legs"][0]["instrument_id"] != plan["child_id"] or
            number(item["share_legs"][0]["shares_per_parent"]) != number(plan["shares_per_parent"])):
        raise ValueError("Holder spin-off instruction does not belong to this candidate")
    release = clock.share_release(plan["economic_effective_at"], plan["first_regular_session"], item["scenario"])
    item["share_legs"][0].update(modeled_release_at=None if release is None else release.isoformat(),
        actual_broker_received_at=None, fractional_policy="pending_share_claim_no_automatic_cash")
    item.update(status="admitted_diagnostic_due_bill_spinoff", data_terms_resolved=True, blockers=[],
        holder_terms_review=deepcopy(plan), economic_effective_at=plan["economic_effective_at"],
        modeled_accounting_at=plan["ex_open_at"], required_ownership_snapshot_at=plan["ownership_snapshot_at"],
        ownership_basis="regular_way_due_bill_rights_at_last_cum_close", cash_per_parent="0",
        fixed_cash_leg_policy="none_distribution_is_shares_fractional_proceeds_remain_unknown",
        modeled_cash_release_at=None, preserve_parent_quantity=True, issue_child_right_once=True,
        rights_survive_later_parent_sale=True, invalidate_pending_orders_and_stops=True,
        fractional_policy="pending_share_claim_no_automatic_cash", fractional_cash_fixing=None,
        pending_claims_must_count_toward_equity_and_exposure=True, actual_delivery_at=None, execution_ready=False,
        required_feature_reset=dict(instrument_id=plan["parent_id"], from_session=plan["ex_date"],
            reason="Retained-parent raw-price distribution: discard pre-distribution feature history"))


def annotate_election_boundary(schedule, boundary):
    if (schedule["instrument_id"] != boundary["instrument_id"] or schedule["record_date"] != boundary["record_date"] or
            any(r["record"]["ex_date"] != boundary["ex_date"] for r in schedule["provider_records"])):
        raise ValueError("Election primary ex-date conflicts with provider or holder identity")
    schedule["reviewed_ownership_boundary"] = deepcopy(boundary)
    # Exact allocations, fractional fixing and schedule admission remain gated.
    # An ex-date corroboration is not an actual record-holder or receipt proof.


def gate_due_bill_spinoff(item):
    """Validate the entire supported instruction contract, without execution."""
    plan = item.get("holder_terms_review", {})
    legs = item.get("share_legs", [])
    reset = item.get("required_feature_reset", {})
    try:
        supported = (item.get("status") == "admitted_diagnostic_due_bill_spinoff" and
            item.get("kind") == "retained_parent_spinoff" and item.get("data_terms_resolved") is True and
            item.get("execution_ready") is False and item.get("actual_delivery_at") is None and
            item.get("historical_known_at") is None and not item.get("blockers") and
            item.get("cash_per_parent") == "0" and item.get("modeled_cash_release_at") is None and
            item.get("ownership_basis") == "regular_way_due_bill_rights_at_last_cum_close" and
            plan["event_id"] == item["event_id"] and plan["parent_id"] == item["parent_id"] and
            plan["economic_date"] == item["economic_date"] and
            item["modeled_accounting_at"] == plan["ex_open_at"] and
            item["required_ownership_snapshot_at"] == plan["ownership_snapshot_at"] and
            instant(plan["ownership_snapshot_at"]) < instant(plan["ex_open_at"]) and
            len(legs) == 1 and legs[0]["instrument_id"] == plan["child_id"] and
            number(legs[0]["shares_per_parent"], positive=True) == number(plan["shares_per_parent"], positive=True) and
            legs[0].get("actual_broker_received_at") is None and
            item.get("fractional_policy") == "pending_share_claim_no_automatic_cash" and
            item.get("fractional_cash_fixing") is None and
            reset.get("instrument_id") == item["parent_id"] and reset.get("from_session") == plan["ex_date"] and
            all(item.get(f) is True for f in ("preserve_parent_quantity", "issue_child_right_once",
                "rights_survive_later_parent_sale", "invalidate_pending_orders_and_stops",
                "pending_claims_must_count_toward_equity_and_exposure")))
        if not supported:
            return False
        release = legs[0].get("modeled_release_at")
        if item["scenario"] == "no_credit":
            return release is None
        return release is not None and instant(release) >= instant(plan["economic_effective_at"])
    except (ValueError, KeyError, TypeError):
        return False

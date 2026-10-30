"""Compile conditional holder schedules, never infer an investor election.

Record-date lots, split ordering, issue-date lots and delivery are separate.
Published approximate SLG allocations remain approximate. This inventory can
detect a missing provider event without fabricating that event's ex-date.
"""

from copy import deepcopy
import json
from pathlib import Path

from backtesting.broad_collection import pin
from backtesting.claim_accounting import number
from backtesting.cohort_audit import checked_file
from backtesting.election_terms import resolve_election


def load_holder_policy(inputs):
    """Bind the selected research rule to the owner's separate approval.

    General diagnostic approval and an edited selection flag are insufficient.
    The original proposal remains immutable evidence of the rule accepted.
    """
    selected = inputs.get("holder_election_selected")
    approval = inputs.get("holder_election_approval")
    if selected is None:
        if approval is not None:
            raise ValueError("Holder approval is present without its selected research rule")
        return None
    if selected != "no_election" or approval is None:
        raise ValueError("Only the separately approved no-election research rule is supported")
    record = json.loads(checked_file(Path.cwd(), approval).read_text(encoding="utf-8"))
    checked_file(Path.cwd(), record["proposal"])
    if (record.get("schema_version") != 1 or record.get("owner_approved") is not True or
            record.get("choice") != selected or record.get("scope") != "historical_research_only" or
            type(record.get("purchases_usd")) is not int or record["purchases_usd"] != 0):
        raise ValueError("Holder research approval does not authorize this choice or scope")
    for field in ("unknown_defaults_may_be_assumed", "rounded_allocations_approved",
                  "missing_entitlement_may_be_assumed", "actual_broker_receipt_may_be_inferred",
                  "performance_authorized", "paper_authorized", "broker_requests_authorized"):
        if record.get(field) is not False:
            raise ValueError("Holder choice cannot relax economic evidence or trading restrictions: " + field)
    return dict(record, approval=approval)


def apply_holder_policy(schedules, policy):
    """Select the approved holder action without admitting missing economics."""
    if policy is None:
        return
    for schedule in schedules:
        schedule.update(selected_holder_election="no_election", holder_policy_owner_approved=True,
                        holder_policy_approval=policy["approval"],
                        selected_default_branch=schedule["source_reported_default"],
                        selected_conditional_allocation=None)
        schedule["blockers"] = [b for b in schedule["blockers"] if
            b != "Holder election is not selected; general accounting approval does not select a branch"]
        if schedule["source_reported_default"] is None:
            schedule["blockers"].append("Issuer no-election default is not established by reviewed evidence")
            continue
        allocation = schedule.get("conditional_allocations", {}).get("no_election")
        if allocation and allocation.get("status") == "conditional_reported_terms_resolved":
            # AIV reported branches remain conditional on holdings and schedule
            # admission. SLG rounded shares and unknown MAC conversion stay blocked.
            if allocation["branch"] != schedule["source_reported_default"]:
                raise ValueError("Selected no-election allocation disagrees with the documented default")
            schedule["selected_conditional_allocation"] = deepcopy(allocation)


def compile_schedules(provider_rows, clock, terms_path, split_review_path, resolution_path, mac_review_path,
                      holder_policy=None):
    terms = json.loads(terms_path.read_text(encoding="utf-8"))
    split_review = json.loads(split_review_path.read_text(encoding="utf-8"))
    resolution = json.loads(resolution_path.read_text(encoding="utf-8"))
    for source in terms["sources"]:
        checked_file(Path.cwd(), source["browser_text"])
    for source in resolution["sources"]:
        if "browser_evidence" in source:
            checked_file(Path.cwd(), source["browser_evidence"])
    split_facts = {s["id"]: s["facts"] for s in split_review["sources"]}
    declarations = {s["id"]: s for s in resolution["sources"]}
    schedules = []
    roots = {"aiv_2019": "COHORT-2016-0046", "aiv_2020": "COHORT-2016-0046",
             "slg_2021": "COHORT-2016-0413", "slg_2022": "COHORT-2016-0413"}
    for original in terms["election_terms"]:
        t = deepcopy(original)
        root = roots[t["id"]]
        records = []
        for row in provider_rows:
            if row["instrument_id"] == root and row["category"] == "cash_dividends":
                record = json.loads(row["record"], parse_float=str)
                if record.get("record_date") == t["record_date"] and record.get("payable_date") == t["payable_date"]:
                    records.append(dict(event_id=row["event_id"], record=record))
        if t["id"] == "slg_2021":
            declaration = declarations["slg_2021_declaration"]
            if declaration["record_date"] != t["record_date"] or declaration["payable_date"] != t["payable_date"]:
                raise ValueError("SLG default election evidence does not match the saved allocation notice")
            default = declaration["no_election_branch"]
        else:
            default = t["no_election_branch"]
        if t["id"] == "slg_2022":
            # The fresh 2020 notice cannot establish a 2021 election's default.
            default = None
        split = split_facts.get(t["id"], {})
        if t["id"] == "slg_2022":
            # Direct newer filing, not the earlier timed-out annual report.
            split = declarations["slg_2022_split"]
            if split["access"] != "primary_browser_text_reviewed":
                raise ValueError("SLG 2022 split needs directly reviewed evidence")
        split_session = split["first_adjusted_session"]
        if clock.open_on(split_session) is None or clock.open_on(t["record_date"]) is None:
            raise ValueError("Election record/split boundary is outside saved sessions")
        if not (t["record_date"] <= t["payable_date"]):
            raise ValueError("Election payment cannot precede record ownership")
        split_before_record = split_session <= t["record_date"]
        operations = (["split_existing_lots", "snapshot_record_date_lots", "issue_election_rights"] if split_before_record else
                      ["snapshot_record_date_lots", "issue_election_rights", "split_existing_lots_and_unfixed_share_rights"])
        if split_before_record and not split_session < t["payable_date"]:
            raise ValueError("Pre-record split order conflicts with the payment date")
        if not split_before_record and not t["payable_date"] < split_session:
            raise ValueError("Dividend-before-split order conflicts with the payment date")
        conditional = {}
        if not t["share_allocation_approximate"]:
            for election in ("no_election", "stock", "cash"):
                conditional[election] = resolve_election(t, election)
        else:
            conditional = dict(reported_cash_election=t["reported_cash_election"], reported_stock_election=t["reported_stock_election"])
        schedules.append(dict(event_id=t["id"], instrument_id=root, record_date=t["record_date"],
            payable_date=t["payable_date"], provider_event_ids=[r["event_id"] for r in records],
            provider_records=records, provider_event_missing=not records, historical_ex_date_verified=False,
            source_known_at=None, published_date=t["published_date"], source_reported_default=default,
            selected_holder_election=None, share_allocation_approximate=t["share_allocation_approximate"],
            stock_conversion_price=t["stock_conversion_price"], conditional_allocations=conditional,
            split_first_adjusted_session=split_session, split_multiplier=split["new_shares_per_old"],
            split_precedes_record_snapshot=split_before_record, required_operation_order=operations,
            separate_record_date_and_payment_date_lots=True, rights_survive_sale_of_parent=True,
            undelivered_share_rights_need_unit_rebasing=not split_before_record,
            cash_receivables_must_not_be_rebased=True, aggregate_issuer_share_totals_are_not_holder_allocations=True,
            fractional_fixings=dict(dividend=None, reverse_split=split.get("fractional_cash_price_usd")),
            status="conditional_schedule_not_admitted", execution_ready=False, actual_broker_received_at=None,
            source=pin(terms_path), split_source=pin(split_review_path), resolution_source=pin(resolution_path),
            blockers=(["Issuer event is absent from cached provider dividend inventory; entitlement boundary requires primary review"] if not records else []) +
                ["Holder election is not selected; general accounting approval does not select a branch"] +
                (["Reported holder shares are approximate; no exact allocation inferred from VWAP or issuer totals"] if t["share_allocation_approximate"] else []) +
                ["Record-date/ex-date/due-bill ownership and fractional fixing instructions require schedule admission"]))
    mac_review = json.loads(mac_review_path.read_text(encoding="utf-8"))
    mac = next(s for s in mac_review["sources"] if s["id"] == "mac")
    checked_file(Path.cwd(), mac["browser_evidence"])
    facts = mac["facts"]
    records = []
    for row in provider_rows:
        if row["instrument_id"] == "COHORT-2016-0288" and row["category"] == "cash_dividends":
            record = json.loads(row["record"], parse_float=str)
            if record.get("record_date") == facts["record_date"] and record.get("payable_date") == facts["payable_date"]:
                records.append(dict(event_id=row["event_id"], record=record))
    schedules.append(dict(event_id="mac_2020", instrument_id="COHORT-2016-0288", record_date=facts["record_date"],
        payable_date=facts["payable_date"], provider_event_ids=[r["event_id"] for r in records], provider_records=records,
        provider_event_missing=not records, source_reported_default="20_percent_cash_80_percent_stock",
        source_total_value=facts["total_dividend_value"], selected_holder_election=None,
        stock_conversion_price=None, required_operation_order=["snapshot_record_date_lots", "issue_election_rights"],
        historical_ex_date_verified=False, actual_broker_received_at=None, source_known_at=None,
        execution_ready=False, status="conditional_schedule_not_admitted", source=pin(mac_review_path),
        blockers=["Final stock conversion, holder allocation and fractional settlement terms unresolved",
                  "Conflicting provider rates are not ordinary cash entitlements"]))
    apply_holder_policy(schedules, holder_policy)
    return schedules

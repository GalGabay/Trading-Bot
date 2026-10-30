"""Conditional election outcomes from reported per-holder terms, not totals.

The caller must supply an election and, when relevant, a lottery outcome. No
choice is inferred from owner approval of general accounting defaults. Rounded
SLG allocations remain blocked rather than promoted to exact share counts.
"""

from fractions import Fraction


def resolve_election(terms,election,*,lottery_selected=None):
    if election not in {"no_election","cash","stock"}:
        raise ValueError("Explicit supported shareholder election required")
    result=dict(event_id=terms["id"],election=election,status="blocked_terms",cash_per_record_share=None,
        shares_per_record_share=None,execution_ready=False,actual_delivery_at=None,
        source=terms["source"],exact_broker_allocation_verified=False)
    if terms["share_allocation_approximate"]:
        return dict(result,reason="Reported share allocations are approximate; exact holder allocation unresolved")
    if election=="no_election":
        if terms.get("no_election_branch") is None:
            return dict(result,reason="Default election not established by reviewed source")
        branch=terms["no_election_branch"]
    elif election=="cash" and terms.get("cash_lottery"):
        if type(lottery_selected) is not bool:
            return dict(result,reason="Cash election requires an evidenced lottery outcome")
        branch="lottery_cash" if lottery_selected else "prorated_cash"
    else:
        branch="prorated_cash" if election=="cash" else "stock"
    allocation=terms["branches"][branch]
    cash=Fraction(allocation["cash"])
    price=Fraction(terms["stock_conversion_price"])
    if price<=0:
        raise ValueError("Stock conversion price must be positive")
    shares=Fraction(allocation["stock_value"])/price
    if cash<0 or shares<0:
        raise ValueError("Negative election allocation")
    return dict(result,status="conditional_reported_terms_resolved",branch=branch,cash_per_record_share=str(cash),
        shares_per_record_share=str(shares),record_date=terms["record_date"],payable_date=terms["payable_date"],
        published_date=terms["published_date"],historical_known_at=None,
        reason="Reported conditional terms only; election, record holdings, ordering, precision and availability still need schedule admission")

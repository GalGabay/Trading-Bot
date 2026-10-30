"""Fixed accounting replays on saved development observations, without signals.

Manual simulated holdings exercise mechanics; they are not a strategy backtest
or the approved 24-case comparison. No return percentages or investment claims
are calculated. No real/paper account or order interface exists here.
"""

from fractions import Fraction

import pandas as pd

from backtesting.claim_accounting import AccountingError, Quote
from backtesting.diagnostic_accounting import DiagnosticClock
from backtesting.diagnostic_bridge import DiagnosticLedger
from backtesting.universe import SplitAction


def audit_saved_accounting(inputs):
    clock = DiagnosticClock([dict(opens_at=s.opens_at.isoformat(), closes_at=s.closes_at.isoformat()) for s in inputs["sessions"]])
    sources = {key: frame.set_index("timestamp", verify_integrity=True) for key, frame in inputs["data"].items()}
    checks = []

    def check(condition, name):
        if not condition:
            raise AccountingError(f"Saved-input accounting replay failed: {name}")
        checks.append(dict(name=name, passed=True))

    def quote(key, index, field="open"):
        stamp = inputs["sessions"][index].opens_at.tz_convert("America/New_York").normalize().tz_convert("UTC")
        row = sources[key].loc[stamp]
        if row["volume"] <= 0:
            raise AccountingError("Saved accounting replay requires an actual positive-volume observation")
        at = clock.opens[index] if field == "open" else clock.closes[index]
        if field == "open":
            return Quote(key, at, str(row["open"]), str(row["open"]), str(row["open"]))
        return Quote(key, at, str(row["low"]), str(row["close"]), str(row["high"]))

    # Genuine split: source ratio and actual pre/post raw observations.
    split = next(a for a in inputs["schedules"]["actions"] if a["kind"] == "ordinary_split" and a["instrument_id"] == "COHORT-2016-0047")
    index = clock.opens.index(pd.Timestamp(split["effective_at"]).to_pydatetime())
    key = split["instrument_id"]
    ledger = DiagnosticLedger("10000", clock)
    ledger.buy("audit-apple", key, 3, quote(key,index-1).close, at=clock.opens[index-1])
    basis = sum(l.basis for l in ledger.lots)
    ratio = Fraction(split["share_multiplier"])
    ledger.split(SplitAction(split["event_id"],key,split["effective_at"][:10],ratio.numerator,ratio.denominator,
        split["effective_at"],"pinned diagnostic split mechanics"),at=clock.opens[index])
    check(ledger.quantity(key) == 12,"AAPL saved four-for-one split: exact whole units")
    check(sum(l.basis for l in ledger.lots) == basis,"AAPL split preserves exact total economic basis")
    check(ledger.mark({key:quote(key,index,"close")},at=clock.closes[index])["reconciliation_passed"],"AAPL split mark reconciles")

    # Fixed merger rights remain unspendable; no parent quote is invented after its interval ends.
    for event in inputs["schedules"]["material"]:
        if event["scenario"] != "base" or event["kind"] != "cash_merger":
            continue
        index = clock.opens.index(pd.Timestamp(event["modeled_accounting_at"]).to_pydatetime())
        key = event["parent_id"]
        ledger = DiagnosticLedger("10000",clock)
        ledger.buy("audit-parent",key,3,quote(key,index-1).close,at=clock.opens[index-1])
        cash = ledger.cash
        ledger.action(event,{},at=clock.opens[index])
        before = ledger.journal
        try:
            ledger.action(event,{},at=clock.opens[index])
        except AccountingError:
            check(ledger.journal==before,f"{event['event_id']}: duplicate action rejected without financial mutation")
        else:
            raise AccountingError("Duplicate saved action was accepted")
        check(ledger.quantity(key)==0 and ledger.cash==cash,f"{event['event_id']}: parent consumed without invented cash")
        expected=3*Fraction(event["cash_per_parent"])
        check(sum(c.amount for c in ledger.claims)==expected,f"{event['event_id']}: exact fixed consideration retained")
        check(ledger.mark({},at=clock.closes[index])["reconciliation_passed"],f"{event['event_id']}: mark needs no ended-parent quote")

    # Due-bill ownership, then parent sale before the delayed child delivery.
    for scenario in inputs["proposal"]["scenarios"]:
        event=next(e for e in inputs["schedules"]["material"] if e["event_id"]=="k_distribution" and e["scenario"]==scenario)
        index=clock.opens.index(pd.Timestamp(event["modeled_accounting_at"]).to_pydatetime())
        parent,child=event["parent_id"],event["share_legs"][0]["instrument_id"]
        ledger=DiagnosticLedger("10000",clock)
        ledger.buy("audit-cum-holder",parent,10,quote(parent,index-1).close,at=clock.opens[index-1])
        oldest=ledger.lots[0].acquired_at
        ledger.action(event,{key:quote(key,index) for key in (parent,child)},at=clock.opens[index],prior_stop="40")
        ledger.release_due(at=clock.opens[index])
        check(ledger.quantity(parent)==10,f"K/KLG {scenario}: parent quantity retained")
        check(ledger.mark({key:quote(key,index,"close") for key in (parent,child)},at=clock.closes[index])["reconciliation_passed"],
            f"K/KLG {scenario}: once-only recognition/release value reconciles")
        ledger.sell("audit-later-parent-sale",parent,10,quote(parent,index+1).close,at=clock.opens[index+1])
        last=index+5
        for i in range(index+1,last+1):
            ledger.release_due(at=clock.opens[i])
        pending=sum((c.units for c in ledger.claims if c.kind=="pending_shares" and c.instrument_id==child),Fraction(0))
        check(ledger.quantity(child)+pending==Fraction(5,2),f"K/KLG {scenario}: exact child right survives parent sale")
        check(ledger.quantity(child)==(0 if scenario=="no_credit" else 2),f"K/KLG {scenario}: whole shares follow modeled availability")
        check(all(l.acquired_at==oldest for l in ledger.lots),f"K/KLG {scenario}: delivered share age preserved")
        check(ledger.mark({child:quote(child,last,"close")},at=clock.closes[last])["reconciliation_passed"],
            f"K/KLG {scenario}: final whole/fractional value reconciles")

    # The reviewed FCX component is already included in a separate total record.
    components=[r for r in inputs["schedules"]["dividends"] if r["scenario"]=="base" and r.get("independent_entitlement") is False]
    for component in components:
        total=next(r for r in inputs["schedules"]["dividends"] if r["scenario"]=="base" and r["event_id"]==component["represented_by_event_id"])
        index=clock.opens.index(pd.Timestamp(total["economic_at"]).to_pydatetime())
        key=total["instrument_id"]
        ledger=DiagnosticLedger("10000",clock)
        ledger.buy("audit-div-holder",key,10,quote(key,index-1).close,at=clock.opens[index-1])
        ledger.dividend_right(component,at=clock.opens[index])
        ledger.dividend_right(total,at=clock.opens[index])
        expected=10*Fraction(total["cash_per_eligible_share"])
        check(len(ledger.claims)==1 and ledger.claims[0].amount==expected,"FCX reviewed total/component: one economic entitlement")
        cash=ledger.cash
        pay=clock.opens.index(pd.Timestamp(total["modeled_release_at"]).to_pydatetime())
        ledger.release_due(at=clock.opens[pay])
        check(ledger.cash==cash+expected and not ledger.claims,"FCX total paid once at modeled availability")
        check(ledger.mark({key:quote(key,pay,"close")},at=clock.closes[pay])["reconciliation_passed"],"FCX saved payment mark reconciles")
    return dict(purpose="fixed saved-data accounting mechanics, not strategy performance",checks=checks,
        checks_passed=len(checks),strategy_runs=0,broker_requests=0,orders=0,purchases_usd=0,
        simulated_holdings_only=True,strict_evidence_approved=False)

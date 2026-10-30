"""Proposed daily research timing and pending-rights accounting, offline only.

This component has no strategy/broker interface. It cannot authorize a run or
change a strict ownership schedule. Unknown values stay unknown; modeled
availability is never reported as actual broker receipt or historical known-at.
"""

from bisect import bisect_right
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from fractions import Fraction
import json
from zoneinfo import ZoneInfo

from backtesting.claim_accounting import AccountingError, Quote, exact, instant, number, text

SCENARIOS = ("base", "delayed_five_sessions", "no_credit")


class DiagnosticClock:
    def __init__(self, sessions):
        self.opens = tuple(instant(s["opens_at"]) for s in sessions)
        self.closes = tuple(instant(s["closes_at"]) for s in sessions)
        self.days = tuple(o.astimezone(ZoneInfo("America/New_York")).date() for o in self.opens)
        if (not self.opens or tuple(sorted(set(self.opens))) != self.opens or
                len(set(self.days)) != len(self.days) or any(o >= c for o,c in zip(self.opens,self.closes)) or
                any(not date(2016,1,1) <= d < date(2024,1,1) for d in self.days) or
                any(c.astimezone(ZoneInfo("America/New_York")).date() != d for d,c in zip(self.days,self.closes)) or
                any(c >= o for c,o in zip(self.closes,self.opens[1:]))):
            raise AccountingError("Require unique ordered saved development sessions")

    def open_on(self, day):
        day = date.fromisoformat(day)
        return self.opens[self.days.index(day)] if day in self.days else None

    def cash_release(self, payable_day, scenario):
        if scenario not in SCENARIOS:
            raise AccountingError("Unknown diagnostic cash scenario")
        if payable_day is None or scenario == "no_credit":
            return None
        day = date.fromisoformat(payable_day)
        index = bisect_right(self.days, day) + (5 if scenario == "delayed_five_sessions" else 0)
        return self.opens[index] if index < len(self.opens) else None

    def share_release(self, economic_at, first_regular_day, scenario):
        if scenario not in SCENARIOS:
            raise AccountingError("Unknown diagnostic share scenario")
        if scenario == "no_credit":
            return None
        economic_at = instant(economic_at)
        day = date.fromisoformat(first_regular_day)
        eligible = [o for d,o in zip(self.days,self.opens) if d >= day and o >= economic_at]
        index = 5 if scenario == "delayed_five_sessions" else 0
        return eligible[index] if index < len(eligible) else None


def plan_dividend(row, clock, scenario):
    """Plan a provider ordinary-dividend candidate, without certifying it.

    Date-only payment anchors release at a later saved session, never at ex-date
    merely because payment evidence is absent. Gross USD and post-split share
    basis are explicit diagnostic assumptions requiring owner review.
    """
    if row["category"] != "cash_dividends" or scenario not in SCENARIOS:
        raise AccountingError("Require a dividend candidate and named scenario")
    record = json.loads(row["record"],parse_float=str)
    ex_day = record.get("ex_date")
    at = clock.open_on(ex_day) if ex_day else None
    payable = record.get("payable_date")
    blockers = []
    if at is None:
        blockers.append("missing_or_nonsession_ex_date")
    if record.get("special") is not False or record.get("foreign") is not False:
        blockers.append("special_foreign_or_unclassified_distribution_requires_terms")
    if record.get("currency") not in (None,"USD"):
        blockers.append("non_usd_distribution_requires_fx_terms")
    try:
        amount = exact(number(str(record["rate"]), positive=True))
    except (KeyError, AccountingError):
        amount = None
        blockers.append("unknown_or_invalid_dividend_rate")
    if payable:
        pay_day = date.fromisoformat(payable)
        if ex_day and pay_day < date.fromisoformat(ex_day):
            blockers.append("payment_precedes_ex_date_possible_due_bill_or_bad_terms")
    release = None if blockers else clock.cash_release(payable, scenario)
    return dict(event_id=row["event_id"], instrument_id=row["instrument_id"], root_id=row["root_id"],
        category="diagnostic_ordinary_cash_candidate", scenario=scenario,
        source_key=row["source_key"], provider_record=record, cash_per_eligible_share=amount,
        economic_at=None if at is None else at.isoformat(),
        historical_known_at=None, modeled_observed_at=None if at is None else at.isoformat(),
        provider_payable_date=payable, modeled_release_at=None if release is None else release.isoformat(),
        status="blocked_terms" if blockers else "candidate_receivable_only" if release is None else "candidate_modeled_payment",
        blockers=blockers, entitlement_basis="assumed_prior_session_close_whole_shares",
        currency_basis="assumed_gross_usd_for_nonforeign_provider_records",
        share_basis="assumed_post_split_requires_same_boundary_review",
        actual_broker_received_at=None, independently_verified_entitlement=False,
        known_at_verified=False, execution_ready=False)


@dataclass(frozen=True)
class PendingRight:
    claim_id: str
    instrument_id: str
    kind: str  # cash or shares; fractional shares remain share claims
    units: Fraction
    cash_amount: Fraction | None
    created_at: str | datetime
    release_at: str | datetime | None
    source: str

    def __post_init__(self):
        text(self.claim_id,"Claim ID")
        text(self.instrument_id,"Claim instrument")
        text(self.source,"Claim source/assumption")
        if self.kind not in {"cash","shares"}:
            raise AccountingError("Unknown diagnostic claim kind")
        object.__setattr__(self,"units",number(self.units,positive=True))
        if self.cash_amount is not None:
            object.__setattr__(self,"cash_amount",number(self.cash_amount))
        if self.kind == "shares" and self.cash_amount is not None:
            raise AccountingError("Share claims cannot invent a cash fixing")
        object.__setattr__(self,"created_at",instant(self.created_at))
        if self.release_at is not None:
            release = instant(self.release_at)
            if release < self.created_at:
                raise AccountingError("Availability cannot precede the right")
            object.__setattr__(self,"release_at",release)


class DiagnosticRightsBook:
    """Pending rights only; Step 2 must atomically bridge releases to its ledger.

    No buy/sell methods or initial account cash exist here. released_cash and
    delivered_shares are cumulative transfer records, not portfolio equity or
    account balances. Active claims are marked separately to avoid counting a
    released right twice. No automatic fractional cash conversion is supported.
    """

    def __init__(self, clock):
        self.clock = clock
        self._pending, self._seen = {}, set()
        self.released_cash = Fraction(0)
        self.delivered_shares = {}
        self._journal = []
        self._at = None

    @property
    def pending(self):
        return tuple(self._pending.values())

    @property
    def journal(self):
        return deepcopy(self._journal)

    def _time(self, at):
        at = instant(at)
        if not datetime(2016,1,1,tzinfo=timezone.utc) <= at < datetime(2024,1,1,tzinfo=timezone.utc):
            raise AccountingError("Diagnostic rights are restricted to development dates")
        if self._at is not None and at < self._at:
            raise AccountingError("Diagnostic accounting clock cannot move backwards")
        return at

    def recognize(self, right):
        if not isinstance(right, PendingRight) or right.claim_id in self._seen:
            raise AccountingError("Require an explicit unique pending right")
        at = self._time(right.created_at)
        if right.release_at is not None and right.release_at not in self.clock.opens:
            raise AccountingError("Modeled availability requires an exact saved open")
        self._pending[right.claim_id] = right
        self._seen.add(right.claim_id)
        self._at = at
        self._journal.append(dict(kind="diagnostic_right", claim_id=right.claim_id,
            at=at.isoformat(), units=exact(right.units), modeled_release_at=None if right.release_at is None else right.release_at.isoformat(),
            actual_broker_received_at=None, independently_verified_entitlement=False))

    def release(self, claim_id, *, at):
        at = self._time(at)
        right = self._pending.get(claim_id)
        if right is None or right.release_at is None or at < right.release_at or at not in self.clock.opens:
            raise AccountingError("Right is absent, unscheduled, or not available at this saved open")
        if right.kind == "cash":
            if right.cash_amount is None:
                raise AccountingError("Unknown cash cannot be released as zero")
            amount, whole, fraction = right.cash_amount, 0, Fraction(0)
        else:
            whole = right.units.numerator // right.units.denominator
            fraction, amount = right.units-whole, Fraction(0)
            if not whole:
                raise AccountingError("A fractional claim needs explicit later fixing/payment terms")
        # Complete all validation before any mutation.
        self._pending.pop(claim_id)
        if fraction:
            self._pending[claim_id] = replace(right,units=fraction,release_at=None)
        self.released_cash += amount
        if whole:
            self.delivered_shares[right.instrument_id] = self.delivered_shares.get(right.instrument_id,0)+whole
        self._at = at
        record = dict(kind="diagnostic_release",claim_id=claim_id,at=at.isoformat(),
            cash=exact(amount),whole_shares=whole,remaining_fraction=exact(fraction),
            actual_broker_received_at=None,availability_is_assumed=True)
        self._journal.append(record)
        return dict(record)

    def mark(self, *, at, quotes):
        """Value active rights only, with exact-current-session close quotes.

        Missing share quotes or unknown cash make the total incomplete. The
        caller must not score returns/drawdown from an incomplete valuation.
        Released transfers are excluded; the integrating ledger must own them.
        """
        at = self._time(at)
        if at not in self.clock.closes:
            raise AccountingError("Pending-right marks require an exact saved close")
        known, unknown, rows = Fraction(0), [], []
        for right in self.pending:
            value = right.cash_amount
            if right.kind == "shares":
                q = quotes.get(right.instrument_id)
                value = right.units*q.close if isinstance(q,Quote) and q.instrument_id==right.instrument_id and q.timestamp==at else None
            if value is None:
                unknown.append(right.claim_id)
            else:
                known += value
            rows.append(dict(claim_id=right.claim_id,value=None if value is None else exact(value)))
        self._at = at
        return dict(complete=not unknown, pending_right_value=None if unknown else exact(known),
            known_component_value=exact(known),unvalued_claims=unknown,claims=rows,
            spendable_contribution="0",valuation_policy="fixed_cash_face_and_current_share_close_assumptions",
            strict_evidence_approved=False)

"""Explicit corporate-action bridge for the existing daily portfolio simulator.

No account, credentials or HTTP access. New research mode requires a reviewed
schedule, raw dated identities and exact exchange opens. Old runs use neither
this runtime nor its accounting/reporting conventions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
import json
from math import isclose, isfinite
from pathlib import Path

import pandas as pd

from app.data.market_calendar import TradingSession
from backtesting.claim_accounting import ClaimLedger, OwnershipEvent, Quote, ShareLeg, instant, number, text
from backtesting.holding_policy import HoldingEntry
from backtesting.universe import (
    OWNERSHIP_SCOPE, CashDividend, CashOutcome, HistoricalUniverse, ListingPeriod,
    SplitAction, UniverseDataError,
)


@dataclass(frozen=True)
class ReviewedOwnership:
    event: OwnershipEvent
    eligibility_policy: str
    eligibility_source: str
    eligibility_known_at: str
    delivery_source: str | None = None
    delivered_at: str | None = None
    delivery_known_at: str | None = None
    reviewed_for_research: bool = False

    def __post_init__(self):
        if not isinstance(self.event, OwnershipEvent) or not self.event.terms_complete:
            raise UniverseDataError("Ownership terms require explicit completed review")
        if self.event.kind == "split":
            raise UniverseDataError("Declare genuine splits in the universe split records")
        if self.reviewed_for_research is not True or self.eligibility_policy != "prior_close_holders_confirmed":
            raise UniverseDataError("Prior-close ownership entitlement must be reviewed; record-date/due-bill gaps cannot be inferred")
        text(self.eligibility_source, "Entitlement evidence")
        if instant(self.eligibility_known_at) > self.event.effective_at:
            raise UniverseDataError("Entitlement evidence was not known at the effective open")
        object.__setattr__(self, "eligibility_known_at", instant(self.eligibility_known_at).isoformat())
        if self.event.known_at > self.event.effective_at:
            raise UniverseDataError("Ownership terms were not known at the effective open")
        if self.event.shares:
            text(self.delivery_source, "Whole-share delivery evidence")
            if instant(self.delivered_at) != self.event.effective_at or instant(self.delivery_known_at) > self.event.effective_at:
                raise UniverseDataError("Whole-share delivery must be confirmed at the effective open; delayed delivery is unsupported")
            object.__setattr__(self, "delivered_at", instant(self.delivered_at).isoformat())
            object.__setattr__(self, "delivery_known_at", instant(self.delivery_known_at).isoformat())
        elif any(value is not None for value in (self.delivery_source, self.delivered_at, self.delivery_known_at)):
            raise UniverseDataError("Cash-only events cannot invent share delivery evidence")


@dataclass(frozen=True)
class CashInstruction:
    instruction_id: str
    claim_id: str
    at: str
    known_at: str
    amount: str
    source: str
    amount_basis: str = "fixed_total"
    expected_fractional_units: str | None = None

    def __post_init__(self):
        for name in ("instruction_id", "claim_id", "source"):
            text(getattr(self, name), name)
        if self.amount != "outstanding_claim":
            object.__setattr__(self, "amount", str(number(self.amount)))
        if self.amount_basis not in {"fixed_total", "per_fractional_share"}:
            raise UniverseDataError("Cash amount basis must be fixed_total or per_fractional_share")
        if self.expected_fractional_units is not None:
            units = number(self.expected_fractional_units, positive=True)
            if units >= 1:
                raise UniverseDataError("A fractional allocation must identify units strictly below one share")
            object.__setattr__(self, "expected_fractional_units", str(units))
        if instant(self.known_at) > instant(self.at):
            raise UniverseDataError("Cash allocation/availability must already be known at its configured instant")
        object.__setattr__(self, "at", instant(self.at).isoformat())
        object.__setattr__(self, "known_at", instant(self.known_at).isoformat())


class OwnershipSchedule:
    """Separate versioned schedule; no unreviewed provider event is promoted."""

    def __init__(self, *, entry_instrument_ids, events=(), payments=(), fixings=()):
        if not isinstance(entry_instrument_ids, (tuple, list)):
            raise UniverseDataError("Explicit research entry IDs are required")
        if len(set(entry_instrument_ids)) != len(entry_instrument_ids):
            raise UniverseDataError("Duplicate research entry ID")
        for key in entry_instrument_ids:
            text(key, "Research entry identity")
            if key != key.strip().upper():
                raise UniverseDataError("Research entry identities must be uppercase stable IDs")
        self.entry_instrument_ids = frozenset(entry_instrument_ids)
        self.manifest_sha256 = None
        self.events, self.payments, self.fixings = tuple(events), tuple(payments), tuple(fixings)
        if any(not isinstance(e, ReviewedOwnership) for e in self.events):
            raise UniverseDataError("Ownership events need ReviewedOwnership records")
        if any(not isinstance(i, CashInstruction) for i in (*self.payments, *self.fixings)):
            raise UniverseDataError("Fixings/payments require explicit cash instructions")
        ids = [e.event.event_id for e in self.events]
        instructions = [i.instruction_id for i in (*self.payments, *self.fixings)]
        if any(key.startswith("fill-") for key in instructions):
            raise UniverseDataError("The fill- instruction prefix is reserved for simulated fills")
        if len(set(ids)) != len(ids) or len(set(instructions)) != len(instructions):
            raise UniverseDataError("Duplicate ownership event or cash instruction")
        for values in (self.payments, self.fixings):
            if len({i.claim_id for i in values}) != len(values):
                raise UniverseDataError("Multiple allocations/payments for one claim require an installment adapter")

    def bind(self, universe):
        if universe.action_scope != OWNERSHIP_SCOPE:
            raise UniverseDataError("Ownership accounting needs its explicit universe action scope")
        if not self.entry_instrument_ids <= universe.instrument_ids:
            raise UniverseDataError("Research entry IDs are outside the declared historical universe")
        opens = {instant(s.opens_at): i for i, s in enumerate(universe.sessions)}
        if any(s.opens_at >= pd.Timestamp("2024-01-01", tz="UTC") for s in universe.sessions):
            raise UniverseDataError("Ownership development mode cannot open the reserved holdout")
        legacy_ids = {a.event_id for a in (*universe.splits, *universe.dividends, *universe.cash_outcomes)}
        if legacy_ids & {e.event.event_id for e in self.events}:
            raise UniverseDataError("Corporate-action IDs must be unique across all event kinds")
        possible_claims = {f"dividend:{d.event_id}": (instant(universe._by_day[pd.Timestamp(d.ex_session).date()].opens_at), "cash")
                           for d in universe.dividends}
        occupied = set()
        for reviewed in self.events:
            event = reviewed.event
            if event.effective_at not in opens:
                raise UniverseDataError("Ownership recognition must be an exact saved exchange open")
            timestamp = universe.dates.iloc[opens[event.effective_at]]
            affected = {event.instrument_id, *(leg.instrument_id for leg in event.shares)}
            if not affected <= universe.instrument_ids:
                raise UniverseDataError("Parent and every successor/child need distinct declared stable identities")
            for key in affected:
                pair = (event.effective_at, key)
                if pair in occupied:
                    raise UniverseDataError("Overlapping same-open ownership events need consolidated reviewed terms")
                occupied.add(pair)
            if event.kind == "exchange":
                if any(a.instrument_id == event.instrument_id for a in universe.cash_outcomes):
                    raise UniverseDataError("Exchange cash rights must use claim payments, not a second immediate-cash outcome")
                periods = [p for p in universe.listings if p.instrument_id == event.instrument_id]
                if any(p.end_session_exclusive is None or p.end_session_exclusive > timestamp.date().isoformat() for p in periods):
                    raise UniverseDataError("An exchange requires a documented ended parent identity")
            elif universe.listing_at(event.instrument_id, timestamp) is None:
                raise UniverseDataError("Retained parent must have a dated listing at the event open")
            for leg in event.shares:
                if universe.listing_at(leg.instrument_id, timestamp) is None:
                    raise UniverseDataError("Successor/child must have a dated listing at delivery")
            index = int(event.kind != "exchange")
            if event.cash_per_parent:
                possible_claims[f"action:{event.event_id}:{index}"] = (event.effective_at, "cash")
                index += 1
            for _ in event.shares:
                possible_claims[f"action:{event.event_id}:{index}"] = (event.effective_at, "fraction")
                index += 1
        for action in (*universe.splits, *universe.cash_outcomes, *universe.dividends):
            effective = action.ex_session if isinstance(action, CashDividend) else action.effective_session
            at = instant(universe._by_day[pd.Timestamp(effective).date()].opens_at)
            if (at, action.instrument_id) in occupied:
                raise UniverseDataError("Same-open split/dividend/terminal and ownership terms need explicit consolidation")
            if isinstance(action, SplitAction):
                possible_claims[f"action:{action.event_id}:0"] = (at, "fraction")
        fixing_by_claim = {i.claim_id: i for i in self.fixings}
        for kind, instructions in (("fixing", self.fixings), ("payment", self.payments)):
            for item in instructions:
                at = instant(item.at)
                if at not in opens or item.claim_id not in possible_claims:
                    raise UniverseDataError("Cash instruction needs a declared possible claim and an exact saved open")
                created, claim_kind = possible_claims[item.claim_id]
                if at < created:
                    raise UniverseDataError("Cash instruction precedes the ownership right")
                if kind == "fixing" and claim_kind != "fraction":
                    raise UniverseDataError("Only a fractional right can receive a cash fixing")
                if kind == "fixing" and item.amount == "outstanding_claim":
                    raise UniverseDataError("Fractional fixing needs an explicit reviewed cash allocation")
                if kind == "fixing":
                    if item.amount_basis == "fixed_total" and item.expected_fractional_units is None:
                        raise UniverseDataError("A total fractional payout needs its reviewed eligible units; use a sourced per-unit rate for varying simulated holdings")
                    if item.amount_basis == "per_fractional_share" and item.expected_fractional_units is not None:
                        raise UniverseDataError("A per-unit allocation cannot also assert holder-specific total units")
                if kind == "payment" and (item.amount_basis != "fixed_total" or item.expected_fractional_units is not None):
                    raise UniverseDataError("Payments settle an exact fixed claim balance, not an unfixed per-unit rate")
                if kind == "payment" and claim_kind == "fraction":
                    fixing = fixing_by_claim.get(item.claim_id)
                    if (fixing is None or instant(fixing.at) > at
                            or (item.amount != "outstanding_claim" and fixing.amount_basis == "fixed_total"
                                and number(fixing.amount) != number(item.amount))):
                        raise UniverseDataError("Fractional payment requires a preceding matching fixed allocation")

    def reset_indices(self, universe, instrument_id):
        by_open = {instant(s.opens_at): i for i, s in enumerate(universe.sessions)}
        return {by_open[r.event.effective_at] for r in self.events
                if instrument_id in {r.event.instrument_id, *(leg.instrument_id for leg in r.event.shares)}}

    def metadata(self):
        events = []
        for reviewed in self.events:
            value = asdict(reviewed)
            event = reviewed.event
            value["event"] = dict(event_id=event.event_id, instrument_id=event.instrument_id, kind=event.kind,
                                  effective_at=event.effective_at.isoformat(), known_at=event.known_at.isoformat(),
                                  source=event.source, cash_per_parent=str(event.cash_per_parent),
                                  shares=[dict(instrument_id=s.instrument_id, shares_per_parent=str(s.shares_per_parent)) for s in event.shares],
                                  terms_complete=event.terms_complete)
            events.append(value)
        return dict(schema_version=1, entry_instrument_ids=sorted(self.entry_instrument_ids), events=events,
                    payments=[asdict(i) for i in self.payments], fixings=[asdict(i) for i in self.fixings])

    @classmethod
    def from_dict(cls, value):
        if set(value) != {"schema_version", "entry_instrument_ids", "events", "payments", "fixings"} or type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise UniverseDataError("Unsupported or incomplete ownership schedule")
        events = []
        for item in value["events"]:
            fields = dict(item["event"])
            fields["shares"] = tuple(ShareLeg(**leg) for leg in fields["shares"])
            events.append(ReviewedOwnership(**{**item, "event": OwnershipEvent(**fields)}))
        return cls(entry_instrument_ids=value["entry_instrument_ids"], events=events,
                   payments=[CashInstruction(**i) for i in value["payments"]],
                   fixings=[CashInstruction(**i) for i in value["fixings"]])

    @classmethod
    def load(cls, path):
        payload = Path(path).read_bytes()
        schedule = cls.from_dict(json.loads(payload.decode("utf-8")))
        schedule.manifest_sha256 = hashlib.sha256(payload).hexdigest()
        return schedule


class OwnershipRuntime:
    """Ledger authority for one run, with open-only actions and close reports."""

    def __init__(self, schedule, universe, initial_cash):
        schedule.bind(universe)
        self.schedule, self.universe = schedule, universe
        self.ledger = ClaimLedger(str(initial_cash))
        self.session_indices = {instant(s.opens_at): i for i, s in enumerate(universe.sessions)}
        self.days, self.fill_details, self.marks, self.risk_rows = [], [], [], []
        self._last_equity = self._close_peak = self._upper_peak = float(initial_cash)

    def positions(self):
        return {key: self.ledger.quantity(key) for key in sorted({lot.instrument_id for lot in self.ledger.lots})}

    def entries(self):
        return {key: HoldingEntry(min(self.session_indices[lot.acquired_at] for lot in self.ledger.lots if lot.instrument_id == key),
                                  quantity, float(sum(lot.basis for lot in self.ledger.lots if lot.instrument_id == key)))
                for key, quantity in self.positions().items()}

    def fraction_units(self):
        values = {}
        for claim in self.ledger.claims:
            if claim.kind == "fractional_shares":
                values[claim.instrument_id] = values.get(claim.instrument_id, Fraction(0)) + claim.units
        return values

    def position_count(self):
        return len(set(self.positions()) | set(self.fraction_units()))

    def claim_values(self, prices):
        fixed = sum((c.amount for c in self.ledger.claims if c.kind == "cash"), Fraction(0))
        dividend = sum((c.amount for c in self.ledger.claims if c.kind == "cash" and c.claim_id.startswith("dividend:")), Fraction(0))
        try:
            fractional = sum((units * number(str(prices[key]), positive=True) for key, units in self.fraction_units().items()), Fraction(0))
        except KeyError as exc:
            raise UniverseDataError("Fractional ownership lacks an actual tradable session quote; no stale mark") from exc
        return float(fixed), float(fractional), float(dividend)

    def _equity_open(self):
        fixed, fraction, _ = self.claim_values(self._opens)
        if set(self.positions()) - set(self._opens):
            raise UniverseDataError("Held whole shares lack a positive-volume session quote; no stale mark or assumed recovery")
        return float(self.ledger.cash) + fixed + fraction + sum(qty * self._opens[key] for key, qty in self.positions().items())

    def begin(self, index, bars):
        self._index, self._bars = index, bars
        self._at = instant(self.universe.sessions[index].opens_at)
        self._opens = {key: float(row["open"]) for key, row in bars.items()}
        self._needed = set(self.positions()) | set(self.fraction_units())
        self._opening_marks, self._touches, self._intraday = [], {}, None
        self.transitions = []
        quotes = {key: Quote(key, self._at, str(row["open"]), str(row["open"]), str(row["open"])) for key, row in bars.items()}
        timestamp = self.universe.dates.iloc[index]
        for split in self.universe.splits_at(timestamp):
            event = OwnershipEvent(split.event_id, split.instrument_id, "split", self._at, split.known_at,
                                   split.source, "0", (ShareLeg(split.instrument_id, f"{split.new_shares}/{split.old_shares}"),), True)
            self._needed.add(split.instrument_id)
            self.ledger.recognize(event, quotes, at=self._at, reference="open")
        for reviewed in self.schedule.events:
            event = reviewed.event
            if event.effective_at != self._at:
                continue
            affected = {event.instrument_id, *(leg.instrument_id for leg in event.shares)}
            self._needed |= affected
            quantity = self.ledger.quantity(event.instrument_id)
            self.ledger.recognize(event, quotes, at=self._at, reference="open")
            record = self.ledger.journal[-1]
            self.transitions.append(dict(parent=event.instrument_id, affected=sorted(affected), old_quantity=quantity,
                                         component_value=float(Fraction(record.get("component_value", "0")))))
        for dividend in self.universe.dividends_at(timestamp):
            self.ledger.dividend(dividend.event_id, dividend.instrument_id, str(dividend.cash_per_share),
                                 known_at=dividend.known_at, at=self._at, source=dividend.source)
        for kind, instructions in (("fix", self.schedule.fixings), ("pay", self.schedule.payments)):
            for item in instructions:
                if instant(item.at) != self._at:
                    continue
                # A flat-start run may have had no entitlement or an exact whole
                # conversion. This is distinct from forgiving a duplicate payment.
                if item.claim_id not in {c.claim_id for c in self.ledger.claims}:
                    continue
                if kind == "fix":
                    claim = next(c for c in self.ledger.claims if c.claim_id == item.claim_id)
                    if item.amount_basis == "fixed_total" and claim.units != number(item.expected_fractional_units):
                        raise UniverseDataError("Holder-specific fractional payout does not match simulated eligible units")
                    amount = number(item.amount) * claim.units if item.amount_basis == "per_fractional_share" else number(item.amount)
                    self.ledger.fix_fraction(item.instruction_id, item.claim_id, amount,
                                             known_at=item.known_at, at=self._at, source=item.source)
                else:
                    claim = next(c for c in self.ledger.claims if c.claim_id == item.claim_id)
                    amount = str(claim.amount) if item.amount == "outstanding_claim" else item.amount
                    self.ledger.pay(item.instruction_id, item.claim_id, amount, available_at=item.at,
                                    known_at=item.known_at, at=self._at, source=item.source)
        for outcome in self.universe.outcomes_at(timestamp):
            self._needed.add(outcome.instrument_id)
            self.ledger.terminal_cash(outcome.event_id, outcome.instrument_id, str(outcome.cash_per_share),
                                      known_at=outcome.known_at, at=self._at, source=outcome.source)
            self.transitions.append(dict(parent=outcome.instrument_id, affected=[outcome.instrument_id],
                                         old_quantity=0, component_value=0))
        self._opening_marks.append(self._equity_open())

    def record_fill(self, fill, *, phase="open"):
        key, qty = fill.symbol, fill.quantity
        self._needed.add(key)
        if key not in self._bars or type(qty) is not int or qty <= 0:
            raise UniverseDataError("Fill requires a positive whole quantity and actual session candle")
        if not all(isfinite(value) for value in (fill.fill_price, fill.commission, fill.reference_open)):
            raise UniverseDataError("Fill contains nonfinite values")
        if not isclose(fill.reference_open, self._opens[key], abs_tol=1e-10):
            raise UniverseDataError("Fill reference differs from its actual session open")
        if phase not in {"open", "intraday"}:
            raise UniverseDataError("Unknown fill accounting phase")
        touch = phase == "intraday"
        if touch and (fill.side.value != "SELL" or not fill.signal_reason.startswith("PROTECTIVE_STOP_TOUCH")):
            raise UniverseDataError("Only protective sells may use intraday-touch accounting")
        if not touch and self._intraday is not None:
            raise UniverseDataError("Opening fills cannot follow intraday exits")
        if touch and (self._intraday is None or key in self._touches):
            raise UniverseDataError("Intraday touch must follow opening-state capture and be unique")
        if fill.side.value == "BUY":
            if key not in self.schedule.entry_instrument_ids or self.ledger.quantity(key) or key in self.fraction_units():
                raise UniverseDataError("Buy violates explicit research eligibility or whole-position entry policy")
            self.ledger.buy(f"fill-{len(self.fill_details)}", key, qty, str(fill.fill_price), at=self._at, fee=str(fill.commission))
            detail = dict(side="BUY", instrument_id=key)
        elif fill.side.value == "SELL":
            if qty != self.ledger.quantity(key):
                raise UniverseDataError("Only whole-position sell fills are supported by this strategy adapter")
            oldest = min(lot.acquired_at for lot in self.ledger.lots if lot.instrument_id == key)
            self.ledger.sell(f"fill-{len(self.fill_details)}", key, qty, str(fill.fill_price), at=self._at, fee=str(fill.commission))
            row = self.ledger.journal[-1]
            detail = dict(side="SELL", instrument_id=key, profit=float(Fraction(row["proceeds"]) - Fraction(row["basis"])),
                          holding_days=(self._at - oldest).total_seconds() / 86400)
        else:
            raise UniverseDataError("Unsupported fill side")
        self.fill_details.append({**detail, "phase": phase})
        if touch:
            self._touches[key] = qty * fill.fill_price - fill.commission
        else:
            self._opening_marks.append(self._equity_open())

    def capture_intraday(self):
        self._intraday = dict(cash=float(self.ledger.cash), positions=self.positions(),
                              fractions=self.fraction_units(), fixed=self.claim_values(self._opens)[0])

    def finish(self):
        if self._intraday is None:
            raise UniverseDataError("Missing pre-intraday holdings snapshot")
        close_at = instant(self.universe.sessions[self._index].closes_at)
        required = set(self.positions()) | set(self.fraction_units())
        quotes = {key: Quote(key, close_at, str(self._bars[key]["low"]), str(self._bars[key]["close"]), str(self._bars[key]["high"]))
                  for key in required}
        mark = self.ledger.mark(quotes, at=close_at)
        lower = upper = self._intraday["cash"] + self._intraday["fixed"]
        for key, qty in self._intraday["positions"].items():
            lo, hi = qty * float(self._bars[key]["low"]), qty * float(self._bars[key]["high"])
            if key in self._touches:
                lo, hi = min(lo, self._touches[key]), max(hi, self._touches[key])
            lower, upper = lower + lo, upper + hi
        for key, units in self._intraday["fractions"].items():
            lower += float(units) * float(self._bars[key]["low"])
            upper += float(units) * float(self._bars[key]["high"])
        equity = float(Fraction(mark["equity"]))
        lower, upper = min(lower, equity, *self._opening_marks), max(upper, equity, *self._opening_marks)
        if lower <= 0:
            raise UniverseDataError("Ownership-aware conservative equity bound is nonpositive")
        self._close_peak, self._upper_peak = max(self._close_peak, equity), max(self._upper_peak, upper)
        self.risk_rows.append(dict(timestamp=self.universe.dates.iloc[self._index].isoformat(), equity_at_close=equity,
                                   cash_at_close=float(self.ledger.cash), equity_lower_envelope=lower, equity_upper_envelope=upper,
                                   observed_closing_drawdown=equity / self._close_peak - 1,
                                   conservative_drawdown_bound=lower / self._upper_peak - 1,
                                   conservative_daily_return_bound=lower / self._last_equity - 1,
                                   model_open_equity_minimum=min(self._opening_marks)))
        self._last_equity = equity
        self.marks.append(mark)
        self.days.append(dict(index=self._index, quotes={key: {field: str(self._bars[key][field]) for field in ("open", "high", "low", "close")}
                                                       for key in sorted(self._needed | required) if key in self._bars}))
        return mark

    def report(self):
        return dict(version=1, initial_cash=str(self.ledger.initial_cash), schedule=self.schedule.metadata(),
                    schedule_source_sha256=self.schedule.manifest_sha256,
                    inherited_stop_policy="opening_component_value_proportional_prior_floor_v1",
                    feature_history_policy="reset_affected_ids_then_require_200_continuous_sessions_for_new_entries",
                    ordinary_dividend_cash_policy="explicit_cash_availability_instruction",
                    holding_age_policy="oldest_parent_and_existing_destination_lots",
                    universe={**self.universe.metadata(), "sessions": [dict(opens_at=s.opens_at.isoformat(), closes_at=s.closes_at.isoformat())
                                                                       for s in self.universe.sessions]},
                    journal=self.ledger.journal, marks=self.marks, days=self.days,
                    fill_details=self.fill_details, daily_risk_envelopes=self.risk_rows,
                    limitations=["Research model, not paper/live execution",
                                 "Open-value economic basis and inherited stop rebasing are explicit model conventions",
                                 "Fixed rights are nominal USD; fractional ownership cannot be stopped or spent",
                                 "Daily risk envelopes are conservative bounds, not observed intraday equity"],
                    market_wide_performance_ready=False)


def replay_accounting(report, fills, curves, *, datasets=None):
    """Recompute the financial journal and risk bounds, without strategy calls.

    Embedded observations suffice for internal financial reconciliation. When
    datasets are supplied, every used quote is also checked against external
    actual raw bars and the dated ticker identity. This does not reselect a
    strategy or certify the human-reviewed evidence declarations.
    """
    from app.strategy.base import SignalAction
    from backtesting.engine import SimulatedFill

    if type(report.get("version")) is not int or report["version"] != 1:
        raise UniverseDataError("Unsupported ownership-accounting report")
    meta = report["universe"]
    universe = HistoricalUniverse(
        sessions=[TradingSession(pd.Timestamp(s["opens_at"]), pd.Timestamp(s["closes_at"])) for s in meta["sessions"]],
        listings=[ListingPeriod(**p) for p in meta["listings"]],
        cash_outcomes=[CashOutcome(**a) for a in meta["cash_outcomes"]],
        splits=[SplitAction(**a) for a in meta["splits"]], dividends=[CashDividend(**a) for a in meta["dividends"]],
        currency=meta["currency"], price_basis="raw", action_scope=meta["price_and_action_scope"],
    )
    universe.manifest_sha256 = meta["manifest_sha256"]
    schedule = OwnershipSchedule.from_dict(report["schedule"])
    schedule.manifest_sha256 = report["schedule_source_sha256"]
    runtime = OwnershipRuntime(schedule, universe, report["initial_cash"])
    days, details = report["days"], report["fill_details"]
    indices = [d["index"] for d in days]
    if (not indices or any(type(i) is not int for i in indices)
            or indices != list(range(indices[0], indices[-1] + 1))
            or indices[0] < 0 or indices[-1] >= len(universe.sessions)
            or len(curves) != len(days) or len(details) != len(fills)):
        raise UniverseDataError("Report sessions or fill phases are incomplete, duplicated or out of order")
    frames = {}
    if datasets is not None:
        if set(datasets) != universe.instrument_ids:
            raise UniverseDataError("External price verification must retain every declared identity")
        for key, frame in datasets.items():
            frame = frame.copy()
            frame["timestamp"] = pd.to_datetime([instant(value) for value in frame["timestamp"]], utc=True)
            if (frame["timestamp"] >= pd.Timestamp("2024-01-01", tz="UTC")).any():
                raise UniverseDataError("Reserved prices cannot enter development ownership diagnostics")
            frames[key] = universe.prepare(key, frame).set_index("timestamp", verify_integrity=True)
    offset = 0
    for day, point in zip(days, curves):
        index = day["index"]
        timestamp = universe.dates.iloc[index]
        if pd.Timestamp(point["timestamp"]) != timestamp:
            raise UniverseDataError("Accounting sessions and saved equity dates differ")
        bars = day["quotes"]
        if not set(bars) <= universe.instrument_ids:
            raise UniverseDataError("Quote identity outside the historical universe")
        for key, row in bars.items():
            if universe.listing_at(key, timestamp) is None:
                raise UniverseDataError("Recorded price lies outside the documented identity/listing lifetime")
            values = {name: number(row[name], positive=True) for name in ("open", "high", "low", "close")}
            if not values["low"] <= min(values["open"], values["close"]) <= max(values["open"], values["close"]) <= values["high"]:
                raise UniverseDataError("Impossible recorded OHLC values")
            if datasets is not None:
                if timestamp not in frames[key].index:
                    raise UniverseDataError("A recorded quote has no actual external bar")
                actual = frames[key].loc[timestamp]
                listing = universe.listing_at(key, timestamp)
                volume = float(actual["volume"])
                if listing is None or actual["symbol"] != key or not isfinite(volume) or volume <= 0:
                    raise UniverseDataError("External quote lacks a matching dated alias or tradable volume")
                if any(number(str(actual[name]), positive=True) != values[name] for name in values):
                    raise UniverseDataError("Recorded OHLC differs from actual external data")
        runtime.begin(index, bars)
        while offset < len(fills) and pd.Timestamp(fills[offset]["timestamp"]) == timestamp:
            value, detail = fills[offset], details[offset]
            phase = detail["phase"]
            if phase == "intraday" and runtime._intraday is None:
                runtime.capture_intraday()
            key = value["symbol"]
            if key not in bars:
                raise UniverseDataError("Fill has no actual session quote")
            protected = value["signal_reason"].startswith("PROTECTIVE_STOP_")
            signal_at = pd.Timestamp(value["signal_timestamp"])
            if signal_at.tzinfo is None or (not protected and signal_at >= timestamp) or (protected and signal_at > universe.sessions[index].opens_at):
                raise UniverseDataError("Fill uses unavailable/future signal information")
            price = number(str(value["fill_price"]), positive=True)
            opening = number(bars[key]["open"], positive=True)
            if phase == "open" and ((value["side"] == "BUY" and price < opening) or (value["side"] == "SELL" and price > opening)):
                raise UniverseDataError("Opening fill has favorable rather than adverse execution costs")
            if phase == "intraday" and price > number(bars[key]["high"], positive=True):
                raise UniverseDataError("Intraday sell exceeds the actual high")
            fill = SimulatedFill(timestamp=timestamp, symbol=key, side=SignalAction(value["side"]), quantity=value["quantity"],
                                 reference_open=value["reference_open"], fill_price=value["fill_price"], commission=value["commission"],
                                 signal_timestamp=signal_at, signal_reason=value["signal_reason"])
            runtime.record_fill(fill, phase=phase)
            offset += 1
        if runtime._intraday is None:
            runtime.capture_intraday()
        mark = runtime.finish()
        comparisons = {"equity": Fraction(mark["equity"]), "cash": runtime.ledger.cash,
                       "exposure": Fraction(mark["gross_exposure"])}
        for field, expected in comparisons.items():
            if field not in point or not isclose(float(expected), point[field], rel_tol=1e-11, abs_tol=1e-6):
                raise UniverseDataError(f"Ownership ledger differs from saved {field}")
        fixed, fraction, dividend = runtime.claim_values({key: row["close"] for key, row in bars.items()})
        for field, expected in {"dividend_receivable": dividend, "ownership_cash_receivable": fixed - dividend,
                                "fractional_claim_value": fraction}.items():
            if field not in point or not isclose(expected, point[field], abs_tol=1e-6):
                raise UniverseDataError(f"Ownership ledger differs from saved {field}")
    if offset != len(fills) or runtime.report() != report:
        raise UniverseDataError("Ownership journal, claims, fills or risk bounds do not reconcile")
    return runtime


def result_inputs(result):
    return ([{**asdict(f), "side": f.side.value} for f in result.fills],
            [dict(timestamp=p.timestamp.isoformat(), equity=p.equity, cash=p.cash, exposure=p.gross_exposure,
                  dividend_receivable=p.dividend_receivable, ownership_cash_receivable=p.ownership_cash_receivable,
                  fractional_claim_value=p.fractional_claim_value) for p in result.equity_curve])


def summarize_ownership(result):
    fills, curves = result_inputs(result)
    runtime = replay_accounting(result.ownership_accounting, fills, curves)
    if runtime.positions() != result.final_positions:
        raise UniverseDataError("Final whole-share positions differ from reconciled ownership")
    if result.final_stops and set(result.final_stops) != set(result.final_positions):
        raise UniverseDataError("Inherited whole shares lack matching final protective stops")
    points = result.equity_curve
    annual, previous = {}, result.costs.initial_cash
    for year in sorted({p.timestamp.year for p in points}):
        last = [p.equity for p in points if p.timestamp.year == year][-1]
        annual[str(year)], previous = last / previous - 1, last
    exits = [d for d in runtime.fill_details if d["side"] == "SELL"]
    profits = [d["profit"] for d in exits]
    realized = {}
    corporate_cash_realized = 0.0
    for row in runtime.ledger.journal:
        if row["kind"] in {"simulated_sell", "immediate_terminal_cash", "claim_paid"}:
            key = row.get("instrument_id")
            if key is None:
                # Claim IDs identify their creation in the reconciled journal;
                # payment P&L is reported separately rather than assigned to a ticker.
                corporate_cash_realized += float(Fraction(row["amount"]) - Fraction(row["basis"]))
                continue
            proceeds = row.get("proceeds", row.get("amount"))
            realized[key] = realized.get(key, 0.0) + float(Fraction(proceeds) - Fraction(row["basis"]))
    final = runtime.marks[-1]
    for key in set(runtime.positions()) | set(runtime.fraction_units()):
        if key not in result.final_closes or not isclose(result.final_closes[key], float(runtime._bars[key]["close"]), abs_tol=1e-10):
            raise UniverseDataError("Final whole/fractional mark differs from the reconciled closing observation")
    open_positions = {}
    for key, qty in result.final_positions.items():
        basis = sum(lot.basis for lot in runtime.ledger.lots if lot.instrument_id == key)
        close = result.final_closes[key]
        if not isclose(close, float(runtime._bars[key]["close"]), abs_tol=1e-10):
            raise UniverseDataError("Final price differs from the reconciled closing observation")
        open_positions[key] = dict(quantity=qty, last_close=close, stop_price=result.final_stops.get(key),
                                   marked_unrealized_pnl=qty * close - float(basis))
    trade_stops = [f for f in result.fills if f.side.value == "SELL" and f.signal_reason.startswith("PROTECTIVE_STOP_")]
    fixed, fractional, dividend = runtime.claim_values({key: row["close"] for key, row in runtime._bars.items()})
    return dict(
        initial_cash=result.costs.initial_cash, final_equity=points[-1].equity,
        total_return=points[-1].equity / result.costs.initial_cash - 1, annual_returns=annual,
        max_drawdown=min(p.drawdown for p in points), max_observed_gross_exposure=max(p.gross_exposure for p in points),
        max_observed_positions=max(p.position_count for p in points), completed_trades=len(exits),
        protective_stop_exits=len(trade_stops), gap_open_stop_exits=sum(f.signal_reason.startswith("PROTECTIVE_STOP_GAP_OPEN") for f in trade_stops),
        winning_trades=sum(p > 0 for p in profits), win_rate=sum(p > 0 for p in profits) / len(profits) if profits else None,
        profit_factor=sum(p for p in profits if p > 0) / abs(sum(p for p in profits if p < 0)) if any(p < 0 for p in profits) else None,
        average_holding_days=sum(d["holding_days"] for d in exits) / len(exits) if exits else None,
        realized_pnl_by_symbol=dict(sorted(realized.items())), open_positions=open_positions, fill_count=len(fills),
        entry_halted_at=result.halted_at, event_count=len(result.events),
        ownership_accounting_reconciled=True, ownership_claims=final["claims"],
        outstanding_claim_value=float(Fraction(final["fixed_cash_receivables"])) + sum(
            float(c.units) * result.final_closes[c.instrument_id] for c in runtime.ledger.claims if c.kind == "fractional_shares"),
        marked_unrealized_pnl_including_claims=float(Fraction(final["unrealized_pnl"])),
        total_realized_pnl=float(runtime.ledger.realized_pnl),
        corporate_action_cash_realized_pnl=corporate_cash_realized,
        realized_pnl_by_symbol_excludes_claim_payments=True,
        trade_metrics_exclude_cash_settlements=True,
        trade_unit="Whole-position sells after economic basis allocation; branches are not independent original investments",
        dividend_income_earned=sum(float(Fraction(row["amount"])) for row in runtime.ledger.journal if row["kind"] == "ordinary_dividend_right"),
        dividend_cash_received=sum(float(Fraction(row["amount"])) for row in runtime.ledger.journal
                                   if row["kind"] == "claim_paid" and row["claim_id"].startswith("dividend:")),
        dividend_receivable=dividend, ownership_cash_receivable=fixed - dividend, fractional_claim_value=fractional,
        internal_financial_reconciliation=True, external_source_prices_verified=False,
    )


def ownership_risk_envelope(case, datasets):
    runtime = replay_accounting(case["ownership_accounting"], case["fills"], case["equity_curve"], datasets=datasets)
    final = {key: p["quantity"] for key, p in case["metrics"]["open_positions"].items()}
    if final != runtime.positions():
        raise UniverseDataError("Final reported positions differ from external-price ownership reconciliation")
    rows = runtime.risk_rows
    worst = min(rows, key=lambda row: row["conservative_drawdown_bound"])
    return dict(ledger_reconciled=True, corporate_actions_reconciled=True, external_source_prices_verified=True,
                intraday_equity_observed=False,
                observed_max_closing_drawdown=min(row["observed_closing_drawdown"] for row in rows),
                conservative_drawdown_bound=worst["conservative_drawdown_bound"], conservative_drawdown_bound_date=worst["timestamp"],
                conservative_daily_return_bound=min(row["conservative_daily_return_bound"] for row in rows),
                daily_envelopes=rows,
                limitation="Daily extrema/pre-post-touch states need not coexist. Nominal cash rights have credit risk; this is not observed intraday equity.")

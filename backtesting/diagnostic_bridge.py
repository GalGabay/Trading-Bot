"""Separate, approved research accounting for modeled availability of rights.

No broker interface, downloads or implicit approvals. Vendor-dependent modeled
observation/release times are never represented as verified historical facts.
The strict ownership adapter and its evidence contract are unchanged.
"""

from copy import deepcopy
from contextlib import contextmanager
from dataclasses import asdict, replace
from fractions import Fraction
from math import isclose

import pandas as pd
from alpaca.data.timeframe import TimeFrame

from app.data.market_data import CANONICAL_CANDLE_COLUMNS, ValidationConfig, validate_candles
from backtesting.claim_accounting import AccountingError, Claim, ClaimLedger, Lot, Quote, exact, instant, number
from backtesting.cohort_audit import SavedCalendar
from backtesting.diagnostic_accounting import DiagnosticClock, DiagnosticRightsBook, PendingRight, SCENARIOS
from backtesting.holding_policy import HoldingEntry
from backtesting.ownership_adapter import OwnershipRuntime
from backtesting.universe import SplitAction, UniverseDataError

DIAGNOSTIC_SCOPE = "approved_diagnostic_pending_rights_v1"


class DiagnosticLedger(ClaimLedger):
    """Reuse exact fill accounting and atomically bridge the pending-right book.

    Claims and the rights book describe the SAME assets; marks count them once.
    Cost basis follows opening component values for economic reconciliation,
    never tax reporting. Fractions retain basis and are never auto-liquidated.
    """

    def __init__(self, initial_cash, clock):
        super().__init__(initial_cash)
        self.rights = DiagnosticRightsBook(clock)
        self.right_details = {}

    @contextmanager
    def _operation(self, at):
        """Snapshot mutable financial state without cloning the saved calendar.

        Lots, claims, pending rights, amounts and timestamps are immutable.
        Journals append records; updates to a newly appended release row stay
        within its operation. Rollback truncates those new rows. Fail closed
        if future changes add state without extending this snapshot contract.
        """
        fields={"initial_cash","cash","realized_pnl","_lots","_claims","_events","_instructions",
            "_journal","_clock","rights","right_details"}
        book_fields={"clock","_pending","_seen","released_cash","delivered_shares","_journal","_at"}
        if set(self.__dict__)!=fields or set(self.rights.__dict__)!=book_fields:
            raise AccountingError("Extend the diagnostic atomic snapshot contract for new mutable state")
        at=instant(at)
        if self._clock is not None and at<self._clock:
            raise AccountingError("Accounting clock cannot move backwards")
        prior=dict(self.__dict__)
        prior.update(_lots=list(self._lots),_claims=dict(self._claims),_events=set(self._events),
            _instructions=set(self._instructions),right_details=dict(self.right_details))
        book=self.rights
        book_prior=dict(book.__dict__)
        book_prior.update(_pending=dict(book._pending),_seen=set(book._seen),delivered_shares=dict(book.delivered_shares))
        journal_length,book_length=len(self._journal),len(book._journal)
        try:
            self._clock=at
            yield at
        except BaseException:
            del prior["_journal"][journal_length:]
            del book_prior["_journal"][book_length:]
            book.__dict__.clear()
            book.__dict__.update(book_prior)
            self.__dict__.clear()
            self.__dict__.update(prior)
            raise

    def _right(self, claim, *, release_at=None, acquired_at=None, stop=None):
        if claim.claim_id in self._claims:
            raise AccountingError("Duplicate diagnostic claim")
        if claim.kind == "pending_shares" and claim.units < 1:
            release_at = None  # No whole shares to release; cash fixing is unknown.
        self.rights.recognize(PendingRight(claim.claim_id, claim.instrument_id,
            "cash" if claim.kind == "cash" else "shares", claim.units or 1,
            claim.amount, claim.created_at, release_at, claim.source))
        self._claims[claim.claim_id] = claim
        self.right_details[claim.claim_id] = dict(acquired_at=acquired_at, stop=stop)

    def dividend_right(self, plan, *, at):
        with self._operation(at) as at:
            identity, event_id = plan["instrument_id"], plan["event_id"]
            if event_id in self._events or instant(plan["economic_at"]) != at:
                raise AccountingError("Duplicate dividend or wrong diagnostic boundary")
            if any(c.kind == "pending_shares" and c.instrument_id == identity for c in self.claims):
                raise AccountingError("Distribution on undelivered/fractional shares needs explicit chained-right terms")
            if plan.get("independent_entitlement") is False:
                self._events.add(event_id)
                self._journal.append(dict(kind="diagnostic_dividend_component_context", event_id=event_id,
                    instrument_id=identity, at=at.isoformat(), represented_by_event_id=plan["represented_by_event_id"],
                    amount="0", reason="Reviewed component already included in the separate total record"))
                return
            quantity = self.quantity(identity)
            amount = quantity * number(plan["cash_per_eligible_share"], positive=True)
            if quantity:
                self._right(Claim(f"dividend:{event_id}", event_id, "cash", identity, Fraction(0), amount,
                    Fraction(0), at, "approved provider-dependent ordinary-dividend accounting"),
                    release_at=plan["modeled_release_at"])
            self._events.add(event_id)
            self._journal.append(dict(kind="diagnostic_dividend", event_id=event_id, instrument_id=identity,
                at=at.isoformat(), quantity=quantity, amount=exact(amount),
                historical_known_at=None, independently_verified_entitlement=False))

    def action(self, plan, quotes, *, at, prior_stop=None):
        with self._operation(at) as at:
            event_id, parent = plan["event_id"], plan["parent_id"]
            if event_id in self._events or instant(plan["modeled_accounting_at"]) != at:
                raise AccountingError("Duplicate material action or wrong diagnostic boundary")
            if any(c.kind == "pending_shares" and c.instrument_id == parent for c in self.claims):
                raise AccountingError("Action on pending ownership needs explicit chained-right terms")
            lots = [lot for lot in self.lots if lot.instrument_id == parent]
            qty = sum(lot.quantity for lot in lots)
            affected = [parent, *(leg["instrument_id"] for leg in plan["share_legs"])]
            if not qty:
                self._events.add(event_id)
                self._journal.append(dict(kind="diagnostic_action_unheld", event_id=event_id, at=at.isoformat()))
                return dict(parent=parent, affected=affected, old_quantity=0, stop_prices={})
            retained = plan["kind"] == "retained_parent_spinoff"
            if not retained and plan["kind"] != "cash_merger":
                raise AccountingError("Unimplemented diagnostic material action")
            legs = [(leg["instrument_id"], qty * number(leg["shares_per_parent"], positive=True), leg["modeled_release_at"])
                    for leg in plan["share_legs"]]
            required = {key for key, _, _ in legs} | ({parent} if retained else set())
            self._quotes(quotes, required, at)
            components = []
            if retained:
                components.append(("retained", parent, Fraction(qty), qty * quotes[parent].close, None))
            cash = qty * number(plan["cash_per_parent"])
            if cash:
                components.append(("cash", parent, Fraction(0), cash, plan["modeled_cash_release_at"]))
            components.extend(("pending_shares", key, units, units * quotes[key].close, release) for key, units, release in legs)
            total = sum(c[3] for c in components)
            if total <= 0:
                raise AccountingError("Positive current opening component value is required for basis allocation")
            basis = sum(lot.basis for lot in lots)
            oldest = min(lot.acquired_at for lot in lots)
            floor_factor = None if prior_stop is None else qty * number(str(prior_stop), positive=True) / total
            stops = {}
            self._lots = [lot for lot in self.lots if lot.instrument_id != parent]
            for i, (kind, identity, units, value, release) in enumerate(components):
                allocated = basis * value / total
                key = f"diagnostic:{event_id}:{i}"
                if kind == "retained":
                    self._lots.append(Lot(key, identity, int(units), allocated, oldest))
                    if floor_factor is not None:
                        stops[identity] = float(quotes[identity].close * floor_factor)
                else:
                    stop = None if kind == "cash" or floor_factor is None else float(quotes[identity].close * floor_factor)
                    self._right(Claim(key, event_id, kind, identity, units,
                        value if kind == "cash" else None, allocated, at, "approved diagnostic material action"),
                        release_at=release, acquired_at=oldest, stop=stop)
            self._events.add(event_id)
            self._journal.append(dict(kind="diagnostic_action", event_id=event_id, parent_id=parent,
                at=at.isoformat(), parent_quantity=qty, prior_basis=exact(basis), component_value=exact(total),
                historical_known_at=None, actual_delivery_at=None, basis_policy="opening_component_values_not_tax_basis"))
            return dict(parent=parent, affected=affected, old_quantity=qty, stop_prices=stops)

    def split(self, action, *, at):
        """A genuine unit conversion is effective immediately in every scenario."""
        with self._operation(at) as at:
            key = action.instrument_id
            if action.event_id in self._events:
                raise AccountingError("Duplicate diagnostic split")
            if any(c.kind == "pending_shares" and c.instrument_id == key for c in self.claims):
                raise AccountingError("Split of outstanding claims needs a separately reviewed chained-right instruction")
            old = [lot for lot in self.lots if lot.instrument_id == key]
            qty = sum(lot.quantity for lot in old)
            if qty:
                units = Fraction(qty * action.new_shares, action.old_shares)
                whole = int(units)
                basis = sum(lot.basis for lot in old)
                oldest = min(lot.acquired_at for lot in old)
                self._lots = [lot for lot in self.lots if lot.instrument_id != key]
                if whole:
                    self._lots.append(Lot(f"split:{action.event_id}", key, whole, basis * whole / units, oldest))
                if units > whole:
                    self._right(Claim(f"split:{action.event_id}:fraction", action.event_id, "pending_shares", key,
                        units - whole, None, basis * (units - whole) / units, at,
                        "approved split fraction; cash allocation unknown"), acquired_at=oldest)
            self._events.add(action.event_id)
            self._journal.append(dict(kind="diagnostic_split", event_id=action.event_id, instrument_id=key,
                at=at.isoformat(), prior_quantity=qty, ratio=f"{action.new_shares}/{action.old_shares}"))

    def release_due(self, *, at):
        with self._operation(at) as at:
            transfers = []
            for right in self.rights.pending:
                if right.release_at is None or right.release_at > at:
                    continue
                if right.release_at != at:
                    raise AccountingError("Missed modeled availability boundary; replay required")
                claim = self._claims[right.claim_id]
                if right.kind == "shares" and right.units < 1:
                    continue  # Exact fraction has no assumed cash fixing.
                result = self.rights.release(right.claim_id, at=at)
                details = self.right_details[right.claim_id]
                if claim.kind == "cash":
                    self.pay(f"release:{right.claim_id}", right.claim_id, claim.amount,
                        available_at=at, known_at=at, at=at, source="modeled diagnostic availability, not broker receipt")
                    self._journal[-1].update(kind="diagnostic_cash_release", historical_known_at=None,
                        modeled_available_at=at.isoformat(), actual_broker_received_at=None)
                    # Do not present the modeling boundary as historical knowledge.
                    self._journal[-1].pop("known_at")
                else:
                    whole = result["whole_shares"]
                    basis = claim.basis * whole / claim.units
                    self._lots.append(Lot(f"release:{right.claim_id}", claim.instrument_id, whole, basis, details["acquired_at"]))
                    rest = claim.units - whole
                    if rest:
                        self._claims[right.claim_id] = replace(claim, units=rest, basis=claim.basis - basis)
                    else:
                        del self._claims[right.claim_id]
                    self._journal.append(dict(kind="diagnostic_share_release", claim_id=right.claim_id,
                        at=at.isoformat(), whole_shares=whole, basis=exact(basis), actual_broker_received_at=None))
                    transfers.append(dict(parent=claim.instrument_id, affected=[claim.instrument_id], old_quantity=0, preserve_existing_stop=True,
                        stop_prices={} if details["stop"] is None else {claim.instrument_id: details["stop"]}))
            return transfers

    def mark(self, quotes, *, at):
        with self._operation(at) as at:
            book = self.rights.mark(at=at, quotes=quotes)
            if not book["complete"]:
                raise AccountingError("Incomplete pending-right value blocks scoring and new entries")
            units = {}
            for lot in self.lots:
                units[lot.instrument_id] = units.get(lot.instrument_id, Fraction(0)) + lot.quantity
            for claim in self.claims:
                if claim.kind == "pending_shares":
                    units[claim.instrument_id] = units.get(claim.instrument_id, Fraction(0)) + claim.units
            self._quotes(quotes, units, at)
            fixed = sum((c.amount for c in self.claims if c.kind == "cash"), Fraction(0))
            shares = sum((qty * quotes[key].close for key, qty in units.items()), Fraction(0))
            pending = fixed + sum((c.units * quotes[c.instrument_id].close for c in self.claims if c.kind == "pending_shares"), Fraction(0))
            if pending != Fraction(book["pending_right_value"]):
                raise AccountingError("Pending-right book and accounting ledger differ")
            basis = sum((lot.basis for lot in self.lots), Fraction(0)) + sum((c.basis for c in self.claims), Fraction(0))
            equity = self.cash + fixed + shares
            unrealized = fixed + shares - basis
            if equity != self.initial_cash + self.realized_pnl + unrealized:
                raise AccountingError("Diagnostic cash/basis/P&L reconciliation failed")
            return dict(timestamp=at.isoformat(), simulated_money=True, equity=exact(equity),
                spendable_cash=exact(self.cash), fixed_cash_receivables=exact(fixed),
                stock_and_pending_share_value=exact(shares), gross_exposure=exact((shares + fixed) / equity) if equity else None,
                economic_book_basis=exact(basis), realized_pnl=exact(self.realized_pnl), unrealized_pnl=exact(unrealized),
                reconciliation_passed=True, pending_right_book=book,
                lots=[dict(lot_id=l.lot_id, instrument_id=l.instrument_id, quantity=l.quantity,
                    basis=exact(l.basis), acquired_at=l.acquired_at.isoformat()) for l in self.lots],
                claims=[dict(claim_id=c.claim_id, event_id=c.event_id, kind=c.kind, instrument_id=c.instrument_id,
                    units=exact(c.units), amount=None if c.amount is None else exact(c.amount), basis=exact(c.basis),
                    created_at=c.created_at.isoformat(), source=c.source) for c in self.claims])


class DiagnosticUniverse:
    """Dated *configured diagnostic intervals*, not verified listing evidence.

    A separate type avoids inventing ListingPeriod known-at/exchange/subtype
    facts. Stable-ID bars retain source aliases as provenance in the manifest.
    """

    action_scope = DIAGNOSTIC_SCOPE

    def __init__(self, sessions, streams, splits=(), *, provenance=None):
        self.sessions = tuple(sessions)
        self.clock = DiagnosticClock([dict(opens_at=s.opens_at.isoformat(), closes_at=s.closes_at.isoformat()) for s in sessions])
        self.streams = deepcopy(streams)
        self.provenance = deepcopy(provenance or {})
        self._streams = {s["instrument_id"]: s for s in self.streams}
        self._expected_cache = {}
        if not streams or len(self._streams) != len(streams):
            raise UniverseDataError("Unique, explicitly retained diagnostic stream IDs are required")
        self.dates = pd.Series([s.opens_at.tz_convert("America/New_York").normalize().tz_convert("UTC") for s in sessions])
        self._index = {t: i for i, t in enumerate(self.dates)}
        self.splits = tuple(splits)
        self._splits = {}
        for split in splits:
            day = pd.Timestamp(split.effective_session, tz="America/New_York").tz_convert("UTC")
            if day not in self._index or split.instrument_id not in self.instrument_ids:
                raise UniverseDataError("Diagnostic split is outside declared identities/calendar")
            self._splits.setdefault(day, []).append(split)

    @property
    def instrument_ids(self):
        return set(self._streams)

    def expected(self, key):
        parts = self._streams[key]["parts"]
        signature=tuple((p["start"],p["end_exclusive"]) for p in parts)
        cached=self._expected_cache.get(key)
        if cached is None or cached[0]!=signature:
            cached=(signature,frozenset(t for t in self.dates if any(start<=t.date().isoformat()<end for start,end in signature)))
            self._expected_cache[key]=cached
        return cached[1]

    def prepare(self, key, source):
        if key not in self.instrument_ids:
            raise UniverseDataError("Unknown diagnostic identity")
        frame = source.loc[:, CANONICAL_CANDLE_COLUMNS].copy()
        if frame.empty:
            if self.expected(key):
                raise UniverseDataError("Empty history during a configured diagnostic interval")
            frame.index = pd.Index([], dtype=int)
            return frame  # Retain the ID when its entire interval is outside this window.
        validate_candles(frame, config=ValidationConfig(timeframe=TimeFrame.Day), calendar=SavedCalendar(self.sessions))
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        if (set(frame["timestamp"]) != self.expected(key) or not frame["timestamp"].is_monotonic_increasing or
                (not frame.empty and set(frame["symbol"]) != {key})):
            raise UniverseDataError("Diagnostic bars have a gap, extra observation, disorder or mismatched ID")
        for name in ("open", "high", "low", "close", "volume"):
            frame[name] = pd.to_numeric(frame[name])
        frame.index = [self._index[t] for t in frame["timestamp"]]
        return frame

    def splits_at(self, timestamp):
        return tuple(self._splits.get(timestamp, ()))

    def dividends_at(self, timestamp):
        return ()  # All diagnostic rights must pass through the separate schedule.

    def outcomes_at(self, timestamp):
        return ()  # No diagnostic cash right is instant spendable terminal cash.

    def metadata(self):
        return dict(schema_version=1, price_and_action_scope=DIAGNOSTIC_SCOPE, currency="USD",
            streams=self.streams, provenance=self.provenance,
            sessions=[dict(opens_at=s.opens_at.isoformat(), closes_at=s.closes_at.isoformat()) for s in self.sessions],
            splits=[asdict(s) for s in self.splits], historical_known_at=None,
            strict_evidence_approved=False, paper_authorized=False,
            market_wide_performance_ready=False, diagnostic_adapter_required=True)


class DiagnosticSchedule:
    def __init__(self, *, entry_instrument_ids, dividends=(), material=(), actions=(), resets=(), scenario,
                 approval_sha256, membership_not_before):
        if scenario not in SCENARIOS or not approval_sha256 or len(set(entry_instrument_ids)) != len(entry_instrument_ids):
            raise UniverseDataError("Require explicit diagnostic scenario, approval and unique entry IDs")
        self.entry_instrument_ids = frozenset(entry_instrument_ids)
        self.dividends, self.material, self.actions, self.resets = deepcopy((list(dividends), list(material), list(actions), list(resets)))
        self.scenario, self.approval_sha256 = scenario, approval_sha256
        self.membership_not_before = (pd.Timestamp(membership_not_before, tz="UTC").isoformat()
            if len(membership_not_before) == 10 else instant(membership_not_before).isoformat())

    def bind(self, universe):
        if not isinstance(universe, DiagnosticUniverse) or not self.entry_instrument_ids <= universe.instrument_ids:
            raise UniverseDataError("Diagnostic schedule requires its separate universe and explicit entry IDs")
        opens = set(universe.clock.opens)
        ids = [r["event_id"] for r in (*self.dividends, *self.material)]
        ids += [s.event_id for s in universe.splits]
        if len(set(ids)) != len(ids):
            raise UniverseDataError("Duplicate diagnostic economic event identity")
        boundaries = set()
        for row in (*self.dividends, *self.material):
            at = instant(row.get("economic_at") or row["modeled_accounting_at"])
            if row.get("scenario") != self.scenario or row.get("blockers") or at not in opens:
                raise UniverseDataError("Unadmitted diagnostic event or wrong scenario/boundary")
            if row.get("historical_known_at") is not None or row.get("execution_ready") is not False:
                raise UniverseDataError("Diagnostic assumptions cannot promote historical/strict evidence flags")
            parent = row.get("instrument_id") or row["parent_id"]
            if parent not in universe.instrument_ids:
                raise UniverseDataError("Diagnostic event parent is outside the retained scope")
            if "share_legs" in row:
                pair = (at, parent)
                if pair in boundaries or row["kind"] not in {"cash_merger", "retained_parent_spinoff"}:
                    raise UniverseDataError("Material events need nonoverlapping supported ownership terms")
                if row.get("data_terms_resolved") is not True:
                    raise UniverseDataError("Clearing explanatory blockers cannot admit unresolved economic terms")
                index = universe.clock.opens.index(at)
                snapshot = row.get("required_ownership_snapshot_at")
                if snapshot is None or (index and instant(snapshot) != universe.clock.closes[index-1]) or instant(snapshot) >= at:
                    raise UniverseDataError("Material entitlement must identify the correct preceding saved close")
                if row["kind"] == "cash_merger":
                    if (row.get("status") != "admitted_diagnostic_cash_receivable" or row["share_legs"] or
                            row.get("modeled_cash_release_at") is not None or row.get("consume_parent_once") is not True):
                        raise UniverseDataError("Cash merger must consume the parent once into an unpaid fixed receivable")
                    number(row["cash_per_parent"], positive=True)
                    if any(p["end_exclusive"] > row["economic_date"] for p in universe._streams[parent]["parts"]):
                        raise UniverseDataError("Cash-merger parent interval must end at its nontradeable boundary")
                elif (row.get("status") != "admitted_diagnostic_due_bill_spinoff" or
                        row.get("preserve_parent_quantity") is not True or not row["share_legs"] or
                        number(row["cash_per_parent"]) != 0):
                    raise UniverseDataError("Spinoff needs admitted retained-parent share terms, without invented cash")
                boundaries.add(pair)
                for leg in row["share_legs"]:
                    if leg["instrument_id"] not in universe.instrument_ids:
                        raise UniverseDataError("Missing retained child identity")
                    release = leg["modeled_release_at"]
                    if release is not None and (instant(release) not in opens or instant(release) < at):
                        raise UniverseDataError("Invalid modeled share release")
                    if self.scenario == "no_credit" and release is not None:
                        raise UniverseDataError("No-credit scenario cannot deliver shares")
            else:
                if row.get("independent_entitlement") is False:
                    totals = [d for d in self.dividends if d["event_id"] == row.get("represented_by_event_id") and
                        d["instrument_id"] == parent and d["economic_at"] == row["economic_at"]]
                    if (row.get("status") != "reviewed_component_in_total_no_independent_right" or
                            number(row["cash_per_eligible_share"]) != 0 or len(totals) != 1 or
                            row.get("component_review", {}).get("kind") != "aggregate_includes_component" or
                            number(totals[0]["cash_per_eligible_share"], positive=True) != number(row["component_review"]["total_rate"], positive=True) or
                            row["modeled_release_at"] is not None):
                        raise UniverseDataError("Zero dividend needs a reviewed, matching nonduplicated total/component treatment")
                else:
                    number(row["cash_per_eligible_share"], positive=True)
                release = row["modeled_release_at"]
                if release is not None and (instant(release) not in opens or instant(release) < at):
                    raise UniverseDataError("Invalid modeled cash release")
                if self.scenario == "no_credit" and release is not None:
                    raise UniverseDataError("No-credit scenario cannot pay cash")
        for row in self.actions:
            if (row.get("blockers") or row.get("data_terms_resolved") is not True or
                    instant(row["effective_at"]) not in opens or row["instrument_id"] not in universe.instrument_ids or
                    row.get("kind") not in {"ordinary_split", "same_instrument_alias", "preinvestment_reference_action"}):
                raise UniverseDataError("Unadmitted diagnostic action")

    def reset_indices(self, universe, key):
        dates = {t.date().isoformat(): i for i, t in enumerate(universe.dates)}
        reset = {dates[r["from_session"]] for r in self.resets if r["instrument_id"] == key and r["from_session"] in dates}
        reset.update(dates[r["economic_date"]] for r in self.material if
            key in {r["parent_id"], *(l["instrument_id"] for l in r["share_legs"])} and r["economic_date"] in dates)
        return reset

    def metadata(self):
        return dict(entry_instrument_ids=sorted(self.entry_instrument_ids), dividends=self.dividends, material=self.material,
            actions=self.actions, resets=self.resets, scenario=self.scenario, approval_sha256=self.approval_sha256,
            membership_not_before=self.membership_not_before)


class DiagnosticRuntime(OwnershipRuntime):
    """Reuse audited fill phases/risk envelopes with a separate diagnostic ledger.

    The strict runtime is never constructed with diagnostic terms. Its reusable
    fill and OHLC-envelope methods operate on this runtime's exact ledger.
    """

    def __init__(self, schedule, universe, initial_cash):
        schedule.bind(universe)
        self.schedule, self.universe = schedule, universe
        self.ledger = DiagnosticLedger(str(initial_cash), universe.clock)
        self.session_indices = {instant(s.opens_at): i for i, s in enumerate(universe.sessions)}
        self.days, self.fill_details, self.marks, self.risk_rows = [], [], [], []
        self._last_equity = self._close_peak = self._upper_peak = float(initial_cash)
        self._dividends, self._material, self._actions = {}, {}, {}
        for values, target, field in ((schedule.dividends, self._dividends, "economic_at"),
                (schedule.material, self._material, "modeled_accounting_at"),
                (schedule.actions, self._actions, "effective_at")):
            for row in values:
                target.setdefault(instant(row[field]), []).append(row)

    def fraction_units(self):
        # Engine compatibility: all unspendable share units count toward entry
        # exposure and the held-name gate, not only the fractional remainder.
        values = {}
        for claim in self.ledger.claims:
            if claim.kind == "pending_shares":
                values[claim.instrument_id] = values.get(claim.instrument_id, Fraction(0)) + claim.units
        return values

    def claim_values(self, prices):
        fixed = sum((c.amount for c in self.ledger.claims if c.kind == "cash"), Fraction(0))
        dividend = sum((c.amount for c in self.ledger.claims if c.claim_id.startswith("dividend:")), Fraction(0))
        try:
            shares = sum((units * number(str(prices[key]), positive=True) for key, units in self.fraction_units().items()), Fraction(0))
        except KeyError as exc:
            raise UniverseDataError("Pending shares lack a current session mark; scoring and entries are blocked") from exc
        return float(fixed), float(shares), float(dividend)

    def share_claim_components(self, prices):
        fractional = sum((c.units % 1) * number(str(prices[c.instrument_id]), positive=True)
            for c in self.ledger.claims if c.kind == "pending_shares")
        shares = self.claim_values(prices)[1]
        return shares - float(fractional), float(fractional)

    def begin(self, index, bars, *, stop_prices=None):
        self._index, self._bars = index, bars
        self._at = instant(self.universe.sessions[index].opens_at)
        self._opens = {key: float(row["open"]) for key, row in bars.items()}
        self._needed = set(self.positions()) | set(self.fraction_units())
        self._opening_marks, self._touches, self._intraday = [], {}, None
        self.transitions = []
        stop_prices = stop_prices or {}
        self._stops_before_open = dict(stop_prices)
        quotes = {key: Quote(key, self._at, str(row["open"]), str(row["open"]), str(row["open"])) for key, row in bars.items()}
        for split in self.universe.splits_at(self.universe.dates.iloc[index]):
            self.ledger.split(split, at=self._at)
            self.transitions.append(dict(parent=split.instrument_id, affected=[split.instrument_id], old_quantity=0, stop_prices={}))
        for event in self._material.get(self._at, ()):
            transition = self.ledger.action(event, quotes, at=self._at, prior_stop=stop_prices.get(event["parent_id"]))
            self.transitions.append(transition)
            self._needed.update(transition["affected"])
        for event in self._actions.get(self._at, ()):
            if event["kind"] == "same_instrument_alias":
                self.transitions.append(dict(parent=event["instrument_id"], affected=[event["instrument_id"]], old_quantity=0, stop_prices={}))
            elif event["kind"] == "preinvestment_reference_action" and self.ledger.quantity(event["instrument_id"]):
                raise UniverseDataError("Preinvestment action cannot encounter an invested holding")
        for event in self._dividends.get(self._at, ()):
            self.ledger.dividend_right(event, at=self._at)
        self.transitions.extend(self.ledger.release_due(at=self._at))
        self._opening_marks.append(self._equity_open())

    def finish(self):
        mark = super().finish()
        self.days[-1]["stop_prices_before_open"] = dict(self._stops_before_open)
        return mark

    def report(self):
        return dict(version="diagnostic_pending_rights_v1", initial_cash=str(self.ledger.initial_cash),
            schedule=self.schedule.metadata(), universe=self.universe.metadata(),
            journal=self.ledger.journal, pending_right_journal=self.ledger.rights.journal,
            marks=self.marks, days=self.days, fill_details=self.fill_details, daily_risk_envelopes=self.risk_rows,
            historical_known_at=None, actual_broker_received_at=None, strict_evidence_approved=False,
            paper_authorized=False, independently_verified_entitlement=False,
            limitations=["Vendor-dependent approved research assumptions; not strict historical evidence",
                "Opening relative-value economic basis, not tax basis",
                "Unknown payment stays a nominal unspendable cash receivable",
                "Pending whole/fractional shares count toward equity/exposure; no automatic fractional cash sale",
                "Chained actions on pending share claims require separate reviewed instructions",
                "OHLC envelopes are conservative bounds, not observed intraday equity"])


def replay_diagnostic(report, fills, curves, *, datasets=None):
    """Replay exact financial operations without generating strategy signals."""
    from app.data.market_calendar import TradingSession
    from app.strategy.base import SignalAction
    from backtesting.engine import SimulatedFill

    if report.get("version") != "diagnostic_pending_rights_v1":
        raise UniverseDataError("Unsupported diagnostic accounting version")
    meta = report["universe"]
    universe = DiagnosticUniverse(
        [TradingSession(pd.Timestamp(s["opens_at"]), pd.Timestamp(s["closes_at"])) for s in meta["sessions"]],
        meta["streams"], [SplitAction(**s) for s in meta["splits"]], provenance=meta["provenance"])
    schedule = DiagnosticSchedule(**report["schedule"])
    runtime = DiagnosticRuntime(schedule, universe, report["initial_cash"])
    days = report["days"]
    indices = [r["index"] for r in days]
    if (not indices or indices != list(range(indices[0], indices[-1] + 1)) or
            indices[0] < 0 or indices[-1] >= len(universe.sessions) or
            len(curves) != len(days) or len(report["fill_details"]) != len(fills)):
        raise UniverseDataError("Diagnostic sessions/fills are missing, duplicated or unordered")
    frames = {}
    if datasets is not None:
        if set(datasets) != universe.instrument_ids:
            raise UniverseDataError("External reconciliation requires every retained identity")
        frames = {key: universe.prepare(key, frame).set_index("timestamp", verify_integrity=True) for key, frame in datasets.items()}
    offset = 0
    for day, point in zip(days, curves):
        index = day["index"]
        timestamp = universe.dates.iloc[index]
        if pd.Timestamp(point["timestamp"]) != timestamp:
            raise UniverseDataError("Diagnostic equity/session dates disagree")
        bars = day["quotes"]
        if not set(bars) <= universe.instrument_ids:
            raise UniverseDataError("Quote outside the declared diagnostic scope")
        for key, row in bars.items():
            values = {name: number(str(row[name]), positive=True) for name in ("open", "high", "low", "close")}
            if not values["low"] <= min(values["open"], values["close"]) <= max(values["open"], values["close"]) <= values["high"]:
                raise UniverseDataError("Impossible diagnostic OHLC quote")
            if timestamp not in universe.expected(key):
                raise UniverseDataError("Quote outside its configured diagnostic interval")
            if datasets is not None:
                if timestamp not in frames[key].index:
                    raise UniverseDataError("No actual observation for a diagnostic quote")
                actual = frames[key].loc[timestamp]
                if actual["volume"] <= 0 or any(number(str(actual[n]), positive=True) != values[n] for n in values):
                    raise UniverseDataError("Recorded diagnostic quote differs from actual tradable data")
        runtime._stops_before_open = dict(day["stop_prices_before_open"])
        runtime.begin(index, bars, stop_prices=runtime._stops_before_open)
        while offset < len(fills) and pd.Timestamp(fills[offset]["timestamp"]) == timestamp:
            value = fills[offset]
            phase = report["fill_details"][offset]["phase"]
            if phase == "intraday" and runtime._intraday is None:
                runtime.capture_intraday()
            signal_at = pd.Timestamp(value["signal_timestamp"])
            protected = value["signal_reason"].startswith("PROTECTIVE_STOP_")
            if (signal_at.tzinfo is None or (not protected and signal_at >= timestamp) or
                    (protected and signal_at > universe.sessions[index].opens_at)):
                raise UniverseDataError("Diagnostic fill uses future/unavailable signal information")
            key = value["symbol"]
            if key not in bars:
                raise UniverseDataError("Fill has no actual diagnostic quote")
            price, opening = number(str(value["fill_price"]), positive=True), number(str(bars[key]["open"]), positive=True)
            if phase == "open" and ((value["side"] == "BUY" and price < opening) or (value["side"] == "SELL" and price > opening)):
                raise UniverseDataError("Diagnostic open fill uses favorable costs")
            if phase == "intraday" and price > number(str(bars[key]["high"]), positive=True):
                raise UniverseDataError("Intraday diagnostic sell exceeds the observed high")
            runtime.record_fill(SimulatedFill(timestamp=timestamp, symbol=key, side=SignalAction(value["side"]),
                quantity=value["quantity"], reference_open=value["reference_open"], fill_price=value["fill_price"],
                commission=value["commission"], signal_timestamp=signal_at, signal_reason=value["signal_reason"]), phase=phase)
            offset += 1
        if runtime._intraday is None:
            runtime.capture_intraday()
        mark = runtime.finish()
        prices = {key: row["close"] for key, row in bars.items()}
        fixed, shares, dividend = runtime.claim_values(prices)
        whole, fraction = runtime.share_claim_components(prices)
        comparisons = dict(equity=float(Fraction(mark["equity"])), cash=float(runtime.ledger.cash),
            exposure=float(Fraction(mark["gross_exposure"])), dividend_receivable=dividend,
            ownership_cash_receivable=fixed-dividend, fractional_claim_value=fraction, pending_share_claim_value=whole)
        for field, expected in comparisons.items():
            if field not in point or not isclose(point[field], expected, rel_tol=1e-11, abs_tol=1e-6):
                raise UniverseDataError(f"Diagnostic ledger differs from saved {field}")
    if offset != len(fills) or runtime.report() != report:
        raise UniverseDataError("Diagnostic journal, rights, marks, fills or risk envelopes do not reconcile")
    return runtime


def summarize_diagnostic(result):
    from backtesting.ownership_adapter import result_inputs
    fills, curves = result_inputs(result)
    for row, point in zip(curves, result.equity_curve):
        row["pending_share_claim_value"] = point.pending_share_claim_value
    runtime = replay_diagnostic(result.diagnostic_accounting, fills, curves)
    if runtime.positions() != result.final_positions:
        raise UniverseDataError("Final diagnostic positions differ from replay")
    final = runtime.marks[-1]
    exits = [row for row in runtime.fill_details if row["side"] == "SELL"]
    profits = [r["profit"] for r in exits]
    annual, previous = {}, result.costs.initial_cash
    for year in sorted({p.timestamp.year for p in result.equity_curve}):
        last = [p.equity for p in result.equity_curve if p.timestamp.year == year][-1]
        annual[str(year)], previous = last / previous - 1, last
    positions = {}
    for key, qty in result.final_positions.items():
        close = result.final_closes[key]
        basis = sum(l.basis for l in runtime.ledger.lots if l.instrument_id == key)
        positions[key] = dict(quantity=qty, last_close=close, stop_price=result.final_stops.get(key), marked_unrealized_pnl=qty*close-float(basis))
    realized = {}
    for r in runtime.ledger.journal:
        if r["kind"] == "simulated_sell":
            key = r["instrument_id"]
            realized[key] = realized.get(key, 0) + float(Fraction(r["proceeds"]) - Fraction(r["basis"]))
    points = result.equity_curve
    return dict(initial_cash=result.costs.initial_cash, final_equity=points[-1].equity,
        total_return=points[-1].equity/result.costs.initial_cash-1, annual_returns=annual,
        max_drawdown=min(p.drawdown for p in points), max_observed_gross_exposure=max(p.gross_exposure for p in points),
        max_observed_positions=max(p.position_count for p in points), completed_trades=len(exits),
        protective_stop_exits=sum(f.signal_reason.startswith("PROTECTIVE_STOP_") for f in result.fills),
        gap_open_stop_exits=sum(f.signal_reason.startswith("PROTECTIVE_STOP_GAP_OPEN") for f in result.fills),
        winning_trades=sum(p>0 for p in profits), win_rate=sum(p>0 for p in profits)/len(profits) if profits else None,
        profit_factor=sum(p for p in profits if p>0)/abs(sum(p for p in profits if p<0)) if any(p<0 for p in profits) else None,
        average_holding_days=sum(r["holding_days"] for r in exits)/len(exits) if exits else None,
        realized_pnl_by_symbol=realized, open_positions=positions, fill_count=len(result.fills),
        entry_halted_at=result.halted_at, event_count=len(result.events),
        total_realized_pnl=float(runtime.ledger.realized_pnl),
        marked_unrealized_pnl_including_claims=float(Fraction(final["unrealized_pnl"])),
        outstanding_claim_value=float(Fraction(final["pending_right_book"]["pending_right_value"])),
        diagnostic_claims=final["claims"],
        diagnostic_accounting_reconciled=True, trade_metrics_exclude_cash_settlements=True,
        dividend_income_earned=sum(float(Fraction(r["amount"])) for r in runtime.ledger.journal if r["kind"]=="diagnostic_dividend"),
        dividend_cash_received=sum(float(Fraction(r["amount"])) for r in runtime.ledger.journal
            if r["kind"]=="diagnostic_cash_release" and r["claim_id"].startswith("dividend:")),
        strict_evidence_approved=False, paper_authorized=False)


def diagnostic_risk_envelope(case, datasets):
    runtime = replay_diagnostic(case["diagnostic_accounting"], case["fills"], case["equity_curve"], datasets=datasets)
    final = float(Fraction(runtime.marks[-1]["equity"]))
    exits = [r for r in runtime.fill_details if r["side"] == "SELL"]
    profits = [r["profit"] for r in exits]
    counts = [len({l["instrument_id"] for l in m["lots"]} | {c["instrument_id"] for c in m["claims"] if c["kind"] == "pending_shares"}) for m in runtime.marks]
    expected = dict(initial_cash=float(runtime.ledger.initial_cash), final_equity=final,
        total_return=final/float(runtime.ledger.initial_cash)-1,
        total_realized_pnl=float(runtime.ledger.realized_pnl),
        marked_unrealized_pnl_including_claims=float(Fraction(runtime.marks[-1]["unrealized_pnl"])),
        max_drawdown=min(r["observed_closing_drawdown"] for r in runtime.risk_rows),
        max_observed_gross_exposure=max(float(Fraction(m["gross_exposure"])) for m in runtime.marks),
        max_observed_positions=max(counts), fill_count=len(runtime.fill_details), completed_trades=len(exits),
        winning_trades=sum(p>0 for p in profits), win_rate=sum(p>0 for p in profits)/len(profits) if profits else None,
        profit_factor=sum(p for p in profits if p>0)/abs(sum(p for p in profits if p<0)) if any(p<0 for p in profits) else None,
        average_holding_days=sum(r["holding_days"] for r in exits)/len(exits) if exits else None)
    for key, value in expected.items():
        actual = case["metrics"].get(key)
        if value is None:
            valid = key in case["metrics"] and actual is None
        else:
            valid = not isinstance(actual, bool) and isinstance(actual, (int, float)) and isclose(actual, value, rel_tol=1e-11, abs_tol=1e-8)
        if not valid:
            raise UniverseDataError(f"Diagnostic reported {key} differs from reconciled accounting")
    if not isclose(case["costs"]["initial_cash"], expected["initial_cash"]):
        raise UniverseDataError("Diagnostic cost capital differs from ledger")
    positions = case["metrics"]["open_positions"]
    if {key: r["quantity"] for key, r in positions.items()} != runtime.positions():
        raise UniverseDataError("Diagnostic final reported positions differ from ledger")
    for key, row in positions.items():
        close = float(runtime._bars[key]["close"])
        basis = float(sum(l.basis for l in runtime.ledger.lots if l.instrument_id == key))
        if not isclose(row["last_close"], close) or not isclose(row["marked_unrealized_pnl"], row["quantity"]*close-basis, abs_tol=1e-8):
            raise UniverseDataError("Diagnostic final position price/basis differs from ledger")
    return dict(ledger_reconciled=True, corporate_actions_reconciled=True, external_source_prices_verified=True,
        intraday_equity_observed=False, observed_max_closing_drawdown=expected["max_drawdown"],
        conservative_drawdown_bound=min(r["conservative_drawdown_bound"] for r in runtime.risk_rows),
        conservative_daily_return_bound=min(r["conservative_daily_return_bound"] for r in runtime.risk_rows),
        daily_envelopes=runtime.risk_rows, strict_evidence_approved=False)

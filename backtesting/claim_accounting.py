"""Offline USD ownership accounting for cash rights and corporate-action branches.

This module has no broker, HTTP, credential or strategy imports. Amounts and
share ratios are exact rational numbers. It is an accounting component, not a
strategy simulator or a tax-lot service. See docs/claim_accounting.md for the
valuation, timing and integration contract.
"""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from fractions import Fraction


class AccountingError(ValueError):
    """An unresolved input or inconsistent ledger prevents accounting."""


def instant(value: str | datetime) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
        if not isinstance(result, datetime) or result.tzinfo is None or result.utcoffset() is None:
            raise ValueError
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError) as exc:
        raise AccountingError("Timestamp must be valid and timezone aware") from exc


def number(value, *, positive=False) -> Fraction:
    # Binary floats are deliberately rejected: use a source decimal string.
    if isinstance(value, bool) or not isinstance(value, (str, int, Fraction)):
        raise AccountingError("Use an exact decimal string, integer or Fraction")
    try:
        result = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise AccountingError("Invalid finite rational amount") from exc
    if result < 0 or (positive and result == 0):
        raise AccountingError("Amount/ratio must be positive" if positive else "Amount cannot be negative")
    return result


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise AccountingError(f"{name} requires a nonempty identifier/source")


def exact(value: Fraction) -> str:
    """Lossless report encoding, including nonterminating fractions of a cent."""
    return str(value)


@dataclass(frozen=True)
class Quote:
    instrument_id: str
    timestamp: str | datetime
    low: str
    close: str
    high: str

    def __post_init__(self):
        text(self.instrument_id, "Quote identity")
        object.__setattr__(self, "timestamp", instant(self.timestamp))
        for field in ("low", "close", "high"):
            object.__setattr__(self, field, number(getattr(self, field), positive=True))
        if not self.low <= self.close <= self.high:
            raise AccountingError("Quote requires low <= close <= high")


@dataclass(frozen=True)
class ShareLeg:
    instrument_id: str
    shares_per_parent: str

    def __post_init__(self):
        text(self.instrument_id, "Successor/child identity")
        object.__setattr__(self, "shares_per_parent", number(self.shares_per_parent, positive=True))


@dataclass(frozen=True)
class OwnershipEvent:
    event_id: str
    instrument_id: str
    kind: str  # exchange consumes parent; spinoff/stock_dividend retain parent
    effective_at: str | datetime
    known_at: str | datetime
    source: str
    cash_per_parent: str = "0"
    shares: tuple[ShareLeg, ...] = ()
    terms_complete: bool = False

    def __post_init__(self):
        for name in ("event_id", "instrument_id", "source"):
            text(getattr(self, name), name)
        if self.kind not in {"exchange", "spinoff", "stock_dividend"}:
            raise AccountingError("Unsupported ownership event kind")
        for name in ("effective_at", "known_at"):
            object.__setattr__(self, name, instant(getattr(self, name)))
        object.__setattr__(self, "cash_per_parent", number(self.cash_per_parent))
        if not isinstance(self.shares, tuple) or any(not isinstance(leg, ShareLeg) for leg in self.shares):
            raise AccountingError("Share legs must be an immutable tuple of ShareLeg records")
        if len({leg.instrument_id for leg in self.shares}) != len(self.shares):
            raise AccountingError("Consolidate duplicate destination legs explicitly")
        if not self.cash_per_parent and not self.shares:
            raise AccountingError("Empty terms are not evidence of a zero recovery")
        if self.kind == "stock_dividend":
            if len(self.shares) != 1 or self.shares[0].instrument_id != self.instrument_id or self.cash_per_parent:
                raise AccountingError("Stock dividend requires one same-identity share leg and no cash")
        elif any(leg.instrument_id == self.instrument_id for leg in self.shares):
            raise AccountingError("An exchange/spinoff needs distinct stable successor/child identities")
        if self.kind == "spinoff" and (not self.shares or self.cash_per_parent):
            raise AccountingError("Spinoff requires child shares; cash boot needs separate reviewed terms")
        if type(self.terms_complete) is not bool:
            raise AccountingError("terms_complete must be an explicit boolean")


@dataclass(frozen=True)
class Lot:
    lot_id: str
    instrument_id: str
    quantity: int
    basis: Fraction
    acquired_at: datetime


@dataclass(frozen=True)
class Claim:
    claim_id: str
    event_id: str
    kind: str  # cash or fractional_shares
    instrument_id: str
    units: Fraction
    amount: Fraction | None
    basis: Fraction
    created_at: datetime
    source: str


class ClaimLedger:
    """Long-only simulation ledger; unresolved claims never fund a purchase.

    Every operation is atomic and time ordered. Duplicate instructions raise
    without changing state. Claims persist across sales and window boundaries.
    Public lots/claims are immutable copies; the journal records exact amounts.
    """

    def __init__(self, initial_cash: str):
        self.initial_cash = number(initial_cash, positive=True)
        self.cash = self.initial_cash
        self.realized_pnl = Fraction(0)
        self._lots: list[Lot] = []
        self._claims: dict[str, Claim] = {}
        self._events: set[str] = set()
        self._instructions: set[str] = set()
        self._journal: list[dict] = []
        self._clock: datetime | None = None

    @property
    def lots(self):
        return tuple(self._lots)

    @property
    def claims(self):
        return tuple(self._claims.values())

    @property
    def journal(self):
        return deepcopy(self._journal)

    def quantity(self, instrument_id):
        return sum(lot.quantity for lot in self._lots if lot.instrument_id == instrument_id)

    @contextmanager
    def _operation(self, at):
        at = instant(at)
        if self._clock is not None and at < self._clock:
            raise AccountingError("Accounting clock cannot move backwards")
        previous = deepcopy(self.__dict__)
        try:
            self._clock = at
            yield at
        except Exception:
            self.__dict__.clear()
            self.__dict__.update(previous)
            raise

    def _instruction(self, instruction_id):
        text(instruction_id, "Instruction ID")
        if instruction_id in self._instructions:
            raise AccountingError("Duplicate accounting instruction")
        self._instructions.add(instruction_id)

    @staticmethod
    def _quotes(quotes, ids, at):
        if not isinstance(quotes, dict):
            raise AccountingError("Quotes must be keyed by stable instrument identity")
        for instrument_id in ids:
            q = quotes.get(instrument_id)
            if not isinstance(q, Quote) or q.instrument_id != instrument_id or q.timestamp != at:
                raise AccountingError(f"{instrument_id}: missing exact-time identity-matched quote; no stale/future marks")

    def buy(self, instruction_id, instrument_id, quantity, price, *, at, fee="0"):
        """Record an explicit simulated fill; this never submits an order."""
        with self._operation(at) as at:
            self._instruction(instruction_id)
            text(instrument_id, "Buy identity")
            if type(quantity) is not int or quantity <= 0:
                raise AccountingError("Buy quantity must be positive whole shares")
            price, fee = number(price, positive=True), number(fee)
            cost = quantity * price + fee
            if cost > self.cash:
                raise AccountingError("Insufficient spendable cash; receivables are not buying power")
            self.cash -= cost
            self._lots.append(Lot(f"fill:{instruction_id}", instrument_id, quantity, cost, at))
            self._journal.append(dict(kind="simulated_buy", instruction_id=instruction_id,
                                      timestamp=at.isoformat(), instrument_id=instrument_id,
                                      quantity=quantity, price=exact(price), fee=exact(fee), cost=exact(cost)))

    def sell(self, instruction_id, instrument_id, quantity, price, *, at, fee="0"):
        with self._operation(at) as at:
            self._instruction(instruction_id)
            if type(quantity) is not int or not 0 < quantity <= self.quantity(instrument_id):
                raise AccountingError("Sale requires owned whole shares; fractional claims cannot be sold")
            price, fee = number(price, positive=True), number(fee)
            proceeds = quantity * price - fee
            if self.cash + proceeds < 0:
                raise AccountingError("Sale fees exceed spendable cash and proceeds")
            remaining, basis = quantity, Fraction(0)
            for lot in sorted(self._lots, key=lambda lot: (lot.acquired_at, lot.lot_id)):
                if lot.instrument_id != instrument_id or not remaining:
                    continue
                used = min(remaining, lot.quantity)
                used_basis = lot.basis * used / lot.quantity
                basis += used_basis
                self._lots.remove(lot)
                if used != lot.quantity:
                    self._lots.append(replace(lot, quantity=lot.quantity - used, basis=lot.basis - used_basis))
                remaining -= used
            self.cash += proceeds
            self.realized_pnl += proceeds - basis
            self._journal.append(dict(kind="simulated_sell", instruction_id=instruction_id,
                                      timestamp=at.isoformat(), instrument_id=instrument_id,
                                      quantity=quantity, price=exact(price), fee=exact(fee),
                                      proceeds=exact(proceeds), basis=exact(basis)))

    def recognize(self, event: OwnershipEvent, quotes: dict[str, Quote], *, at):
        """Recognize rights before subsequent fills at this accounting instant.

        Basis is allocated by contemporaneous close fair values, solely for
        economic research reconciliation. No future payout or price is used.
        Unresolved election/proration and unknown-at-effective-time terms fail.
        """
        if not isinstance(event, OwnershipEvent):
            raise AccountingError("An explicit OwnershipEvent is required")
        with self._operation(at) as at:
            if event.event_id in self._events:
                raise AccountingError("Duplicate ownership event")
            if not event.terms_complete:
                raise AccountingError("Election/proration or other ownership terms remain unresolved")
            if at != event.effective_at or event.known_at > at:
                raise AccountingError("Ownership terms must be known by the exact effective accounting instant")
            affected = {event.instrument_id, *(leg.instrument_id for leg in event.shares)}
            if any(row["kind"] in {"simulated_buy", "simulated_sell"}
                   and row["timestamp"] == at.isoformat() and row["instrument_id"] in affected
                   for row in self._journal):
                raise AccountingError("Ownership recognition must precede affected fills at the same instant")
            if any(row["kind"] in {"ownership_event", "ownership_event_unheld"}
                   and row.get("parent_id") == event.instrument_id and row["timestamp"] == at.isoformat()
                   for row in self._journal):
                raise AccountingError("Consolidate same-parent same-instant ownership terms explicitly")
            if any(c.kind == "fractional_shares" and c.instrument_id == event.instrument_id for c in self.claims):
                raise AccountingError("Action on an outstanding fractional claim needs explicit chained-event terms")
            self._events.add(event.event_id)
            parents = [lot for lot in self._lots if lot.instrument_id == event.instrument_id]
            qty = sum(lot.quantity for lot in parents)
            if not qty:
                self._journal.append(dict(kind="ownership_event_unheld", event_id=event.event_id,
                                          parent_id=event.instrument_id, timestamp=at.isoformat(),
                                          known_at=event.known_at.isoformat(), source=event.source))
                return
            retained = event.kind != "exchange"
            required = {leg.instrument_id for leg in event.shares}
            if retained:
                required.add(event.instrument_id)
            self._quotes(quotes, required, at)
            old_basis = sum((lot.basis for lot in parents), Fraction(0))
            oldest = min(lot.acquired_at for lot in parents)
            cash_amount = qty * event.cash_per_parent
            components = []
            if retained:
                components.append(("retained", event.instrument_id, Fraction(qty), qty * quotes[event.instrument_id].close))
            if cash_amount:
                components.append(("cash", event.instrument_id, Fraction(0), cash_amount))
            for leg in event.shares:
                units = qty * leg.shares_per_parent
                components.append(("shares", leg.instrument_id, units, units * quotes[leg.instrument_id].close))
            total_value = sum(item[3] for item in components)
            if total_value <= 0:
                raise AccountingError("Cannot allocate basis without explicit positive component values")
            self._lots = [lot for lot in self._lots if lot.instrument_id != event.instrument_id]
            created_lots, created_claims = [], []
            for index, (kind, instrument_id, units, value) in enumerate(components):
                basis = old_basis * value / total_value
                key = f"action:{event.event_id}:{index}"
                if kind == "cash":
                    claim = Claim(key, event.event_id, "cash", instrument_id, Fraction(0), value, basis, at, event.source)
                    self._claims[key] = claim
                    created_claims.append(key)
                else:
                    whole = units.numerator // units.denominator
                    fraction = units - whole
                    if whole:
                        lot = Lot(key, instrument_id, whole, basis * whole / units, oldest)
                        self._lots.append(lot)
                        created_lots.append(key)
                    if fraction:
                        claim = Claim(key, event.event_id, "fractional_shares", instrument_id, fraction,
                                      None, basis * fraction / units, at, event.source)
                        self._claims[key] = claim
                        created_claims.append(key)
            # Existing successor holdings remain separate lots. Identity changes
            # do not fabricate buys or credit spendable cash. A converted parent
            # holding is aggregated with its oldest age (not tax-lot continuity).
            self._journal.append(dict(
                kind="ownership_event", event_id=event.event_id, event_kind=event.kind,
                timestamp=at.isoformat(), source=event.source, parent_id=event.instrument_id,
                known_at=event.known_at.isoformat(), cash_per_parent=exact(event.cash_per_parent),
                share_terms=[dict(instrument_id=leg.instrument_id, shares_per_parent=exact(leg.shares_per_parent))
                             for leg in event.shares],
                parent_quantity=qty, parent_retained=retained, old_basis=exact(old_basis),
                component_value=exact(total_value), lots_created=created_lots,
                claims_created=created_claims,
                invalidated_execution_state=sorted({event.instrument_id, *required}),
                basis_policy="contemporaneous_close_relative_fair_value_not_tax_basis",
            ))

    def fix_fraction(self, instruction_id, claim_id, total_cash, *, known_at, at, source):
        """Replace fractional ownership with a documented fixed cash right.

        total_cash is the actual reviewed allocation, never an invented market
        sale or a multiplication by a future price. It remains unspendable.
        """
        with self._operation(at) as at:
            self._instruction(instruction_id)
            text(source, "Fractional cash allocation evidence")
            if instant(known_at) > at:
                raise AccountingError("Fractional payout was not known at this instant")
            claim = self._claims.get(claim_id)
            if claim is None or claim.kind != "fractional_shares":
                raise AccountingError("Fixing requires an outstanding fractional-share claim")
            amount = number(total_cash)
            self._claims[claim_id] = replace(claim, kind="cash", amount=amount, source=source)
            self._journal.append(dict(kind="fractional_cash_fixed", instruction_id=instruction_id,
                                      timestamp=at.isoformat(), claim_id=claim_id, amount=exact(amount),
                                      prior_units=exact(claim.units), known_at=instant(known_at).isoformat(), source=source))

    def pay(self, instruction_id, claim_id, amount, *, available_at, known_at, at, source):
        """Credit a cash claim once, at its explicitly evidenced availability.

        There is deliberately no default settlement lag or payable-date guess.
        Missing the modeled credit instant requires a corrected replay.
        """
        with self._operation(at) as at:
            self._instruction(instruction_id)
            text(source, "Spendable-cash evidence/convention")
            if instant(available_at) != at or instant(known_at) > at:
                raise AccountingError("Cash availability must be explicit, exact-time and already known")
            claim = self._claims.get(claim_id)
            if claim is None or claim.kind != "cash":
                raise AccountingError("Payment requires an outstanding fixed cash claim")
            amount = number(amount)
            if amount != claim.amount:
                raise AccountingError("Payment amount differs from the exact outstanding claim")
            self.cash += amount
            self.realized_pnl += amount - claim.basis
            del self._claims[claim_id]
            self._journal.append(dict(kind="claim_paid", instruction_id=instruction_id,
                                      timestamp=at.isoformat(), claim_id=claim_id,
                                      amount=exact(amount), basis=exact(claim.basis),
                                      available_at=instant(available_at).isoformat(),
                                      known_at=instant(known_at).isoformat(), source=source))

    def mark(self, quotes: dict[str, Quote], *, at) -> dict:
        """Reconcile cash, rights, owned shares and current-ownership OHLC bounds.

        Bounds assume simultaneous highs/lows and are not observed intraday
        portfolio values. They exclude pre-event/pre-fill holdings and cannot
        certify a complete session drawdown. Fixed cash rights are nominal
        USD, not risk free.
        """
        with self._operation(at) as at:
            units = {}
            for lot in self.lots:
                units[lot.instrument_id] = units.get(lot.instrument_id, Fraction(0)) + lot.quantity
            for claim in self.claims:
                if claim.kind == "fractional_shares":
                    units[claim.instrument_id] = units.get(claim.instrument_id, Fraction(0)) + claim.units
            self._quotes(quotes, units, at)
            stock = sum((qty * quotes[key].close for key, qty in units.items()), Fraction(0))
            cash_claims = sum((c.amount for c in self.claims if c.kind == "cash"), Fraction(0))
            basis = sum((lot.basis for lot in self.lots), Fraction(0)) + sum((c.basis for c in self.claims), Fraction(0))
            equity = self.cash + cash_claims + stock
            unrealized = cash_claims + stock - basis
            if equity != self.initial_cash + self.realized_pnl + unrealized:
                raise AccountingError("Cash / economic basis / P&L reconciliation failed")
            return dict(
                accounting_ledger_version=1,
                timestamp=at.isoformat(), simulated_money=True, spendable_cash=exact(self.cash),
                fixed_cash_receivables=exact(cash_claims), stock_and_fraction_value=exact(stock),
                equity=exact(equity), gross_exposure=exact(stock / equity) if equity else None,
                equity_lower_bound=exact(self.cash + cash_claims + sum(qty * quotes[key].low for key, qty in units.items())),
                equity_upper_bound=exact(self.cash + cash_claims + sum(qty * quotes[key].high for key, qty in units.items())),
                economic_book_basis=exact(basis), realized_pnl=exact(self.realized_pnl), unrealized_pnl=exact(unrealized),
                reconciliation_passed=True,
                lots=[dict(lot_id=lot.lot_id, instrument_id=lot.instrument_id, quantity=lot.quantity,
                           basis=exact(lot.basis), acquired_at=lot.acquired_at.isoformat()) for lot in self.lots],
                claims=[dict(claim_id=c.claim_id, event_id=c.event_id, kind=c.kind, instrument_id=c.instrument_id,
                             units=exact(c.units), amount=None if c.amount is None else exact(c.amount),
                             basis=exact(c.basis), created_at=c.created_at.isoformat(), source=c.source) for c in self.claims],
                limitations=["Nominal fixed cash rights: credit risk/discounting not modeled",
                             "OHLC bounds are conservative, not an observed intraday path",
                             "Current-ownership snapshot bounds exclude pre-event/pre-fill holdings",
                             "Economic basis convention; not tax accounting or broker settlement proof"],
            )

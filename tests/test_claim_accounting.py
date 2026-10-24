"""Focused offline checks requested before expanding the historical backtest."""

from dataclasses import replace
from copy import deepcopy
from fractions import Fraction as F
import unittest

from backtesting.claim_accounting import (
    AccountingError, ClaimLedger, OwnershipEvent, Quote, ShareLeg,
)

PRIOR = "2018-11-27T21:00:00Z"
NOW = "2018-11-28T21:00:00Z"
LATER = "2018-11-29T21:00:00Z"
LAST = "2018-11-30T21:00:00Z"
SOURCE = "synthetic focused-check convention; not actual payment evidence"


def quote(identity="CVS", *, at=NOW):
    return Quote(identity, at, "60", "65", "70")


def event(**changes):
    value = OwnershipEvent("AET-CVS", "AET", "exchange", NOW, PRIOR, SOURCE,
                           "145", (ShareLeg("CVS", "0.8378"),), terms_complete=True)
    return replace(value, **changes)


def seeded():
    ledger = ClaimLedger("1000")
    ledger.buy("entry", "AET", 3, "200", at=PRIOR)
    return ledger


class ClaimAccountingTests(unittest.TestCase):
    def test_mixed_merger_exact_quantity_cash_and_basis(self):
        ledger = seeded()
        ledger.recognize(event(), {"CVS": quote()}, at=NOW)
        self.assertEqual(ledger.quantity("AET"), 0)
        self.assertEqual(ledger.quantity("CVS"), 2)
        self.assertEqual(ledger.cash, 400)
        self.assertEqual(sum((lot.basis for lot in ledger.lots), F(0)) + sum(c.basis for c in ledger.claims), 600)
        self.assertEqual(next(c.units for c in ledger.claims if c.kind == "fractional_shares"), F("0.5134"))
        self.assertEqual(next(c.amount for c in ledger.claims if c.kind == "cash"), 435)
        self.assertEqual(ledger.lots[0].acquired_at.isoformat(), "2018-11-27T21:00:00+00:00")
        self.assertTrue(ledger.mark({"CVS": quote()}, at=NOW)["reconciliation_passed"])

    def test_delayed_cash_is_equity_but_not_buying_power(self):
        ledger = seeded()
        ledger.recognize(event(shares=(), cash_per_parent="145"), {}, at=NOW)
        mark = ledger.mark({}, at=NOW)
        self.assertEqual(F(mark["equity"]), 835)
        self.assertEqual(F(mark["spendable_cash"]), 400)
        with self.assertRaisesRegex(AccountingError, "buying power"):
            ledger.buy("unfunded", "OTHER", 5, "100", at=NOW)
        self.assertEqual(len(ledger.lots), 0)

    def test_payment_credits_once_and_removes_claim(self):
        ledger = seeded()
        ledger.recognize(event(shares=()), {}, at=NOW)
        claim = ledger.claims[0]
        ledger.pay("payment", claim.claim_id, "435", available_at=LATER, known_at=NOW, at=LATER, source=SOURCE)
        self.assertEqual(ledger.cash, 835)
        self.assertEqual(ledger.claims, ())
        self.assertEqual(ledger.realized_pnl, -165)
        with self.assertRaises(AccountingError):
            ledger.pay("payment-again", claim.claim_id, "435", available_at=LATER, known_at=NOW, at=LATER, source=SOURCE)
        with self.assertRaisesRegex(AccountingError, "Duplicate"):
            ledger.pay("payment", claim.claim_id, "435", available_at=LATER, known_at=NOW, at=LATER, source=SOURCE)
        self.assertEqual(ledger.cash, 835)
        self.assertTrue(ledger.mark({}, at=LATER)["reconciliation_passed"])

    def test_payment_requires_known_exact_amount_and_available_time(self):
        for amount, available, known in (("434", LATER, NOW), ("435", LAST, NOW), ("435", LATER, LAST)):
            with self.subTest(amount=amount, available=available, known=known):
                ledger = seeded()
                ledger.recognize(event(shares=()), {}, at=NOW)
                before = deepcopy(ledger.__dict__)
                with self.assertRaises(AccountingError):
                    ledger.pay("bad", ledger.claims[0].claim_id, amount, available_at=available,
                               known_at=known, at=LATER, source=SOURCE)
                self.assertEqual(ledger.__dict__, before)

    def test_fraction_survives_sale_and_has_price_exposure(self):
        ledger = seeded()
        ledger.recognize(event(), {"CVS": quote()}, at=NOW)
        ledger.sell("exit", "CVS", 2, "65", at=NOW)
        mark = ledger.mark({"CVS": quote()}, at=NOW)
        self.assertEqual(F(mark["stock_and_fraction_value"]), F("0.5134") * 65)
        self.assertEqual(F(mark["equity_upper_bound"]) - F(mark["equity_lower_bound"]), F("0.5134") * 10)
        self.assertEqual(len(ledger.claims), 2)
        with self.assertRaises(AccountingError):
            ledger.sell("fraction-sale", "CVS", 1, "65", at=NOW)

    def test_fraction_fixing_then_delayed_payment(self):
        ledger = seeded()
        ledger.recognize(event(), {"CVS": quote()}, at=NOW)
        claim = next(c for c in ledger.claims if c.kind == "fractional_shares")
        ledger.fix_fraction("fix", claim.claim_id, "33.20", known_at=LATER, at=LATER, source=SOURCE)
        self.assertEqual(ledger.cash, 400)
        mark = ledger.mark({"CVS": quote(at=LATER)}, at=LATER)
        self.assertEqual(F(mark["stock_and_fraction_value"]), 130)
        self.assertEqual(F(mark["fixed_cash_receivables"]), F("468.20"))
        ledger.pay("fraction-pay", claim.claim_id, "33.20", available_at=LAST, known_at=LATER, at=LAST, source=SOURCE)
        self.assertEqual(ledger.cash, F("433.20"))
        self.assertTrue(ledger.mark({"CVS": quote(at=LAST)}, at=LAST)["reconciliation_passed"])
        with self.assertRaises(AccountingError):
            ledger.fix_fraction("fix-again", claim.claim_id, "33.20", known_at=LAST, at=LAST, source=SOURCE)

    def test_unpriced_or_future_fraction_fix_rejected(self):
        for known, amount in ((LAST, "30"), (NOW, "-1"), (NOW, float("nan"))):
            with self.subTest(known=known, amount=amount):
                ledger = seeded()
                ledger.recognize(event(), {"CVS": quote()}, at=NOW)
                claim = next(c for c in ledger.claims if c.kind == "fractional_shares")
                with self.assertRaises(AccountingError):
                    ledger.fix_fraction("bad", claim.claim_id, amount, known_at=known, at=LATER, source=SOURCE)
                self.assertEqual(len(ledger.claims), 2)
                self.assertEqual(ledger.cash, 400)

    def test_fraction_cannot_be_paid_before_fixing(self):
        ledger = seeded()
        ledger.recognize(event(), {"CVS": quote()}, at=NOW)
        claim = next(c for c in ledger.claims if c.kind == "fractional_shares")
        with self.assertRaisesRegex(AccountingError, "fixed cash"):
            ledger.pay("bad", claim.claim_id, "30", available_at=LATER, known_at=NOW, at=LATER, source=SOURCE)

    def test_spinoff_retains_parent_and_exact_child_fraction(self):
        ledger = seeded()
        e = event(kind="spinoff", cash_per_parent="0", shares=(ShareLeg("CHILD", "1/4"),))
        quotes = {"AET": quote("AET"), "CHILD": quote("CHILD")}
        ledger.recognize(e, quotes, at=NOW)
        self.assertEqual(ledger.quantity("AET"), 3)
        self.assertEqual(ledger.quantity("CHILD"), 0)
        self.assertEqual(ledger.claims[0].units, F(3, 4))
        self.assertEqual(sum(lot.basis for lot in ledger.lots) + ledger.claims[0].basis, 600)
        self.assertTrue(ledger.mark(quotes, at=NOW)["reconciliation_passed"])

    def test_stock_dividend_same_identity(self):
        ledger = seeded()
        e = event(kind="stock_dividend", cash_per_parent="0", shares=(ShareLeg("AET", "1/2"),))
        ledger.recognize(e, {"AET": quote("AET")}, at=NOW)
        self.assertEqual(ledger.quantity("AET"), 4)
        self.assertEqual(ledger.claims[0].units, F(1, 2))
        self.assertTrue(ledger.mark({"AET": quote("AET")}, at=NOW)["reconciliation_passed"])

    def test_existing_successor_position_preserved_as_separate_lot(self):
        ledger = seeded()
        ledger.buy("existing", "CVS", 1, "60", at=PRIOR)
        ledger.recognize(event(), {"CVS": quote()}, at=NOW)
        self.assertEqual(ledger.quantity("CVS"), 3)
        self.assertEqual(len(ledger.lots), 2)
        ledger.sell("partial-exit", "CVS", 1, "66", at=NOW, fee="1")
        self.assertTrue(ledger.mark({"CVS": quote()}, at=NOW)["reconciliation_passed"])

    def test_duplicate_event_does_not_double_shares_or_cash(self):
        ledger = seeded()
        ledger.recognize(event(), {"CVS": quote()}, at=NOW)
        before = ledger.mark({"CVS": quote()}, at=NOW)
        with self.assertRaisesRegex(AccountingError, "Duplicate"):
            ledger.recognize(event(), {"CVS": quote()}, at=NOW)
        self.assertEqual(before, ledger.mark({"CVS": quote()}, at=NOW))

    def test_unknown_or_unresolved_event_rejected_atomically(self):
        for e in (event(known_at=LATER), event(terms_complete=False), event(effective_at=LATER)):
            with self.subTest(event=e):
                ledger = seeded()
                with self.assertRaises(AccountingError):
                    ledger.recognize(e, {"CVS": quote()}, at=NOW)
                self.assertEqual(ledger.quantity("AET"), 3)
                self.assertEqual(ledger.cash, 400)
                ledger.recognize(event(), {"CVS": quote()}, at=NOW)  # Failed attempt did not consume event ID.

    def test_missing_wrong_identity_stale_and_future_quotes_rejected(self):
        for quotes in ({}, {"CVS": quote("OTHER")}, {"CVS": quote(at=PRIOR)}, {"CVS": quote(at=LATER)}):
            with self.subTest(quotes=quotes):
                ledger = seeded()
                with self.assertRaisesRegex(AccountingError, "quote"):
                    ledger.recognize(event(), quotes, at=NOW)
                self.assertEqual(ledger.quantity("AET"), 3)

    def test_action_on_outstanding_fraction_requires_chained_terms(self):
        ledger = seeded()
        ledger.recognize(event(), {"CVS": quote()}, at=NOW)
        e = event(event_id="NEXT", instrument_id="CVS", effective_at=LATER, shares=())
        with self.assertRaisesRegex(AccountingError, "chained-event"):
            ledger.recognize(e, {}, at=LATER)

    def test_unheld_event_creates_no_rights_and_is_still_deduplicated(self):
        ledger = ClaimLedger("1000")
        ledger.recognize(event(), {}, at=NOW)
        self.assertEqual(ledger.claims, ())
        with self.assertRaises(AccountingError):
            ledger.recognize(event(), {}, at=NOW)

    def test_invalid_inputs_rejected(self):
        inputs = [lambda: ClaimLedger(float("inf")), lambda: ClaimLedger("NaN"),
                  lambda: ShareLeg("CVS", "0"), lambda: ShareLeg("CVS", "-1"),
                  lambda: quote(at="2018-11-28"), lambda: Quote("CVS", NOW, "70", "65", "60"),
                  lambda: event(shares=(), cash_per_parent="0"),
                  lambda: event(shares=(ShareLeg("AET", "1"),)),
                  lambda: event(shares=(ShareLeg("CVS", "1"), ShareLeg("CVS", "1"))),
                  lambda: event(source=""), lambda: event(terms_complete="yes")]
        for make in inputs:
            with self.subTest(make=make), self.assertRaises(AccountingError):
                make()

    def test_clock_prevents_using_future_mark_then_backdating_event(self):
        ledger = seeded()
        ledger.mark({"AET": quote("AET", at=LATER)}, at=LATER)
        with self.assertRaisesRegex(AccountingError, "backwards"):
            ledger.recognize(event(), {"CVS": quote()}, at=NOW)

    def test_immutable_claims_and_journal_snapshot(self):
        ledger = seeded()
        ledger.recognize(event(), {"CVS": quote()}, at=NOW)
        copy = ledger.journal
        copy[-1]["invalidated_execution_state"].clear()
        self.assertTrue(ledger.journal[-1]["invalidated_execution_state"])

    def test_partial_sales_and_fees_reconcile(self):
        ledger = ClaimLedger("1000")
        ledger.buy("one", "CVS", 3, "60", at=PRIOR, fee="1")
        ledger.buy("two", "CVS", 2, "61", at=PRIOR, fee="1")
        ledger.sell("partial", "CVS", 4, "65", at=NOW, fee="1")
        self.assertEqual(ledger.quantity("CVS"), 1)
        self.assertTrue(ledger.mark({"CVS": quote()}, at=NOW)["reconciliation_passed"])

    def test_legacy_risk_diagnostics_cannot_silently_ignore_claims(self):
        from backtesting.risk_diagnostics import daily_risk_envelope
        ledger = seeded()
        ledger.recognize(event(shares=()), {}, at=NOW)
        with self.assertRaisesRegex(ValueError, "must not omit"):
            daily_risk_envelope(ledger.mark({}, at=NOW), {})

    def test_unapproved_terms_fail_closed_by_default(self):
        e = OwnershipEvent("unreviewed", "AET", "exchange", NOW, PRIOR, SOURCE, "145")
        ledger = seeded()
        with self.assertRaisesRegex(AccountingError, "unresolved"):
            ledger.recognize(e, {}, at=NOW)

    def test_event_must_precede_fills_at_same_instant(self):
        ledger = seeded()
        ledger.sell("same-time-sale", "AET", 1, "200", at=NOW)
        with self.assertRaisesRegex(AccountingError, "precede"):
            ledger.recognize(event(), {"CVS": quote()}, at=NOW)

    def test_same_instant_distributions_must_be_consolidated(self):
        ledger = seeded()
        e = event(kind="spinoff", cash_per_parent="0", shares=(ShareLeg("CVS", "1"),))
        quotes = {"AET": quote("AET"), "CVS": quote()}
        ledger.recognize(e, quotes, at=NOW)
        with self.assertRaisesRegex(AccountingError, "Consolidate"):
            ledger.recognize(replace(e, event_id="other"), quotes, at=NOW)

    def test_fractional_mark_requires_quote_after_whole_shares_sold(self):
        ledger = seeded()
        ledger.recognize(event(), {"CVS": quote()}, at=NOW)
        ledger.sell("exit", "CVS", 2, "65", at=NOW)
        with self.assertRaisesRegex(AccountingError, "quote"):
            ledger.mark({}, at=LATER)
        self.assertTrue(ledger.mark({"CVS": quote(at=LATER)}, at=LATER)["reconciliation_passed"])

    def test_multiple_child_branches_conserve_all_basis(self):
        ledger = seeded()
        e = event(kind="spinoff", cash_per_parent="0",
                  shares=(ShareLeg("CHILD-A", "1/3"), ShareLeg("CHILD-B", "1/4")))
        quotes = {identity: quote(identity) for identity in ("AET", "CHILD-A", "CHILD-B")}
        ledger.recognize(e, quotes, at=NOW)
        self.assertEqual(ledger.quantity("CHILD-A"), 1)
        self.assertEqual(ledger.quantity("CHILD-B"), 0)
        self.assertEqual(sum(lot.basis for lot in ledger.lots) + sum(c.basis for c in ledger.claims), 600)
        self.assertTrue(ledger.mark(quotes, at=NOW)["reconciliation_passed"])


if __name__ == "__main__":
    unittest.main()

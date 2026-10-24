"""Risk-ledger tests across splits, dividend claims and terminal cash."""

from copy import deepcopy

from backtesting.daily_research import pack
from backtesting.portfolio_engine import summarize_portfolio
from backtesting.risk_diagnostics import daily_risk_envelope
from backtesting.universe import CashDividend, CashOutcome, SplitAction
from tests.test_universe import UniverseFixture


class ActionRiskTests(UniverseFixture):
    def case(self, *, split=False, dividend=False, terminal=False, paid=True):
        splits = [SplitAction("split", "ID-A", self.day(202), 2, 1, self.known(202), "synthetic")] if split else []
        dividends = [CashDividend("div", "ID-A", self.day(202), self.day(205 if paid else 209), 1, self.known(202), "synthetic")] if dividend else []
        outcomes = [CashOutcome("cash", "ID-A", self.day(204), 110, self.known(204), "synthetic")] if terminal else []
        universe = self.universe(listings=[self.listing(end=204 if terminal else None)], cash=outcomes,
                                 action_scope="explicit_splits_and_ordinary_cash_dividends", splits=splits, dividends=dividends)
        data = self.bars(end=204 if terminal else 208)
        if split:
            data.loc[202:, ["open", "high", "low", "close"]] = 50
            data.loc[202:, "volume"] = 2000
        result = self.run_case(universe, data)
        return pack(result), {"ID-A": data}

    def test_split_has_no_mechanical_drawdown(self):
        case, data = self.case(split=True)
        risk = daily_risk_envelope(case, data)
        self.assertEqual(risk["observed_max_closing_drawdown"], 0)
        self.assertEqual(risk["conservative_drawdown_bound"], 0)

    def test_paid_and_unpaid_dividends_both_reconcile(self):
        for paid in (True, False):
            with self.subTest(paid=paid):
                case, data = self.case(dividend=True, paid=paid)
                risk = daily_risk_envelope(case, data)
                self.assertTrue(risk["ledger_reconciled"])
                self.assertEqual(risk["daily_envelopes"][-1]["dividend_receivable_at_close"], 0 if paid else 10)

    def test_terminal_cash_does_not_require_a_fabricated_price(self):
        case, data = self.case(terminal=True)
        risk = daily_risk_envelope(case, data)
        self.assertEqual(risk["daily_envelopes"][-1]["cash_at_close"], 10100)

    def test_combined_split_dividend_and_terminal_payment(self):
        case, data = self.case(split=True, dividend=True, terminal=True)
        risk = daily_risk_envelope(case, data)
        self.assertEqual(risk["daily_envelopes"][-1]["cash_at_close"], 11220)

    def test_corrupted_split_quantity_fails(self):
        case, data = self.case(split=True)
        case["share_actions"][0]["new_quantity"] += 1
        with self.assertRaisesRegex(ValueError, "Split"):
            daily_risk_envelope(case, data)

    def test_dropped_split_event_fails_reconciliation(self):
        case, data = self.case(split=True)
        case["share_actions"] = []
        with self.assertRaisesRegex(ValueError, "equity"):
            daily_risk_envelope(case, data)

    def test_duplicate_dividend_entitlement_fails(self):
        case, data = self.case(dividend=True)
        case["dividend_entitlements"] *= 2
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            daily_risk_envelope(case, data)

    def test_dividend_claim_cannot_be_changed_to_cash_early(self):
        case, data = self.case(dividend=True)
        case["dividend_payments"][0]["timestamp"] = self.dates[204].isoformat()
        with self.assertRaisesRegex(ValueError, "entitlement/date"):
            daily_risk_envelope(case, data)

    def test_tampered_cash_point_fails(self):
        case, data = self.case(dividend=True)
        case["equity_curve"][-1]["cash"] += 100
        with self.assertRaisesRegex(ValueError, "saved cash"):
            daily_risk_envelope(case, data)

    def test_tampered_final_receivable_fails(self):
        case, data = self.case(dividend=True, paid=False)
        case["final_dividend_receivables"] = []
        with self.assertRaisesRegex(ValueError, "final dividend"):
            daily_risk_envelope(case, data)

    def test_terminal_amount_must_match_rate(self):
        case, data = self.case(terminal=True)
        case["cash_settlements"][0]["total_cash"] += 1
        with self.assertRaisesRegex(ValueError, "terminal cash"):
            daily_risk_envelope(case, data)

    def test_action_outside_equity_dates_fails(self):
        case, data = self.case(split=True)
        case["share_actions"][0]["timestamp"] = self.dates[209].isoformat()
        with self.assertRaisesRegex(ValueError, "outside"):
            daily_risk_envelope(case, data)

    def test_action_metadata_is_required(self):
        case, data = self.case(split=True)
        del case["universe_metadata"]
        with self.assertRaisesRegex(ValueError, "metadata"):
            daily_risk_envelope(case, data)

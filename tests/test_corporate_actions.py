"""Synthetic split/dividend accounting and causal-history checks."""

from dataclasses import replace

import pandas as pd

from app.strategy.base import SignalAction
from backtesting.corporate_actions import feature_views
from backtesting.daily_research import pack
from backtesting.holding_policy import HoldingPolicy
from backtesting.portfolio_engine import summarize_portfolio
from backtesting.protective_exits import ProtectiveExitConfig
from backtesting.risk_diagnostics import daily_risk_envelope
from backtesting.universe import CashDividend, CashOutcome, SplitAction, UniverseDataError
from tests.test_universe import UniverseFixture


class CorporateActionTests(UniverseFixture):
    def split(self, *, index=202, new=2, old=1, event_id="split-1"):
        return SplitAction(event_id, "ID-A", self.day(index), new, old, self.known(index), "synthetic split evidence")

    def dividend(self, *, ex=202, pay=205, amount=1):
        return CashDividend("div-1", "ID-A", self.day(ex), self.day(pay), amount, self.known(ex), "synthetic ordinary dividend")

    def action_universe(self, *, splits=None, dividends=None, **kwargs):
        return self.universe(action_scope="explicit_splits_and_ordinary_cash_dividends", splits=splits, dividends=dividends, **kwargs)

    def split_bars(self, ratio=2):
        frame = self.bars()
        frame["volume"] = frame["volume"].astype(float)
        frame[["open", "high", "low", "close"]] = frame[["open", "high", "low", "close"]].astype(float)
        frame.loc[202:, ["open", "high", "low", "close"]] /= ratio
        frame.loc[202:, "volume"] *= ratio
        return frame

    def test_forward_split_preserves_equity_and_basis_without_trade(self):
        result = self.run_case(self.action_universe(splits=[self.split()]), self.split_bars())
        self.assertEqual(result.final_positions, {"ID-A": 20})
        self.assertEqual(result.equity_curve[-1].equity, 10000)
        self.assertEqual(summarize_portfolio(result)["open_positions"]["ID-A"]["marked_unrealized_pnl"], 0)
        self.assertEqual(len(result.fills), 1)

    def test_reverse_split_preserves_whole_share_value(self):
        result = self.run_case(self.action_universe(splits=[self.split(new=1, old=2)]), self.split_bars(.5))
        self.assertEqual(result.final_positions, {"ID-A": 5})
        self.assertEqual(summarize_portfolio(result)["final_equity"], 10000)

    def test_fractional_owned_split_requires_cash_in_lieu_evidence(self):
        with self.assertRaisesRegex(UniverseDataError, "fractional"):
            self.run_case(self.action_universe(splits=[self.split(new=1, old=3)]), self.split_bars(1 / 3))

    def test_sell_after_split_closes_converted_quantity(self):
        result = self.run_case(self.action_universe(splits=[self.split()]), self.split_bars(),
                               self.engine({("ID-A", 199): SignalAction.BUY, ("ID-A", 203): SignalAction.SELL}))
        self.assertEqual(result.fills[-1].quantity, 20)
        self.assertEqual(summarize_portfolio(result)["completed_trades"], 1)
        self.assertEqual(summarize_portfolio(result)["realized_pnl_by_symbol"], {"ID-A": 0})

    def test_split_rebases_pending_buy_ceiling_before_execution(self):
        result = self.run_case(self.action_universe(splits=[self.split()]), self.split_bars(), self.engine({("ID-A", 201): SignalAction.BUY}))
        self.assertEqual(result.fills[0].quantity, 20)
        self.assertEqual(result.fills[0].fill_price, 50)
        self.assertEqual(summarize_portfolio(result)["final_equity"], 10000)

    def test_past_feature_views_do_not_use_future_split(self):
        universe = self.action_universe(splits=[self.split()])
        source = self.split_bars()
        prepared = universe.prepare("ID-A", source)
        original = prepared.copy(deep=True)
        views, _ = feature_views(prepared, "ID-A", universe, 252)
        self.assertEqual(views[201].loc[201, "close"], 100)
        self.assertEqual(views[202].loc[201, "close"], 50)
        self.assertAlmostEqual(views[202].loc[202, "ema_200"], 50)
        self.assertAlmostEqual(views[202].loc[202, "return_1"], 0)
        self.assertEqual(views[202].loc[201, "volume"], 2000)
        pd.testing.assert_frame_equal(prepared, original)

    def test_late_split_knowledge_rejected(self):
        with self.assertRaisesRegex(UniverseDataError, "not known"):
            self.action_universe(splits=[replace(self.split(), known_at=self.sessions[202].closes_at.isoformat())])

    def test_split_rebases_protective_stop(self):
        data = self.split_bars()
        data["high"] = data["close"] * 1.01
        data["low"] = data["close"] * .99
        result = self.run_case(self.action_universe(splits=[self.split()]), data,
                               self.engine(protection=ProtectiveExitConfig(atr_multiple=3, max_risk_per_trade=.01, trailing=False)))
        self.assertAlmostEqual(result.final_stops["ID-A"], 47)
        self.assertEqual(len(result.fills), 1)

    def test_split_preserves_holding_age_review(self):
        result = self.run_case(self.action_universe(splits=[self.split()]), self.split_bars(),
                               self.engine(holding_policy=HoldingPolicy("maximum", first_review=6)))
        self.assertEqual(result.fills[-1].timestamp, self.dates[206])
        self.assertEqual(result.fills[-1].quantity, 20)
        self.assertEqual(summarize_portfolio(result)["completed_trades"], 1)

    def test_invalid_split_ratios_rejected(self):
        for new, old in ((0, 1), (1, 0), (True, 2), (2, 2), (1.5, 1)):
            with self.subTest(new=new, old=old), self.assertRaises(UniverseDataError):
                self.split(new=new, old=old)

    def test_duplicate_action_ids_rejected_across_event_types(self):
        with self.assertRaisesRegex(UniverseDataError, "Duplicate"):
            self.action_universe(splits=[self.split(event_id="div-1")], dividends=[self.dividend()])

    def test_actions_require_explicit_scope(self):
        with self.assertRaisesRegex(UniverseDataError, "event-free"):
            self.universe(splits=[self.split()])

    def test_dividend_receivable_offsets_ex_date_price_drop(self):
        data = self.bars()
        data.loc[202:, ["open", "high", "low", "close"]] = 99
        result = self.run_case(self.action_universe(dividends=[self.dividend()]), data)
        point = result.equity_curve[202]
        self.assertEqual(point.equity, 10000)
        self.assertEqual(point.cash, 9000)
        self.assertEqual(point.dividend_receivable, 10)
        self.assertEqual(result.equity_curve[205].cash, 9010)
        self.assertEqual(result.equity_curve[205].dividend_receivable, 0)
        self.assertEqual(summarize_portfolio(result)["dividend_income_earned"], 10)

    def test_ex_date_buyer_is_not_entitled(self):
        result = self.run_case(self.action_universe(dividends=[self.dividend()]), engine=self.engine({("ID-A", 201): SignalAction.BUY}))
        self.assertFalse(result.dividend_entitlements)
        self.assertFalse(result.dividend_payments)

    def test_ex_date_seller_keeps_receivable_after_sale(self):
        result = self.run_case(self.action_universe(dividends=[self.dividend()]),
                               engine=self.engine({("ID-A", 199): SignalAction.BUY, ("ID-A", 201): SignalAction.SELL}))
        self.assertEqual(result.final_positions, {})
        self.assertEqual(result.dividend_payments[0]["amount"], 10)
        self.assertEqual(summarize_portfolio(result)["final_equity"], 10010)

    def test_payment_after_window_remains_receivable_not_cash(self):
        result = self.run_case(self.action_universe(dividends=[self.dividend(pay=209)]))
        self.assertEqual(result.equity_curve[-1].cash, 9000)
        self.assertEqual(result.final_dividend_receivables[0]["amount"], 10)
        self.assertEqual(summarize_portfolio(result)["dividend_receivable"], 10)
        self.assertFalse(result.dividend_payments)

    def test_same_day_split_then_dividend_uses_post_split_shares(self):
        result = self.run_case(self.action_universe(splits=[self.split()], dividends=[self.dividend()]), self.split_bars())
        self.assertEqual(result.dividend_entitlements[0]["quantity"], 20)
        self.assertEqual(summarize_portfolio(result)["final_equity"], 10020)

    def test_dividend_amount_is_not_multiplied_by_a_later_split(self):
        result = self.run_case(self.action_universe(splits=[self.split()], dividends=[self.dividend(ex=201)]), self.split_bars())
        self.assertEqual(result.dividend_payments[0]["amount"], 10)
        self.assertEqual(summarize_portfolio(result)["final_equity"], 10010)

    def test_dividend_claim_survives_a_terminal_cash_exit(self):
        outcome = CashOutcome("terminal", "ID-A", self.day(203), 110, self.known(203), "synthetic cash exit")
        universe = self.action_universe(listings=[self.listing(end=203)], cash=[outcome], dividends=[self.dividend()])
        result = self.run_case(universe, self.bars(end=203))
        self.assertEqual(summarize_portfolio(result)["final_equity"], 10110)
        self.assertEqual(result.dividend_payments[0]["amount"], 10)

    def test_multiple_splits_preserve_basis(self):
        second = self.split(index=204, new=3, event_id="split-2")
        data = self.split_bars()
        data.loc[204:, ["open", "high", "low", "close"]] /= 3
        data.loc[204:, "volume"] *= 3
        result = self.run_case(self.action_universe(splits=[self.split(), second]), data)
        self.assertEqual(result.final_positions["ID-A"], 60)
        self.assertAlmostEqual(summarize_portfolio(result)["final_equity"], 10000)

    def test_special_dividend_rejected(self):
        with self.assertRaisesRegex(UniverseDataError, "Special"):
            replace(self.dividend(), kind="special_due_bill")

    def test_payment_before_ex_date_rejected(self):
        with self.assertRaisesRegex(UniverseDataError, "precede"):
            self.dividend(pay=201)

    def test_old_risk_helper_refuses_to_drop_corporate_actions(self):
        result = self.run_case(self.action_universe(dividends=[self.dividend()]))
        with self.assertRaisesRegex(ValueError, "corporate-action"):
            daily_risk_envelope(pack(result), {"ID-A": self.bars()})

    def test_tampered_dividend_ledger_is_rejected(self):
        result = self.run_case(self.action_universe(dividends=[self.dividend()]))
        bad = replace(result, dividend_entitlements=({**result.dividend_entitlements[0], "amount": 999},))
        with self.assertRaisesRegex(ValueError, "amount"):
            summarize_portfolio(bad)

    def test_dividend_after_sale_is_not_counted_as_a_completed_stock_trade(self):
        result = self.run_case(self.action_universe(dividends=[self.dividend()]))
        metrics = summarize_portfolio(result)
        self.assertEqual(metrics["completed_trades"], 0)
        self.assertEqual(pack(result)["metrics"]["instruments_with_closed_trades"], 0)

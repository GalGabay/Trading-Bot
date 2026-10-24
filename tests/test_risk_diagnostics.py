"""Hand-calculated long-only ledgers and daily-envelope failure cases."""

from copy import deepcopy
from unittest import TestCase

import pandas as pd

from backtesting.risk_diagnostics import daily_risk_envelope
from tests.test_portfolio_backtesting import daily_candles


class RiskEnvelopeTests(TestCase):
    dates = ["2022-01-03T05:00:00Z", "2022-01-04T05:00:00Z"]

    def fixture(self):
        frame = daily_candles("AAPL", self.dates, [100., 100.], [100., 100.], lows=[90., 90.], highs=[110., 110.])
        case = {"costs": {"initial_cash": 1000},
                "fills": [self.fill("BUY", 5, 100, 0)],
                "equity_curve": [{"timestamp": day, "equity": 1000, "exposure": .5} for day in self.dates],
                "metrics": {"open_positions": {"AAPL": {"quantity": 5}}}}
        return case, {"AAPL": frame}

    def fill(self, side, quantity, price, day, *, reason="rule", commission=0, symbol="AAPL"):
        return {"timestamp": self.dates[day], "symbol": symbol, "side": side, "quantity": quantity,
                "fill_price": price, "commission": commission, "signal_reason": reason}

    def test_flat_closes_can_hide_a_large_unobserved_envelope(self):
        case, data = self.fixture()
        original = deepcopy(case)
        report = daily_risk_envelope(case, data)
        self.assertEqual(report["observed_max_closing_drawdown"], 0)
        self.assertAlmostEqual(report["conservative_drawdown_bound"], 950 / 1050 - 1)
        self.assertAlmostEqual(report["conservative_daily_return_bound"], -.05)
        self.assertFalse(report["intraday_equity_observed"])
        self.assertTrue(report["ledger_reconciled"])
        self.assertEqual(case, original)

    def test_all_cash_account_has_zero_exposure_and_no_invented_prices(self):
        case, _ = self.fixture()
        case["fills"] = []
        case["metrics"]["open_positions"] = {}
        for point in case["equity_curve"]:
            point["exposure"] = 0
        report = daily_risk_envelope(case, {})
        self.assertEqual(report["conservative_drawdown_bound"], 0)
        self.assertEqual(report["daily_envelopes"][0]["cash_at_close"], 1000)

    def test_gap_exit_does_not_keep_exposure_to_later_daily_extremes(self):
        case, data = self.fixture()
        data["AAPL"].loc[1, ["open", "high", "low", "close"]] = [80, 300, 10, 200]
        case["fills"].append(self.fill("SELL", 5, 79, 1, reason="PROTECTIVE_STOP_GAP_OPEN: active stop 90", commission=1))
        case["equity_curve"][1].update(equity=894, exposure=0)
        case["metrics"]["open_positions"] = {}
        row = daily_risk_envelope(case, data)["daily_envelopes"][1]
        self.assertEqual(row["equity_lower_envelope"], 894)
        self.assertEqual(row["equity_upper_envelope"], 900)

    def test_touch_exit_preserves_pre_exit_range_and_after_exit_cash(self):
        case, data = self.fixture()
        data["AAPL"].loc[1, "low"] = 70
        case["fills"].append(self.fill("SELL", 5, 89.775, 1, reason="PROTECTIVE_STOP_TOUCH: active stop 90", commission=1))
        case["equity_curve"][1].update(equity=947.875, exposure=0)
        case["metrics"]["open_positions"] = {}
        row = daily_risk_envelope(case, data)["daily_envelopes"][1]
        self.assertEqual(row["equity_lower_envelope"], 850)
        self.assertEqual(row["equity_upper_envelope"], 1050)
        self.assertEqual(row["cash_at_close"], 947.875)

    def test_stop_cost_can_put_net_sale_proceeds_below_the_bar_low(self):
        case, data = self.fixture()
        data["AAPL"].loc[1, "low"] = 89.9
        case["fills"].append(self.fill("SELL", 5, 89.775, 1, reason="PROTECTIVE_STOP_TOUCH: active stop 90", commission=1))
        case["equity_curve"][1].update(equity=947.875, exposure=0)
        case["metrics"]["open_positions"] = {}
        self.assertEqual(daily_risk_envelope(case, data)["daily_envelopes"][1]["equity_lower_envelope"], 947.875)

    def test_same_day_buy_and_touch_exit_include_both_commissions(self):
        case, data = self.fixture()
        case["fills"][0]["commission"] = 1
        case["fills"].append(self.fill("SELL", 5, 90, 0, reason="PROTECTIVE_STOP_TOUCH: active stop 90", commission=1))
        for point in case["equity_curve"]:
            point.update(equity=948, exposure=0)
        case["metrics"]["open_positions"] = {}
        report = daily_risk_envelope(case, data)
        self.assertEqual(report["daily_envelopes"][0]["cash_at_close"], 948)

    def test_independent_multi_stock_extrema_are_not_called_observed_equity(self):
        case, data = self.fixture()
        data["MSFT"] = daily_candles("MSFT", self.dates, [50, 50], [50, 50], lows=[40, 40], highs=[60, 60])
        case["fills"].append(self.fill("BUY", 5, 50, 0, symbol="MSFT"))
        case["metrics"]["open_positions"]["MSFT"] = {"quantity": 5}
        for point in case["equity_curve"]:
            point["exposure"] = .75
        report = daily_risk_envelope(case, data)
        self.assertEqual(report["daily_envelopes"][0]["equity_lower_envelope"], 900)
        self.assertEqual(report["daily_envelopes"][0]["equity_upper_envelope"], 1100)
        self.assertFalse(report["intraday_equity_observed"])

    def test_empty_duplicate_unordered_naive_and_holdout_curves_are_rejected(self):
        for mode in ("empty", "duplicate", "unordered", "naive", "holdout"):
            case, data = self.fixture()
            if mode == "empty":
                case["equity_curve"] = []
            elif mode == "duplicate":
                case["equity_curve"][1]["timestamp"] = self.dates[0]
            elif mode == "unordered":
                case["equity_curve"].reverse()
            elif mode == "naive":
                case["equity_curve"][0]["timestamp"] = "2022-01-03"
            else:
                case["equity_curve"][1]["timestamp"] = "2024-01-02T05:00:00Z"
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                daily_risk_envelope(case, data)

    def test_missing_prices_are_rejected_without_forward_fill(self):
        case, data = self.fixture()
        data["AAPL"] = data["AAPL"].iloc[:1].copy()
        original = data["AAPL"].copy(deep=True)
        with self.assertRaisesRegex(ValueError, "Missing session"):
            daily_risk_envelope(case, data)
        pd.testing.assert_frame_equal(data["AAPL"], original)

    def test_equity_exposure_and_final_position_mismatches_are_rejected(self):
        for mode in ("equity", "exposure", "positions"):
            case, data = self.fixture()
            if mode == "positions":
                case["metrics"]["open_positions"] = {}
            else:
                case["equity_curve"][1][mode] += .1
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                daily_risk_envelope(case, data)

    def test_invalid_side_quantity_price_or_fee_is_rejected(self):
        for key, values in (("side", ("HOLD",)), ("quantity", (True, 0, -1, 1.5)),
                            ("fill_price", (0, -1, float("nan"), float("inf"))),
                            ("commission", (-1, float("nan"), float("inf")))):
            for value in values:
                case, data = self.fixture()
                case["fills"][0][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    daily_risk_envelope(case, data)

    def test_nonfinite_or_impossible_traded_ohlc_is_rejected(self):
        for field, value in (("low", float("nan")), ("high", float("inf")), ("high", 80), ("low", 120), ("open", -1)):
            case, data = self.fixture()
            data["AAPL"].loc[0, field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                daily_risk_envelope(case, data)

    def test_fill_outside_sessions_or_in_unknown_symbol_is_rejected(self):
        for changes in ({"timestamp": "2022-01-05T05:00:00Z"}, {"symbol": "UNKNOWN"}):
            case, data = self.fixture()
            case["fills"][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                daily_risk_envelope(case, data)

    def test_partial_exit_or_duplicate_intraday_stop_is_rejected(self):
        for quantity, duplicate in ((4, False), (5, True)):
            case, data = self.fixture()
            fill = self.fill("SELL", quantity, 90, 1, reason="PROTECTIVE_STOP_TOUCH: active stop 90")
            case["fills"].append(fill)
            if duplicate:
                case["fills"].append(deepcopy(fill))
            with self.subTest(quantity=quantity, duplicate=duplicate), self.assertRaises(ValueError):
                daily_risk_envelope(case, data)

    def test_pyramiding_sell_without_position_and_negative_cash_are_rejected(self):
        for mode in ("pyramid", "naked_sell", "negative_cash"):
            case, data = self.fixture()
            if mode == "pyramid":
                case["fills"].append(self.fill("BUY", 1, 100, 1))
            elif mode == "naked_sell":
                case["fills"][0]["side"] = "SELL"
            else:
                case["fills"][0]["quantity"] = 11
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                daily_risk_envelope(case, data)

    def test_invalid_initial_cash_is_rejected(self):
        for value in (0, -1, float("nan"), float("inf"), True):
            case, data = self.fixture()
            case["costs"]["initial_cash"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                daily_risk_envelope(case, data)

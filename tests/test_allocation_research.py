"""Causal allocation, daily pause, and permanent drawdown-halt checks."""

from math import floor
from unittest import TestCase

import pandas as pd

from app.ai.features import build_features
from app.strategy.base import SignalAction
from backtesting.allocation_research import ARMS, select_earlier, simulate_policy
from backtesting.daily_research import passive_spy
from backtesting.engine import BacktestConfig
from backtesting.portfolio_engine import PortfolioBacktestEngine
from backtesting.research_policy import AllocationPolicy, HaltPolicy, ResearchHaltState
from tests.test_portfolio_backtesting import ScriptedDailyStrategy, daily_candles


class HaltStateTests(TestCase):
    def observe(self, state, index, *, equity=960, previous=960, phase="open", review=False):
        return state.observe(index=index, timestamp=f"session-{index}", phase=phase,
                             equity=equity, previous_close=previous, peak=1000, review_ready=review)

    def paused(self):
        state = ResearchHaltState(HaltPolicy(5), .03, .10)
        self.observe(state, 2, previous=1000, phase="close")
        return state

    def test_default_daily_halt_stays_latched(self):
        state = ResearchHaltState(HaltPolicy(), .03, .10)
        self.observe(state, 2, previous=1000)
        self.observe(state, 50, review=True)
        self.assertTrue(state.blocked)
        self.assertEqual(state.permanent_reason, "daily loss limit reached")
        self.assertEqual(len(state.events), 1)

    def test_pause_waits_five_complete_sessions_then_open_review(self):
        state = self.paused()
        for index in range(3, 8):
            self.observe(state, index, review=True)
            self.assertTrue(state.blocked)
        self.observe(state, 8, phase="close", review=True)
        self.assertTrue(state.blocked)
        self.observe(state, 8, review=True)
        self.assertFalse(state.blocked)
        self.assertEqual(state.events[-1]["kind"], "restart")
        self.assertEqual(state.first_halted_at, "session-2")

    def test_failed_review_keeps_pause_active_after_deadline(self):
        state = self.paused()
        self.observe(state, 8, review=False)
        self.assertTrue(state.blocked)
        self.observe(state, 9, review=True)
        self.assertFalse(state.blocked)

    def test_new_breach_extends_pause_and_same_day_is_not_counted_twice(self):
        state = self.paused()
        self.observe(state, 5, equity=930, previous=980)
        self.observe(state, 5, equity=920, previous=980, phase="close")
        self.assertEqual(state.pause_until_index, 10)
        self.assertEqual(sum(event["kind"] == "daily_halt" for event in state.events), 2)
        self.observe(state, 8, equity=950, previous=950, review=True)
        self.assertTrue(state.blocked)
        self.observe(state, 11, equity=950, previous=950, review=True)
        self.assertFalse(state.blocked)

    def test_drawdown_during_pause_becomes_permanent_and_never_resets_peak(self):
        state = self.paused()
        self.observe(state, 4, equity=895, previous=900)
        self.assertEqual(state.permanent_reason, "maximum drawdown reached")
        self.observe(state, 100, equity=980, previous=980, review=True)
        self.assertTrue(state.blocked)
        self.assertEqual(state.events[-1]["kind"], "drawdown_halt")

    def test_loss_check_precedes_restart_at_open(self):
        state = self.paused()
        self.observe(state, 8, equity=925, previous=960, review=True)
        self.assertTrue(state.blocked)
        self.assertEqual(state.pause_until_index, 13)
        self.assertNotEqual(state.events[-1]["kind"], "restart")

    def test_exact_thresholds_halt_and_drawdown_has_priority(self):
        state = ResearchHaltState(HaltPolicy(5), .03, .10)
        self.observe(state, 1, equity=970, previous=1000)
        self.assertTrue(state.blocked)
        self.assertEqual(state.events[-1]["kind"], "daily_halt")
        self.observe(state, 2, equity=900, previous=970)
        self.assertEqual(state.events[-1]["kind"], "drawdown_halt")
        self.assertEqual(state.permanent_reason, "maximum drawdown reached")

    def test_invalid_pause_policy_is_rejected(self):
        for value in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                HaltPolicy(value)


class AllocationTests(TestCase):
    def test_inverse_volatility_reduces_weight_and_never_exceeds_cap(self):
        policy = AllocationPolicy(.01)
        self.assertAlmostEqual(policy.fraction(.05, .20), .05)
        self.assertAlmostEqual(policy.fraction(.05, .40), .025)
        self.assertEqual(policy.fraction(.05, .01), .05)
        self.assertEqual(AllocationPolicy().fraction(.05, float("nan")), .05)

    def test_unavailable_volatility_blocks_sizing(self):
        for value in (0, -1, float("nan"), float("inf")):
            self.assertIsNone(AllocationPolicy(.01).fraction(.05, value))
        for value in (0, -1, True, float("nan")):
            with self.assertRaises(ValueError):
                AllocationPolicy(value)

    def test_sizing_uses_signal_volatility_and_future_prices_cannot_change_fill(self):
        dates = pd.bdate_range("2022-01-03", periods=30, tz="America/New_York").tz_convert("UTC")
        prices = [100 + (index % 2) * 5 for index in range(30)]
        data = daily_candles("AAPL", [day.isoformat() for day in dates], prices, prices)
        row = build_features(data).iloc[21]
        fraction = min(.10, .01 / row["historical_volatility_20"])
        planned = floor(fraction * 10_000 / row["close"])
        expected = min(planned, floor(fraction * 10_000 / data.iloc[22]["open"]))
        strategy = ScriptedDailyStrategy({("AAPL", dates[21].date().isoformat()): SignalAction.BUY})
        engine = PortfolioBacktestEngine(strategy, costs=BacktestConfig(initial_cash=10_000, slippage_bps=0, spread_bps=0),
                                         allocation=AllocationPolicy(.01))
        result = engine.run({"AAPL": data}, trade_start=dates[21], trade_end=dates[-1])
        self.assertEqual(result.fills[0].quantity, expected)
        changed = data.copy()
        changed.loc[23:, ["open", "high", "low", "close"]] = 500
        other = engine.run({"AAPL": changed}, trade_start=dates[21], trade_end=dates[-1])
        self.assertEqual(result.fills[0], other.fills[0])

    def test_volatility_warmup_has_no_fabricated_fallback(self):
        dates = ["2022-01-03T05:00:00Z", "2022-01-04T05:00:00Z"]
        data = {"AAPL": daily_candles("AAPL", dates, [100, 100], [100, 100])}
        engine = PortfolioBacktestEngine(ScriptedDailyStrategy({("AAPL", "2022-01-03"): SignalAction.BUY}),
                                         allocation=AllocationPolicy(.01))
        result = engine.run(data, trade_start=pd.Timestamp(dates[0]), trade_end=pd.Timestamp("2022-02-01", tz="UTC"))
        self.assertEqual(result.fills, ())
        self.assertTrue(any("volatility unavailable" in event for event in result.events))


class RestartIntegrationTests(TestCase):
    def fixture(self, *, breach_index=1):
        dates = pd.bdate_range("2022-01-03", periods=10, tz="America/New_York").tz_convert("UTC")
        frame = daily_candles("AAPL", [day.isoformat() for day in dates], [100]*10, [100]*10)
        frame.loc[breach_index:, ["open", "high", "low", "close"]] = 60
        frame.loc[breach_index, ["open", "high"]] = 100
        data = {"AAPL": frame, "MSFT": daily_candles("MSFT", [day.isoformat() for day in dates], [100]*10, [100]*10)}
        return dates, data

    def run_policy(self, dates, data, actions, review, *, delay=1):
        engine = PortfolioBacktestEngine(ScriptedDailyStrategy(actions),
                                         costs=BacktestConfig(initial_cash=10_000, slippage_bps=0, spread_bps=0),
                                         halt_policy=HaltPolicy(2), restart_review=review, execution_delay_sessions=delay)
        return engine.run(data, trade_start=dates[0], trade_end=dates[-1])

    def test_restart_needs_fresh_signal_and_sells_continue_during_pause(self):
        dates, data = self.fixture()
        actions = {("AAPL", dates[0].date().isoformat()): SignalAction.BUY,
                   ("AAPL", dates[2].date().isoformat()): SignalAction.SELL}
        actions.update({("MSFT", day.date().isoformat()): SignalAction.BUY for day in dates[1:5]})
        result = self.run_policy(dates, data, actions, {day: True for day in dates})
        self.assertEqual([(fill.symbol, fill.timestamp) for fill in result.fills],
                         [("AAPL", dates[1]), ("AAPL", dates[3]), ("MSFT", dates[5])])
        self.assertEqual(result.fills[-1].signal_timestamp, dates[4])
        self.assertEqual([event["timestamp"] for event in result.risk_events if event["kind"] == "restart"], [dates[4].isoformat()])

    def test_review_uses_exact_prior_date_not_todays_future_close_or_forward_fill(self):
        dates, data = self.fixture()
        actions = {("AAPL", dates[0].date().isoformat()): SignalAction.BUY}
        review = {dates[2]: True, dates[4]: True}  # date[3] is absent.
        result = self.run_policy(dates, data, actions, review)
        restart = next(event for event in result.risk_events if event["kind"] == "restart")
        self.assertEqual(restart["timestamp"], dates[5].isoformat())

    def test_halt_cancels_buy_queued_before_breach_even_with_delayed_orders(self):
        dates, data = self.fixture(breach_index=2)
        actions = {("AAPL", dates[0].date().isoformat()): SignalAction.BUY,
                   ("MSFT", dates[1].date().isoformat()): SignalAction.BUY,
                   ("MSFT", dates[5].date().isoformat()): SignalAction.BUY}
        result = self.run_policy(dates, data, actions, {day: True for day in dates}, delay=2)
        msft = [fill for fill in result.fills if fill.symbol == "MSFT"]
        self.assertEqual(len(msft), 1)
        self.assertEqual(msft[0].timestamp, dates[7])
        self.assertEqual(msft[0].signal_timestamp, dates[5])

    def test_pause_without_review_series_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "restart_review"):
            PortfolioBacktestEngine(ScriptedDailyStrategy({}), halt_policy=HaltPolicy(5))
        with self.assertRaisesRegex(ValueError, "boolean"):
            PortfolioBacktestEngine(ScriptedDailyStrategy({}), halt_policy=HaltPolicy(5),
                                     restart_review={pd.Timestamp("2022-01-03", tz="UTC"): float("nan")})


class PolicyStudyTests(TestCase):
    def training(self):
        return {arm.id: {"pessimistic": {"metrics": {
            "annual_returns": {"2020": .03, "2021": .04}, "completed_trades": 25,
            "instruments_with_closed_trades": 6, "max_drawdown": -.04,
            "worst_closing_daily_return": -.01, "permanent_halt_reason": None,
        }}} for arm in ARMS}

    def test_selection_ignores_full_allocation_diagnostic_arms(self):
        data = self.training()
        data["full_pause"]["pessimistic"]["metrics"]["annual_returns"] = {"2020": 1, "2021": 1}
        selected, _ = select_earlier(data)
        self.assertEqual(selected, "half_latched")

    def test_permanent_halt_or_large_daily_loss_prevents_selection(self):
        data = self.training()
        for arm in ARMS:
            data[arm.id]["pessimistic"]["metrics"]["worst_closing_daily_return"] = -.04
        self.assertIsNone(select_earlier(data)[0])

    def test_passive_reference_supports_smaller_predeclared_allocation(self):
        dates = ["2021-12-31T05:00:00Z", "2022-01-03T05:00:00Z", "2022-01-04T05:00:00Z"]
        data = daily_candles("SPY", dates, [100]*3, [100, 100, 110])
        costs = BacktestConfig(slippage_bps=0, spread_bps=0)
        lower = passive_spy(data, costs, start="2022-01-01", end="2023-01-01", initial_fraction=.35)
        higher = passive_spy(data, costs, start="2022-01-01", end="2023-01-01", initial_fraction=.70)
        self.assertEqual(lower["quantity"] * 2, higher["quantity"])
        self.assertAlmostEqual(lower["total_return"] * 2, higher["total_return"])

    def test_holdout_guard_applies_before_loading_context(self):
        with self.assertRaisesRegex(ValueError, "Reserved holdout"):
            simulate_policy(ARMS[0], {}, pd.DataFrame(), BacktestConfig(), start="2023-01-01", end="2025-01-01")

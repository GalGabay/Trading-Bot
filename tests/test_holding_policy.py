"""Causal holding-clock, continuation, stop, cash, and default-policy checks."""

from datetime import timedelta
from unittest import TestCase

import pandas as pd

from app.strategy.base import SignalAction
from backtesting.allocation_research import pack_policy
from backtesting.engine import BacktestConfig
from backtesting.holding_policy import HoldingEntry, HoldingPolicy
from backtesting.portfolio_engine import PortfolioBacktestEngine, ResearchPortfolioLimits
from backtesting.protective_exits import ProtectiveExitConfig
from backtesting.research_policy import AllocationPolicy
from tests.test_portfolio_backtesting import ScriptedDailyStrategy, daily_candles


class HoldingPolicyTests(TestCase):
    def history(self, count=100):
        frame = pd.DataFrame({"timestamp": pd.bdate_range("2022-01-03", periods=count, tz="UTC"),
                              "symbol": "AAPL", "high": 100., "close": 99., "ema_200": 90.})
        frame.loc[len(frame)-1, ["high", "close"]] = [106., 105.]
        return frame

    def review(self, age, *, history=None, **kwargs):
        frame = self.history() if history is None else history
        return HoldingPolicy("continuation").review(frame, HoldingEntry(100 - age, 10, 1001), 99,
                                                    market_on=kwargs.get("market_on", True), sale_multiplier=.0025, sale_commission=1)

    def test_exact_amended_review_schedule_has_no_hard_maximum(self):
        policy = HoldingPolicy("continuation")
        self.assertEqual([age for age in range(1, 151) if policy.due(age)], [30, 35, 40, 45, 50, 55, 60, 90, 120, 150])

    def test_maximum_policy_starts_at_thirtieth_held_session(self):
        policy = HoldingPolicy("maximum")
        self.assertFalse(policy.due(29))
        self.assertTrue(policy.due(30))
        self.assertTrue(policy.due(60))

    def test_passing_continuation_retains_at_60_90_and_120(self):
        for age in (60, 90, 120):
            with self.subTest(age=age):
                self.assertEqual(self.review(age)["decision"], "retain")
                self.assertEqual(self.review(age)["reason"], "HOLDING_CONTINUATION_CONFIRMED")

    def test_failing_review_queues_exit_and_non_review_day_does_nothing(self):
        self.assertEqual(self.review(90, market_on=False)["decision"], "exit")
        self.assertIsNone(self.review(61, market_on=False))

    def test_prior_high_excludes_current_bar_and_requires_strict_break(self):
        frame = self.history()
        frame.loc[len(frame)-1, "high"] = 1000
        self.assertEqual(self.review(30, history=frame)["decision"], "retain")
        frame.loc[len(frame)-1, "close"] = 100
        self.assertFalse(self.review(30, history=frame)["gates"]["fresh_20_session_high"])

    def test_estimated_sale_profit_includes_entry_and_exit_costs(self):
        frame = self.history()
        frame.loc[len(frame)-1, "close"] = 100.15
        review = self.review(30, history=frame)
        self.assertFalse(review["gates"]["positive_estimated_net_profit"])
        self.assertEqual(review["decision"], "exit")

    def test_stock_filter_missing_warmup_and_market_off_cannot_extend(self):
        frame = self.history()
        for ema in (105., float("nan")):
            frame.loc[len(frame)-1, "ema_200"] = ema
            self.assertEqual(self.review(30, history=frame)["decision"], "exit")
        self.assertEqual(self.review(30, history=self.history(20))["decision"], "exit")
        self.assertEqual(self.review(30, market_on=False)["decision"], "exit")

    def test_invalid_policy_counts_and_modes_are_rejected(self):
        for kwargs in ({"mode": "unknown"}, {"mode": "maximum", "first_review": True},
                       {"mode": "continuation", "early_interval": 0},
                       {"mode": "continuation", "extended_interval": 1.5},
                       {"mode": "continuation", "extended_from": 20}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                HoldingPolicy(**kwargs)


class HoldingEngineTests(TestCase):
    def data(self, count=15, *, symbols=("AAPL",), dates=None):
        timestamps = list(pd.bdate_range("2022-01-03", periods=count, tz="America/New_York").tz_convert("UTC")) if dates is None else list(pd.to_datetime(dates, utc=True))
        frames = {symbol: daily_candles(symbol, [day.isoformat() for day in timestamps], [100.]*len(timestamps), [100.]*len(timestamps),
                                       lows=[99.]*len(timestamps), highs=[101.]*len(timestamps)) for symbol in symbols}
        return timestamps, frames

    def run_policy(self, data, dates, actions, *, policy=None, delay=1, cooldown=0, protection=None, context=None, max_positions=7, allocation=None, record=True):
        engine = PortfolioBacktestEngine(ScriptedDailyStrategy(actions), costs=BacktestConfig(initial_cash=10000, slippage_bps=0, spread_bps=0),
                                         limits=ResearchPortfolioLimits(max_positions=max_positions), holding_policy=policy,
                                         holding_market_review=context, execution_delay_sessions=delay, reentry_cooldown_sessions=cooldown,
                                         protection=protection, record_decisions=record, allocation=allocation)
        return engine.run(data, trade_start=dates[0], trade_end=dates[-1].to_pydatetime() + timedelta(days=1))

    def test_entry_fill_not_signal_starts_clock_and_sell_fills_next_open(self):
        dates, data = self.data()
        result = self.run_policy(data, dates, {("AAPL", dates[0].date().isoformat()): SignalAction.BUY}, policy=HoldingPolicy("maximum", first_review=3))
        self.assertEqual([fill.timestamp for fill in result.fills], [dates[1], dates[4]])
        self.assertEqual(result.holding_reviews[0]["age_sessions"], 3)
        self.assertEqual(result.fills[1].signal_timestamp, dates[3])

    def test_weekends_and_known_holiday_do_not_age_position(self):
        dates, data = self.data(dates=["2022-01-13T05:00:00Z", "2022-01-14T05:00:00Z", "2022-01-18T05:00:00Z", "2022-01-19T05:00:00Z", "2022-01-20T05:00:00Z"])
        result = self.run_policy(data, dates, {("AAPL", "2022-01-13"): SignalAction.BUY}, policy=HoldingPolicy("maximum", first_review=2))
        self.assertEqual(result.fills[1].timestamp, dates[3])

    def test_natural_exit_has_precedence_at_the_age_review_close(self):
        dates, data = self.data()
        actions = {("AAPL", dates[0].date().isoformat()): SignalAction.BUY, ("AAPL", dates[3].date().isoformat()): SignalAction.SELL}
        result = self.run_policy(data, dates, actions, policy=HoldingPolicy("maximum", first_review=3))
        self.assertEqual(result.holding_reviews, ())
        self.assertEqual(result.fills[1].signal_reason, "scripted SELL")

    def test_delayed_natural_exit_is_not_replaced_by_age_exit(self):
        dates, data = self.data()
        actions = {("AAPL", dates[0].date().isoformat()): SignalAction.BUY, ("AAPL", dates[3].date().isoformat()): SignalAction.SELL}
        result = self.run_policy(data, dates, actions, policy=HoldingPolicy("maximum", first_review=3), delay=2)
        self.assertEqual([fill.timestamp for fill in result.fills], [dates[2], dates[5]])
        self.assertEqual(result.holding_reviews, ())

    def test_delayed_time_exit_uses_delayed_fill_age_not_signal_age(self):
        dates, data = self.data()
        result = self.run_policy(data, dates, {("AAPL", dates[0].date().isoformat()): SignalAction.BUY}, policy=HoldingPolicy("maximum", first_review=3), delay=2)
        self.assertEqual([fill.timestamp for fill in result.fills], [dates[2], dates[6]])
        self.assertEqual(len(result.holding_reviews), 1)

    def test_reentry_after_cooldown_starts_new_clock(self):
        dates, data = self.data()
        actions = {("AAPL", dates[index].date().isoformat()): SignalAction.BUY for index in (0, 5, 6)}
        result = self.run_policy(data, dates, actions, policy=HoldingPolicy("maximum", first_review=3), cooldown=2)
        self.assertEqual([fill.timestamp for fill in result.fills], [dates[1], dates[4], dates[7], dates[10]])
        self.assertEqual([row["age_sessions"] for row in result.holding_reviews], [3, 3])

    def test_age_exit_releases_slot_before_already_queued_replacement(self):
        dates, data = self.data(symbols=("AAPL", "MSFT"))
        actions = {("AAPL", dates[0].date().isoformat()): SignalAction.BUY, ("MSFT", dates[3].date().isoformat()): SignalAction.BUY}
        result = self.run_policy(data, dates, actions, policy=HoldingPolicy("maximum", first_review=3), max_positions=1)
        fills = [fill for fill in result.fills if fill.timestamp == dates[4]]
        self.assertEqual([(fill.symbol, fill.side.value) for fill in fills], [("AAPL", "SELL"), ("MSFT", "BUY")])
        decision = next(row for row in result.buy_decisions if row["timestamp"] == dates[4].isoformat() and row["phase"] == "open")
        self.assertEqual(decision["position_count"], 0)

    def test_no_replacement_signal_means_cash_not_a_forced_buy(self):
        dates, data = self.data(symbols=("AAPL", "MSFT"))
        result = self.run_policy(data, dates, {("AAPL", dates[0].date().isoformat()): SignalAction.BUY}, policy=HoldingPolicy("maximum", first_review=3))
        self.assertEqual(len(result.fills), 2)
        self.assertEqual(result.final_positions, {})

    def test_last_close_exit_stays_unfilled_without_a_future_open(self):
        dates, data = self.data(count=4)
        result = self.run_policy(data, dates, {("AAPL", dates[0].date().isoformat()): SignalAction.BUY}, policy=HoldingPolicy("maximum", first_review=3))
        self.assertEqual(len(result.fills), 1)
        self.assertIn("AAPL", result.final_positions)
        self.assertTrue(any("unfilled SELL" in event for event in result.events))

    def test_open_gap_stop_cancels_queued_age_exit_without_duplicate_sale(self):
        dates, data = self.data(count=35)
        data["AAPL"].loc[24, ["open", "low", "close"]] = [90., 89., 90.]
        result = self.run_policy(data, dates, {("AAPL", dates[20].date().isoformat()): SignalAction.BUY},
                                 policy=HoldingPolicy("maximum", first_review=3), protection=ProtectiveExitConfig(atr_multiple=3, trailing=False))
        self.assertEqual(len(result.fills), 2)
        self.assertEqual(result.fills[1].timestamp, dates[24])
        self.assertTrue(result.fills[1].signal_reason.startswith("PROTECTIVE_STOP_GAP_OPEN"))

    def test_entry_day_stop_exits_before_age_review(self):
        dates, data = self.data(count=35)
        data["AAPL"].loc[21, "low"] = 90.
        result = self.run_policy(data, dates, {("AAPL", dates[20].date().isoformat()): SignalAction.BUY},
                                 policy=HoldingPolicy("maximum", first_review=1), protection=ProtectiveExitConfig(atr_multiple=3, trailing=False))
        self.assertEqual(len(result.fills), 2)
        self.assertEqual(result.fills[0].timestamp, result.fills[1].timestamp)
        self.assertEqual(result.holding_reviews, ())

    def test_continuation_can_retain_beyond_60_and_90_and_is_causal(self):
        dates, data = self.data(count=300)
        prices = [100 + index for index in range(300)]
        data["AAPL"] = daily_candles("AAPL", [day.isoformat() for day in dates], prices, [p + .2 for p in prices],
                                     lows=[p - .1 for p in prices], highs=[p + .3 for p in prices])
        actions = {("AAPL", dates[201].date().isoformat()): SignalAction.BUY}
        context = {day: True for day in dates}
        original = self.run_policy(data, dates, actions, policy=HoldingPolicy("continuation"), context=context)
        self.assertEqual([row["age_sessions"] for row in original.holding_reviews], [30, 35, 40, 45, 50, 55, 60, 90])
        self.assertTrue(all(row["decision"] == "retain" for row in original.holding_reviews))
        changed = {"AAPL": data["AAPL"].copy()}
        changed["AAPL"].loc[270:, ["open", "high", "low", "close"]] = 1000
        modified = self.run_policy(changed, dates, actions, policy=HoldingPolicy("continuation"), context=context)
        cutoff = dates[270].isoformat()
        self.assertEqual([r for r in original.holding_reviews if r["timestamp"] < cutoff], [r for r in modified.holding_reviews if r["timestamp"] < cutoff])

    def test_default_and_diagnostic_journal_leave_financial_results_unchanged(self):
        dates, data = self.data()
        actions = {("AAPL", dates[0].date().isoformat()): SignalAction.BUY}
        off = self.run_policy(data, dates, actions, record=False)
        on = self.run_policy(data, dates, actions)
        self.assertEqual(pack_policy(off), pack_policy(on))
        self.assertEqual(off.buy_decisions, ())

    def test_capacity_and_missing_sizing_journals_identify_actual_first_blocker(self):
        dates, data = self.data(symbols=("AAPL", "MSFT"))
        actions = {(symbol, dates[0].date().isoformat()): SignalAction.BUY for symbol in data}
        result = self.run_policy(data, dates, actions, max_positions=1)
        blocked = next(row for row in result.buy_decisions if row["status"] == "blocked")
        self.assertEqual(blocked["blockers"], ["position_count"])
        self.assertGreater(blocked["cash"], 0)
        missing = self.run_policy(data, dates, actions, allocation=AllocationPolicy(.01))
        self.assertTrue(any(row["blockers"] == ["missing_volatility"] for row in missing.buy_decisions))

    def test_continuation_rejects_absent_or_stale_market_context(self):
        dates, data = self.data()
        actions = {("AAPL", dates[0].date().isoformat()): SignalAction.BUY}
        with self.assertRaisesRegex(ValueError, "market context"):
            self.run_policy(data, dates, actions, policy=HoldingPolicy("continuation"))
        with self.assertRaisesRegex(ValueError, "exact-date"):
            self.run_policy(data, dates, actions, policy=HoldingPolicy("continuation"), context={dates[0]: True})

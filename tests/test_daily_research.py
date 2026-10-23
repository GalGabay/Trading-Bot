"""Offline checks for causal daily research rules and execution controls."""

from dataclasses import replace
from types import SimpleNamespace
from unittest import TestCase

import pandas as pd

from app.ai.features import build_features
from app.strategy.base import SignalAction
from backtesting.daily_research import ARMS, assert_baseline_matches, bootstrap_difference, select_on_earlier_years, simulate
from backtesting.daily_strategies import DailyResearchStrategy, DailyRuleConfig, market_regime
from backtesting.engine import BacktestConfig
from backtesting.portfolio_engine import PortfolioBacktestEngine
from backtesting.protective_exits import ProtectiveExitConfig, raised_stop
from tests.test_portfolio_backtesting import ScriptedDailyStrategy, daily_candles


class DailyRuleTests(TestCase):
    def features(self, count=60):
        dates = pd.bdate_range("2021-01-04", periods=count, tz="America/New_York").tz_convert("UTC")
        return pd.DataFrame({"timestamp": dates, "symbol": "AAPL", "open": 100.0, "high": 101.0,
                             "low": 99.0, "close": 100.0, "ema_20": 98.0, "ema_50": 95.0,
                             "ema_200": 90.0, "rsi_14": 60.0, "volume": 1000.0, "volume_ratio_20": 0.1})

    def strategy(self, data, style="breakout", **kwargs):
        return DailyResearchStrategy(DailyRuleConfig(style, **kwargs),
                                     regime={date: True for date in data["timestamp"]})

    def test_breakout_excludes_current_high_and_requires_strict_break(self):
        data = self.features()
        data.loc[len(data)-1, ["high", "close"]] = [500, 102]
        strategy = self.strategy(data)
        self.assertEqual(strategy.generate_signal(data).action, SignalAction.BUY)
        data.loc[len(data)-1, "close"] = 101
        self.assertEqual(strategy.generate_signal(data).action, SignalAction.HOLD)

    def test_exit_channel_excludes_current_low(self):
        data = self.features()
        data.loc[len(data)-1, ["low", "close"]] = [80, 98]
        signal = self.strategy(data).generate_signal(data, SimpleNamespace(quantity=5))
        self.assertEqual(signal.action, SignalAction.SELL)

    def test_breakout_waits_for_full_channel(self):
        data = self.features(20)
        self.assertEqual(self.strategy(data).generate_signal(data).action, SignalAction.HOLD)

    def test_market_off_exits_and_blocks_buys(self):
        data = self.features()
        strategy = DailyResearchStrategy(DailyRuleConfig("trend"), regime={data.iloc[-1]["timestamp"]: False})
        self.assertEqual(strategy.generate_signal(data).action, SignalAction.HOLD)
        self.assertEqual(strategy.generate_signal(data, SimpleNamespace(quantity=1)).action, SignalAction.SELL)

    def test_market_regime_must_match_exact_signal_date(self):
        data = self.features()
        strategy = DailyResearchStrategy(DailyRuleConfig("trend"), regime={})
        with self.assertRaisesRegex(ValueError, "regime missing"):
            strategy.generate_signal(data)

    def test_trend_accepts_strong_rsi_and_ignores_volume(self):
        data = self.features()
        data.loc[len(data)-1, "rsi_14"] = 80
        self.assertEqual(self.strategy(data, "trend").generate_signal(data).action, SignalAction.BUY)
        self.assertEqual(self.strategy(data, "no_volume").generate_signal(data).action, SignalAction.HOLD)
        data.loc[len(data)-1, "rsi_14"] = 60
        strategy = self.strategy(data, "no_volume")
        before = strategy.generate_signal(data)
        data.loc[:, "volume_ratio_20"] = 1e9
        self.assertEqual(before, strategy.generate_signal(data))

    def test_market_context_and_strategy_are_invariant_to_future_prices(self):
        count = 260
        dates = pd.bdate_range("2020-01-02", periods=count, tz="America/New_York").tz_convert("UTC")
        prices = [100 + index * 0.2 + (index % 3) * 0.1 for index in range(count)]
        spy = daily_candles("SPY", [date.isoformat() for date in dates], prices, prices)
        prefix = spy.iloc[:240].copy()
        original_regime = market_regime(spy)
        changed = spy.copy()
        changed.loc[240:, ["open", "high", "low", "close"]] = 1
        future_regime = market_regime(changed)
        self.assertEqual(market_regime(prefix), {key: original_regime[key] for key in prefix["timestamp"]})
        features = build_features(prefix)
        strategy = DailyResearchStrategy(DailyRuleConfig("trend"), regime=original_regime)
        other = DailyResearchStrategy(DailyRuleConfig("trend"), regime=future_regime)
        self.assertEqual(strategy.generate_signal(features), other.generate_signal(features))


class DailyExecutionTests(TestCase):
    def fixture(self, count=7):
        dates = pd.bdate_range("2022-01-03", periods=count, tz="America/New_York").tz_convert("UTC")
        data = {"AAPL": daily_candles("AAPL", [date.isoformat() for date in dates], [100]*count, [100]*count)}
        return dates, data

    def run_engine(self, engine, data, signal_data=None):
        return engine.run(data, trade_start=pd.Timestamp("2022-01-01", tz="UTC"),
                          trade_end=pd.Timestamp("2022-04-01", tz="UTC"), signal_datasets=signal_data)

    def engine(self, actions, **kwargs):
        return PortfolioBacktestEngine(ScriptedDailyStrategy(actions),
                                      costs=BacktestConfig(initial_cash=10_000, slippage_bps=0, spread_bps=0), **kwargs)

    def test_delay_preserves_original_quantity_and_has_one_pending_order(self):
        dates, data = self.fixture()
        data["AAPL"].loc[1:, ["open", "high", "low", "close"]] = 50
        actions = {("AAPL", date.date().isoformat()): SignalAction.BUY for date in dates}
        result = self.run_engine(self.engine(actions, execution_delay_sessions=2), data)
        self.assertEqual(len(result.fills), 1)
        self.assertEqual(result.fills[0].timestamp, dates[2])
        self.assertEqual(result.fills[0].quantity, 10)
        self.assertEqual(result.fills[0].signal_timestamp, dates[0])

    def test_cooldown_counts_complete_sessions_after_discretionary_exit(self):
        dates, data = self.fixture()
        actions = {("AAPL", date.date().isoformat()): SignalAction.BUY for date in dates}
        actions[("AAPL", dates[1].date().isoformat())] = SignalAction.SELL
        result = self.run_engine(self.engine(actions, reentry_cooldown_sessions=2), data)
        self.assertEqual([fill.timestamp for fill in result.fills], [dates[1], dates[2], dates[5]])

    def test_signal_feed_plans_quantity_but_execution_feed_prices_fill(self):
        dates, data = self.fixture()
        signals = {"AAPL": data["AAPL"].copy()}
        data["AAPL"].loc[:, ["open", "high", "low", "close"]] = 50
        result = self.run_engine(self.engine({("AAPL", dates[0].date().isoformat()): SignalAction.BUY}), data, signals)
        self.assertEqual(result.fills[0].quantity, 10)
        self.assertEqual(result.fills[0].fill_price, 50)
        self.assertEqual(result.final_closes["AAPL"], 50)

    def test_signal_feed_cannot_fill_an_absent_session(self):
        _, data = self.fixture()
        signals = {"AAPL": data["AAPL"].iloc[:-1]}
        with self.assertRaisesRegex(ValueError, "signal and execution session timestamps"):
            self.run_engine(self.engine({}), data, signals)

    def test_fixed_initial_stop_and_wider_trailing_distance(self):
        fixed = ProtectiveExitConfig(atr_multiple=3, trailing=False)
        self.assertEqual(raised_stop(94, 120, 2, fixed), 94)
        trailing = replace(fixed, trailing=True, trailing_atr_multiple=4)
        self.assertEqual(raised_stop(94, 120, 2, trailing), 112)
        self.assertEqual(raised_stop(112, 100, 2, trailing), 112)

    def test_stop_remains_active_while_delayed_exit_is_pending(self):
        dates, data = self.fixture(30)
        data["AAPL"].loc[:, "low"] = 99
        data["AAPL"].loc[:, "high"] = 101
        data["AAPL"].loc[23, ["open", "low", "close"]] = [90, 89, 90]
        actions = {("AAPL", dates[20].date().isoformat()): SignalAction.BUY,
                   ("AAPL", dates[22].date().isoformat()): SignalAction.SELL}
        result = self.run_engine(self.engine(actions, execution_delay_sessions=2,
                                             protection=ProtectiveExitConfig(trailing=False)), data)
        self.assertEqual([fill.timestamp for fill in result.fills], [dates[22], dates[23]])
        self.assertIn("PROTECTIVE_STOP_GAP_OPEN", result.fills[1].signal_reason)

    def test_cooldown_also_applies_after_intraday_protective_exit(self):
        dates, data = self.fixture(30)
        data["AAPL"].loc[:, "low"] = 99
        data["AAPL"].loc[:, "high"] = 101
        data["AAPL"].loc[21, "low"] = 90
        actions = {("AAPL", date.date().isoformat()): SignalAction.BUY for date in dates[20:]}
        result = self.run_engine(self.engine(actions, reentry_cooldown_sessions=2,
                                             protection=ProtectiveExitConfig(trailing=False)), data)
        self.assertEqual([fill.timestamp for fill in result.fills[:3]], [dates[21], dates[21], dates[24]])

    def test_invalid_execution_controls_are_rejected(self):
        for kwargs in ({"execution_delay_sessions": 0}, {"execution_delay_sessions": True}, {"reentry_cooldown_sessions": -1}):
            with self.assertRaises(ValueError):
                self.engine({}, **kwargs)

    def test_study_cannot_score_reserved_holdout(self):
        _, data = self.fixture()
        with self.assertRaisesRegex(ValueError, "reserved holdout"):
            simulate(ARMS[0], data, data["AAPL"], BacktestConfig(), start="2022-01-01", end="2025-01-01")


class ResearchSelectionTests(TestCase):
    def test_baseline_reference_allows_only_missing_null_stop_metadata(self):
        original = {"cost_scenarios": {"base": {"metrics": {"open_positions": {"AAPL": {"quantity": 10}}}, "fills": []}}}
        current = {"base": {"metrics": {"open_positions": {"AAPL": {"quantity": 10, "stop_price": None}}}, "fills": []}}
        assert_baseline_matches(current, original)
        current["base"]["metrics"]["open_positions"]["AAPL"]["quantity"] = 11
        with self.assertRaisesRegex(ValueError, "Baseline replay differs"):
            assert_baseline_matches(current, original)

    def training(self):
        return {arm.id: {"pessimistic": {"metrics": {
            "annual_returns": {"2020": 0.03, "2021": 0.04}, "max_drawdown": -0.05,
            "entry_halted_at": None, "completed_trades": 25, "instruments_with_closed_trades": 6,
        }}} for arm in ARMS if arm.eligible}

    def test_selects_by_worst_earlier_year_then_trade_count(self):
        training = self.training()
        training["regime_trend"]["pessimistic"]["metrics"]["completed_trades"] = 20
        selected, checks = select_on_earlier_years(training)
        self.assertEqual(selected, "regime_trend")
        self.assertTrue(all(checks[selected].values()))

    def test_returns_no_selection_instead_of_relaxing_sample_gate(self):
        training = self.training()
        for result in training.values():
            result["pessimistic"]["metrics"]["completed_trades"] = 2
        selected, checks = select_on_earlier_years(training)
        self.assertIsNone(selected)
        self.assertFalse(any(all(row.values()) for row in checks.values()))

    def test_latched_halt_disqualifies_earlier_candidate(self):
        training = self.training()
        for result in training.values():
            result["pessimistic"]["metrics"]["entry_halted_at"] = "2020-03-16"
        self.assertIsNone(select_on_earlier_years(training)[0])

    def test_paired_bootstrap_identical_paths_have_zero_difference(self):
        equity = [100_000 + index * 10 for index in range(50)]
        output = bootstrap_difference(equity, equity, draws=50)
        self.assertEqual(output["observed_return_difference"], 0)
        self.assertEqual(output["percentile_2_5"], 0)
        self.assertEqual(output["percentile_97_5"], 0)
        self.assertEqual(output, bootstrap_difference(equity, equity, draws=50))
        with self.assertRaises(ValueError):
            bootstrap_difference(equity, equity[:-1])

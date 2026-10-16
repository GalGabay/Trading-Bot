from __future__ import annotations

from datetime import datetime
from unittest import TestCase

import pandas as pd

from app.strategy.base import Signal, SignalAction, Strategy
from backtesting.engine import BacktestConfig, BacktestEngine


def candles() -> pd.DataFrame:
    return pd.DataFrame({
        "timestamp": pd.to_datetime([
            "2026-01-02T15:00:00Z", "2026-01-02T16:00:00Z",
            "2026-01-02T17:00:00Z", "2026-01-02T18:00:00Z",
        ], utc=True),
        "symbol": ["AAPL"] * 4,
        "open": [100.0, 110.0, 120.0, 90.0],
        "high": [102.0, 125.0, 125.0, 95.0],
        "low": [99.0, 108.0, 115.0, 85.0],
        "close": [101.0, 120.0, 118.0, 88.0],
        "volume": [1_000.0] * 4,
    })


class ScriptedStrategy(Strategy):
    name = "scripted_test"

    def __init__(self, actions: list[SignalAction]) -> None:
        self.actions = actions
        self.input_lengths: list[int] = []
        self.portfolios = []

    def generate_signal(self, market_data: pd.DataFrame, portfolio=None) -> Signal:
        self.input_lengths.append(len(market_data))
        self.portfolios.append(portfolio)
        action = self.actions[len(self.input_lengths) - 1]
        timestamp = pd.Timestamp(market_data.iloc[-1]["timestamp"]).to_pydatetime()
        return Signal("AAPL", action, 1.0, f"{action} scripted", timestamp, self.name)


class BacktestEngineTests(TestCase):
    def test_buy_is_filled_at_next_open_not_signal_close(self) -> None:
        strategy = ScriptedStrategy([SignalAction.BUY, SignalAction.HOLD, SignalAction.HOLD, SignalAction.HOLD])
        result = BacktestEngine(strategy, config=BacktestConfig(
            initial_cash=10_000, position_fraction=0.5, slippage_bps=10, commission_per_order=2
        )).run(candles())
        self.assertEqual(len(result.fills), 1)
        fill = result.fills[0]
        self.assertEqual(fill.timestamp, pd.Timestamp("2026-01-02T16:00:00Z"))
        self.assertEqual(fill.signal_timestamp, pd.Timestamp("2026-01-02T15:00:00Z"))
        self.assertEqual(fill.reference_open, 110.0)
        self.assertAlmostEqual(fill.fill_price, 110.11)
        self.assertEqual(fill.quantity, 45)
        self.assertEqual(result.equity_curve[0].quantity, 0)
        self.assertEqual(result.equity_curve[1].quantity, 45)

    def test_strategy_receives_only_features_available_at_each_close(self) -> None:
        strategy = ScriptedStrategy([SignalAction.HOLD] * 4)
        BacktestEngine(strategy).run(candles())
        self.assertEqual(strategy.input_lengths, [1, 2, 3, 4])
        self.assertEqual(strategy.portfolios[0].quantity, 0)

    def test_sell_closes_existing_position_at_later_next_open(self) -> None:
        strategy = ScriptedStrategy([SignalAction.BUY, SignalAction.HOLD, SignalAction.SELL, SignalAction.HOLD])
        result = BacktestEngine(strategy, config=BacktestConfig(
            initial_cash=10_000, position_fraction=0.5, slippage_bps=0
        )).run(candles())
        self.assertEqual([fill.side for fill in result.fills], [SignalAction.BUY, SignalAction.SELL])
        self.assertEqual(result.fills[0].timestamp, pd.Timestamp("2026-01-02T16:00:00Z"))
        self.assertEqual(result.fills[1].timestamp, pd.Timestamp("2026-01-02T18:00:00Z"))
        self.assertEqual(result.equity_curve[-1].quantity, 0)

    def test_final_candle_signal_is_left_unfilled(self) -> None:
        strategy = ScriptedStrategy([SignalAction.HOLD, SignalAction.HOLD, SignalAction.HOLD, SignalAction.BUY])
        result = BacktestEngine(strategy).run(candles())
        self.assertEqual(result.fills, ())
        self.assertIn("Unfilled BUY signal", result.events[0])

    def test_equity_curve_tracks_drawdown_after_market_move(self) -> None:
        strategy = ScriptedStrategy([SignalAction.BUY, SignalAction.HOLD, SignalAction.HOLD, SignalAction.HOLD])
        result = BacktestEngine(strategy, config=BacktestConfig(
            initial_cash=10_000, position_fraction=0.5, slippage_bps=0
        )).run(candles())
        self.assertLess(result.equity_curve[-1].drawdown, 0)
        self.assertEqual(result.final_equity, result.equity_curve[-1].equity)

    def test_rejects_multi_symbol_input(self) -> None:
        mixed = pd.concat([candles(), candles().assign(symbol="MSFT")], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "exactly one symbol"):
            BacktestEngine(ScriptedStrategy([SignalAction.HOLD] * 8)).run(mixed)

    def test_invalid_configuration_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "initial_cash"):
            BacktestConfig(initial_cash=0)
        with self.assertRaisesRegex(ValueError, "position_fraction"):
            BacktestConfig(position_fraction=1.1)

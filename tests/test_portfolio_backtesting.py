"""Focused offline checks for the shared-cash daily simulator."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import pandas as pd

from app.strategy.base import Signal, SignalAction, Strategy
from backtesting.engine import BacktestConfig
from backtesting.portfolio_engine import (
    PortfolioBacktestEngine, ResearchPortfolioLimits, summarize_portfolio,
)
from backtesting.protective_exits import (
    ProtectiveExitConfig, initial_stop, raised_stop, stop_reference,
)
from backtesting.portfolio_research import run_portfolio_research


def daily_candles(
    symbol: str, dates: list[str], opens: list[float], closes: list[float],
    *, lows: list[float] | None = None, highs: list[float] | None = None,
) -> pd.DataFrame:
    minimums = lows or [min(open_price, close) for open_price, close in zip(opens, closes)]
    maximums = highs or [max(open_price, close) for open_price, close in zip(opens, closes)]
    return pd.DataFrame({
        "timestamp": pd.to_datetime(dates, utc=True),
        "symbol": [symbol] * len(dates),
        "open": opens,
        "high": maximums,
        "low": minimums,
        "close": closes,
        "volume": [1000] * len(dates),
    })


class ScriptedDailyStrategy(Strategy):
    name = "scripted_daily"
    latest_row_only = True

    def __init__(self, actions: dict[tuple[str, str], SignalAction]) -> None:
        self.actions = actions

    def generate_signal(self, market_data: pd.DataFrame, portfolio=None) -> Signal:
        row = market_data.iloc[-1]
        timestamp = pd.Timestamp(row["timestamp"])
        symbol = str(row["symbol"])
        action = self.actions.get((symbol, timestamp.date().isoformat()), SignalAction.HOLD)
        return Signal(symbol, action, 1.0, f"scripted {action.value}", timestamp.to_pydatetime(), self.name)


class SharedCashBacktestTests(TestCase):
    dates = [
        "2022-01-03T05:00:00Z", "2022-01-04T05:00:00Z",
        "2022-01-05T05:00:00Z", "2022-01-06T05:00:00Z",
    ]

    def engine(
        self, actions: dict[tuple[str, str], SignalAction], *,
        max_positions: int = 7, priority: str = "alphabetical",
        daily_loss: float = 0.03,
    ) -> PortfolioBacktestEngine:
        return PortfolioBacktestEngine(
            ScriptedDailyStrategy(actions),
            costs=BacktestConfig(initial_cash=10_000, position_fraction=0.10, slippage_bps=0, spread_bps=0),
            limits=ResearchPortfolioLimits(max_positions=max_positions, max_daily_loss=daily_loss),
            buy_priority=priority,
        )

    def run_engine(self, engine: PortfolioBacktestEngine, datasets: dict[str, pd.DataFrame]):
        return engine.run(
            datasets, trade_start=pd.Timestamp("2022-01-01T00:00:00Z"),
            trade_end=pd.Timestamp("2022-02-01T00:00:00Z"),
        )

    def test_simultaneous_buys_share_cash_and_have_declared_priority(self) -> None:
        data = {
            symbol: daily_candles(symbol, self.dates, [100] * 4, [100] * 4)
            for symbol in ("AAPL", "MSFT")
        }
        actions = {(symbol, "2022-01-03"): SignalAction.BUY for symbol in data}
        normal = self.run_engine(self.engine(actions, max_positions=1), data)
        reverse = self.run_engine(self.engine(actions, max_positions=1, priority="reverse"), data)
        self.assertEqual([(fill.symbol, fill.quantity) for fill in normal.fills], [("AAPL", 10)])
        self.assertEqual([(fill.symbol, fill.quantity) for fill in reverse.fills], [("MSFT", 10)])
        self.assertTrue(any("position-count limit" in event for event in normal.events))
        self.assertEqual(normal.equity_curve[-1].cash, 9_000)

    def test_sells_release_position_slot_and_cash_before_buys(self) -> None:
        data = {
            symbol: daily_candles(symbol, self.dates, [100] * 4, [100] * 4)
            for symbol in ("AAPL", "MSFT")
        }
        actions = {
            ("AAPL", "2022-01-03"): SignalAction.BUY,
            ("AAPL", "2022-01-04"): SignalAction.SELL,
            ("MSFT", "2022-01-04"): SignalAction.BUY,
        }
        result = self.run_engine(self.engine(actions, max_positions=1), data)
        self.assertEqual(
            [(fill.symbol, fill.side) for fill in result.fills],
            [("AAPL", SignalAction.BUY), ("AAPL", SignalAction.SELL), ("MSFT", SignalAction.BUY)],
        )
        self.assertEqual(result.fills[1].timestamp, result.fills[2].timestamp)
        self.assertEqual(result.equity_curve[-1].position_count, 1)

    def test_favorable_open_does_not_increase_planned_share_count(self) -> None:
        data = {"AAPL": daily_candles("AAPL", self.dates, [100, 50, 50, 50], [100, 50, 50, 50])}
        result = self.run_engine(self.engine({("AAPL", "2022-01-03"): SignalAction.BUY}), data)
        self.assertEqual(result.fills[0].quantity, 10)  # Planned from the earlier $100 close.
        self.assertEqual(result.fills[0].reference_open, 50)

    def test_positions_and_equity_carry_across_year_end(self) -> None:
        dates = ["2022-12-29T05:00:00Z", "2022-12-30T05:00:00Z", "2023-01-03T05:00:00Z"]
        data = {"AAPL": daily_candles("AAPL", dates, [100, 100, 110], [100, 110, 120])}
        result = self.engine({("AAPL", "2022-12-29"): SignalAction.BUY}).run(
            data, trade_start=pd.Timestamp("2022-12-29T00:00:00Z"),
            trade_end=pd.Timestamp("2023-01-04T00:00:00Z"),
        )
        metrics = summarize_portfolio(result)
        self.assertEqual(result.final_positions, {"AAPL": 10})
        self.assertAlmostEqual(metrics["annual_returns"]["2022"], 0.01)
        self.assertAlmostEqual(metrics["annual_returns"]["2023"], 10_200 / 10_100 - 1)
        self.assertAlmostEqual(metrics["final_equity"], 10_200)
        self.assertEqual(metrics["completed_trades"], 0)

    def test_daily_loss_halts_new_buys_but_allows_exits(self) -> None:
        data = {
            "AAPL": daily_candles("AAPL", self.dates, [100, 100, 50, 50], [100, 100, 50, 50]),
            "MSFT": daily_candles("MSFT", self.dates, [100] * 4, [100] * 4),
        }
        actions = {
            ("AAPL", "2022-01-03"): SignalAction.BUY,
            ("AAPL", "2022-01-05"): SignalAction.SELL,
            ("MSFT", "2022-01-05"): SignalAction.BUY,
        }
        result = self.run_engine(self.engine(actions), data)
        self.assertIsNotNone(result.halted_at)
        self.assertEqual([(fill.symbol, fill.side) for fill in result.fills], [
            ("AAPL", SignalAction.BUY), ("AAPL", SignalAction.SELL),
        ])
        self.assertTrue(any("entry halt active" in event for event in result.events))

    def test_misaligned_sessions_are_rejected_without_filling_data(self) -> None:
        data = {
            "AAPL": daily_candles("AAPL", self.dates, [100] * 4, [100] * 4),
            "MSFT": daily_candles("MSFT", self.dates[:-1], [100] * 3, [100] * 3),
        }
        with self.assertRaisesRegex(ValueError, "session timestamps do not match"):
            self.run_engine(self.engine({}), data)

    def test_invalid_limits_and_naive_bounds_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "max_single_position"):
            ResearchPortfolioLimits(max_single_position=0.8)
        data = {"AAPL": daily_candles("AAPL", self.dates, [100] * 4, [100] * 4)}
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            self.engine({}).run(
                data, trade_start=pd.Timestamp("2022-01-01"),
                trade_end=pd.Timestamp("2022-02-01T00:00:00Z"),
            )


class ProtectiveExitTests(TestCase):
    def fixture(
        self, *, entry_low: float = 99, entry_close: float = 100,
        next_open: float = 100, next_low: float = 99, next_close: float = 100,
    ) -> tuple[dict[str, pd.DataFrame], list[pd.Timestamp]]:
        dates = list(pd.bdate_range("2022-01-03", periods=24, tz="America/New_York").tz_convert("UTC"))
        opens = [100.0] * len(dates)
        closes = [100.0] * len(dates)
        lows = [99.0] * len(dates)
        highs = [101.0] * len(dates)
        lows[21], closes[21] = entry_low, entry_close
        highs[21] = max(101.0, entry_close)
        opens[22], lows[22], closes[22] = next_open, next_low, next_close
        highs[22] = max(101.0, next_open, next_close)
        frame = daily_candles(
            "AAPL", [date.isoformat() for date in dates], opens, closes,
            lows=lows, highs=highs,
        )
        return {"AAPL": frame}, dates

    def run_protected(
        self, data: dict[str, pd.DataFrame], dates: list[pd.Timestamp], *,
        protection: ProtectiveExitConfig | None = None,
        sell_after_entry: bool = False,
    ):
        actions = {("AAPL", dates[20].date().isoformat()): SignalAction.BUY}
        if sell_after_entry:
            actions[("AAPL", dates[21].date().isoformat())] = SignalAction.SELL
        engine = PortfolioBacktestEngine(
            ScriptedDailyStrategy(actions),
            costs=BacktestConfig(initial_cash=10_000, position_fraction=0.10, slippage_bps=0, spread_bps=0),
            protection=protection or ProtectiveExitConfig(),
        )
        return engine.run(
            data, trade_start=dates[20],
            trade_end=pd.Timestamp("2022-03-01T00:00:00Z"),
        )

    def test_stop_reference_uses_open_for_gap_and_stop_for_low_touch(self) -> None:
        self.assertEqual(stop_reference(90, 85, 95), (90, True))
        self.assertEqual(stop_reference(100, 94, 95), (95, False))
        self.assertIsNone(stop_reference(100, 96, 95))
        self.assertEqual(initial_stop(100, 2, ProtectiveExitConfig()), 96)
        self.assertIsNone(initial_stop(100, None, ProtectiveExitConfig()))
        self.assertEqual(raised_stop(96, 95, 2, ProtectiveExitConfig()), 96)

    def test_intraday_stop_can_close_on_entry_day(self) -> None:
        data, dates = self.fixture(entry_low=95)
        result = self.run_protected(data, dates)
        self.assertEqual([(fill.side, fill.timestamp) for fill in result.fills], [
            (SignalAction.BUY, dates[21]), (SignalAction.SELL, dates[21]),
        ])
        self.assertAlmostEqual(result.fills[1].fill_price, 96)
        self.assertIn("PROTECTIVE_STOP_TOUCH", result.fills[1].signal_reason)
        self.assertEqual(summarize_portfolio(result)["protective_stop_exits"], 1)

    def test_gap_below_stop_fills_at_open_before_pending_trend_sell(self) -> None:
        data, dates = self.fixture(next_open=80, next_low=79, next_close=80)
        result = self.run_protected(data, dates, sell_after_entry=True)
        self.assertEqual([fill.side for fill in result.fills], [SignalAction.BUY, SignalAction.SELL])
        self.assertEqual(result.fills[1].timestamp, dates[22])
        self.assertAlmostEqual(result.fills[1].fill_price, 80)
        self.assertIn("PROTECTIVE_STOP_GAP_OPEN", result.fills[1].signal_reason)
        self.assertEqual(summarize_portfolio(result)["gap_open_stop_exits"], 1)
        self.assertEqual(result.final_positions, {})

    def test_trailing_stop_rises_after_close_then_can_lock_profit(self) -> None:
        data, dates = self.fixture(entry_close=110, next_open=110, next_low=103, next_close=110)
        result = self.run_protected(data, dates)
        self.assertEqual(len(result.fills), 2)
        self.assertGreater(result.fills[1].fill_price, result.fills[0].fill_price)
        self.assertLess(result.fills[1].fill_price, 110)
        self.assertTrue(any("trailing stop raised" in event for event in result.events))

    def test_planned_risk_cap_reduces_shares_and_extra_stop_slippage_is_adverse(self) -> None:
        data, dates = self.fixture(next_open=80, next_low=79, next_close=80)
        narrow = self.run_protected(data, dates, protection=ProtectiveExitConfig(max_risk_per_trade=0.001))
        stressed = self.run_protected(data, dates, protection=ProtectiveExitConfig(
            max_risk_per_trade=0.001, extra_stop_slippage_bps=50,
        ))
        self.assertEqual(narrow.fills[0].quantity, 2)
        self.assertEqual(stressed.fills[0].quantity, 2)
        self.assertAlmostEqual(narrow.fills[1].fill_price, 80)
        self.assertAlmostEqual(stressed.fills[1].fill_price, 79.6)
        self.assertLess(summarize_portfolio(stressed)["final_equity"], summarize_portfolio(narrow)["final_equity"])
        self.assertLess(
            summarize_portfolio(narrow)["final_equity"] - 10_000,
            -10_000 * 0.001,  # A gap can lose more than the planned risk cap.
        )

    def test_higher_open_reduces_shares_to_keep_planned_risk_within_cap(self) -> None:
        data, dates = self.fixture(entry_low=119, entry_close=120)
        data["AAPL"].loc[21, "open"] = 120
        data["AAPL"].loc[21, "high"] = 121
        result = self.run_protected(data, dates)
        self.assertLessEqual(result.fills[0].quantity, 4)
        self.assertGreater(result.fills[0].quantity, 0)

    def test_entry_open_below_planned_stop_is_rejected(self) -> None:
        data, dates = self.fixture(entry_low=89, entry_close=90)
        data["AAPL"].loc[21, "open"] = 90
        data["AAPL"].loc[21, "high"] = 91
        result = self.run_protected(data, dates)
        self.assertEqual(result.fills, ())
        self.assertTrue(any("open is at or below planned stop" in event for event in result.events))

    def test_missing_atr_rejects_buy_without_creating_stop_or_fill(self) -> None:
        dates = ["2022-01-03T05:00:00Z", "2022-01-04T05:00:00Z"]
        data = {"AAPL": daily_candles("AAPL", dates, [100, 100], [100, 100], lows=[99, 99], highs=[101, 101])}
        strategy = ScriptedDailyStrategy({("AAPL", "2022-01-03"): SignalAction.BUY})
        result = PortfolioBacktestEngine(
            strategy, costs=BacktestConfig(slippage_bps=0, spread_bps=0),
            protection=ProtectiveExitConfig(),
        ).run(
            data, trade_start=pd.Timestamp("2022-01-03T00:00:00Z"),
            trade_end=pd.Timestamp("2022-01-05T00:00:00Z"),
        )
        self.assertEqual(result.fills, ())
        self.assertTrue(any("valid ATR stop unavailable" in event for event in result.events))

    def test_invalid_stop_configuration_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "atr_multiple"):
            ProtectiveExitConfig(atr_multiple=0)
        with self.assertRaisesRegex(ValueError, "max_risk_per_trade"):
            ProtectiveExitConfig(max_risk_per_trade=2)


class PortfolioResearchLoaderTests(TestCase):
    def write_dataset(self, directory: Path, symbol: str, *, feed: str = "sip") -> Path:
        path = directory / f"{symbol}.csv"
        path.write_text(
            "timestamp,symbol,open,high,low,close,volume\n"
            f"2022-01-03T05:00:00Z,{symbol},100,101,99,100,1000\n"
            f"2022-01-04T05:00:00Z,{symbol},100,101,99,100,1000\n",
            encoding="utf-8",
        )
        path.with_suffix(".manifest.json").write_text(json.dumps({
            "symbol": symbol, "timeframe": "1Day", "feed": feed, "adjustment": "all",
            "start_utc": "2022-01-01", "end_exclusive_utc": "2022-02-01",
            "row_count": 2, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "validation_warnings": [], "universe_scope": "single_symbol_case_study",
        }), encoding="utf-8")
        return path

    def test_runner_rejects_mixed_feeds(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first = self.write_dataset(root, "AAPL")
            second = self.write_dataset(root, "MSFT", feed="iex")
            with self.assertRaisesRegex(ValueError, "same range, feed, and adjustment"):
                run_portfolio_research(
                    [first, second], trade_start="2022-01-01", trade_end="2022-02-01",
                )

    def test_runner_rejects_changed_dataset_hash(self) -> None:
        with TemporaryDirectory() as directory:
            first = self.write_dataset(Path(directory), "AAPL")
            first.write_text(first.read_text(encoding="utf-8").replace("101,99", "102,99"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum"):
                run_portfolio_research(
                    [first], trade_start="2022-01-01", trade_end="2022-02-01",
                )

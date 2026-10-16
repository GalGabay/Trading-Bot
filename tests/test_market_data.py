from __future__ import annotations

from datetime import UTC, date, datetime
from unittest import TestCase

import pandas as pd
from alpaca.data.timeframe import TimeFrame

from app.data.market_calendar import AlpacaMarketCalendar, TradingSession
from app.data.market_data import (
    CandleValidationError,
    MarketDataService,
    ValidationConfig,
    validate_candles,
)


def candles(timestamps: list[str] | None = None) -> pd.DataFrame:
    return pd.DataFrame({
        "timestamp": pd.to_datetime(timestamps or ["2026-01-02T15:00:00Z", "2026-01-02T16:00:00Z"], utc=True),
        "symbol": ["AAPL"] * len(timestamps or [1, 2]),
        "open": [100.0, 101.0][:len(timestamps or [1, 2])],
        "high": [102.0, 103.0][:len(timestamps or [1, 2])],
        "low": [99.0, 100.0][:len(timestamps or [1, 2])],
        "close": [101.0, 102.0][:len(timestamps or [1, 2])],
        "volume": [1000, 1100][:len(timestamps or [1, 2])],
    })


class StaticCalendar:
    def __init__(self, sessions: list[TradingSession]) -> None:
        self._sessions = sessions

    def sessions(self, start: date, end: date) -> list[TradingSession]:
        return [session for session in self._sessions if start <= session.opens_at.date() <= end]


def friday_session() -> TradingSession:
    return TradingSession(pd.Timestamp("2026-01-02T14:30:00Z"), pd.Timestamp("2026-01-02T17:00:00Z"))


class FakeBarSet:
    def __init__(self, frame: pd.DataFrame) -> None:
        self.df = frame


class FakeBroker:
    def __init__(self) -> None:
        self.calls = []

    def get_market_data(self, symbol, *, start, end, timeframe):
        self.calls.append((symbol, start, end, timeframe))
        return FakeBarSet(candles().set_index(["symbol", "timestamp"]))


class FakeCalendarBroker:
    def get_market_calendar(self, *, start, end):
        day = type("CalendarDay", (), {})()
        day.open = datetime(2026, 1, 2, 9, 30)
        day.close = datetime(2026, 1, 2, 16, 0)
        return [day]


class MarketDataTests(TestCase):
    def assert_error(self, frame: pd.DataFrame, code: str, **kwargs) -> None:
        with self.assertRaises(CandleValidationError) as context:
            validate_candles(frame, **kwargs)
        self.assertEqual(context.exception.issues[0].code, code)

    def test_valid_regular_session_candles_pass(self) -> None:
        report = validate_candles(
            candles(), calendar=StaticCalendar([friday_session()]),
            requested_start=datetime(2026, 1, 2, 15, 0, tzinfo=UTC),
            requested_end=datetime(2026, 1, 2, 16, 0, tzinfo=UTC),
        )
        self.assertEqual(report.warnings, ())

    def test_alpaca_naive_calendar_times_are_interpreted_as_new_york_time(self) -> None:
        session = AlpacaMarketCalendar(FakeCalendarBroker()).sessions(date(2026, 1, 2), date(2026, 1, 2))[0]
        self.assertEqual(session.opens_at, pd.Timestamp("2026-01-02T14:30:00Z"))
        self.assertEqual(session.closes_at, pd.Timestamp("2026-01-02T21:00:00Z"))

    def test_daily_bars_use_midnight_new_york_timestamp(self) -> None:
        daily = candles(["2026-01-02T05:00:00Z"])
        report = validate_candles(
            daily, config=ValidationConfig(timeframe=TimeFrame.Day), calendar=StaticCalendar([friday_session()]),
            requested_start=datetime(2026, 1, 2, 0, 0, tzinfo=UTC),
            requested_end=datetime(2026, 1, 2, 23, 59, tzinfo=UTC),
        )
        self.assertEqual(report.warnings, ())

    def test_invalid_and_naive_timestamps_are_rejected(self) -> None:
        invalid = candles().astype({"timestamp": "object"})
        invalid.loc[0, "timestamp"] = "not-a-date"
        self.assert_error(invalid, "invalid_timestamp")
        naive = candles().astype({"timestamp": "object"})
        naive.loc[0, "timestamp"] = "2026-01-02 14:30:00"
        self.assert_error(naive, "timezone_missing")

    def test_duplicate_candle_is_rejected(self) -> None:
        self.assert_error(pd.concat([candles(), candles().iloc[[0]]], ignore_index=True), "duplicate_candles")

    def test_missing_scheduled_candle_is_rejected(self) -> None:
        self.assert_error(
            candles().iloc[[0]], "unobserved_intervals", calendar=StaticCalendar([friday_session()]),
            config=ValidationConfig(require_all_scheduled_bars=True),
            requested_start=datetime(2026, 1, 2, 15, 0, tzinfo=UTC),
            requested_end=datetime(2026, 1, 2, 16, 0, tzinfo=UTC),
        )

    def test_unobserved_interval_is_warning_without_complete_feed_assumption(self) -> None:
        report = validate_candles(
            candles().iloc[[0]], calendar=StaticCalendar([friday_session()]),
            requested_start=datetime(2026, 1, 2, 15, 0, tzinfo=UTC),
            requested_end=datetime(2026, 1, 2, 16, 0, tzinfo=UTC),
        )
        self.assertEqual(report.time_gaps, 1)
        self.assertIn("unobserved_intervals", {issue.code for issue in report.warnings})

    def test_holiday_or_weekend_gap_is_not_a_missing_candle(self) -> None:
        short_friday = TradingSession(
            pd.Timestamp("2026-01-02T14:30:00Z"), pd.Timestamp("2026-01-02T15:30:00Z")
        )
        report = validate_candles(
            candles().iloc[[0]], calendar=StaticCalendar([short_friday]),
            requested_start=datetime(2026, 1, 2, 15, 0, tzinfo=UTC),
            requested_end=datetime(2026, 1, 5, 15, 0, tzinfo=UTC),
        )
        self.assertEqual(report.time_gaps, 0)

    def test_outside_regular_session_is_rejected(self) -> None:
        outside = candles(["2026-01-02T13:00:00Z"])
        self.assert_error(outside, "outside_market_session", calendar=StaticCalendar([friday_session()]))

    def test_impossible_ohlc_and_zero_price_are_rejected(self) -> None:
        bad_high = candles()
        bad_high.loc[0, "high"] = 98.0
        self.assert_error(bad_high, "invalid_high")
        zero_price = candles()
        zero_price.loc[0, "close"] = 0
        self.assert_error(zero_price, "invalid_price")

    def test_negative_volume_is_rejected(self) -> None:
        invalid = candles()
        invalid.loc[0, "volume"] = -1
        self.assert_error(invalid, "negative_volume")

    def test_infinite_price_is_rejected(self) -> None:
        invalid = candles()
        invalid.loc[0, "high"] = float("inf")
        self.assert_error(invalid, "invalid_ohlcv")

    def test_zero_and_anomalous_volume_are_warnings(self) -> None:
        frame = candles()
        frame.loc[0, "volume"] = 0
        frame.loc[1, "volume"] = 100_000
        extra = frame.iloc[[1]].copy()
        extra["timestamp"] = pd.Timestamp("2026-01-02T16:30:00Z")
        extra["volume"] = 100
        report = validate_candles(
            pd.concat([frame, extra], ignore_index=True),
            config=ValidationConfig(volume_anomaly_multiple=1.1),
        )
        self.assertEqual({warning.code for warning in report.warnings}, {"zero_volume", "volume_anomaly"})

    def test_service_uses_calendar_and_normalizes_broker_bars(self) -> None:
        broker = FakeBroker()
        service = MarketDataService(broker, calendar=StaticCalendar([friday_session()]))
        result, _ = service.get_historical_candles(
            " aapl ", start=datetime(2026, 1, 2, 14, 30, tzinfo=UTC),
            end=datetime(2026, 1, 2, 16, 0, tzinfo=UTC), timeframe=TimeFrame.Hour,
        )
        self.assertEqual(result.columns.tolist(), ["timestamp", "symbol", "open", "high", "low", "close", "volume"])
        self.assertEqual(broker.calls[0][0], "AAPL")

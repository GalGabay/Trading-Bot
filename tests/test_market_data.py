from __future__ import annotations

from datetime import UTC, datetime
from unittest import TestCase

import pandas as pd
from alpaca.data.timeframe import TimeFrame

from app.data.market_data import CandleValidationError, MarketDataService, validate_candles


def candles() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2026-01-02T14:30:00Z", "2026-01-02T15:30:00Z"], utc=True
            ),
            "symbol": ["AAPL", "AAPL"],
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
            "volume": [1000, 0],
        }
    )


class FakeBarSet:
    def __init__(self, frame: pd.DataFrame) -> None:
        self.df = frame


class FakeBroker:
    def __init__(self) -> None:
        self.calls = []

    def get_market_data(self, symbol, *, start, end, timeframe):
        self.calls.append((symbol, start, end, timeframe))
        source = candles().set_index(["symbol", "timestamp"])
        return FakeBarSet(source)


class MarketDataTests(TestCase):
    def test_valid_candles_report_zero_volume_without_rejecting_data(self) -> None:
        report = validate_candles(candles())
        self.assertEqual(report.zero_volume_rows, 1)

    def test_duplicate_symbol_timestamp_is_rejected(self) -> None:
        duplicate = pd.concat([candles(), candles().iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(CandleValidationError, "Duplicate"):
            validate_candles(duplicate)

    def test_impossible_ohlc_is_rejected(self) -> None:
        invalid = candles()
        invalid.loc[0, "high"] = 98.0
        with self.assertRaisesRegex(CandleValidationError, "High"):
            validate_candles(invalid)

    def test_service_normalizes_and_validates_broker_bars(self) -> None:
        broker = FakeBroker()
        service = MarketDataService(broker)
        start = datetime(2026, 1, 2, tzinfo=UTC)
        result, report = service.get_historical_candles(
            " aapl ", start=start, timeframe=TimeFrame.Hour
        )
        self.assertEqual(result.columns.tolist(), [
            "timestamp", "symbol", "open", "high", "low", "close", "volume"
        ])
        self.assertEqual(result["symbol"].tolist(), ["AAPL", "AAPL"])
        self.assertEqual(report.zero_volume_rows, 1)
        self.assertEqual(broker.calls[0][0], "AAPL")

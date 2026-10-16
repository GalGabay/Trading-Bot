from __future__ import annotations

import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import pandas as pd

from app.data.database import DataStorageError, TradingDatabase
from app.data.market_data import CandleValidationError


def candle_frame() -> pd.DataFrame:
    return pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-01-02T15:00:00Z", "2026-01-02T16:00:00Z"], utc=True),
        "symbol": ["aapl", "aapl"],
        "open": [100.0, 101.0], "high": [102.0, 103.0], "low": [99.0, 100.0],
        "close": [101.0, 102.0], "volume": [1000, 1100],
    })


class TradingDatabaseTests(TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "state.sqlite3"
        self.database = TradingDatabase(self.database_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_initialize_creates_all_audit_tables(self) -> None:
        self.database.initialize()
        connection = sqlite3.connect(self.database_path)
        try:
            table_names = {
                row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
        finally:
            connection.close()
        self.assertTrue({
            "candles", "features", "signals", "orders", "fills", "positions",
            "portfolio_snapshots", "strategy_runs", "model_predictions", "system_events",
        }.issubset(table_names))

    def test_candles_round_trip_as_canonical_utc_data(self) -> None:
        self.assertEqual(self.database.upsert_candles(candle_frame(), timeframe="1Hour"), 2)
        stored = self.database.get_candles("AAPL", timeframe="1Hour")
        self.assertEqual(stored["symbol"].tolist(), ["AAPL", "AAPL"])
        self.assertEqual(stored["timestamp"].dt.tz, pd.Timestamp("2026-01-02T15:00:00Z").tz)
        self.assertEqual(stored["close"].tolist(), [101.0, 102.0])

    def test_upsert_updates_existing_candle_without_duplicate(self) -> None:
        self.database.upsert_candles(candle_frame(), timeframe="1Hour")
        revised = candle_frame().iloc[[0]].copy()
        revised.loc[0, "close"] = 101.5
        revised.loc[0, "high"] = 102.5
        self.assertEqual(self.database.upsert_candles(revised, timeframe="1Hour"), 1)
        stored = self.database.get_candles("AAPL", timeframe="1Hour")
        self.assertEqual(len(stored), 2)
        self.assertEqual(stored.loc[0, "close"], 101.5)

    def test_invalid_batch_is_rejected_without_partial_write(self) -> None:
        self.database.upsert_candles(candle_frame().iloc[[0]], timeframe="1Hour")
        invalid = candle_frame()
        invalid.loc[1, "volume"] = -1
        with self.assertRaises(CandleValidationError):
            self.database.upsert_candles(invalid, timeframe="1Hour")
        stored = self.database.get_candles("AAPL", timeframe="1Hour")
        self.assertEqual(len(stored), 1)

    def test_empty_timeframe_is_rejected(self) -> None:
        with self.assertRaises(DataStorageError):
            self.database.upsert_candles(candle_frame(), timeframe="  ")

    def test_time_range_query_is_inclusive(self) -> None:
        self.database.upsert_candles(candle_frame(), timeframe="1Hour")
        stored = self.database.get_candles(
            "AAPL", timeframe="1Hour", start=pd.Timestamp("2026-01-02T16:00:00Z")
        )
        self.assertEqual(stored["timestamp"].tolist(), [pd.Timestamp("2026-01-02T16:00:00Z")])

    def test_features_are_upserted_by_timestamp_symbol_and_version(self) -> None:
        features = candle_frame().iloc[[0]].copy()
        features["ema_20"] = [100.5]
        features["rsi_14"] = [55.0]
        self.assertEqual(self.database.upsert_features(features, timeframe="1Hour", feature_version="technical_v1"), 1)
        features["rsi_14"] = [56.0]
        self.database.upsert_features(features, timeframe="1Hour", feature_version="technical_v1")
        connection = sqlite3.connect(self.database_path)
        try:
            row = connection.execute("SELECT values_json FROM features").fetchone()
        finally:
            connection.close()
        self.assertIn('"rsi_14": 56.0', row[0])

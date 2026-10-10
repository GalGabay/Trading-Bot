"""SQLite persistence for validated trading-bot state.

The first repository API persists candles. The remaining schema tables provide
stable audit storage for later phases without putting strategy logic here.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from app.data.market_data import CANONICAL_CANDLE_COLUMNS, validate_candles

SCHEMA_VERSION = 1


class DataStorageError(ValueError):
    """Raised when data cannot be stored safely in the local database."""


class TradingDatabase:
    """A small SQLite repository with explicit schema initialization.

    SQLite connections are short-lived, so this class is safe to create in a
    Windows development process and in the Raspberry Pi service. It does not
    share a connection across threads or processes.
    """

    def __init__(self, path: str | Path = "data/trading_bot.sqlite3") -> None:
        self.path = Path(path)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create the initial schema if it has not already been created."""
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                );

                CREATE TABLE IF NOT EXISTS candles (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    open REAL NOT NULL CHECK (open > 0),
                    high REAL NOT NULL CHECK (high >= open AND high >= low AND high >= close),
                    low REAL NOT NULL CHECK (low <= open AND low <= high AND low <= close),
                    close REAL NOT NULL CHECK (close > 0),
                    volume REAL NOT NULL CHECK (volume >= 0),
                    timeframe TEXT NOT NULL,
                    UNIQUE (timestamp, symbol, timeframe)
                );
                CREATE INDEX IF NOT EXISTS ix_candles_symbol_timeframe_timestamp
                    ON candles (symbol, timeframe, timestamp);

                CREATE TABLE IF NOT EXISTS features (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    feature_version TEXT NOT NULL,
                    values_json TEXT NOT NULL,
                    UNIQUE (timestamp, symbol, timeframe, feature_version)
                );
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    score REAL,
                    reason TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY,
                    client_order_id TEXT NOT NULL UNIQUE,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL CHECK (quantity > 0),
                    order_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    alpaca_order_id TEXT UNIQUE
                );
                CREATE TABLE IF NOT EXISTS fills (
                    id INTEGER PRIMARY KEY,
                    order_id INTEGER NOT NULL REFERENCES orders(id),
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    quantity REAL NOT NULL CHECK (quantity > 0),
                    price REAL NOT NULL CHECK (price > 0)
                );
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    average_entry_price REAL,
                    market_price REAL,
                    UNIQUE (timestamp, symbol)
                );
                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL UNIQUE,
                    equity REAL NOT NULL,
                    cash REAL NOT NULL,
                    buying_power REAL,
                    payload_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS strategy_runs (
                    id INTEGER PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    strategy TEXT NOT NULL,
                    status TEXT NOT NULL,
                    configuration_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS model_predictions (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    prediction REAL NOT NULL,
                    confidence REAL,
                    UNIQUE (timestamp, symbol, model_version)
                );
                CREATE TABLE IF NOT EXISTS system_events (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}'
                );
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations (version) VALUES (?)", (SCHEMA_VERSION,)
            )

    def upsert_candles(self, candles: pd.DataFrame, *, timeframe: str) -> int:
        """Atomically store canonical candles, updating an existing identity.

        Call this after :class:`MarketDataService` completes calendar-aware
        validation. Structural validation runs again here as a defence in
        depth; it never fills or fabricates data.
        """
        normalized_timeframe = timeframe.strip()
        if not normalized_timeframe:
            raise DataStorageError("timeframe must not be empty")
        missing = set(CANONICAL_CANDLE_COLUMNS) - set(candles.columns)
        if missing:
            raise DataStorageError(f"Candle table is missing required columns: {sorted(missing)}")
        validate_candles(candles)
        records = self._candle_records(candles, normalized_timeframe)
        self.initialize()
        with self._connection() as connection:
            connection.executemany(
                """
                INSERT INTO candles (timestamp, symbol, open, high, low, close, volume, timeframe)
                VALUES (:timestamp, :symbol, :open, :high, :low, :close, :volume, :timeframe)
                ON CONFLICT(timestamp, symbol, timeframe) DO UPDATE SET
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    close = excluded.close,
                    volume = excluded.volume
                """,
                records,
            )
        return len(records)

    def get_candles(
        self,
        symbol: str,
        *,
        timeframe: str,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        """Return stored candles ordered by UTC timestamp, without mutation."""
        self.initialize()
        clauses = ["symbol = ?", "timeframe = ?"]
        parameters: list[str] = [symbol.strip().upper(), timeframe.strip()]
        if start is not None:
            clauses.append("timestamp >= ?")
            parameters.append(self._timestamp_text(start))
        if end is not None:
            clauses.append("timestamp <= ?")
            parameters.append(self._timestamp_text(end))
        query = "SELECT timestamp, symbol, open, high, low, close, volume FROM candles WHERE "
        query += " AND ".join(clauses) + " ORDER BY timestamp"
        with self._connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        result = pd.DataFrame([dict(row) for row in rows], columns=CANONICAL_CANDLE_COLUMNS)
        if not result.empty:
            result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True)
        return result

    @staticmethod
    def _timestamp_text(value: object) -> str:
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise DataStorageError("Database timestamps must include a timezone offset.")
        return timestamp.tz_convert("UTC").isoformat().replace("+00:00", "Z")

    def _candle_records(self, candles: pd.DataFrame, timeframe: str) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        for row in candles.loc[:, CANONICAL_CANDLE_COLUMNS].to_dict("records"):
            records.append({
                "timestamp": self._timestamp_text(row["timestamp"]),
                "symbol": str(row["symbol"]).strip().upper(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
                "timeframe": timeframe,
            })
        return records

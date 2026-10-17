"""SQLite persistence for validated trading-bot state.

The first repository API persists candles. The remaining schema tables provide
stable audit storage for later phases without putting strategy logic here.
"""

from __future__ import annotations

import sqlite3
import json
import math
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from app.data.market_data import CANONICAL_CANDLE_COLUMNS, validate_candles
from app.strategy.base import Signal

SCHEMA_VERSION = 4


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
                    limit_price TEXT,
                    status TEXT NOT NULL,
                    alpaca_order_id TEXT UNIQUE
                );
                CREATE TABLE IF NOT EXISTS order_events (
                    id INTEGER PRIMARY KEY,
                    client_order_id TEXT NOT NULL REFERENCES orders(client_order_id),
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    filled_quantity TEXT,
                    filled_average_price TEXT,
                    details_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS ix_order_events_client_time
                    ON order_events (client_order_id, id);
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
                CREATE TABLE IF NOT EXISTS broker_open_orders (
                    alpaca_order_id TEXT PRIMARY KEY,
                    client_order_id TEXT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    status TEXT NOT NULL,
                    quantity TEXT,
                    notional TEXT,
                    filled_quantity TEXT,
                    observed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS broker_current_positions (
                    symbol TEXT PRIMARY KEY,
                    side TEXT NOT NULL,
                    quantity TEXT NOT NULL,
                    average_entry_price TEXT NOT NULL,
                    market_price TEXT NOT NULL,
                    market_value TEXT NOT NULL,
                    unrealized_pl TEXT,
                    observed_at TEXT NOT NULL
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
            # Existing Phase 12 databases have the original orders table.
            # Keep those rows, but their unknown limit must not match a new
            # intent with the same client ID.
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(orders)")}
            if "limit_price" not in columns:
                connection.execute("ALTER TABLE orders ADD COLUMN limit_price TEXT")
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

    def upsert_features(self, features: pd.DataFrame, *, timeframe: str, feature_version: str) -> int:
        """Persist a feature row as JSON keyed by time, symbol, and version."""
        if features.empty:
            raise DataStorageError("features must not be empty")
        if not timeframe.strip() or not feature_version.strip():
            raise DataStorageError("timeframe and feature_version must not be empty")
        required = {"timestamp", "symbol"}
        if missing := required - set(features.columns):
            raise DataStorageError(f"Feature table is missing required columns: {sorted(missing)}")
        feature_columns = [column for column in features.columns if column not in CANONICAL_CANDLE_COLUMNS]
        if not feature_columns:
            raise DataStorageError("features must contain at least one calculated feature column")
        records = []
        for row in features.to_dict("records"):
            values = {column: (None if pd.isna(row[column]) else float(row[column])) for column in feature_columns}
            records.append({
                "timestamp": self._timestamp_text(row["timestamp"]), "symbol": str(row["symbol"]).upper().strip(),
                "timeframe": timeframe.strip(), "feature_version": feature_version.strip(),
                "values_json": json.dumps(values, allow_nan=False, sort_keys=True),
            })
        self.initialize()
        with self._connection() as connection:
            connection.executemany(
                """INSERT INTO features (timestamp, symbol, timeframe, feature_version, values_json)
                VALUES (:timestamp, :symbol, :timeframe, :feature_version, :values_json)
                ON CONFLICT(timestamp, symbol, timeframe, feature_version) DO UPDATE SET values_json = excluded.values_json""",
                records,
            )
        return len(records)

    def record_signal(self, signal: Signal) -> int:
        """Append an immutable strategy decision to the audit trail.

        Signals are deliberately recorded by the application/backtest caller,
        rather than inside a strategy. That preserves the strategy's ability
        to run without SQLite while ensuring each consumed decision can be
        reconstructed later.
        """
        self.initialize()
        with self._connection() as connection:
            cursor = connection.execute(
                """INSERT INTO signals (timestamp, symbol, strategy, signal, score, reason)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    self._timestamp_text(signal.timestamp),
                    signal.symbol.strip().upper(),
                    signal.strategy,
                    str(signal.action),
                    signal.confidence,
                    signal.reason,
                ),
            )
        return int(cursor.lastrowid)

    def record_portfolio_state(self, state: Mapping[str, Any]) -> dict[str, Any] | None:
        """Atomically append one broker-authoritative snapshot and its positions.

        Return the previous snapshot for reconciliation reporting. The JSON
        payload preserves decimal strings and open-order state; the existing
        relational columns support simple time-series queries. Short position
        quantities are stored as negative numbers in the positions table.
        """
        if state.get("source") != "alpaca_paper" or not isinstance(state.get("positions"), list):
            raise DataStorageError("Portfolio state must contain Alpaca paper positions")
        if not isinstance(state.get("account_id"), str) or not state["account_id"].strip():
            raise DataStorageError("Portfolio state must identify the Alpaca paper account")
        if not isinstance(state.get("open_orders"), list):
            raise DataStorageError("Portfolio state must contain Alpaca paper open orders")
        timestamp = self._timestamp_text(state.get("as_of"))
        try:
            payload_json = json.dumps(state, allow_nan=False, sort_keys=True)
            equity = float(state["equity"])
            cash = float(state["cash"])
            buying_power = float(state["buying_power"])
            positions = [
                (
                    timestamp, row["symbol"],
                    float(row["quantity"]) * (-1 if row["side"] == "short" else 1),
                    float(row["average_entry_price"]), float(row["market_price"]),
                )
                for row in state["positions"]
            ]
            orders = [
                (
                    row["order_id"], row.get("client_order_id"), row["symbol"],
                    row["side"], row["status"], row.get("quantity"),
                    row.get("notional"), row.get("filled_quantity"), timestamp,
                )
                for row in state["open_orders"]
            ]
            current_positions = [
                (
                    row["symbol"], row["side"], row["quantity"],
                    row["average_entry_price"], row["market_price"],
                    row["market_value"], row.get("unrealized_pl"), timestamp,
                )
                for row in state["positions"]
            ]
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise DataStorageError("Portfolio state has invalid numeric or position fields") from exc
        if not all(math.isfinite(value) for value in (equity, cash, buying_power)):
            raise DataStorageError("Portfolio balances exceed SQLite's finite numeric range")
        if any(not all(math.isfinite(value) for value in (row[2], row[3], row[4])) for row in positions):
            raise DataStorageError("Portfolio positions exceed SQLite's finite numeric range")
        self.initialize()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload_json FROM portfolio_snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
            previous = None if row is None else json.loads(row["payload_json"])
            if previous is not None and previous.get("account_id") not in (None, state["account_id"]):
                raise DataStorageError("This database contains snapshots for a different Alpaca account")
            connection.execute(
                """INSERT INTO portfolio_snapshots (timestamp, equity, cash, buying_power, payload_json)
                VALUES (?, ?, ?, ?, ?)""",
                (timestamp, equity, cash, buying_power, payload_json),
            )
            connection.executemany(
                """INSERT INTO positions (timestamp, symbol, quantity, average_entry_price, market_price)
                VALUES (?, ?, ?, ?, ?)""",
                positions,
            )
            connection.execute("DELETE FROM broker_current_positions")
            connection.executemany(
                """INSERT INTO broker_current_positions
                (symbol, side, quantity, average_entry_price, market_price, market_value, unrealized_pl, observed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                current_positions,
            )
            connection.execute("DELETE FROM broker_open_orders")
            connection.executemany(
                """INSERT INTO broker_open_orders
                (alpaca_order_id, client_order_id, symbol, side, status, quantity, notional, filled_quantity, observed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                orders,
            )
        return previous

    def get_latest_portfolio_state(self) -> dict[str, Any] | None:
        """Read the latest reconciled broker snapshot, if one exists."""
        self.initialize()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT payload_json FROM portfolio_snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return None if row is None else json.loads(row["payload_json"])

    def get_peak_portfolio_equity(self) -> float | None:
        """Highest observed broker equity in this database's snapshot history."""
        self.initialize()
        with self._connection() as connection:
            value = connection.execute("SELECT MAX(equity) FROM portfolio_snapshots").fetchone()[0]
        return None if value is None else float(value)

    def get_order_record(self, client_order_id: str) -> dict[str, Any] | None:
        """Return the current local order journal row, if present."""
        self.initialize()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM orders WHERE client_order_id = ?", (client_order_id,)
            ).fetchone()
        return None if row is None else dict(row)

    def reserve_order(
        self, *, client_order_id: str, timestamp: object, symbol: str,
        side: str, quantity: int, limit_price: str,
        order_type: str = "limit",
    ) -> tuple[bool, dict[str, Any]]:
        """Reserve a stable client ID before any broker submission.

        Return ``(created, row)``. Existing IDs are never overwritten here;
        the caller must compare the stored identity and must not resubmit.
        """
        if not client_order_id or not symbol or side not in {"buy", "sell"} or type(quantity) is not int or quantity < 1 or order_type != "limit":
            raise DataStorageError("Invalid order reservation")
        try:
            price = Decimal(str(limit_price))
        except (InvalidOperation, ValueError, TypeError):
            raise DataStorageError("Invalid order limit price") from None
        if not price.is_finite() or price <= 0:
            raise DataStorageError("Invalid order limit price")
        timestamp_text = self._timestamp_text(timestamp)
        self.initialize()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """INSERT OR IGNORE INTO orders
                (client_order_id, timestamp, symbol, side, quantity, order_type, limit_price, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'reserved')""",
                (client_order_id, timestamp_text, symbol, side, quantity, order_type, str(price)),
            )
            row = connection.execute(
                "SELECT * FROM orders WHERE client_order_id = ?", (client_order_id,)
            ).fetchone()
            if cursor.rowcount == 1:
                connection.execute(
                    "INSERT INTO order_events (client_order_id, timestamp, status) VALUES (?, ?, 'reserved')",
                    (client_order_id, timestamp_text),
                )
        return cursor.rowcount == 1, dict(row)

    def record_order_update(
        self, *, client_order_id: str, timestamp: object, status: str,
        alpaca_order_id: str | None = None, filled_quantity: str | None = None,
        filled_average_price: str | None = None, details: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Atomically update current order status and append an audit event."""
        if not status:
            raise DataStorageError("Order status must not be empty")
        timestamp_text = self._timestamp_text(timestamp)
        details_json = json.dumps(details or {}, allow_nan=False, sort_keys=True)
        self.initialize()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM orders WHERE client_order_id = ?", (client_order_id,)
            ).fetchone()
            if row is None:
                raise DataStorageError("Order must be reserved before its status can be updated")
            if row["alpaca_order_id"] and alpaca_order_id and row["alpaca_order_id"] != alpaca_order_id:
                raise DataStorageError("Alpaca order ID changed for a stable client order ID")
            connection.execute(
                """UPDATE orders SET status = ?, alpaca_order_id = COALESCE(?, alpaca_order_id)
                WHERE client_order_id = ?""",
                (status, alpaca_order_id, client_order_id),
            )
            connection.execute(
                """INSERT INTO order_events
                (client_order_id, timestamp, status, filled_quantity, filled_average_price, details_json)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (client_order_id, timestamp_text, status, filled_quantity, filled_average_price, details_json),
            )
            updated = connection.execute(
                "SELECT * FROM orders WHERE client_order_id = ?", (client_order_id,)
            ).fetchone()
        return dict(updated)

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

"""Persistent, fail-closed stop for new paper orders.

The latch uses its own SQLite file so corruption of the trading-state database
does not erase an emergency stop. A missing or unreadable latch denies orders.
Only an explicit operator reset can clear a trip. No position is liquidated.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.risk.risk_manager import RiskLimits, RiskManager, RiskPortfolioSnapshot


@dataclass(frozen=True)
class KillSwitchStatus:
    allow_new_orders: bool
    reason: str | None
    consecutive_api_failures: int
    tripped_at: str | None


class KillSwitch:
    """Store one durable stop state shared by Windows or Pi processes."""

    def __init__(self, path: str | Path = "data/kill_switch.sqlite3", *, max_api_failures: int = 3) -> None:
        if type(max_api_failures) is not int or max_api_failures < 1:
            raise ValueError("max_api_failures must be a positive integer")
        self.path = Path(path)
        self.max_api_failures = max_api_failures

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS kill_switch_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    allow_new_orders INTEGER NOT NULL CHECK (allow_new_orders IN (0, 1)),
                    reason TEXT,
                    consecutive_api_failures INTEGER NOT NULL DEFAULT 0,
                    tripped_at TEXT
                );
                CREATE TABLE IF NOT EXISTS kill_switch_events (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT NOT NULL
                );
            """)
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _from_row(row: sqlite3.Row | None) -> KillSwitchStatus:
        if row is None:
            return KillSwitchStatus(False, "uninitialized", 0, None)
        return KillSwitchStatus(
            bool(row["allow_new_orders"]), row["reason"],
            int(row["consecutive_api_failures"]), row["tripped_at"],
        )

    def status(self) -> KillSwitchStatus:
        """Return denied if the latch is missing, locked, or unreadable."""
        try:
            with self._connect() as connection:
                row = connection.execute("SELECT * FROM kill_switch_state WHERE id = 1").fetchone()
            return self._from_row(row)
        except (sqlite3.Error, OSError):
            return KillSwitchStatus(False, "kill_switch_unavailable", 0, None)

    def trip(self, reason: str) -> KillSwitchStatus:
        """Latch an emergency stop; a subsequent trip cannot clear it."""
        reason = reason.strip() if isinstance(reason, str) else ""
        if not reason:
            raise ValueError("A nonempty trip reason is required")
        now = self._now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM kill_switch_state WHERE id = 1").fetchone()
            if row is not None and not row["allow_new_orders"]:
                return self._from_row(row)
            failures = 0 if row is None else int(row["consecutive_api_failures"])
            connection.execute(
                """INSERT INTO kill_switch_state
                (id, allow_new_orders, reason, consecutive_api_failures, tripped_at)
                VALUES (1, 0, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET allow_new_orders = 0, reason = excluded.reason,
                consecutive_api_failures = excluded.consecutive_api_failures,
                tripped_at = excluded.tripped_at""",
                (reason, failures, now),
            )
            connection.execute(
                "INSERT INTO kill_switch_events (timestamp, action, reason) VALUES (?, 'trip', ?)",
                (now, reason),
            )
            return KillSwitchStatus(False, reason, failures, now)

    def reset(self, operator_note: str) -> KillSwitchStatus:
        """Explicitly re-enable new orders after an operator review."""
        note = operator_note.strip() if isinstance(operator_note, str) else ""
        if not note:
            raise ValueError("An operator note is required to reset the kill switch")
        now = self._now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """INSERT INTO kill_switch_state
                (id, allow_new_orders, reason, consecutive_api_failures, tripped_at)
                VALUES (1, 1, NULL, 0, NULL)
                ON CONFLICT(id) DO UPDATE SET allow_new_orders = 1, reason = NULL,
                consecutive_api_failures = 0, tripped_at = NULL"""
            )
            connection.execute(
                "INSERT INTO kill_switch_events (timestamp, action, reason) VALUES (?, 'reset', ?)",
                (now, note),
            )
        return KillSwitchStatus(True, None, 0, None)

    def record_api_failure(self) -> KillSwitchStatus:
        """Trip after the configured number of consecutive broker failures."""
        now = self._now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM kill_switch_state WHERE id = 1").fetchone()
            if row is None or not row["allow_new_orders"]:
                return self._from_row(row)
            failures = int(row["consecutive_api_failures"]) + 1
            tripped = failures >= self.max_api_failures
            reason = "api_failure_threshold" if tripped else None
            connection.execute(
                """UPDATE kill_switch_state SET allow_new_orders = ?, reason = ?,
                consecutive_api_failures = ?, tripped_at = ? WHERE id = 1""",
                (0 if tripped else 1, reason, failures, now if tripped else None),
            )
            if tripped:
                connection.execute(
                    "INSERT INTO kill_switch_events (timestamp, action, reason) VALUES (?, 'trip', ?)",
                    (now, reason),
                )
            return KillSwitchStatus(not tripped, reason, failures, now if tripped else None)

    def record_api_success(self) -> KillSwitchStatus:
        """Clear the failure streak, but never clear a latched stop."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM kill_switch_state WHERE id = 1").fetchone()
            if row is None or not row["allow_new_orders"]:
                return self._from_row(row)
            connection.execute("UPDATE kill_switch_state SET consecutive_api_failures = 0 WHERE id = 1")
        return KillSwitchStatus(True, None, 0, None)

    def observe_portfolio(self, snapshot: RiskPortfolioSnapshot | None, limits: RiskLimits) -> KillSwitchStatus:
        """Trip for unexpected state or an account loss ceiling.

        The order workflow must call this after fetching a fresh snapshot and
        then check ``status().allow_new_orders`` before every submission.
        """
        if (
            not isinstance(snapshot, RiskPortfolioSnapshot)
            or snapshot.complete is not True
            or not isinstance(snapshot.as_of, datetime)
            or snapshot.as_of.tzinfo is None
            or snapshot.as_of.utcoffset() is None
            or not RiskManager._valid_snapshot(snapshot)
        ):
            return self.trip("unexpected_account_state")
        if snapshot.equity <= snapshot.day_start_equity * (1 - limits.max_daily_loss):
            return self.trip("daily_loss_limit")
        if snapshot.equity <= snapshot.peak_equity * (1 - limits.max_drawdown):
            return self.trip("drawdown_limit")
        return self.status()

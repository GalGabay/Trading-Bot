"""Phase 13 startup recovery. Broker access here is read-only.

Recovery never resets the kill switch, submits, replaces, or cancels an order.
It checks persisted state before constructing the paper broker, reconciles
unfinished order IDs and a fresh account snapshot, and returns an explicit
readiness decision. A later service may use that decision to resume *order
evaluation*; this module cannot enable execution by itself.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.broker.alpaca_client import AlpacaClient
from app.data.database import TradingDatabase
from app.orders.order_manager import OrderManager
from app.portfolio.portfolio_manager import PortfolioManager
from app.risk.config import load_paper_risk_limits
from app.risk.kill_switch import KillSwitch
from app.risk.risk_manager import RiskLimits, RiskManager


@dataclass(frozen=True)
class RecoveryReport:
    checked_at: datetime
    database_valid: bool
    account_id: str | None
    snapshot_as_of: datetime | None
    market_open: bool | None
    local_orders_checked: int
    resolved_order_ids: tuple[str, ...]
    unresolved_order_ids: tuple[str, ...]
    status_changes: tuple[str, ...]
    portfolio_changes: tuple[str, ...]
    external_open_order_ids: tuple[str, ...]
    reasons: tuple[str, ...]
    can_resume_order_evaluation: bool

    def as_dict(self) -> dict[str, Any]:
        """JSON-safe operational summary without credentials or order prices."""
        return {
            "checked_at": self.checked_at.isoformat(),
            "database_valid": self.database_valid,
            "account_id": self.account_id,
            "snapshot_as_of": None if self.snapshot_as_of is None else self.snapshot_as_of.isoformat(),
            "market_open": self.market_open,
            "local_orders_checked": self.local_orders_checked,
            "resolved_order_ids": list(self.resolved_order_ids),
            "unresolved_order_ids": list(self.unresolved_order_ids),
            "status_changes": list(self.status_changes),
            "portfolio_changes": list(self.portfolio_changes),
            "external_open_order_ids": list(self.external_open_order_ids),
            "reasons": list(self.reasons),
            "can_resume_order_evaluation": self.can_resume_order_evaluation,
        }


class RecoveryManager:
    """Reconcile one paper account at boot while keeping submissions disabled.

    Each instance assumes the paper account has one active bot process. The
    broker factory is called only after the local database passes validation.
    An unapproved risk file still permits a read-only recovery report, but it
    can never yield readiness for order evaluation.
    """

    def __init__(
        self, database: TradingDatabase, kill_switch: KillSwitch, *,
        risk_config_path: str | Path = "config/risk_limits.json",
        broker_factory: Callable[[], AlpacaClient] = AlpacaClient,
        max_order_lookups: int = 100,
    ) -> None:
        if type(max_order_lookups) is not int or max_order_lookups < 1:
            raise ValueError("max_order_lookups must be a positive integer")
        self.database = database
        self.kill_switch = kill_switch
        self.risk_config_path = Path(risk_config_path)
        self.broker_factory = broker_factory
        self.max_order_lookups = max_order_lookups

    @staticmethod
    def _label(value: Any) -> str:
        return str(getattr(value, "value", value)).strip().lower()

    @staticmethod
    def _fresh_clock(clock: Any, checked_at: datetime) -> bool:
        timestamp = getattr(clock, "timestamp", None)
        return (
            isinstance(timestamp, datetime)
            and timestamp.tzinfo is not None
            and timestamp.utcoffset() is not None
            and 0 <= (checked_at - timestamp).total_seconds() <= 30
        )

    def run(self) -> RecoveryReport:
        checked_at = datetime.now(timezone.utc)
        reasons: list[str] = []
        resolved: list[str] = []
        active_broker_orders: dict[str, tuple[str, str | None]] = {}
        unresolved: list[str] = []
        status_changes: list[str] = []
        portfolio_changes: list[str] = []
        external_open: list[str] = []
        database_valid = False
        account_id: str | None = None
        snapshot_as_of: datetime | None = None
        market_open: bool | None = None
        checked_orders = 0

        def trip(reason: str) -> None:
            try:
                self.kill_switch.trip(reason)
            except Exception:
                reasons.append("kill_switch_unavailable")

        def finish() -> RecoveryReport:
            if not self.kill_switch.status().allow_new_orders:
                reasons.append("kill_switch_denied")
            unique_reasons = tuple(dict.fromkeys(reasons))
            report = RecoveryReport(
                checked_at=checked_at, database_valid=database_valid,
                account_id=account_id, snapshot_as_of=snapshot_as_of,
                market_open=market_open, local_orders_checked=checked_orders,
                resolved_order_ids=tuple(resolved), unresolved_order_ids=tuple(unresolved),
                status_changes=tuple(status_changes), portfolio_changes=tuple(portfolio_changes),
                external_open_order_ids=tuple(external_open), reasons=unique_reasons,
                can_resume_order_evaluation=database_valid and not unique_reasons,
            )
            if database_valid:
                try:
                    self.database.record_system_event(
                        level="info" if report.can_resume_order_evaluation else "warning",
                        event_type="startup_recovery", message="Startup reconciliation completed",
                        payload=report.as_dict(), timestamp=checked_at,
                    )
                except Exception:
                    trip("recovery_audit_failed")
                    return replace(
                        report,
                        reasons=tuple(dict.fromkeys((*report.reasons, "recovery_audit_failed"))),
                        can_resume_order_evaluation=False,
                    )
            return report

        try:
            limits: RiskLimits | None = load_paper_risk_limits(self.risk_config_path)
        except (OSError, ValueError):
            limits = None
            reasons.append("risk_config_unapproved_or_invalid")

        database_existed = self.database.path.exists()
        try:
            self.database.validate_integrity()
            database_valid = True
            previous = self.database.get_latest_portfolio_state()
            unsettled = self.database.list_unsettled_orders(limit=self.max_order_lookups + 1)
        except Exception:
            reasons.append("database_invalid_or_unavailable")
            trip("startup_database_invalid")
            return finish()
        if not database_existed or previous is None:
            reasons.append("no_prior_portfolio_baseline")
            trip("startup_baseline_missing")
        if len(unsettled) > self.max_order_lookups:
            reasons.append("too_many_unsettled_orders")
            trip("startup_order_inventory_incomplete")
            return finish()

        try:
            broker = self.broker_factory()
            initial_account = broker.get_account()
            account_id = self._label(getattr(initial_account, "id", None))
            if not account_id or account_id == "none":
                raise ValueError("Paper account ID is unavailable")
        except Exception:
            reasons.append("paper_broker_unavailable")
            trip("startup_broker_unavailable")
            return finish()

        order_manager = OrderManager(
            broker, self.database, self.kill_switch,
            risk_config_path=self.risk_config_path, enable_paper_submission=False,
        )
        for row in unsettled:
            client_id = str(row["client_order_id"])
            checked_orders += 1
            try:
                outcome = order_manager.refresh_status(client_id)
            except Exception:
                outcome = None
            if outcome is None or outcome.status in {"unknown", "identity_conflict"}:
                unresolved.append(client_id)
                continue
            resolved.append(client_id)
            if outcome.status not in {"filled", "canceled", "expired", "rejected", "replaced", "blocked"}:
                active_broker_orders[client_id] = (outcome.status, outcome.alpaca_order_id)
            if outcome.status != row["status"]:
                status_changes.append(f"{client_id}: {row['status']} -> {outcome.status}")
        if unresolved:
            reasons.append("unresolved_local_orders")
            trip("startup_orders_unresolved")
        if status_changes:
            reasons.append("order_status_changed_during_downtime")
            trip("startup_order_status_changed")

        try:
            snapshot = PortfolioManager(broker, self.database).reconcile().snapshot
            snapshot_as_of = snapshot.as_of
            current = snapshot.as_record()
            if snapshot.account_id != account_id:
                reasons.append("account_identity_changed")
                trip("startup_account_identity_changed")
            if (
                self._label(getattr(initial_account, "status", None)) != "active"
                or getattr(initial_account, "trading_blocked", None) is not False
                or getattr(initial_account, "account_blocked", None) is not False
            ):
                reasons.append("account_not_active")
                trip("startup_account_not_active")
            if previous is not None:
                portfolio_changes.extend(PortfolioManager._compare(previous, current))
            if any(change.startswith(("position ", "open order ")) for change in portfolio_changes):
                reasons.append("holdings_or_open_orders_changed_during_downtime")
                trip("startup_portfolio_changed")
            if snapshot.open_orders:
                reasons.append("open_orders_present")
                for order in snapshot.open_orders:
                    local = self.database.get_order_record(order.client_order_id or "")
                    if (
                        local is None
                        or local["status"] in {"filled", "canceled", "expired", "rejected", "replaced", "blocked"}
                        or local["alpaca_order_id"] not in (None, order.order_id)
                    ):
                        external_open.append(order.order_id)
                if external_open:
                    reasons.append("external_or_mismatched_open_orders")
                    trip("startup_external_open_orders")
            open_by_client = {
                order.client_order_id: order for order in snapshot.open_orders
                if order.client_order_id is not None
            }
            if any(
                client_id not in open_by_client
                or open_by_client[client_id].order_id != broker_id
                or open_by_client[client_id].status != status
                for client_id, (status, broker_id) in active_broker_orders.items()
            ):
                reasons.append("broker_order_inventory_mismatch")
                trip("startup_order_inventory_mismatch")
            peak = self.database.get_peak_portfolio_equity()
            risk_snapshot = OrderManager._risk_snapshot(snapshot, peak)
            if not risk_snapshot.complete or not RiskManager._valid_snapshot(risk_snapshot):
                reasons.append("incomplete_or_inconsistent_account_state")
                trip("startup_account_state_invalid")
            elif limits is not None:
                age = (datetime.now(timezone.utc) - risk_snapshot.as_of).total_seconds()
                if age < 0 or age > limits.max_snapshot_age_seconds:
                    reasons.append("portfolio_snapshot_stale")
                    trip("startup_snapshot_stale")
                if not self.kill_switch.observe_portfolio(risk_snapshot, limits).allow_new_orders:
                    reasons.append("risk_or_kill_switch_denied")
        except Exception:
            reasons.append("portfolio_reconciliation_failed")
            trip("startup_portfolio_reconciliation_failed")
            return finish()

        try:
            clock = broker.get_market_clock()
            clock_checked_at = datetime.now(timezone.utc)
            if not self._fresh_clock(clock, clock_checked_at):
                reasons.append("market_clock_invalid_or_stale")
                trip("startup_market_clock_invalid")
            elif getattr(clock, "is_open", None) is True:
                market_open = True
            elif getattr(clock, "is_open", None) is False:
                market_open = False
                reasons.append("market_closed")
            else:
                reasons.append("market_clock_invalid_or_stale")
                trip("startup_market_clock_invalid")
        except Exception:
            reasons.append("market_clock_unavailable")
            trip("startup_market_clock_unavailable")
        return finish()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconcile Alpaca paper state after restart; never submit or cancel orders."
    )
    parser.add_argument("--database", default="data/trading_bot.sqlite3")
    parser.add_argument("--kill-switch", default="data/kill_switch.sqlite3")
    parser.add_argument("--risk-config", default="config/risk_limits.json")
    args = parser.parse_args()
    report = RecoveryManager(
        TradingDatabase(args.database), KillSwitch(args.kill_switch),
        risk_config_path=args.risk_config,
    ).run()
    print(json.dumps(report.as_dict(), indent=2))
    if not report.can_resume_order_evaluation:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

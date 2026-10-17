"""Phase 12 order manager with explicit, fail-closed paper submission gates.

The default path is an offline preview. Submission requires a separate
constructor flag, an owner-approved risk file, a healthy kill switch, fresh
broker state, an open market, and a unique client order ID. Unknown outcomes
are never retried automatically.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Any

from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import LimitOrderRequest

from app.broker.alpaca_client import AlpacaClient
from app.data.database import TradingDatabase
from app.portfolio.portfolio_manager import PortfolioManager, PortfolioSnapshot
from app.risk.config import load_paper_risk_limits
from app.risk.kill_switch import KillSwitch
from app.risk.position_sizing import size_buy
from app.risk.risk_manager import (
    RiskDecision, RiskLimits, RiskManager, RiskPortfolioSnapshot, RiskPosition,
    TradeCandidate,
)
from app.strategy.base import Signal, SignalAction


@dataclass(frozen=True)
class OrderIntent:
    """One stable decision ID; reuse the same ID when investigating a timeout."""

    client_order_id: str
    signal: Signal
    quantity: int
    estimated_price: float
    limit_price: float
    stop_price: float | None = None
    sector: str | None = None
    annualized_volatility: float | None = None

    @classmethod
    def for_signal(
        cls, signal: Signal, quantity: int, estimated_price: float,
        limit_price: float, *, stop_price: float | None = None,
        sector: str | None = None, annualized_volatility: float | None = None,
    ) -> OrderIntent:
        """Build an intent whose broker ID survives a restart of this signal."""
        return cls(
            client_order_id_for(signal), signal, quantity, estimated_price,
            limit_price, stop_price, sector, annualized_volatility,
        )


@dataclass(frozen=True)
class OrderDecision:
    approved: bool
    reasons: tuple[str, ...]
    request: LimitOrderRequest | None
    risk_decision: RiskDecision | None
    proposed_quantity: int


@dataclass(frozen=True)
class OrderOutcome:
    client_order_id: str
    status: str
    submitted: bool
    reasons: tuple[str, ...] = ()
    alpaca_order_id: str | None = None


def _value(raw: Any) -> str:
    return str(getattr(raw, "value", raw)).strip().lower()


def _aware(value: Any) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _same_decimal(left: Any, right: Any) -> bool:
    try:
        return Decimal(str(left)) == Decimal(str(right))
    except (InvalidOperation, ValueError, TypeError):
        return False


def client_order_id_for(signal: Signal) -> str:
    """One broker-visible ID per strategy, symbol, action and signal instant.

    The signal time must be the original decision time, normally the closed
    candle's timestamp. Regenerating a fresh timestamp creates a new decision.
    """
    if not isinstance(signal, Signal) or not _aware(signal.timestamp):
        raise ValueError("A timezone-aware strategy signal is required")
    key = [
        signal.strategy, signal.symbol.strip().upper(), signal.action.value,
        signal.timestamp.astimezone(timezone.utc).isoformat(timespec="microseconds"),
    ]
    digest = sha256(json.dumps(key, separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()
    return "tb1-" + digest[:40]


class OrderManager:
    """Single entry point for controlled Alpaca paper order submission.

    The caller must run only one active bot instance per paper account. Phase
    13 will add startup recovery and service ownership. This class never
    automatically resubmits a reserved or uncertain client order ID.
    """

    def __init__(
        self, broker: AlpacaClient, database: TradingDatabase,
        kill_switch: KillSwitch, *,
        risk_config_path: str | Path = "config/risk_limits.json",
        enable_paper_submission: bool = False,
    ) -> None:
        self.broker = broker
        self.database = database
        self.kill_switch = kill_switch
        self.risk_config_path = Path(risk_config_path)
        self.enable_paper_submission = enable_paper_submission

    @staticmethod
    def _risk_snapshot(portfolio: PortfolioSnapshot, peak_equity: float | None) -> RiskPortfolioSnapshot:
        """Convert only fully accounted whole-share long equity state."""
        positions: list[RiskPosition] = []
        complete = portfolio.accounting_consistent and portfolio.day_start_equity is not None
        for holding in portfolio.positions:
            if (
                holding.asset_class != "us_equity" or holding.side != "long"
                or holding.quantity != holding.quantity.to_integral_value()
            ):
                complete = False
                continue
            positions.append(RiskPosition(holding.symbol, int(holding.quantity), float(holding.market_price)))
        if peak_equity is None or not isfinite(peak_equity):
            complete = False
        equity = float(portfolio.equity)
        day_start = float(portfolio.day_start_equity) if portfolio.day_start_equity is not None else 0.0
        return RiskPortfolioSnapshot(
            as_of=portfolio.as_of, cash=float(portfolio.cash), equity=equity,
            day_start_equity=day_start,
            peak_equity=max(peak_equity or 0.0, equity, day_start),
            positions=tuple(positions), complete=bool(complete),
        )

    def preview(
        self, intent: OrderIntent, portfolio: PortfolioSnapshot,
        market_clock: Any, *, limits: RiskLimits | None = None,
        peak_equity: float | None = None, evaluated_at: datetime | None = None,
    ) -> OrderDecision:
        """Construct a DAY limit-order proposal without calling Alpaca."""
        now = evaluated_at or datetime.now(timezone.utc)
        reasons: list[str] = []
        client_id = intent.client_order_id
        if not isinstance(client_id, str) or not client_id or len(client_id) > 48 or not all(
            char.isascii() and (char.isalnum() or char in "-_") for char in client_id
        ):
            reasons.append("invalid_client_order_id")
        signal = intent.signal
        if not isinstance(signal, Signal) or signal.action not in {SignalAction.BUY, SignalAction.SELL}:
            reasons.append("not_actionable")
        elif client_id != client_order_id_for(signal):
            reasons.append("client_order_id_not_signal_stable")
        if type(intent.quantity) is not int or intent.quantity < 1:
            reasons.append("invalid_quantity")
        if isinstance(intent.estimated_price, bool) or not isinstance(intent.estimated_price, (int, float)) or not isfinite(intent.estimated_price) or intent.estimated_price <= 0:
            reasons.append("invalid_estimated_price")
        if isinstance(intent.limit_price, bool) or not isinstance(intent.limit_price, (int, float)) or not isfinite(intent.limit_price) or intent.limit_price <= 0:
            reasons.append("invalid_limit_price")
        if reasons:
            return OrderDecision(False, tuple(reasons), None, None, 0)
        if signal.action == SignalAction.BUY and intent.limit_price > intent.estimated_price:
            reasons.append("limit_above_risk_estimate")
        if not _aware(now):
            reasons.append("invalid_evaluation_time")
        clock_time = getattr(market_clock, "timestamp", None)
        if getattr(market_clock, "is_open", None) is not True or not _aware(clock_time):
            reasons.append("market_closed_or_clock_invalid")
        elif _aware(now) and not 0 <= (now - clock_time).total_seconds() <= 30:
            reasons.append("stale_market_clock")
        if portfolio.open_orders:
            reasons.append("existing_open_orders")
        if not portfolio.accounting_consistent:
            reasons.append("accounting_gap")
        risk_snapshot = self._risk_snapshot(portfolio, peak_equity)
        policy = limits or RiskLimits()
        candidate = TradeCandidate(
            signal, intent.quantity, intent.estimated_price, intent.stop_price,
            intent.sector, intent.annualized_volatility,
        )
        risk = RiskManager(limits=policy).evaluate(candidate, risk_snapshot, evaluated_at=now)
        if not risk.approved:
            reasons.extend(issue.code for issue in risk.issues)
        if signal.action == SignalAction.BUY:
            sizing = size_buy(
                signal, risk_snapshot, estimated_price=intent.estimated_price,
                stop_price=intent.stop_price, limits=policy, evaluated_at=now,
                sector=intent.sector, annualized_volatility=intent.annualized_volatility,
            )
            if intent.quantity > sizing.quantity:
                reasons.append("quantity_exceeds_sizing_limit")
            if intent.quantity * intent.estimated_price > float(portfolio.buying_power):
                reasons.append("insufficient_buying_power")
        if reasons:
            return OrderDecision(False, tuple(dict.fromkeys(reasons)), None, risk, intent.quantity)
        request = LimitOrderRequest(
            symbol=signal.symbol.strip().upper(), qty=intent.quantity,
            side=OrderSide.BUY if signal.action == SignalAction.BUY else OrderSide.SELL,
            time_in_force=TimeInForce.DAY, limit_price=intent.limit_price,
            client_order_id=client_id, extended_hours=False,
        )
        return OrderDecision(True, (), request, risk, intent.quantity)

    def _match_broker_order(self, intent: OrderIntent, order: Any) -> bool:
        signal = intent.signal
        return (
            str(getattr(order, "client_order_id", "")) == intent.client_order_id
            and str(getattr(order, "symbol", "")).strip().upper() == signal.symbol.strip().upper()
            and _value(getattr(order, "side", None)) == signal.action.value.lower()
            and _same_decimal(getattr(order, "qty", None), intent.quantity)
            and _value(getattr(order, "type", None) or getattr(order, "order_type", None)) == "limit"
            and _value(getattr(order, "time_in_force", None)) == "day"
            and _same_decimal(getattr(order, "limit_price", None), intent.limit_price)
            and getattr(order, "extended_hours", None) is False
        )

    def _record_broker_order(self, intent: OrderIntent, order: Any) -> OrderOutcome:
        if not self._match_broker_order(intent, order):
            self.kill_switch.trip("duplicate_order_identity_conflict")
            return OrderOutcome(intent.client_order_id, "identity_conflict", False, ("broker_order_mismatch",))
        status = _value(getattr(order, "status", None))
        order_id = str(getattr(order, "id", ""))
        if not status or status == "none" or not order_id or order_id == "None":
            self.kill_switch.trip("invalid_broker_order_response")
            return OrderOutcome(intent.client_order_id, "unknown", False, ("invalid_broker_order_response",))
        self.database.record_order_update(
            client_order_id=intent.client_order_id, timestamp=datetime.now(timezone.utc),
            status=status, alpaca_order_id=order_id,
            filled_quantity=None if getattr(order, "filled_qty", None) is None else str(order.filled_qty),
            filled_average_price=None if getattr(order, "filled_avg_price", None) is None else str(order.filled_avg_price),
        )
        return OrderOutcome(intent.client_order_id, status, False, (), order_id)

    def submit(self, intent: OrderIntent) -> OrderOutcome:
        """Submit at most once, only when every paper safety gate passes.

        This method is never called by a CLI or scheduler in Phase 12. An
        ambiguous broker response remains unknown and requires reconciliation;
        it is not safe to retry automatically.
        """
        if not isinstance(intent, OrderIntent):
            return OrderOutcome("", "blocked", False, ("invalid_order_intent",))
        client_id = intent.client_order_id if isinstance(intent.client_order_id, str) else ""
        if not self.enable_paper_submission:
            return OrderOutcome(client_id, "disabled", False, ("paper_submission_disabled",))
        if (
            not client_id or len(client_id) > 48
            or not all(char.isascii() and (char.isalnum() or char in "-_") for char in client_id)
            or not isinstance(intent.signal, Signal)
            or intent.signal.action not in {SignalAction.BUY, SignalAction.SELL}
            or client_id != client_order_id_for(intent.signal)
            or type(intent.quantity) is not int or intent.quantity < 1
            or not isinstance(intent.limit_price, (int, float))
            or isinstance(intent.limit_price, bool) or not isfinite(intent.limit_price)
            or intent.limit_price <= 0
            or not isinstance(intent.estimated_price, (int, float))
            or isinstance(intent.estimated_price, bool) or not isfinite(intent.estimated_price)
            or intent.estimated_price <= 0
        ):
            return OrderOutcome(client_id, "blocked", False, ("invalid_order_intent",))
        try:
            limits = load_paper_risk_limits(self.risk_config_path)
        except (OSError, ValueError) as exc:
            return OrderOutcome(client_id, "blocked", False, (f"risk_config_unapproved: {exc}",))
        if not self.kill_switch.status().allow_new_orders:
            return OrderOutcome(client_id, "blocked", False, ("kill_switch_denied",))
        try:
            existing = self.database.get_order_record(client_id)
        except Exception:
            self.kill_switch.trip("order_database_unavailable")
            return OrderOutcome(client_id, "blocked", False, ("order_database_unavailable",))
        if existing is not None:
            if (
                existing["symbol"] != intent.signal.symbol.strip().upper()
                or existing["side"] != intent.signal.action.value.lower()
                or existing["quantity"] != intent.quantity
                or existing["order_type"] != "limit"
                or not _same_decimal(existing["limit_price"], intent.limit_price)
            ):
                self.kill_switch.trip("duplicate_order_identity_conflict")
                return OrderOutcome(client_id, "identity_conflict", False, ("client_order_id_reused",))
            return OrderOutcome(client_id, existing["status"], False, ("already_recorded_no_resubmit",), existing["alpaca_order_id"])
        try:
            broker_existing = self.broker.get_order_by_client_id(client_id)
            if broker_existing is not None:
                created, _ = self.database.reserve_order(
                    client_order_id=client_id, timestamp=datetime.now(timezone.utc),
                    symbol=intent.signal.symbol.strip().upper(), side=intent.signal.action.value.lower(),
                    quantity=intent.quantity, limit_price=str(intent.limit_price),
                )
                if not created:
                    return OrderOutcome(client_id, "duplicate", False, ("already_reserved",))
                return self._record_broker_order(intent, broker_existing)
            portfolio = PortfolioManager(self.broker, self.database).reconcile().snapshot
            clock = self.broker.get_market_clock()
            asset = self.broker.get_asset(intent.signal.symbol.strip().upper())
            account = self.broker.get_account()
            self.kill_switch.record_api_success()
        except Exception:
            self.kill_switch.record_api_failure()
            return OrderOutcome(client_id, "blocked", False, ("broker_preflight_failed",))
        if (
            _value(getattr(asset, "asset_class", None)) != "us_equity"
            or str(getattr(asset, "symbol", "")).strip().upper() != intent.signal.symbol.strip().upper()
            or getattr(asset, "tradable", None) is not True
            or _value(getattr(asset, "status", None)) != "active"
        ):
            return OrderOutcome(client_id, "blocked", False, ("asset_not_tradable_us_equity",))
        if (
            _value(getattr(account, "status", None)) != "active"
            or getattr(account, "trading_blocked", None) is not False
            or getattr(account, "account_blocked", None) is not False
            or str(getattr(account, "id", "")).lower() != portfolio.account_id
        ):
            return OrderOutcome(client_id, "blocked", False, ("account_not_active_or_changed",))
        try:
            peak = self.database.get_peak_portfolio_equity()
        except Exception:
            self.kill_switch.trip("order_database_unavailable")
            return OrderOutcome(client_id, "blocked", False, ("order_database_unavailable",))
        risk_snapshot = self._risk_snapshot(portfolio, peak)
        if not self.kill_switch.observe_portfolio(risk_snapshot, limits).allow_new_orders:
            return OrderOutcome(client_id, "blocked", False, ("kill_switch_denied_account_state",))
        decision = self.preview(intent, portfolio, clock, limits=limits, peak_equity=peak)
        if not decision.approved:
            return OrderOutcome(client_id, "blocked", False, decision.reasons)
        try:
            created, _ = self.database.reserve_order(
                client_order_id=client_id, timestamp=datetime.now(timezone.utc),
                symbol=intent.signal.symbol.strip().upper(), side=intent.signal.action.value.lower(),
                quantity=intent.quantity, limit_price=str(intent.limit_price),
            )
        except Exception:
            self.kill_switch.trip("order_database_unavailable")
            return OrderOutcome(client_id, "blocked", False, ("order_database_unavailable",))
        if not created:
            return OrderOutcome(client_id, "duplicate", False, ("already_reserved",))
        if not self.kill_switch.status().allow_new_orders:
            self.database.record_order_update(client_order_id=client_id, timestamp=datetime.now(timezone.utc), status="blocked")
            return OrderOutcome(client_id, "blocked", False, ("kill_switch_denied",))
        try:
            final_clock = self.broker.get_market_clock()
            final_time = getattr(final_clock, "timestamp", None)
            now = datetime.now(timezone.utc)
            if (
                getattr(final_clock, "is_open", None) is not True
                or not _aware(final_time)
                or not 0 <= (now - final_time).total_seconds() <= 30
            ):
                self.database.record_order_update(
                    client_order_id=client_id, timestamp=now, status="blocked"
                )
                return OrderOutcome(client_id, "blocked", False, ("market_closed_or_clock_invalid",))
        except Exception:
            self.kill_switch.record_api_failure()
            self.database.record_order_update(
                client_order_id=client_id, timestamp=datetime.now(timezone.utc), status="blocked"
            )
            return OrderOutcome(client_id, "blocked", False, ("final_market_clock_failed",))
        try:
            broker_order = self.broker.submit_order(decision.request)
        except Exception:
            # A timeout can occur after Alpaca accepts the order. Query once,
            # then stop. Never retry a submission with this or a new ID.
            try:
                broker_order = self.broker.get_order_by_client_id(client_id)
            except Exception:
                broker_order = None
            if broker_order is None:
                self.database.record_order_update(client_order_id=client_id, timestamp=datetime.now(timezone.utc), status="unknown")
                self.kill_switch.trip("order_submission_uncertain")
                return OrderOutcome(client_id, "unknown", False, ("manual_broker_reconciliation_required",))
        try:
            outcome = self._record_broker_order(intent, broker_order)
        except Exception:
            self.kill_switch.trip("order_persistence_failure")
            return OrderOutcome(client_id, "unknown", True, ("manual_broker_reconciliation_required",))
        return OrderOutcome(
            outcome.client_order_id, outcome.status,
            outcome.alpaca_order_id is not None, outcome.reasons,
            outcome.alpaca_order_id,
        )

    def refresh_status(self, client_order_id: str) -> OrderOutcome:
        """Reconcile one known order by client ID without placing another."""
        row = self.database.get_order_record(client_order_id)
        if row is None:
            return OrderOutcome(client_order_id, "unknown", False, ("no_local_order_record",))
        try:
            order = self.broker.get_order_by_client_id(client_order_id)
        except Exception:
            self.kill_switch.record_api_failure()
            return OrderOutcome(client_order_id, "unknown", False, ("broker_lookup_failed",))
        if order is None:
            return OrderOutcome(client_order_id, "unknown", False, ("broker_order_not_found_do_not_retry",))
        self.kill_switch.record_api_success()
        if row["side"] not in {"buy", "sell"}:
            self.kill_switch.trip("invalid_local_order_record")
            return OrderOutcome(client_order_id, "unknown", False, ("invalid_local_order_record",))
        # Legacy rows without a stored limit cannot pass identity validation.
        # Reserved/unknown rows may not yet have a broker order ID; capture it
        # only after the full broker order identity matches.
        if not (
            str(getattr(order, "client_order_id", "")) == client_order_id
            and str(getattr(order, "symbol", "")).strip().upper() == row["symbol"]
            and _value(getattr(order, "side", None)) == row["side"]
            and _same_decimal(getattr(order, "qty", None), row["quantity"])
            and _value(getattr(order, "type", None) or getattr(order, "order_type", None)) == "limit"
            and _value(getattr(order, "time_in_force", None)) == "day"
            and getattr(order, "extended_hours", None) is False
            and _same_decimal(getattr(order, "limit_price", None), row["limit_price"])
            and (row["alpaca_order_id"] is None or str(getattr(order, "id", "")) == row["alpaca_order_id"])
        ):
            self.kill_switch.trip("order_reconciliation_identity_conflict")
            return OrderOutcome(client_order_id, "identity_conflict", False, ("broker_order_mismatch",))
        status = _value(getattr(order, "status", None))
        if not status or status == "none":
            self.kill_switch.trip("invalid_broker_order_response")
            return OrderOutcome(client_order_id, "unknown", False, ("invalid_broker_order_response",))
        try:
            self.database.record_order_update(
                client_order_id=client_order_id, timestamp=datetime.now(timezone.utc),
                status=status, alpaca_order_id=str(order.id),
                filled_quantity=None if getattr(order, "filled_qty", None) is None else str(order.filled_qty),
                filled_average_price=None if getattr(order, "filled_avg_price", None) is None else str(order.filled_avg_price),
            )
        except Exception:
            self.kill_switch.trip("order_persistence_failure")
            return OrderOutcome(client_order_id, "unknown", False, ("order_persistence_failure",))
        return OrderOutcome(client_order_id, status, False, (), str(order.id))

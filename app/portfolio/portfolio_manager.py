"""Capture and reconcile paper-account portfolio state without placing orders.

Alpaca is authoritative for account balances, open positions, and open orders.
Snapshots are observations, not an atomic broker transaction. Realized P&L is
unknown until a complete fill/activity ledger is implemented in a later phase.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from app.broker.alpaca_client import AlpacaClient
from app.data.database import TradingDatabase


class PortfolioValidationError(ValueError):
    """Broker data is missing, inconsistent, or cannot be safely interpreted."""


def _decimal(value: Any, name: str, *, required: bool = True) -> Decimal | None:
    if value is None and not required:
        return None
    if value is None or isinstance(value, bool):
        raise PortfolioValidationError(f"{name} is missing or invalid")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise PortfolioValidationError(f"{name} must be a finite number") from None
    if not result.is_finite():
        raise PortfolioValidationError(f"{name} must be a finite number")
    return result


def _label(value: Any, name: str) -> str:
    if value is None:
        raise PortfolioValidationError(f"{name} is missing")
    result = str(getattr(value, "value", value)).strip().lower()
    if not result:
        raise PortfolioValidationError(f"{name} is empty")
    return result


@dataclass(frozen=True)
class PortfolioPosition:
    symbol: str
    side: str
    quantity: Decimal
    average_entry_price: Decimal
    market_price: Decimal
    market_value: Decimal
    unrealized_pl: Decimal | None
    asset_class: str | None = None

    def as_record(self) -> dict[str, str | None]:
        return {
            "symbol": self.symbol, "side": self.side,
            "quantity": str(self.quantity), "average_entry_price": str(self.average_entry_price),
            "market_price": str(self.market_price), "market_value": str(self.market_value),
            "unrealized_pl": None if self.unrealized_pl is None else str(self.unrealized_pl),
            "asset_class": self.asset_class,
        }


@dataclass(frozen=True)
class OpenOrder:
    order_id: str
    client_order_id: str | None
    symbol: str
    side: str
    status: str
    quantity: Decimal | None
    notional: Decimal | None
    filled_quantity: Decimal | None

    def as_record(self) -> dict[str, str | None]:
        return {
            "order_id": self.order_id, "client_order_id": self.client_order_id,
            "symbol": self.symbol, "side": self.side, "status": self.status,
            "quantity": None if self.quantity is None else str(self.quantity),
            "notional": None if self.notional is None else str(self.notional),
            "filled_quantity": None if self.filled_quantity is None else str(self.filled_quantity),
        }


@dataclass(frozen=True)
class PortfolioSnapshot:
    as_of: datetime
    account_id: str
    cash: Decimal
    buying_power: Decimal
    equity: Decimal
    day_start_equity: Decimal | None
    positions: tuple[PortfolioPosition, ...]
    open_orders: tuple[OpenOrder, ...]
    gross_exposure: Decimal
    net_exposure: Decimal
    valuation_gap: Decimal
    accounting_consistent: bool
    unrealized_pl: Decimal | None
    realized_pl: None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "source": "alpaca_paper", "as_of": self.as_of.isoformat(),
            "account_id": self.account_id,
            "cash": str(self.cash), "buying_power": str(self.buying_power),
            "equity": str(self.equity),
            "day_start_equity": None if self.day_start_equity is None else str(self.day_start_equity),
            "gross_exposure": str(self.gross_exposure), "net_exposure": str(self.net_exposure),
            "valuation_gap": str(self.valuation_gap),
            "accounting_consistent": self.accounting_consistent,
            "unrealized_pl": None if self.unrealized_pl is None else str(self.unrealized_pl),
            "realized_pl": None,
            "positions": [position.as_record() for position in self.positions],
            "open_orders": [order.as_record() for order in self.open_orders],
        }


@dataclass(frozen=True)
class ReconciliationResult:
    snapshot: PortfolioSnapshot
    previous_as_of: str | None
    changes: tuple[str, ...]


class PortfolioManager:
    """Periodically call ``reconcile`` from an eventual service or manually.

    The broker must expose get_account/get_positions/get_open_orders. A failed
    fetch or invalid response leaves the last persisted snapshot untouched.
    """

    def __init__(self, broker: AlpacaClient, database: TradingDatabase) -> None:
        self.broker = broker
        self.database = database

    def reconcile(self) -> ReconciliationResult:
        positions_raw = self.broker.get_positions()
        orders_raw = self.broker.get_open_orders()
        account = self.broker.get_account()
        if positions_raw is None or orders_raw is None or account is None:
            raise PortfolioValidationError("Alpaca account, positions, and open orders must all be available")
        snapshot = self._normalize(account, positions_raw, orders_raw)
        previous = self.database.record_portfolio_state(snapshot.as_record())
        return ReconciliationResult(
            snapshot=snapshot,
            previous_as_of=None if previous is None else previous.get("as_of"),
            changes=self._compare(previous, snapshot.as_record()),
        )

    @staticmethod
    def _normalize(account: Any, positions_raw: Any, orders_raw: Any) -> PortfolioSnapshot:
        account_id = _label(getattr(account, "id", None), "account.id")
        currency = getattr(account, "currency", None)
        if currency is not None and _label(currency, "account.currency") != "usd":
            raise PortfolioValidationError("Only USD-denominated Alpaca accounts are supported")
        cash = _decimal(getattr(account, "cash", None), "account.cash")
        buying_power = _decimal(getattr(account, "buying_power", None), "account.buying_power")
        equity = _decimal(getattr(account, "equity", None), "account.equity")
        day_start = _decimal(getattr(account, "last_equity", None), "account.last_equity", required=False)
        if equity <= 0 or buying_power < 0 or (day_start is not None and day_start <= 0):
            raise PortfolioValidationError("account equity must be positive and buying power nonnegative")
        if not isinstance(positions_raw, (list, tuple)) or not isinstance(orders_raw, (list, tuple)):
            raise PortfolioValidationError("Alpaca positions and open orders must be sequences")

        positions: list[PortfolioPosition] = []
        symbols: set[str] = set()
        for raw in positions_raw:
            symbol = _label(getattr(raw, "symbol", None), "position.symbol").upper()
            side = _label(getattr(raw, "side", None), f"{symbol}.side")
            quantity = _decimal(getattr(raw, "qty", None), f"{symbol}.qty")
            entry = _decimal(getattr(raw, "avg_entry_price", None), f"{symbol}.avg_entry_price")
            price = _decimal(getattr(raw, "current_price", None), f"{symbol}.current_price")
            market_value = _decimal(getattr(raw, "market_value", None), f"{symbol}.market_value")
            unrealized = _decimal(getattr(raw, "unrealized_pl", None), f"{symbol}.unrealized_pl", required=False)
            if symbol in symbols or side not in {"long", "short"} or quantity == 0 or entry <= 0 or price <= 0 or market_value == 0:
                raise PortfolioValidationError(f"{symbol}: duplicate or invalid position")
            # Broker quantity/value sign conventions can differ across assets;
            # the explicit side determines our canonical signed market value.
            quantity = abs(quantity)
            market_value = abs(market_value) * (1 if side == "long" else -1)
            symbols.add(symbol)
            raw_asset_class = getattr(raw, "asset_class", None)
            asset_class = None if raw_asset_class is None else _label(raw_asset_class, f"{symbol}.asset_class")
            positions.append(PortfolioPosition(symbol, side, quantity, entry, price, market_value, unrealized, asset_class))

        orders: list[OpenOrder] = []
        order_ids: set[str] = set()
        for raw in orders_raw:
            order_id = _label(getattr(raw, "id", None), "order.id")
            symbol = _label(getattr(raw, "symbol", None), "order.symbol").upper()
            side = _label(getattr(raw, "side", None), f"order {order_id}.side")
            status = _label(getattr(raw, "status", None), f"order {order_id}.status")
            quantity = _decimal(getattr(raw, "qty", None), f"order {order_id}.qty", required=False)
            notional = _decimal(getattr(raw, "notional", None), f"order {order_id}.notional", required=False)
            filled = _decimal(getattr(raw, "filled_qty", None), f"order {order_id}.filled_qty", required=False)
            if order_id in order_ids or side not in {"buy", "sell"} or (quantity is None and notional is None):
                raise PortfolioValidationError(f"order {order_id}: duplicate or invalid open order")
            if (quantity is not None and quantity <= 0) or (notional is not None and notional <= 0) or (filled is not None and filled < 0):
                raise PortfolioValidationError(f"order {order_id}: invalid quantity or notional")
            order_ids.add(order_id)
            client_id = getattr(raw, "client_order_id", None)
            orders.append(OpenOrder(order_id, None if client_id is None else str(client_id), symbol, side, status, quantity, notional, filled))

        positions.sort(key=lambda position: position.symbol)
        orders.sort(key=lambda order: order.order_id)
        gross_value = sum((abs(position.market_value) for position in positions), Decimal(0))
        net_value = sum((position.market_value for position in positions), Decimal(0))
        valuation_gap = equity - (cash + net_value)
        accounting_consistent = abs(valuation_gap) <= max(Decimal("0.01"), equity * Decimal("0.001"))
        if positions and any(position.unrealized_pl is None for position in positions):
            unrealized_total = None
        else:
            unrealized_total = sum((position.unrealized_pl for position in positions), Decimal(0))
        return PortfolioSnapshot(
            as_of=datetime.now(timezone.utc), account_id=account_id,
            cash=cash, buying_power=buying_power,
            equity=equity, day_start_equity=day_start,
            positions=tuple(positions), open_orders=tuple(orders),
            gross_exposure=gross_value / equity, net_exposure=net_value / equity,
            valuation_gap=valuation_gap, accounting_consistent=accounting_consistent,
            unrealized_pl=unrealized_total,
        )

    @staticmethod
    def _compare(previous: Mapping[str, Any] | None, current: Mapping[str, Any]) -> tuple[str, ...]:
        if previous is None:
            return ()
        changes: list[str] = []
        for field in ("cash", "buying_power", "equity"):
            if previous.get(field) != current[field]:
                changes.append(f"{field}: {previous.get(field)} -> {current[field]}")
        prior_positions = {row["symbol"]: row for row in previous.get("positions", [])}
        current_positions = {row["symbol"]: row for row in current["positions"]}
        for symbol in sorted(prior_positions.keys() | current_positions.keys()):
            old, new = prior_positions.get(symbol), current_positions.get(symbol)
            if old is None or new is None or (old.get("side"), old.get("quantity")) != (new.get("side"), new.get("quantity")):
                changes.append(f"position {symbol}: {None if old is None else old.get('quantity')} -> {None if new is None else new.get('quantity')}")
        prior_orders = {row["order_id"]: row for row in previous.get("open_orders", [])}
        current_orders = {row["order_id"]: row for row in current["open_orders"]}
        for order_id in sorted(prior_orders.keys() | current_orders.keys()):
            old, new = prior_orders.get(order_id), current_orders.get(order_id)
            if old is None or new is None or old != new:
                changes.append(
                    f"open order {order_id}: "
                    f"{None if old is None else (old.get('status'), old.get('filled_quantity'))} -> "
                    f"{None if new is None else (new.get('status'), new.get('filled_quantity'))}"
                )
        return tuple(changes)


def main() -> None:
    parser = argparse.ArgumentParser(description="Read and reconcile an Alpaca paper portfolio; never place orders.")
    parser.add_argument("--database", default="data/trading_bot.sqlite3", help="Local SQLite path")
    args = parser.parse_args()
    result = PortfolioManager(AlpacaClient(), TradingDatabase(args.database)).reconcile()
    print(json.dumps({
        "as_of": result.snapshot.as_of.isoformat(),
        "cash": str(result.snapshot.cash), "buying_power": str(result.snapshot.buying_power),
        "equity": str(result.snapshot.equity), "gross_exposure": str(result.snapshot.gross_exposure),
        "valuation_gap": str(result.snapshot.valuation_gap),
        "accounting_consistent": result.snapshot.accounting_consistent,
        "unrealized_pl": None if result.snapshot.unrealized_pl is None else str(result.snapshot.unrealized_pl),
        "realized_pl": None, "position_count": len(result.snapshot.positions),
        "open_order_count": len(result.snapshot.open_orders), "changes": result.changes,
    }, indent=2))


if __name__ == "__main__":
    main()

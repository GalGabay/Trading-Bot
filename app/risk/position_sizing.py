"""Whole-share sizing for a proposed long BUY; no order submission."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import floor, isfinite

from app.risk.risk_manager import (
    RiskDecision, RiskLimits, RiskManager, RiskPortfolioSnapshot, TradeCandidate,
)
from app.strategy.base import Signal, SignalAction


@dataclass(frozen=True)
class SizingDecision:
    """A quantity is only a proposal and must be rechecked before submission."""

    quantity: int
    allowed_risk: float | None
    stop_distance: float | None
    binding_cap: str | None
    risk_decision: RiskDecision


def size_buy(
    signal: Signal,
    snapshot: RiskPortfolioSnapshot | None,
    *,
    estimated_price: float,
    stop_price: float,
    limits: RiskLimits | None = None,
    evaluated_at: datetime | None = None,
    sector: str | None = None,
    annualized_volatility: float | None = None,
) -> SizingDecision:
    """Size by stop risk, single position, gross exposure, and cash.

    The smallest cap wins. The risk gate validates a one-share BUY first, then
    validates the final size. Prices are conservative execution estimates;
    stop fills and loss amounts are never guaranteed.
    """
    manager = RiskManager(limits=limits)

    def evaluate(quantity: int) -> RiskDecision:
        return manager.evaluate(
            TradeCandidate(signal, quantity, estimated_price, stop_price, sector, annualized_volatility),
            snapshot, evaluated_at=evaluated_at,
        )

    first = evaluate(1)
    if not first.approved or snapshot is None or signal.action != SignalAction.BUY:
        return SizingDecision(0, None, None, None, first)

    stop_distance = estimated_price - stop_price
    allowed_risk = snapshot.equity * manager.limits.max_risk_per_trade
    exposure_used = sum(position.quantity * position.market_price for position in snapshot.positions)
    caps = {
        "stop_risk": allowed_risk / stop_distance,
        "single_position": snapshot.equity * manager.limits.max_single_position / estimated_price,
        "portfolio_exposure": (snapshot.equity * manager.limits.max_portfolio_exposure - exposure_used) / estimated_price,
        "available_cash": snapshot.cash / estimated_price,
    }
    if manager.limits.max_sector_exposure is not None:
        sector_used = sum(
            position.quantity * position.market_price for position in snapshot.positions
            if position.sector and position.sector.strip().upper() == sector.strip().upper()
        )
        caps["sector_exposure"] = (
            snapshot.equity * manager.limits.max_sector_exposure - sector_used
        ) / estimated_price
    if any(not isfinite(cap) for cap in caps.values()):
        return SizingDecision(0, allowed_risk, stop_distance, None, first)
    binding_cap = min(caps, key=caps.get)
    high = floor(min(caps.values()))
    # The one-share gate already passed, so at least one share must be viable.
    # Binary search handles floating-point boundary rounding without an
    # unbounded decrement loop.
    low = 1
    while low < high:
        middle = (low + high + 1) // 2
        if evaluate(middle).approved:
            low = middle
        else:
            high = middle - 1
    final = evaluate(low)
    return SizingDecision(low if final.approved else 0, allowed_risk, stop_distance, binding_cap, final)

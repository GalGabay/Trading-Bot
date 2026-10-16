"""Fail-closed, long-only risk gate for strategy trade candidates.

The manager only evaluates supplied state. It does not fetch account data,
size trades, submit orders, or mutate a portfolio. A future paper-order
workflow must recheck the policy using fresh account state and a conservative
estimated fill cost immediately before submission.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from numbers import Real

from app.strategy.base import Signal, SignalAction


def _finite(value: float) -> bool:
    if isinstance(value, bool) or not isinstance(value, Real):
        return False
    return isfinite(value)


def _aware(value: datetime) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


@dataclass(frozen=True)
class RiskLimits:
    """Provisional research defaults, not approved paper-trading settings.

    Fractions use 1.0 for 100%. Sector and volatility gates are disabled until
    trustworthy metadata is available; setting either limit requires it.
    """

    max_portfolio_exposure: float = 0.70
    max_single_position: float = 0.10
    max_risk_per_trade: float = 0.01
    max_daily_loss: float = 0.03
    max_drawdown: float = 0.10
    max_positions: int = 7
    max_snapshot_age_seconds: int = 300
    max_signal_age_seconds: int = 300
    max_sector_exposure: float | None = None
    max_annualized_volatility: float | None = None

    def __post_init__(self) -> None:
        for name in (
            "max_portfolio_exposure", "max_single_position", "max_risk_per_trade",
            "max_daily_loss", "max_drawdown",
        ):
            value = getattr(self, name)
            if not _finite(value) or not 0 < value <= 1:
                raise ValueError(f"{name} must be a finite fraction greater than 0 and at most 1")
        if self.max_single_position > self.max_portfolio_exposure:
            raise ValueError("max_single_position cannot exceed max_portfolio_exposure")
        if type(self.max_positions) is not int or self.max_positions < 1:
            raise ValueError("max_positions must be a positive integer")
        if type(self.max_snapshot_age_seconds) is not int or self.max_snapshot_age_seconds < 1:
            raise ValueError("max_snapshot_age_seconds must be a positive integer")
        if type(self.max_signal_age_seconds) is not int or self.max_signal_age_seconds < 1:
            raise ValueError("max_signal_age_seconds must be a positive integer")
        if self.max_sector_exposure is not None and (
            not _finite(self.max_sector_exposure) or not 0 < self.max_sector_exposure <= 1
        ):
            raise ValueError("max_sector_exposure must be a finite fraction greater than 0 and at most 1")
        if self.max_annualized_volatility is not None and (
            not _finite(self.max_annualized_volatility) or self.max_annualized_volatility <= 0
        ):
            raise ValueError("max_annualized_volatility must be finite and positive")


@dataclass(frozen=True)
class RiskPosition:
    """One current long position, valued using a recent market price."""

    symbol: str
    quantity: int
    market_price: float
    sector: str | None = None


@dataclass(frozen=True)
class RiskPortfolioSnapshot:
    """Complete account state captured at one timezone-aware instant.

    ``complete`` must be set explicitly by the future portfolio adapter after
    reconciling all cash and positions. The initial gate supports long-only
    holdings; unknown or inconsistent account state is rejected.
    """

    as_of: datetime
    cash: float
    equity: float
    day_start_equity: float
    peak_equity: float
    positions: tuple[RiskPosition, ...] = ()
    complete: bool = False


@dataclass(frozen=True)
class TradeCandidate:
    """A proposed whole-share trade; approval is never an order instruction.

    ``estimated_price`` must conservatively include likely adverse execution
    costs. A BUY requires a stop below this price to measure initial risk.
    """

    signal: Signal
    quantity: int
    estimated_price: float
    stop_price: float | None = None
    sector: str | None = None
    annualized_volatility: float | None = None


@dataclass(frozen=True)
class RiskIssue:
    code: str
    message: str


@dataclass(frozen=True)
class RiskDecision:
    """Structured, auditable decision that cannot submit a trade by itself."""

    approved: bool
    policy_version: str
    limits: RiskLimits
    signal: Signal
    evaluated_at: datetime
    snapshot_as_of: datetime | None
    issues: tuple[RiskIssue, ...]
    proposed_notional: float | None = None
    projected_exposure_fraction: float | None = None
    estimated_risk_fraction: float | None = None


class RiskManager:
    """Check a proposed BUY or risk-reducing SELL against explicit limits."""

    policy_version = "risk_v1"

    def __init__(self, *, limits: RiskLimits | None = None) -> None:
        self.limits = limits or RiskLimits()

    def evaluate(
        self, candidate: TradeCandidate, snapshot: RiskPortfolioSnapshot | None,
        *, evaluated_at: datetime | None = None,
    ) -> RiskDecision:
        """Return limit failures using the explicit decision time when available.

        The default decision time is the signal time for deterministic research.
        A future paper workflow must pass its actual evaluation time.
        """
        signal = candidate.signal
        decision_time = evaluated_at if evaluated_at is not None else signal.timestamp
        issues: list[RiskIssue] = []

        def reject(code: str, message: str) -> None:
            issues.append(RiskIssue(code, message))

        def decision(
            *, proposed_notional: float | None = None,
            projected_exposure_fraction: float | None = None,
            estimated_risk_fraction: float | None = None,
        ) -> RiskDecision:
            return RiskDecision(
                approved=not issues, policy_version=self.policy_version,
                limits=self.limits, signal=signal, evaluated_at=decision_time,
                snapshot_as_of=snapshot.as_of if snapshot is not None else None,
                issues=tuple(issues), proposed_notional=proposed_notional,
                projected_exposure_fraction=projected_exposure_fraction,
                estimated_risk_fraction=estimated_risk_fraction,
            )

        if not _aware(decision_time):
            reject("invalid_evaluation_time", "Risk evaluation time must include a timezone offset.")
            return decision()
        signal_age = (decision_time - signal.timestamp).total_seconds()
        if signal_age < 0 or signal_age > self.limits.max_signal_age_seconds:
            reject("stale_signal", "Signal must precede the risk evaluation and be recent.")
            return decision()
        if signal.action not in {SignalAction.BUY, SignalAction.SELL}:
            reject("not_actionable", "Only BUY and SELL signals can become trade candidates.")
            return decision()
        if type(candidate.quantity) is not int or candidate.quantity < 1:
            reject("invalid_quantity", "Trade quantity must be a positive whole-share count.")
        if not _finite(candidate.estimated_price) or candidate.estimated_price <= 0:
            reject("invalid_price", "Estimated execution price must be finite and positive.")
        if issues:
            return decision()
        if snapshot is None or snapshot.complete is not True:
            reject("incomplete_snapshot", "A complete, reconciled portfolio snapshot is required.")
            return decision()
        if not _aware(snapshot.as_of):
            reject("invalid_snapshot_time", "Portfolio snapshot time must include a timezone offset.")
            return decision()
        age = (decision_time - snapshot.as_of).total_seconds()
        if age < 0 or age > self.limits.max_snapshot_age_seconds:
            reject("stale_snapshot", "Portfolio snapshot must precede the evaluation and be recent.")
            return decision()
        if not self._valid_snapshot(snapshot):
            reject("invalid_snapshot", "Account values or positions are invalid or inconsistent.")
            return decision()

        symbol = signal.symbol.strip().upper()
        positions = {position.symbol.strip().upper(): position for position in snapshot.positions}
        holding = positions.get(symbol)
        notional = candidate.quantity * candidate.estimated_price
        if not _finite(notional):
            reject("invalid_notional", "Proposed trade notional must be finite.")
            return decision()

        # A reducing exit may proceed after a loss threshold is reached. It
        # still requires fresh, complete state and cannot exceed the holding.
        if signal.action == SignalAction.SELL:
            if holding is None or candidate.quantity > holding.quantity:
                reject("invalid_exit", "SELL quantity must not exceed the current long holding.")
            return decision(proposed_notional=notional)

        if holding is not None:
            reject("position_already_open", "Additional BUYs for an open position are not supported.")
        if candidate.stop_price is None or not _finite(candidate.stop_price) or not 0 < candidate.stop_price < candidate.estimated_price:
            reject("invalid_stop", "A BUY needs a finite stop price above zero and below its estimated entry price.")
            risk_fraction = None
        else:
            risk_fraction = candidate.quantity * (candidate.estimated_price - candidate.stop_price) / snapshot.equity
            if risk_fraction > self.limits.max_risk_per_trade:
                reject("risk_per_trade_limit", "Proposed loss to the stop exceeds the per-trade risk limit.")

        gross_exposure = sum(position.quantity * position.market_price for position in snapshot.positions)
        projected_exposure = (gross_exposure + notional) / snapshot.equity
        if notional > snapshot.cash:
            reject("insufficient_cash", "Estimated trade cost exceeds available cash.")
        if len(snapshot.positions) >= self.limits.max_positions:
            reject("position_count_limit", "Opening another position exceeds the position-count limit.")
        if notional / snapshot.equity > self.limits.max_single_position:
            reject("single_position_limit", "Proposed position exceeds the single-position limit.")
        if projected_exposure > self.limits.max_portfolio_exposure:
            reject("portfolio_exposure_limit", "Projected gross exposure exceeds the portfolio limit.")
        daily_loss = max(0.0, 1 - snapshot.equity / snapshot.day_start_equity)
        drawdown = max(0.0, 1 - snapshot.equity / snapshot.peak_equity)
        if daily_loss >= self.limits.max_daily_loss:
            reject("daily_loss_limit", "Current daily loss has reached the configured limit.")
        if drawdown >= self.limits.max_drawdown:
            reject("drawdown_limit", "Current portfolio drawdown has reached the configured limit.")

        if self.limits.max_sector_exposure is not None:
            sector = candidate.sector.strip().upper() if isinstance(candidate.sector, str) else ""
            if not sector or any(not position.sector or not position.sector.strip() for position in snapshot.positions):
                reject("sector_data_missing", "Sector data is required for the configured sector limit.")
            else:
                sector_notional = sum(
                    position.quantity * position.market_price
                    for position in snapshot.positions
                    if position.sector.strip().upper() == sector
                ) + notional
                if sector_notional / snapshot.equity > self.limits.max_sector_exposure:
                    reject("sector_exposure_limit", "Projected sector exposure exceeds the configured limit.")
        if self.limits.max_annualized_volatility is not None:
            volatility = candidate.annualized_volatility
            if volatility is None or not _finite(volatility) or volatility < 0:
                reject("volatility_data_missing", "Valid annualized volatility is required for the configured limit.")
            elif volatility > self.limits.max_annualized_volatility:
                reject("volatility_limit", "Candidate volatility exceeds the configured limit.")

        return decision(
            proposed_notional=notional,
            projected_exposure_fraction=projected_exposure,
            estimated_risk_fraction=risk_fraction,
        )

    @staticmethod
    def _valid_snapshot(snapshot: RiskPortfolioSnapshot) -> bool:
        if not isinstance(snapshot.positions, tuple):
            return False
        values = (snapshot.cash, snapshot.equity, snapshot.day_start_equity, snapshot.peak_equity)
        if any(not _finite(value) for value in values):
            return False
        if snapshot.cash < 0 or snapshot.equity <= 0 or snapshot.day_start_equity <= 0:
            return False
        if snapshot.peak_equity < max(snapshot.equity, snapshot.day_start_equity):
            return False
        symbols: set[str] = set()
        position_value = 0.0
        for position in snapshot.positions:
            if not isinstance(position, RiskPosition):
                return False
            symbol = position.symbol.strip().upper() if isinstance(position.symbol, str) else ""
            if (
                not symbol or symbol in symbols or type(position.quantity) is not int
                or position.quantity < 1 or not _finite(position.market_price)
                or position.market_price <= 0
                or (position.sector is not None and not isinstance(position.sector, str))
            ):
                return False
            symbols.add(symbol)
            position_value += position.quantity * position.market_price
        if not _finite(position_value):
            return False
        # This initial policy assumes a fully accounted, long-only portfolio.
        tolerance = max(0.01, snapshot.equity * 0.001)
        return abs(snapshot.cash + position_value - snapshot.equity) <= tolerance

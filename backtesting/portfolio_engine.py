"""Offline, shared-cash backtester for aligned daily stock bars.

No broker client or order endpoint is imported here. Historical daily bars
are treated as completed only when their session ends; signals fill at the
following session's open. Entry limits are research approximations, not an
implementation of the complete paper-trading risk policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import floor, isfinite

import pandas as pd

from app.ai.features import FeatureConfig, build_features
from app.data.market_data import CANONICAL_CANDLE_COLUMNS, validate_candles
from app.strategy.base import Signal, SignalAction, Strategy
from backtesting.engine import BacktestConfig, BacktestPortfolio, SimulatedFill


@dataclass(frozen=True)
class ResearchPortfolioLimits:
    """Configurable entry and loss gates; these do not approve paper trading."""

    max_portfolio_exposure: float = 0.70
    max_single_position: float = 0.10
    max_positions: int = 7
    max_daily_loss: float = 0.03
    max_drawdown: float = 0.10

    def __post_init__(self) -> None:
        for name in ("max_portfolio_exposure", "max_single_position", "max_daily_loss", "max_drawdown"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not 0 < value <= 1:
                raise ValueError(f"{name} must be a finite fraction in (0, 1]")
        if self.max_single_position > self.max_portfolio_exposure:
            raise ValueError("max_single_position cannot exceed max_portfolio_exposure")
        if type(self.max_positions) is not int or self.max_positions < 1:
            raise ValueError("max_positions must be a positive integer")


@dataclass(frozen=True)
class PortfolioEquityPoint:
    timestamp: pd.Timestamp
    cash: float
    equity: float
    gross_exposure: float
    position_count: int
    drawdown: float


@dataclass(frozen=True)
class PortfolioBacktestResult:
    costs: BacktestConfig
    limits: ResearchPortfolioLimits
    buy_priority: str
    signals: tuple[Signal, ...]
    fills: tuple[SimulatedFill, ...]
    equity_curve: tuple[PortfolioEquityPoint, ...]
    events: tuple[str, ...]
    final_positions: dict[str, int]
    final_closes: dict[str, float]
    halted_at: str | None


@dataclass(frozen=True)
class _PendingOrder:
    signal: Signal
    planned_quantity: int | None = None


class PortfolioBacktestEngine:
    """Run one rule across symbols with shared cash and synchronized sessions."""

    def __init__(
        self, strategy: Strategy, *, costs: BacktestConfig | None = None,
        limits: ResearchPortfolioLimits | None = None, buy_priority: str = "alphabetical",
    ) -> None:
        if buy_priority not in {"alphabetical", "reverse"}:
            raise ValueError("buy_priority must be alphabetical or reverse")
        self.strategy = strategy
        self.costs = costs or BacktestConfig()
        self.limits = limits or ResearchPortfolioLimits()
        self.buy_priority = buy_priority

    def run(
        self, datasets: dict[str, pd.DataFrame], *, trade_start: pd.Timestamp,
        trade_end: pd.Timestamp,
    ) -> PortfolioBacktestResult:
        start = self._utc_bound(trade_start)
        end = self._utc_bound(trade_end)
        if start >= end:
            raise ValueError("trade_start must precede trade_end")
        if not datasets:
            raise ValueError("At least one symbol dataset is required")

        bars: dict[str, pd.DataFrame] = {}
        features: dict[str, pd.DataFrame] = {}
        dates: pd.Series | None = None
        for symbol, source in sorted(datasets.items()):
            if not symbol or symbol != symbol.strip().upper() or symbol in bars:
                raise ValueError("Dataset keys must be unique uppercase symbols")
            validate_candles(source)
            frame = source.loc[:, CANONICAL_CANDLE_COLUMNS].copy()
            frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
            frame = frame.sort_values("timestamp", ignore_index=True)
            if set(frame["symbol"].astype(str).str.upper().str.strip()) != {symbol}:
                raise ValueError(f"{symbol}: dataset symbol differs from its key")
            if dates is None:
                dates = frame["timestamp"]
            elif not dates.equals(frame["timestamp"]):
                raise ValueError(f"{symbol}: session timestamps do not match the other datasets; no prices are filled")
            bars[symbol] = frame
            features[symbol] = build_features(
                frame, config=FeatureConfig(periods_per_year=self.costs.periods_per_year)
            )
        assert dates is not None
        indices = [index for index, timestamp in enumerate(dates) if start <= timestamp < end]
        if not indices:
            raise ValueError("No sessions fall in the requested trading window")
        symbols = sorted(bars)
        cash = self.costs.initial_cash
        positions: dict[str, int] = {}
        pending: dict[str, _PendingOrder] = {}
        fills: list[SimulatedFill] = []
        signals: list[Signal] = []
        points: list[PortfolioEquityPoint] = []
        events: list[str] = []
        peak = cash
        previous_close_equity = cash
        halted_at: str | None = None
        multiplier = (self.costs.slippage_bps + self.costs.spread_bps / 2) / 10_000

        for index in indices:
            timestamp = dates.iloc[index]
            open_prices = {symbol: float(bars[symbol].iloc[index]["open"]) for symbol in symbols}
            close_prices = {symbol: float(bars[symbol].iloc[index]["close"]) for symbol in symbols}

            # Orders originated at the previous completed close. Release cash
            # from all exits before considering competing entries.
            for symbol in sorted(pending):
                signal = pending[symbol].signal
                if signal.action != SignalAction.SELL:
                    continue
                quantity = positions.pop(symbol, 0)
                if not quantity:
                    events.append(f"{timestamp.isoformat()} {symbol}: skipped SELL; no position")
                    continue
                price = open_prices[symbol] * (1 - multiplier)
                cash += quantity * price - self.costs.commission_per_order
                fills.append(self._fill(timestamp, signal, quantity, open_prices[symbol], price))

            open_equity = cash + sum(quantity * open_prices[symbol] for symbol, quantity in positions.items())
            if open_equity <= 0:
                raise ValueError("Portfolio equity became nonpositive at an open")
            if halted_at is None:
                reason = self._loss_breach(open_equity, previous_close_equity, peak)
                if reason is not None:
                    halted_at = timestamp.isoformat()
                    events.append(f"{halted_at}: entry halt at open: {reason}; SELLs remain permitted")

            buy_symbols = sorted(pending, reverse=self.buy_priority == "reverse")
            for symbol in buy_symbols:
                order = pending[symbol]
                signal = order.signal
                if signal.action != SignalAction.BUY:
                    continue
                if halted_at is not None:
                    events.append(f"{timestamp.isoformat()} {symbol}: skipped BUY; entry halt active")
                    continue
                if symbol in positions:
                    events.append(f"{timestamp.isoformat()} {symbol}: skipped BUY; position already open")
                    continue
                if len(positions) >= self.limits.max_positions:
                    events.append(f"{timestamp.isoformat()} {symbol}: skipped BUY; position-count limit")
                    continue
                equity = cash + sum(quantity * open_prices[name] for name, quantity in positions.items())
                gross = sum(quantity * open_prices[name] for name, quantity in positions.items())
                price = open_prices[symbol] * (1 + multiplier)
                budget = min(
                    self.costs.position_fraction * equity,
                    self.limits.max_single_position * equity,
                    self.limits.max_portfolio_exposure * equity - gross,
                    cash - self.costs.commission_per_order,
                )
                # The signal-close quantity is a ceiling: a favorable next
                # open cannot enlarge an order using information unavailable
                # when the order was planned. Gaps can reduce or reject it.
                quantity = min(order.planned_quantity or 0, floor(max(0.0, budget) / price))
                if quantity < 1:
                    events.append(f"{timestamp.isoformat()} {symbol}: skipped BUY; cash or exposure limit")
                    continue
                cash -= quantity * price + self.costs.commission_per_order
                positions[symbol] = quantity
                fills.append(self._fill(timestamp, signal, quantity, open_prices[symbol], price))
            pending = {}
            if cash < -1e-6 or len(positions) > self.limits.max_positions:
                raise ValueError("Shared cash or position-count invariant failed")

            equity = cash + sum(quantity * close_prices[symbol] for symbol, quantity in positions.items())
            if equity <= 0:
                raise ValueError("Portfolio equity became nonpositive at a close")
            peak = max(peak, equity)
            gross_close = sum(quantity * close_prices[symbol] for symbol, quantity in positions.items())
            points.append(PortfolioEquityPoint(
                timestamp=timestamp, cash=cash, equity=equity,
                gross_exposure=gross_close / equity, position_count=len(positions),
                drawdown=equity / peak - 1,
            ))
            if halted_at is None:
                reason = self._loss_breach(equity, previous_close_equity, peak)
                if reason is not None:
                    halted_at = timestamp.isoformat()
                    events.append(f"{halted_at}: entry halt at close: {reason}; SELLs remain permitted")
            previous_close_equity = equity

            # Every strategy call receives only that symbol's completed bars.
            for symbol in symbols:
                available = (
                    features[symbol].iloc[[index]] if self.strategy.latest_row_only
                    else features[symbol].iloc[:index + 1]
                )
                signal = self.strategy.generate_signal(
                    available, BacktestPortfolio(cash, positions.get(symbol, 0), equity)
                )
                if signal.symbol.strip().upper() != symbol or pd.Timestamp(signal.timestamp) != timestamp:
                    raise ValueError(f"{symbol}: strategy returned a mismatched signal")
                signals.append(signal)
                if signal.action in {SignalAction.BUY, SignalAction.SELL}:
                    planned_quantity = None
                    if signal.action == SignalAction.BUY:
                        planned_budget = min(
                            self.costs.position_fraction * equity,
                            self.limits.max_single_position * equity,
                        )
                        planned_quantity = floor(
                            planned_budget / (close_prices[symbol] * (1 + multiplier))
                        )
                    pending[symbol] = _PendingOrder(signal, planned_quantity)

        for symbol, order in sorted(pending.items()):
            signal = order.signal
            events.append(f"{symbol}: unfilled {signal.action.value} signal at {signal.timestamp.isoformat()}; no next session")
        return PortfolioBacktestResult(
            costs=self.costs, limits=self.limits, buy_priority=self.buy_priority,
            signals=tuple(signals), fills=tuple(fills), equity_curve=tuple(points),
            events=tuple(events), final_positions=dict(sorted(positions.items())),
            final_closes=close_prices, halted_at=halted_at,
        )

    def _loss_breach(self, equity: float, prior_close: float, peak: float) -> str | None:
        if equity / peak - 1 <= -self.limits.max_drawdown:
            return "maximum drawdown reached"
        if equity / prior_close - 1 <= -self.limits.max_daily_loss:
            return "daily loss limit reached"
        return None

    def _fill(
        self, timestamp: pd.Timestamp, signal: Signal, quantity: int,
        reference_open: float, price: float,
    ) -> SimulatedFill:
        return SimulatedFill(
            timestamp=timestamp, symbol=signal.symbol, side=signal.action,
            quantity=quantity, reference_open=reference_open, fill_price=price,
            commission=self.costs.commission_per_order,
            signal_timestamp=pd.Timestamp(signal.timestamp), signal_reason=signal.reason,
        )

    @staticmethod
    def _utc_bound(value: pd.Timestamp) -> pd.Timestamp:
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is None:
            raise ValueError("Trading-window bounds must be timezone-aware")
        return timestamp.tz_convert("UTC")


def summarize_portfolio(result: PortfolioBacktestResult) -> dict[str, object]:
    """Summarize a continuous account, including realized and open P&L."""
    points = result.equity_curve
    if not points:
        raise ValueError("No equity observations")
    annual_returns: dict[str, float] = {}
    prior_year_end = result.costs.initial_cash
    yearly_last: dict[int, float] = {}
    for point in points:
        year = point.timestamp.tz_convert("America/New_York").year
        yearly_last[year] = point.equity
    for year, equity in sorted(yearly_last.items()):
        annual_returns[str(year)] = equity / prior_year_end - 1
        prior_year_end = equity

    entries: dict[str, SimulatedFill] = {}
    realized: dict[str, float] = {}
    profits: list[float] = []
    durations: list[float] = []
    for fill in result.fills:
        if fill.side == SignalAction.BUY:
            if fill.symbol in entries:
                raise ValueError(f"{fill.symbol}: overlapping BUY fills")
            entries[fill.symbol] = fill
        else:
            entry = entries.pop(fill.symbol, None)
            if entry is None or entry.quantity != fill.quantity:
                raise ValueError(f"{fill.symbol}: SELL does not close its BUY")
            profit = fill.quantity * (fill.fill_price - entry.fill_price) - entry.commission - fill.commission
            profits.append(profit)
            realized[fill.symbol] = realized.get(fill.symbol, 0.0) + profit
            durations.append((fill.timestamp - entry.timestamp).total_seconds() / 86400)
    if set(entries) != set(result.final_positions):
        raise ValueError("Open fills do not match final positions")
    open_positions = {
        symbol: {
            "quantity": entry.quantity,
            "last_close": result.final_closes[symbol],
            "marked_unrealized_pnl": entry.quantity * (result.final_closes[symbol] - entry.fill_price) - entry.commission,
        }
        for symbol, entry in sorted(entries.items())
    }
    accounted_profit = sum(realized.values()) + sum(
        position["marked_unrealized_pnl"] for position in open_positions.values()
    )
    if abs(accounted_profit - (points[-1].equity - result.costs.initial_cash)) > 1e-6:
        raise ValueError("Realized plus marked P&L does not reconcile to final equity")
    max_exposure = max(point.gross_exposure for point in points)
    return {
        "initial_cash": result.costs.initial_cash,
        "final_equity": points[-1].equity,
        "total_return": points[-1].equity / result.costs.initial_cash - 1,
        "annual_returns": annual_returns,
        "max_drawdown": min(point.drawdown for point in points),
        "max_observed_gross_exposure": max_exposure,
        "max_observed_positions": max(point.position_count for point in points),
        "completed_trades": len(profits),
        "winning_trades": sum(profit > 0 for profit in profits),
        "win_rate": sum(profit > 0 for profit in profits) / len(profits) if profits else None,
        "profit_factor": sum(p for p in profits if p > 0) / abs(sum(p for p in profits if p < 0))
        if any(p < 0 for p in profits) else None,
        "average_holding_days": sum(durations) / len(durations) if durations else None,
        "realized_pnl_by_symbol": dict(sorted(realized.items())),
        "open_positions": open_positions,
        "fill_count": len(result.fills),
        "entry_halted_at": result.halted_at,
        "event_count": len(result.events),
    }

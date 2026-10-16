"""Performance measures derived from a completed backtest audit trail."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np
import pandas as pd

from app.strategy.base import SignalAction
from backtesting.engine import BacktestResult


@dataclass(frozen=True)
class BacktestMetrics:
    """Net portfolio and completed-trade statistics.

    ``None`` means the quantity cannot be estimated from the observed run,
    such as profit factor when no losing trade has closed. Open positions are
    included in equity but excluded from completed-trade statistics.
    """

    total_return: float
    annualized_return: float | None
    cagr: float | None
    max_drawdown: float
    sharpe_ratio: float | None
    sortino_ratio: float | None
    win_rate: float | None
    profit_factor: float | None
    average_trade: float | None
    number_of_trades: int
    volatility: float | None
    largest_win: float | None
    largest_loss: float | None
    average_win: float | None
    average_loss: float | None
    average_holding_days: float | None
    open_position: bool


def calculate_metrics(result: BacktestResult, *, periods_per_year: int) -> BacktestMetrics:
    """Calculate net metrics using per-candle equity and completed round trips.

    Period-based measures require at least two return observations and an
    explicit annualization factor appropriate to the candle timeframe.
    CAGR uses elapsed calendar time, while annualized_return is the arithmetic
    mean per-candle return multiplied by ``periods_per_year``.
    """
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    if not result.equity_curve:
        raise ValueError("The backtest has no equity observations")

    equity = np.asarray([point.equity for point in result.equity_curve], dtype=float)
    if not np.isfinite(equity).all() or (equity <= 0).any():
        raise ValueError("Equity must remain finite and positive to calculate return metrics")
    initial = result.config.initial_cash
    returns = equity[1:] / equity[:-1] - 1
    annualized_return = float(returns.mean() * periods_per_year) if len(returns) >= 2 else None
    volatility = float(returns.std(ddof=1) * sqrt(periods_per_year)) if len(returns) >= 2 else None
    sharpe = None
    if len(returns) >= 2 and returns.std(ddof=1) > 0:
        sharpe = float(returns.mean() / returns.std(ddof=1) * sqrt(periods_per_year))
    downside = np.minimum(returns, 0.0)
    downside_deviation = float(np.sqrt(np.mean(downside**2))) if len(returns) >= 2 else 0.0
    sortino = float(returns.mean() / downside_deviation * sqrt(periods_per_year)) if downside_deviation > 0 else None

    start = pd.Timestamp(result.equity_curve[0].timestamp)
    end = pd.Timestamp(result.equity_curve[-1].timestamp)
    years = (end - start).total_seconds() / (365.2425 * 86400)
    cagr = float((equity[-1] / initial) ** (1 / years) - 1) if years > 0 else None

    profits: list[float] = []
    holding_days: list[float] = []
    entry = None
    for fill in result.fills:
        if fill.side == SignalAction.BUY:
            if entry is not None:
                raise ValueError("A second BUY fill appeared before the open trade was closed")
            entry = fill
        elif fill.side == SignalAction.SELL:
            if entry is None or fill.quantity != entry.quantity:
                raise ValueError("SELL fill does not match an open BUY fill")
            profits.append(
                fill.quantity * (fill.fill_price - entry.fill_price)
                - entry.commission - fill.commission
            )
            holding_days.append(
                (pd.Timestamp(fill.timestamp) - pd.Timestamp(entry.timestamp)).total_seconds() / 86400
            )
            entry = None

    wins = [profit for profit in profits if profit > 0]
    losses = [profit for profit in profits if profit < 0]
    number_of_trades = len(profits)
    return BacktestMetrics(
        total_return=float(equity[-1] / initial - 1),
        annualized_return=annualized_return,
        cagr=cagr,
        max_drawdown=float(min(point.drawdown for point in result.equity_curve)),
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        win_rate=len(wins) / number_of_trades if number_of_trades else None,
        profit_factor=sum(wins) / abs(sum(losses)) if losses else None,
        average_trade=float(np.mean(profits)) if profits else None,
        number_of_trades=number_of_trades,
        volatility=volatility,
        largest_win=max(wins) if wins else None,
        largest_loss=min(losses) if losses else None,
        average_win=float(np.mean(wins)) if wins else None,
        average_loss=float(np.mean(losses)) if losses else None,
        average_holding_days=float(np.mean(holding_days)) if holding_days else None,
        open_position=entry is not None,
    )

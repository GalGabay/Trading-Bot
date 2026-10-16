"""A single-symbol backtesting engine that prevents same-candle execution."""

from __future__ import annotations

from dataclasses import dataclass
from math import floor

import pandas as pd

from app.ai.features import FeatureConfig, build_features
from app.data.market_data import CANONICAL_CANDLE_COLUMNS, validate_candles
from app.strategy.base import Signal, SignalAction, Strategy


@dataclass(frozen=True)
class BacktestConfig:
    """Explicit assumptions for a reproducible backtest scenario.

    Cost values are scenario assumptions, not assertions about a broker's
    current pricing. Slippage is adverse: it increases a buy fill and reduces
    a sell fill. The defaults are intentionally visible in every result.
    """

    initial_cash: float = 100_000.0
    position_fraction: float = 0.10
    commission_per_order: float = 0.0
    slippage_bps: float = 5.0
    spread_bps: float = 2.0
    periods_per_year: int = 252

    def __post_init__(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError("initial_cash must be positive")
        if not 0 < self.position_fraction <= 1:
            raise ValueError("position_fraction must be greater than 0 and at most 1")
        if self.commission_per_order < 0 or self.slippage_bps < 0 or self.spread_bps < 0:
            raise ValueError("commission_per_order, slippage_bps, and spread_bps cannot be negative")
        if self.slippage_bps + self.spread_bps / 2 >= 10_000:
            raise ValueError("combined selling costs must stay below the entire open price")
        if self.periods_per_year <= 0:
            raise ValueError("periods_per_year must be positive")


@dataclass(frozen=True)
class BacktestPortfolio:
    """Read-only state made available to a strategy at a candle close."""

    cash: float
    quantity: int
    equity: float


@dataclass(frozen=True)
class SimulatedFill:
    """A next-candle market fill produced only by the backtest engine."""

    timestamp: pd.Timestamp
    symbol: str
    side: SignalAction
    quantity: int
    reference_open: float
    fill_price: float
    commission: float
    signal_timestamp: pd.Timestamp
    signal_reason: str


@dataclass(frozen=True)
class EquityPoint:
    """Portfolio value after the candle's execution and closing mark."""

    timestamp: pd.Timestamp
    cash: float
    quantity: int
    close: float
    equity: float
    drawdown: float


@dataclass(frozen=True)
class BacktestResult:
    """Auditable outputs of one deterministic backtest run."""

    config: BacktestConfig
    signals: tuple[Signal, ...]
    fills: tuple[SimulatedFill, ...]
    equity_curve: tuple[EquityPoint, ...]
    events: tuple[str, ...]

    @property
    def final_equity(self) -> float:
        return self.equity_curve[-1].equity if self.equity_curve else self.config.initial_cash


@dataclass(frozen=True)
class _PendingOrder:
    signal: Signal


class BacktestEngine:
    """Run one strategy on one symbol with next-candle market execution.

    The engine calls a strategy after each candle closes. An actionable signal
    is held as a pending order and filled at the following candle's open. It
    therefore never uses a closing price to claim execution at that same close.
    """

    def __init__(self, strategy: Strategy, *, config: BacktestConfig | None = None) -> None:
        self._strategy = strategy
        self._config = config or BacktestConfig()

    def run(
        self, candles: pd.DataFrame, *, trade_start: pd.Timestamp | None = None,
        trade_end: pd.Timestamp | None = None,
    ) -> BacktestResult:
        """Backtest validated candles for exactly one symbol.

        The supplied candle data is never modified. Feature calculations are
        causal, and the strategy receives only rows available at each close.
        Unfilled last-candle signals are recorded as events, never fabricated.
        """
        self._validate_input(candles)
        ordered = candles.loc[:, CANONICAL_CANDLE_COLUMNS].copy()
        ordered["timestamp"] = pd.to_datetime(ordered["timestamp"], utc=True)
        ordered["symbol"] = ordered["symbol"].astype(str).str.upper().str.strip()
        ordered = ordered.sort_values("timestamp", ignore_index=True)
        if trade_start is not None:
            trade_start = self._utc_bound(trade_start)
        if trade_end is not None:
            trade_end = self._utc_bound(trade_end)
            ordered = ordered.loc[ordered["timestamp"] < trade_end].reset_index(drop=True)
        if trade_start is not None and trade_end is not None and trade_start >= trade_end:
            raise ValueError("trade_start must precede trade_end")
        if ordered.empty or (trade_start is not None and not (ordered["timestamp"] >= trade_start).any()):
            raise ValueError("No candles fall within the requested trading window")
        features = build_features(
            ordered, config=FeatureConfig(periods_per_year=self._config.periods_per_year)
        )

        cash = self._config.initial_cash
        quantity = 0
        pending: _PendingOrder | None = None
        signals: list[Signal] = []
        fills: list[SimulatedFill] = []
        points: list[EquityPoint] = []
        events: list[str] = []
        peak_equity = self._config.initial_cash

        for index, candle in ordered.iterrows():
            timestamp = candle["timestamp"]
            if trade_start is not None and timestamp < trade_start:
                continue  # Earlier rows warm up causal indicators without simulated trades.
            if pending is not None:
                cash, quantity, fill, event = self._fill_pending_order(
                    pending, candle, cash=cash, quantity=quantity
                )
                if fill is not None:
                    fills.append(fill)
                if event is not None:
                    events.append(event)
                pending = None

            close = float(candle["close"])
            equity = cash + quantity * close
            portfolio = BacktestPortfolio(cash=cash, quantity=quantity, equity=equity)
            available_features = (
                features.iloc[[index]] if self._strategy.latest_row_only
                else features.iloc[: index + 1]
            )
            signal = self._strategy.generate_signal(available_features, portfolio)
            if signal.symbol.strip().upper() != str(candle["symbol"]):
                raise ValueError("Strategy signal symbol does not match the evaluated candle")
            if pd.Timestamp(signal.timestamp) != timestamp:
                raise ValueError("Strategy signal timestamp does not match the evaluated candle")
            signals.append(signal)
            if signal.action in {SignalAction.BUY, SignalAction.SELL}:
                pending = _PendingOrder(signal)

            peak_equity = max(peak_equity, equity)
            points.append(EquityPoint(
                timestamp=timestamp, cash=cash, quantity=quantity, close=close,
                equity=equity, drawdown=(equity / peak_equity) - 1,
            ))

        if pending is not None:
            events.append(
                f"Unfilled {pending.signal.action} signal at {pending.signal.timestamp.isoformat()}: no next candle open."
            )
        return BacktestResult(
            config=self._config, signals=tuple(signals), fills=tuple(fills),
            equity_curve=tuple(points), events=tuple(events),
        )

    def _fill_pending_order(
        self, pending: _PendingOrder, candle: pd.Series, *, cash: float, quantity: int
    ) -> tuple[float, int, SimulatedFill | None, str | None]:
        signal = pending.signal
        open_price = float(candle["open"])
        multiplier = (self._config.slippage_bps + self._config.spread_bps / 2) / 10_000
        timestamp = pd.Timestamp(candle["timestamp"])
        if signal.action == SignalAction.BUY:
            if quantity:
                return cash, quantity, None, f"Skipped BUY at {timestamp.isoformat()}: position already open."
            fill_price = open_price * (1 + multiplier)
            target_value = (cash + quantity * open_price) * self._config.position_fraction
            target_quantity = floor(target_value / fill_price)
            affordable_quantity = floor((cash - self._config.commission_per_order) / fill_price)
            fill_quantity = min(target_quantity, affordable_quantity)
            if fill_quantity < 1:
                return cash, quantity, None, f"Skipped BUY at {timestamp.isoformat()}: insufficient cash."
            cash -= fill_quantity * fill_price + self._config.commission_per_order
            quantity += fill_quantity
        elif signal.action == SignalAction.SELL:
            if quantity < 1:
                return cash, quantity, None, f"Skipped SELL at {timestamp.isoformat()}: no position is open."
            fill_price = open_price * (1 - multiplier)
            fill_quantity = quantity
            cash += fill_quantity * fill_price - self._config.commission_per_order
            quantity = 0
        else:
            return cash, quantity, None, None

        fill = SimulatedFill(
            timestamp=timestamp, symbol=str(candle["symbol"]), side=signal.action,
            quantity=fill_quantity, reference_open=open_price, fill_price=fill_price,
            commission=self._config.commission_per_order,
            signal_timestamp=pd.Timestamp(signal.timestamp), signal_reason=signal.reason,
        )
        return cash, quantity, fill, None

    @staticmethod
    def _validate_input(candles: pd.DataFrame) -> None:
        validate_candles(candles)
        symbols = candles["symbol"].astype(str).str.upper().str.strip().unique()
        if len(symbols) != 1 or not symbols[0]:
            raise ValueError("A backtest run must contain candles for exactly one symbol")

    @staticmethod
    def _utc_bound(value: pd.Timestamp) -> pd.Timestamp:
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is None:
            raise ValueError("Backtest trading-window bounds must be timezone-aware")
        return timestamp.tz_convert("UTC")

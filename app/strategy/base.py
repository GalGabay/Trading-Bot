"""Stable interface for strategies that produce explainable trade candidates."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import isfinite
from typing import Any

import pandas as pd


class SignalAction(StrEnum):
    """Actions a strategy may propose; execution is a later responsibility."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class Signal:
    """An immutable, auditable strategy recommendation.

    It is deliberately not an order. Risk management and order management
    decide whether a future BUY/SELL signal can result in a broker request.
    """

    symbol: str
    action: SignalAction
    confidence: float
    reason: str
    timestamp: datetime
    strategy: str

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("signal symbol must not be empty")
        if not isinstance(self.action, SignalAction):
            raise ValueError("signal action must be a SignalAction")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("signal confidence must be between 0 and 1")
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("signal timestamp must be timezone-aware")


class Strategy(ABC):
    """A replaceable component that turns completed features into a signal."""

    name: str
    latest_row_only: bool = False

    @abstractmethod
    def generate_signal(self, market_data: pd.DataFrame, portfolio: Any | None = None) -> Signal:
        """Return a signal from data available at the latest completed candle.

        ``portfolio`` exposes read-only simulated state when backtesting. A
        strategy may use it to avoid repeated entries or request an exit, but
        must never submit orders or mutate the state.
        """

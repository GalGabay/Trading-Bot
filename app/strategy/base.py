"""Stable interface for strategies that produce explainable trade candidates."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
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
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("signal confidence must be between 0 and 1")
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("signal timestamp must be timezone-aware")


class Strategy(ABC):
    """A replaceable component that turns completed features into a signal."""

    name: str

    @abstractmethod
    def generate_signal(self, market_data: pd.DataFrame, portfolio: Any | None = None) -> Signal:
        """Return a signal from data available at the latest completed candle.

        ``portfolio`` is part of the stable interface for future strategies.
        The first strategy does not use it: risk and position policy belong to
        later phases, so a strategy must not submit orders or mutate it.
        """

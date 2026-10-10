"""Market-session calendars used when validating US equity candles."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol
from zoneinfo import ZoneInfo

import pandas as pd


@dataclass(frozen=True)
class TradingSession:
    """One exchange session, with UTC opening and closing timestamps."""

    opens_at: pd.Timestamp
    closes_at: pd.Timestamp

    def __post_init__(self) -> None:
        if self.opens_at.tz is None or self.closes_at.tz is None:
            raise ValueError("Trading-session timestamps must be timezone-aware.")
        if self.opens_at >= self.closes_at:
            raise ValueError("A trading session must close after it opens.")


class MarketCalendar(Protocol):
    """Supplies actual exchange sessions for a requested date range."""

    def sessions(self, start: date, end: date) -> Iterable[TradingSession]: ...


class AlpacaMarketCalendar:
    """US market calendar supplied by the configured Alpaca account."""

    def __init__(self, broker: Any) -> None:
        self._broker = broker

    def sessions(self, start: date, end: date) -> list[TradingSession]:
        calendar_days = self._broker.get_market_calendar(start=start, end=end)
        return [
            TradingSession(
                opens_at=self._to_utc(day.open),
                closes_at=self._to_utc(day.close),
            )
            for day in calendar_days
        ]

    @staticmethod
    def _to_utc(value: Any) -> pd.Timestamp:
        """Normalize Alpaca calendar times, which the SDK exposes as naive ET."""
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            timestamp = timestamp.tz_localize(ZoneInfo("America/New_York"))
        return timestamp.tz_convert("UTC")

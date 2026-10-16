"""Central, paper-only Alpaca API client.

Credentials are loaded from environment variables or the repository-root
``.env`` file. This module never logs or prints credential values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.live import StockDataStream
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import QueryOrderStatus
from alpaca.trading.requests import GetCalendarRequest, GetOrdersRequest, OrderRequest
from dotenv import load_dotenv


class AlpacaConfigurationError(ValueError):
    """Raised when the local Alpaca configuration is missing or unsafe."""


@dataclass(frozen=True)
class _AlpacaCredentials:
    api_key: str
    secret_key: str

    @classmethod
    def load(cls) -> _AlpacaCredentials:
        # Resolve from this file's location so startup does not depend on the
        # shell's current working directory (Windows and Raspberry Pi alike).
        repository_root = Path(__file__).resolve().parents[2]
        load_dotenv(repository_root / ".env", override=False)

        api_key = os.getenv("ALPACA_API_KEY", "").strip()
        secret_key = os.getenv("ALPACA_SECRET_KEY", "").strip()
        if not api_key or not secret_key:
            raise AlpacaConfigurationError(
                "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in the environment "
                "or in the repository-root .env file."
            )

        paper_setting = os.getenv("ALPACA_PAPER", "true").strip().lower()
        if paper_setting not in {"true", "1", "yes"}:
            raise AlpacaConfigurationError(
                "This implementation is paper-trading only. Set ALPACA_PAPER=true."
            )

        return cls(api_key=api_key, secret_key=secret_key)


class AlpacaClient:
    """One controlled entry point for Alpaca trading and stock market data.

    The SDK trading client is always constructed with ``paper=True``. This
    class intentionally provides no live-trading configuration path.
    """

    def __init__(self) -> None:
        credentials = _AlpacaCredentials.load()
        self._trading = TradingClient(
            credentials.api_key,
            credentials.secret_key,
            paper=True,
        )
        self._historical_data = StockHistoricalDataClient(
            credentials.api_key,
            credentials.secret_key,
        )
        self._stream: StockDataStream | None = None
        # Keep credentials only as long as client construction requires them.
        del credentials

    def get_account(self) -> Any:
        """Return the Alpaca paper account details."""
        return self._trading.get_account()

    def get_positions(self) -> list[Any]:
        """Return all currently open paper positions."""
        return self._trading.get_all_positions()

    def get_orders(self) -> list[Any]:
        """Return all paper orders, including closed and canceled orders."""
        request = GetOrdersRequest(status=QueryOrderStatus.ALL)
        return self._trading.get_orders(filter=request)

    def get_market_calendar(self, *, start: date, end: date) -> list[Any]:
        """Return Alpaca's exchange sessions for the inclusive date range."""
        return self._trading.get_calendar(GetCalendarRequest(start=start, end=end))

    def submit_order(self, order: OrderRequest) -> Any:
        """Submit an Alpaca order request to the paper account."""
        return self._trading.submit_order(order)

    def cancel_order(self, order_id: str) -> None:
        """Request cancellation of a paper order by its Alpaca order ID."""
        self._trading.cancel_order_by_id(order_id)

    def get_market_data(
        self,
        symbol: str,
        *,
        start: datetime,
        end: datetime | None = None,
        timeframe: TimeFrame = TimeFrame.Hour,
        adjustment: Adjustment | None = None,
        feed: DataFeed | None = None,
    ) -> Any:
        """Fetch historical/recent stock bars for one symbol.

        ``start`` and ``end`` should be timezone-aware datetimes. The SDK's
        BarSet is returned unchanged so the data layer can validate and store
        it without hiding broker response details.
        """
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("symbol must not be empty")
        if start.tzinfo is None or start.utcoffset() is None:
            raise ValueError("start must be timezone-aware")
        if end is not None and (end.tzinfo is None or end.utcoffset() is None):
            raise ValueError("end must be timezone-aware")

        request = StockBarsRequest(
            symbol_or_symbols=normalized_symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            adjustment=adjustment,
            feed=feed,
        )
        return self._historical_data.get_stock_bars(request)

    def get_stock_data_stream(self) -> StockDataStream:
        """Return the lazily created Alpaca real-time stock data stream."""
        if self._stream is None:
            credentials = _AlpacaCredentials.load()
            self._stream = StockDataStream(
                credentials.api_key,
                credentials.secret_key,
            )
        return self._stream

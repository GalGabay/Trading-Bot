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
from alpaca.data.models import BarSet
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import AssetClass, QueryOrderStatus
from alpaca.trading.requests import GetAssetsRequest, GetCalendarRequest, GetOrdersRequest, OrderRequest
from alpaca.common.exceptions import APIError
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

    def get_open_orders(self) -> list[Any]:
        """Return open paper orders; reject a potentially truncated response.

        Alpaca caps one response at 500 orders. An apparently full response
        cannot be treated as a complete inventory for reconciliation.
        """
        request = GetOrdersRequest(status=QueryOrderStatus.OPEN, limit=500)
        orders = self._trading.get_orders(filter=request)
        if len(orders) >= 500:
            raise RuntimeError("Open-order response reached Alpaca's 500-order limit; reconciliation is incomplete.")
        return orders

    def get_order_by_client_id(self, client_order_id: str) -> Any | None:
        """Look up one paper order; return None only for an explicit 404."""
        try:
            return self._trading.get_order_by_client_id(client_order_id)
        except APIError as exc:
            if exc.status_code == 404:
                return None
            raise

    def get_order_by_id(self, order_id: str) -> Any:
        """Return one paper order by Alpaca's identifier."""
        return self._trading.get_order_by_id(order_id)

    def get_market_clock(self) -> Any:
        """Return Alpaca's US-equities market clock."""
        return self._trading.get_clock()

    def get_asset(self, symbol: str) -> Any:
        """Return the broker's asset metadata for a proposed symbol."""
        return self._trading.get_asset(symbol)

    def get_assets(self) -> list[dict[str, Any]]:
        """Snapshot US-equity assets, including inactive/nontradable entries.

        This is current broker metadata, not historical universe membership.
        Omitting status requests all statuses; it does not establish that
        every historical delisting or ticker identity is represented.
        """
        # The pinned SDK's AssetExchange enum rejects some newer catalog
        # exchanges. Preserve public metadata verbatim through the SDK's
        # authenticated GET transport instead of dropping unknown exchanges
        # or changing the trading client's global response mode.
        request = GetAssetsRequest(asset_class=AssetClass.US_EQUITY)
        response = self._trading.get("/assets", request.to_request_fields())
        if not isinstance(response, list) or any(not isinstance(asset, dict) for asset in response):
            raise ValueError("Alpaca asset catalog must be a list of metadata objects")
        return response

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

    def get_market_data_batch(
        self, symbols: list[str], *, start: datetime, end: datetime,
        timeframe: TimeFrame = TimeFrame.Day,
        adjustment: Adjustment = Adjustment.ALL, feed: DataFeed = DataFeed.SIP,
    ) -> BarSet:
        """Read paginated bars using the multi-symbol endpoint.

        The old SDK's single-symbol parser fails on some empty responses.
        Keep a genuine empty result empty, reject malformed/repeated pages,
        and retain every returned symbol for downstream identity validation.
        This does not change the clients' global response modes.
        """
        if not symbols or any(not symbol.strip() for symbol in symbols):
            raise ValueError("At least one nonempty symbol is required")
        if any(value.tzinfo is None or value.utcoffset() is None for value in (start, end)):
            raise ValueError("Market data bounds must be timezone-aware")
        if start >= end:
            raise ValueError("Market data end must follow start")
        request = StockBarsRequest(
            symbol_or_symbols=[s.strip().upper() for s in symbols], start=start,
            end=end, timeframe=timeframe, adjustment=adjustment, feed=feed,
        )
        params = request.to_request_fields()
        params["symbols"] = ",".join(params.pop("symbol_or_symbols"))
        params["limit"] = 10000
        collected: dict[str, list[Any]] = {}
        tokens: set[str] = set()
        for _ in range(100):
            page = self._historical_data.get("/stocks/bars", params, api_version="v2")
            if not isinstance(page, dict) or "bars" not in page:
                raise ValueError("Historical response lacks bars")
            bars = page["bars"]
            if bars is not None:
                if not isinstance(bars, dict) or any(not isinstance(rows, list) for rows in bars.values()):
                    raise ValueError("Historical bars must be grouped by symbol")
                for symbol, rows in bars.items():
                    collected.setdefault(symbol, []).extend(rows)
            token = page.get("next_page_token")
            if token is None:
                return BarSet(collected)
            if not isinstance(token, str) or token in tokens:
                raise ValueError("Invalid or repeated historical pagination token")
            tokens.add(token)
            params["page_token"] = token
        raise ValueError("Historical response exceeded 100-page safety bound")

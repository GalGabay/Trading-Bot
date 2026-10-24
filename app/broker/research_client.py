"""Bounded GET-only historical data transport under existing entitlement.

No trading client, account lookup, billing API, subscription change, endpoint
override, automatic retry, feed fallback, or redirects. Credentials use the
existing central loader. This module cannot start a paid service or order.
"""

from datetime import UTC, date, datetime, timedelta
import json
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.broker.alpaca_client import _AlpacaCredentials


class ResearchDataError(RuntimeError):
    def __init__(self, status=None):
        super().__init__("Read-only historical data unavailable; no upgrade or retry attempted")
        self.status_code = status


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HistoricalResearchClient:
    """Only pre-2024 bars/events, capped at 192 actual HTTP attempts per run."""

    def __init__(self):
        self._credentials = _AlpacaCredentials.load()
        self._opener = build_opener(_NoRedirects())
        self.request_count = 0
        self._last_request = 0.0

    @staticmethod
    def _symbol(value):
        if not isinstance(value, str) or not re.fullmatch(r"[A-Z][A-Z0-9.]{0,11}", value):
            raise ValueError("Research symbol must be explicit uppercase letters/digits/dots")

    def _get(self, path, params):
        if path not in {"/v2/stocks/bars", "/v1/corporate-actions"} or self.request_count >= 192:
            raise ValueError("Historical research endpoint/request budget exceeded")
        delay = .4 - (time.monotonic() - self._last_request)
        if delay > 0:
            time.sleep(delay)
        request = Request("https://data.alpaca.markets" + path + "?" + urlencode(params),
                          headers={"APCA-API-KEY-ID": self._credentials.api_key,
                                   "APCA-API-SECRET-KEY": self._credentials.secret_key}, method="GET")
        self.request_count += 1
        self._last_request = time.monotonic()
        try:
            with self._opener.open(request, timeout=30) as response:
                payload = response.read(8_000_001)
        except HTTPError as exc:
            raise ResearchDataError(exc.code) from None
        except OSError:
            raise ResearchDataError() from None
        if len(payload) > 8_000_000:
            raise ValueError("Research response exceeds the 8 MB page budget")
        result = json.loads(payload)
        if not isinstance(result, dict):
            raise ValueError("Research response must be a JSON object")
        return result

    def bars_page(self, *, symbol, start, end_exclusive, token=None):
        self._symbol(symbol)
        for value in (start, end_exclusive):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("Research bounds require timezones")
        if not datetime(2016, 1, 1, tzinfo=UTC) <= start < end_exclusive <= datetime(2024, 1, 1, tzinfo=UTC):
            raise ValueError("Historical prices restricted to 2016-2023")
        params = {"symbols": symbol, "start": start.isoformat(),
                  "end": (end_exclusive - timedelta(microseconds=1)).isoformat(),
                  "timeframe": "1Day", "adjustment": "raw", "feed": "sip",
                  "asof": "-", "currency": "USD", "limit": 10000, "sort": "asc"}
        if token is not None:
            params["page_token"] = token
        return self._get("/v2/stocks/bars", params)

    def actions_page(self, *, symbol, token=None):
        self._symbol(symbol)
        params = {"symbols": symbol, "start": date(2016, 1, 1).isoformat(),
                  "end": date(2023, 12, 31).isoformat(), "limit": 1000,
                  "sort": "asc", "data_quality": "all"}
        if token is not None:
            params["page_token"] = token
        return self._get("/v1/corporate-actions", params)

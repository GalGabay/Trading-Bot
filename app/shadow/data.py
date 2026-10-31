"""Bounded GET-only IEX collection; no account, order or subscription methods."""

from datetime import datetime, timedelta, timezone
import json
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.shadow.config import symbol, utc


class ShadowDataError(RuntimeError):
    pass


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ShadowDataClient:
    """Fixed endpoints and a lifetime 110-request cap; no retries or fallback.

    Credentials are loaded only when this transport is explicitly constructed
    for collect. Importing the observer or observing saved files loads none.
    """

    def __init__(self):
        from app.broker.alpaca_client import _AlpacaCredentials
        self._credentials = _AlpacaCredentials.load()
        self._opener = build_opener(_NoRedirects())
        self.request_count = 0
        self._last_request = 0.0
        self._started = time.monotonic()
        self._stopped = False

    def _get(self, path, params=None):
        if path == "/v2/stocks/bars":
            host = "https://data.alpaca.markets"
        elif path == "/v2/calendar" or re.fullmatch(r"/v2/assets/[A-Z][A-Z0-9.]{0,11}", path):
            host = "https://paper-api.alpaca.markets"
        else:
            raise ValueError("Endpoint is outside the shadow read-only allowlist")
        remaining = 180 - (time.monotonic() - self._started)
        if self._stopped or self.request_count >= 110 or remaining <= 0:
            raise ShadowDataError("Shadow request budget exhausted or collection already stopped")
        delay = .4 - (time.monotonic() - self._last_request)
        if delay > 0:
            time.sleep(delay)
        remaining = 180 - (time.monotonic() - self._started)
        if remaining <= 0:
            self._stopped = True
            raise ShadowDataError("Shadow collection time budget expired")
        query = "?" + urlencode(params) if params else ""
        request = Request(host + path + query, method="GET", headers={
            "APCA-API-KEY-ID": self._credentials.api_key,
            "APCA-API-SECRET-KEY": self._credentials.secret_key})
        self.request_count += 1
        self._last_request = time.monotonic()
        try:
            with self._opener.open(request, timeout=min(20, remaining)) as response:
                payload = response.read(5_000_001)
            if time.monotonic() - self._started >= 180:
                raise ShadowDataError("Shadow collection time budget expired")
            if len(payload) > 5_000_000:
                raise ShadowDataError("Shadow response exceeded the page size cap")
            return json.loads(payload)
        except HTTPError as exc:
            self._stopped = True
            raise ShadowDataError(f"Shadow GET stopped at HTTP {exc.code}; no retry or upgrade") from None
        except (OSError, ValueError, ShadowDataError):
            self._stopped = True
            raise ShadowDataError("Shadow GET failed; no retry or fallback") from None

    def collect(self, config):
        observed = datetime.now(timezone.utc)
        start = utc(config.history_start + "T00:00:00Z")
        if start >= utc(observed):
            raise ValueError("Shadow history start must precede collection")
        calendar = self._get("/v2/calendar", {"start": config.history_start,
            "end": (observed + timedelta(days=14)).date().isoformat()})
        if not isinstance(calendar, list) or not calendar or len(calendar) > 5000:
            raise ShadowDataError("Invalid or oversized market calendar")
        assets, bars = {}, {}
        for name in (*config.symbols, "SPY"):
            symbol(name)
            assets[name] = self._get("/v2/assets/" + name)
            rows, token, seen = [], None, set()
            for _ in range(3):
                params = dict(symbols=name, timeframe="1Day", start=start.isoformat(),
                    end=observed.isoformat(), adjustment="split", feed="iex", sort="asc", limit=10000)
                if token is not None:
                    params["page_token"] = token
                page = self._get("/v2/stocks/bars", params)
                if not isinstance(page, dict) or not isinstance(page.get("bars"), dict):
                    raise ShadowDataError("Invalid bars response; no data inferred")
                if set(page["bars"]) - {name}:
                    raise ShadowDataError("Bars response contains an unexpected symbol")
                part = page["bars"].get(name, [])
                if not isinstance(part, list) or len(rows) + len(part) > 20000:
                    raise ShadowDataError("Invalid or oversized daily bars")
                rows.extend(part)
                token = page.get("next_page_token")
                if token is None:
                    break
                if not isinstance(token, str) or not token or token in seen:
                    raise ShadowDataError("Invalid or repeated pagination token")
                seen.add(token)
            else:
                raise ShadowDataError("Pagination exceeded the shadow page cap")
            bars[name] = rows
        return dict(schema_version=1, observed_at=datetime.now(timezone.utc).isoformat(),
            request_end=observed.isoformat(), history_start=config.history_start,
            feed="iex", adjustment="split", timeframe="1Day", symbols=list(config.symbols),
            calendar=calendar, assets=assets, bars=bars, requests=self.request_count,
            provenance="Current provider split-adjusted signal data; no historical known-at certification",
            broker_account_requests=0, orders=0, purchases_usd=0)

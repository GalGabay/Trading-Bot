"""Explicit historical security identities and listing/cash-outcome evidence.

No vendor, account, price download or automatic event inference lives here.
Evidence timestamps mean when the historical fact became public, not when
we downloaded it. This contract supports daily USD common-stock research.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import asdict, dataclass
from datetime import date
from math import isfinite
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from app.data.market_calendar import TradingSession
from app.data.market_data import CANONICAL_CANDLE_COLUMNS, validate_candles


class UniverseDataError(ValueError):
    """Missing, contradictory or unsupported historical-universe evidence."""


def _aware(value) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp) or timestamp.tzinfo is None:
        raise UniverseDataError("Universe evidence timestamps must be valid and timezone-aware")
    return timestamp.tz_convert("UTC")


def _date(value) -> date:
    if type(value) is date:
        return value
    if not isinstance(value, str):
        raise UniverseDataError("Effective sessions must be YYYY-MM-DD dates")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise UniverseDataError("Effective sessions must be YYYY-MM-DD dates")
    return parsed


def _text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise UniverseDataError(f"{name} requires a nonempty evidence value")


@dataclass(frozen=True)
class ListingPeriod:
    instrument_id: str
    symbol: str
    exchange: str
    security_type: str
    start_session: str
    end_session_exclusive: str | None
    start_known_at: str
    end_known_at: str | None
    source: str

    def __post_init__(self):
        for name in ("instrument_id", "symbol", "exchange", "security_type", "source"):
            _text(getattr(self, name), name)
        for name in ("instrument_id", "symbol"):
            if getattr(self, name) != getattr(self, name).strip().upper():
                raise UniverseDataError(f"{name} must be an uppercase stable key/symbol")
        start = _date(self.start_session)
        _aware(self.start_known_at)
        if self.security_type not in {"common_stock", "reit_common"}:
            raise UniverseDataError("Only explicitly classified common stocks/REIT common shares are supported")
        if self.exchange not in {"NYSE", "NASDAQ", "AMEX"}:
            raise UniverseDataError("This research contract supports NYSE, NASDAQ and AMEX listings")
        if self.end_session_exclusive is None:
            if self.end_known_at is not None:
                raise UniverseDataError("An open listing period cannot have end evidence")
        else:
            if _date(self.end_session_exclusive) <= start:
                raise UniverseDataError("Listing end must follow its start")
            if self.end_known_at is None:
                raise UniverseDataError("A listing end requires independently dated end evidence")
            _aware(self.end_known_at)

    def contains(self, day: date) -> bool:
        return _date(self.start_session) <= day and (
            self.end_session_exclusive is None or day < _date(self.end_session_exclusive)
        )


@dataclass(frozen=True)
class CashOutcome:
    """Verified cash available at a session open; never a guessed last-price sale.

    A zero payment requires the same source evidence as a positive payment.
    Share exchanges, delayed receivables, splits and uncertain recoveries
    require separate adapters and are deliberately unsupported here.
    """

    event_id: str
    instrument_id: str
    effective_session: str
    cash_per_share: float
    known_at: str
    source: str

    def __post_init__(self):
        for name in ("event_id", "instrument_id", "source"):
            _text(getattr(self, name), name)
        if self.instrument_id != self.instrument_id.strip().upper():
            raise UniverseDataError("Cash outcome requires an uppercase stable instrument key")
        _date(self.effective_session)
        _aware(self.known_at)
        if isinstance(self.cash_per_share, bool) or not isinstance(self.cash_per_share, (int, float)) or not isfinite(self.cash_per_share) or self.cash_per_share < 0:
            raise UniverseDataError("Verified cash per share must be finite and nonnegative")


class HistoricalUniverse:
    """Daily calendar plus independently sourced historical identity intervals.

    Listing starts/ends are checked against publication timestamps. Runtime
    checks use the current session only, never tomorrow's universe membership.
    Missing in-lifetime bars are unresolved: no inference from price endpoints.
    """

    def __init__(
        self, *, sessions: list[TradingSession], listings: list[ListingPeriod],
        cash_outcomes: list[CashOutcome] | None = None, currency: str = "USD",
        price_basis: str, action_scope: str,
    ):
        if currency != "USD" or not sessions or not listings:
            raise UniverseDataError("Universe requires USD, explicit sessions and listing evidence")
        if price_basis != "raw" or action_scope != "event_free_except_terminal_cash":
            raise UniverseDataError("Initial universe mode requires declared raw, event-free inputs except supported terminal cash; other action adapters are incomplete")
        self.sessions = tuple(sessions)
        self.manifest_sha256: str | None = None
        self.listings = tuple(listings)
        self.cash_outcomes = tuple(cash_outcomes or ())
        self.dates = pd.Series([
            session.opens_at.tz_convert(ZoneInfo("America/New_York")).normalize().tz_convert("UTC")
            for session in sessions
        ])
        if not self.dates.is_monotonic_increasing or self.dates.duplicated().any():
            raise UniverseDataError("Universe calendar must contain unique ordered daily sessions")
        if any(s.opens_at.date() != s.closes_at.date() for s in sessions):
            raise UniverseDataError("Universe contract requires regular same-UTC-date US sessions")
        self._by_day = {t.date(): s for t, s in zip(self.dates, sessions)}
        self._index = {t: i for i, t in enumerate(self.dates)}
        self._listings: dict[str, list[ListingPeriod]] = {}
        for listing in listings:
            self._listings.setdefault(listing.instrument_id, []).append(listing)
            for effective, known in ((listing.start_session, listing.start_known_at),
                                     (listing.end_session_exclusive, listing.end_known_at)):
                if effective is None:
                    continue
                day = _date(effective)
                # Period boundaries outside this saved calendar remain explicit;
                # compare with local midnight conservatively for those boundaries.
                deadline = self._by_day[day].opens_at if day in self._by_day else pd.Timestamp(day, tz="America/New_York")
                if _aware(known) > deadline:
                    raise UniverseDataError(f"{listing.instrument_id}: listing boundary not known by its effective session")
        for instrument_id, periods in self._listings.items():
            periods.sort(key=lambda p: p.start_session)
            for previous, current in zip(periods, periods[1:]):
                if previous.end_session_exclusive is None or previous.end_session_exclusive > current.start_session:
                    raise UniverseDataError(f"{instrument_id}: overlapping identity/listing intervals")
        # The same alias may be reused only in nonoverlapping date intervals.
        by_alias: dict[str, list[ListingPeriod]] = {}
        for listing in listings:
            by_alias.setdefault(listing.symbol, []).append(listing)
        for symbol, periods in by_alias.items():
            periods.sort(key=lambda p: p.start_session)
            for previous, current in zip(periods, periods[1:]):
                if previous.end_session_exclusive is None or previous.end_session_exclusive > current.start_session:
                    raise UniverseDataError(f"{symbol}: ambiguous historical ticker identity")
        self._outcomes: dict[pd.Timestamp, list[CashOutcome]] = {}
        event_ids, terminated = set(), set()
        for outcome in self.cash_outcomes:
            if outcome.event_id in event_ids or outcome.instrument_id in terminated:
                raise UniverseDataError("Duplicate terminal cash outcome")
            event_ids.add(outcome.event_id)
            terminated.add(outcome.instrument_id)
            day = _date(outcome.effective_session)
            if day not in self._by_day:
                raise UniverseDataError("Cash payment must identify a saved exchange session")
            if _aware(outcome.known_at) > self._by_day[day].opens_at:
                raise UniverseDataError("Cash payment was not known by the modeled payment open")
            periods = self._listings.get(outcome.instrument_id, [])
            if not periods or any(p.end_session_exclusive is None or p.end_session_exclusive > outcome.effective_session for p in periods):
                raise UniverseDataError("Terminal payment requires a documented ended identity")
            timestamp = self.dates.iloc[self._index[pd.Timestamp(day, tz="America/New_York").tz_convert("UTC")]]
            self._outcomes.setdefault(timestamp, []).append(outcome)

    @property
    def instrument_ids(self) -> set[str]:
        return set(self._listings)

    def listing_at(self, instrument_id: str, timestamp: pd.Timestamp) -> ListingPeriod | None:
        day = timestamp.tz_convert("America/New_York").date()
        return next((p for p in self._listings.get(instrument_id, ()) if p.contains(day)), None)

    def outcomes_at(self, timestamp: pd.Timestamp) -> tuple[CashOutcome, ...]:
        return tuple(self._outcomes.get(timestamp, ()))

    def prepare(self, instrument_id: str, source: pd.DataFrame) -> pd.DataFrame:
        """Map dated source tickers to one stable key, preserving actual rows only."""
        if instrument_id not in self._listings:
            raise UniverseDataError(f"Unknown stable instrument ID: {instrument_id}")
        if source.empty:
            if set(CANONICAL_CANDLE_COLUMNS) - set(source.columns):
                raise UniverseDataError("Empty histories still require the candle schema")
            if any(self.listing_at(instrument_id, timestamp) is not None for timestamp in self.dates):
                raise UniverseDataError(f"{instrument_id}: empty history during a documented listing; no survivor exclusion allowed")
            return source.loc[:, CANONICAL_CANDLE_COLUMNS].copy()
        validate_candles(source)
        frame = source.loc[:, CANONICAL_CANDLE_COLUMNS].copy()
        for column in ("open", "high", "low", "close", "volume"):
            frame[column] = pd.to_numeric(frame[column])
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        frame = frame.sort_values("timestamp", ignore_index=True)
        if frame["timestamp"].duplicated().any():
            raise UniverseDataError(f"{instrument_id}: duplicate observations across aliases")
        expected = {timestamp for timestamp in self.dates if self.listing_at(instrument_id, timestamp) is not None}
        missing = expected - set(frame["timestamp"])
        if missing:
            raise UniverseDataError(
                f"{instrument_id}: {len(missing)} unexplained in-lifetime sessions have no bar; "
                "obtain data or independently documented lifecycle boundaries. Do not fill or silently exclude this instrument."
            )
        for row in frame.itertuples(index=False):
            listing = self.listing_at(instrument_id, row.timestamp)
            if row.timestamp not in self._index or listing is None:
                raise UniverseDataError(f"{instrument_id}: candle outside saved calendar/listing lifetime")
            if row.symbol != listing.symbol:
                raise UniverseDataError(f"{instrument_id}: candle ticker does not match dated alias evidence")
        frame["symbol"] = instrument_id
        frame.index = [self._index[t] for t in frame["timestamp"]]
        return frame

    def metadata(self) -> dict:
        return {
            "schema_version": 1, "identity_keys": "stable instrument IDs; ticker aliases are dated metadata",
            "currency": "USD", "instrument_count": len(self._listings),
            "calendar_sessions": len(self.sessions),
            "listing_sources": sorted({p.source for p in self.listings}),
            "listings": [asdict(p) for p in self.listings],
            "cash_outcomes": [asdict(p) for p in self.cash_outcomes],
            "manifest_sha256": self.manifest_sha256,
            "market_wide_performance_ready": False,
            "price_and_action_scope": "Engineering support only: raw/event-free inputs; split, dividend, share-exchange and receivable adapters remain unimplemented.",
            "limitation": "Supplied evidence is validated, not independently certified; no market-wide completeness assertion.",
        }

    @classmethod
    def load(cls, path: Path) -> HistoricalUniverse:
        """Load an explicit versioned manifest. Never infer events from CSV gaps."""
        value = json.loads(path.read_text(encoding="utf-8"))
        required = {"schema_version", "currency", "price_basis", "action_scope", "sessions", "listings", "cash_outcomes"}
        if set(value) != required or type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise UniverseDataError("Unsupported or incomplete historical-universe manifest")
        universe = cls(
            currency=value["currency"],
            price_basis=value["price_basis"], action_scope=value["action_scope"],
            sessions=[TradingSession(_aware(s["opens_at"]), _aware(s["closes_at"])) for s in value["sessions"]],
            listings=[ListingPeriod(**item) for item in value["listings"]],
            cash_outcomes=[CashOutcome(**item) for item in value["cash_outcomes"]],
        )
        universe.manifest_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        return universe

"""Retrieve and validate Alpaca stock candles before they reach the strategy."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from app.data.market_calendar import AlpacaMarketCalendar, MarketCalendar, TradingSession

CANONICAL_CANDLE_COLUMNS = ["timestamp", "symbol", "open", "high", "low", "close", "volume"]


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    row_count: int = 0


class CandleValidationError(ValueError):
    """A hard data-quality failure that prevents the candle data being used."""

    def __init__(self, message: str, *, issues: tuple[ValidationIssue, ...] = ()) -> None:
        super().__init__(message)
        self.issues = issues or (ValidationIssue("invalid_candles", message),)


@dataclass(frozen=True)
class ValidationConfig:
    """Policy for regular-session US equity candles.

    Timestamps mean the start of an interval. A volume above ten times the
    positive median for its symbol is a warning by default, never a trade.
    """

    timeframe: TimeFrame = TimeFrame.Hour
    volume_anomaly_multiple: float = 10.0
    require_all_scheduled_bars: bool = False

    def __post_init__(self) -> None:
        if self.volume_anomaly_multiple <= 1:
            raise ValueError("volume_anomaly_multiple must be greater than 1.")


@dataclass(frozen=True)
class CandleValidationReport:
    zero_volume_rows: int = 0
    time_gaps: int = 0
    warnings: tuple[ValidationIssue, ...] = field(default_factory=tuple)


def _hard_error(code: str, message: str, row_count: int = 0) -> None:
    raise CandleValidationError(message, issues=(ValidationIssue(code, message, row_count),))


def _validate_raw_timestamps(timestamps: pd.Series) -> pd.Series:
    values: list[pd.Timestamp] = []
    invalid_count = 0
    for value in timestamps:
        try:
            parsed = pd.Timestamp(value)
        except (TypeError, ValueError, OverflowError):
            invalid_count += 1
            continue
        if pd.isna(parsed):
            invalid_count += 1
        else:
            values.append(parsed)
    if invalid_count:
        _hard_error("invalid_timestamp", "Every candle timestamp must be valid.", invalid_count)
    naive_count = sum(value.tzinfo is None or value.utcoffset() is None for value in values)
    if naive_count:
        _hard_error(
            "timezone_missing",
            "Every candle timestamp must include a timezone offset; naive timestamps are unsafe.",
            naive_count,
        )
    return pd.to_datetime(values, utc=True)


def _as_utc(value: datetime) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        _hard_error("timezone_missing", "Requested validation bounds must include a timezone offset.")
    return timestamp.tz_convert("UTC")


def _timeframe_delta(timeframe: TimeFrame) -> timedelta:
    if timeframe.unit_value == TimeFrameUnit.Minute:
        return timedelta(minutes=timeframe.amount_value)
    if timeframe.unit_value == TimeFrameUnit.Hour:
        return timedelta(hours=timeframe.amount_value)
    if timeframe.unit_value == TimeFrameUnit.Day:
        return timedelta(days=timeframe.amount_value)
    raise ValueError(f"Unsupported candle timeframe for validation: {timeframe}")


def _expected_timestamps(
    sessions: list[TradingSession], timeframe: TimeFrame, start: pd.Timestamp, end: pd.Timestamp
) -> set[pd.Timestamp]:
    expected: set[pd.Timestamp] = set()
    for session in sessions:
        if timeframe.unit_value == TimeFrameUnit.Day:
            # Alpaca daily stock bars are timestamped at midnight New York
            # time, rather than at the regular-session opening time.
            values = [
                session.opens_at.tz_convert(ZoneInfo("America/New_York"))
                .normalize()
                .tz_convert("UTC")
            ]
        else:
            values = []
            # Alpaca intraday bars are clock-aligned. For example, a 1-hour
            # bar during a 09:30 ET opening starts at 10:00 ET, not 09:30 ET.
            if timeframe.unit_value == TimeFrameUnit.Minute:
                frequency = f"{timeframe.amount_value}min"
            elif timeframe.unit_value == TimeFrameUnit.Hour:
                frequency = f"{timeframe.amount_value}h"
            else:
                raise ValueError(f"Unsupported candle timeframe for validation: {timeframe}")
            interval = _timeframe_delta(timeframe)
            # Hourly Alpaca bars are aligned to the wall clock; the first
            # regular-session hour begins before the 09:30 ET opening.
            current = (
                session.opens_at.floor(frequency)
                if timeframe.unit_value == TimeFrameUnit.Hour
                else session.opens_at.ceil(frequency)
            )
            while current < session.closes_at:
                values.append(current)
                current += interval
        expected.update(timestamp for timestamp in values if start <= timestamp <= end)
    return expected


def _validate_sessions(
    candles: pd.DataFrame,
    *,
    calendar: MarketCalendar,
    timeframe: TimeFrame,
    requested_start: datetime | None,
    requested_end: datetime | None,
    require_all_scheduled_bars: bool,
) -> int:
    observed_start, observed_end = candles["timestamp"].min(), candles["timestamp"].max()
    start = _as_utc(requested_start) if requested_start else observed_start
    end = _as_utc(requested_end) if requested_end else observed_end
    if end < start:
        _hard_error("invalid_range", "The requested candle end must be after its start.")
    sessions = list(calendar.sessions(start.date(), end.date()))
    expected = _expected_timestamps(sessions, timeframe, start, end)
    observed = set(candles["timestamp"])
    outside_session = observed - expected
    if outside_session:
        _hard_error(
            "outside_market_session",
            "Candle timestamps fall outside scheduled regular-market session boundaries.",
            len(outside_session),
        )
    missing = expected - observed
    if missing:
        if require_all_scheduled_bars:
            _hard_error(
                "unobserved_intervals",
                f"No bar was observed in {len(missing)} scheduled {timeframe} interval(s). Investigate feed coverage or no-trade intervals.",
                len(missing),
            )
    return len(missing)


def validate_candles(
    candles: pd.DataFrame,
    *,
    config: ValidationConfig | None = None,
    calendar: MarketCalendar | None = None,
    requested_start: datetime | None = None,
    requested_end: datetime | None = None,
) -> CandleValidationReport:
    """Raise for hard failures and return structured warnings for usable data.

    Without a market calendar, structural checks still run but gaps are never
    classified as missing. This avoids mistaking holidays or session breaks for
    corruption. The application service always supplies Alpaca's calendar.
    """
    config = config or ValidationConfig()
    missing_columns = set(CANONICAL_CANDLE_COLUMNS) - set(candles.columns)
    if missing_columns:
        _hard_error("missing_columns", f"Candle table is missing required columns: {sorted(missing_columns)}")
    if candles.empty:
        _hard_error("empty_candles", "No candles were returned for the requested range.")

    checked = candles.loc[:, CANONICAL_CANDLE_COLUMNS].copy()
    checked["timestamp"] = _validate_raw_timestamps(checked["timestamp"])
    if checked["symbol"].isna().any() or (checked["symbol"].astype(str).str.strip() == "").any():
        _hard_error("missing_symbol", "Every candle must have a symbol.")
    checked["symbol"] = checked["symbol"].astype(str).str.upper().str.strip()
    duplicates = int(checked.duplicated(subset=["timestamp", "symbol"]).sum())
    if duplicates:
        _hard_error("duplicate_candles", "Duplicate timestamp/symbol candle rows were returned.", duplicates)

    numeric_columns = ["open", "high", "low", "close", "volume"]
    for column in numeric_columns:
        checked[column] = pd.to_numeric(checked[column], errors="coerce")
    if not np.isfinite(checked[numeric_columns].to_numpy(dtype=float)).all():
        _hard_error("invalid_ohlcv", "OHLCV values must be finite numbers and present.")
    if (checked[["open", "high", "low", "close"]] <= 0).any().any():
        _hard_error("invalid_price", "Open, high, low, and close values must be positive.")
    if (checked["volume"] < 0).any():
        _hard_error("negative_volume", "Volume cannot be negative.")
    if (checked["high"] < checked[["open", "close", "low"]].max(axis=1)).any():
        _hard_error("invalid_high", "High must be at least open, close, and low.")
    if (checked["low"] > checked[["open", "close", "high"]].min(axis=1)).any():
        _hard_error("invalid_low", "Low must be at most open, close, and high.")

    warnings: list[ValidationIssue] = []
    zero_volume = int((checked["volume"] == 0).sum())
    if zero_volume:
        warnings.append(ValidationIssue("zero_volume", "Zero-volume candles were returned.", zero_volume))
    for symbol, rows in checked.groupby("symbol"):
        positive = rows.loc[rows["volume"] > 0, "volume"]
        if not positive.empty:
            count = int((positive > positive.median() * config.volume_anomaly_multiple).sum())
            if count:
                warnings.append(ValidationIssue(
                    "volume_anomaly",
                    f"{symbol} has {count} volume value(s) over {config.volume_anomaly_multiple:g}x its positive median.",
                    count,
                ))

    gaps = 0
    if calendar is not None:
        gaps = _validate_sessions(
            checked, calendar=calendar, timeframe=config.timeframe,
            requested_start=requested_start, requested_end=requested_end,
            require_all_scheduled_bars=config.require_all_scheduled_bars,
        )
        if gaps:
            warnings.append(ValidationIssue(
                "unobserved_intervals",
                f"No bar was observed in {gaps} scheduled interval(s); this can reflect no trades or missing data.",
                gaps,
            ))
    return CandleValidationReport(zero_volume_rows=zero_volume, time_gaps=gaps, warnings=tuple(warnings))


def _barset_to_candles(barset: Any, requested_symbol: str) -> pd.DataFrame:
    raw = getattr(barset, "df", barset)
    if not isinstance(raw, pd.DataFrame):
        raise TypeError("Expected Alpaca market data as a pandas DataFrame or BarSet.")
    candles = raw.copy()
    if isinstance(candles.index, pd.MultiIndex) or candles.index.name is not None or isinstance(candles.index, pd.DatetimeIndex):
        candles = candles.reset_index()
    columns = {str(column).lower(): column for column in candles.columns}
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not required.issubset(columns):
        _hard_error("bad_broker_response", "Alpaca response did not include the required timestamp and OHLCV fields.")
    return pd.DataFrame({
        "timestamp": candles[columns["timestamp"]],
        "symbol": candles[columns["symbol"]] if "symbol" in columns else requested_symbol,
        "open": candles[columns["open"]], "high": candles[columns["high"]],
        "low": candles[columns["low"]], "close": candles[columns["close"]],
        "volume": candles[columns["volume"]],
    }).sort_values(["symbol", "timestamp"], ignore_index=True)


def regular_session_candles(
    candles: pd.DataFrame,
    *,
    calendar: MarketCalendar,
    timeframe: TimeFrame,
    requested_start: datetime,
    requested_end: datetime,
) -> pd.DataFrame:
    """Select scheduled bar timestamps and exclude Alpaca extended-hours bars.

    This filters source bars; it never creates a missing bar. The caller must
    still validate the selected rows against the complete session calendar.
    """
    start, end = _as_utc(requested_start), _as_utc(requested_end)
    sessions = list(calendar.sessions(start.date(), end.date()))
    expected = _expected_timestamps(sessions, timeframe, start, end)
    timestamps = _validate_raw_timestamps(candles["timestamp"])
    return candles.loc[timestamps.isin(expected)].reset_index(drop=True)


class MarketDataService:
    def __init__(self, broker: Any, *, calendar: MarketCalendar | None = None) -> None:
        self._broker = broker
        self._calendar = calendar or AlpacaMarketCalendar(broker)

    def get_historical_candles(
        self, symbol: str, *, start: datetime, end: datetime | None = None,
        timeframe: TimeFrame = TimeFrame.Hour,
        adjustment: Any | None = None, feed: Any | None = None,
    ) -> tuple[pd.DataFrame, CandleValidationReport]:
        normalized_symbol = symbol.strip().upper()
        request_options = {}
        if adjustment is not None:
            request_options["adjustment"] = adjustment
        if feed is not None:
            request_options["feed"] = feed
        response = self._broker.get_market_data(
            normalized_symbol, start=start, end=end, timeframe=timeframe, **request_options
        )
        candles = _barset_to_candles(response, normalized_symbol)
        if end is not None:
            candles = regular_session_candles(
                candles, calendar=self._calendar, timeframe=timeframe,
                requested_start=start, requested_end=end,
            )
        report = validate_candles(
            candles, config=ValidationConfig(timeframe=timeframe), calendar=self._calendar,
            requested_start=start, requested_end=end,
        )
        return candles, report

    def get_realtime_stream(self) -> Any:
        return self._broker.get_stock_data_stream()

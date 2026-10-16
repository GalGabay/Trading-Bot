"""First simple, deterministic trend-following strategy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.strategy.base import Signal, SignalAction, Strategy


@dataclass(frozen=True)
class TrendFollowingV1Config:
    """Explicit thresholds for the initial architecture-validation strategy."""

    rsi_minimum: float = 50.0
    rsi_maximum: float = 70.0
    minimum_volume_ratio: float = 1.0

    def __post_init__(self) -> None:
        if not 0 <= self.rsi_minimum <= self.rsi_maximum <= 100:
            raise ValueError("RSI thresholds must be ordered values from 0 to 100")
        if self.minimum_volume_ratio <= 0:
            raise ValueError("minimum_volume_ratio must be positive")


class TrendFollowingV1(Strategy):
    """Propose BUY only for a confirmed trend with moderate momentum.

    Rules on the latest completed candle:
    - close > EMA200
    - EMA20 > EMA50
    - RSI14 lies inclusively between 50 and 70 by default
    - volume ratio exceeds 1.0 by default

    When a position is open, a broken trend proposes SELL. Stop loss and
    position sizing remain responsibilities of later risk and portfolio phases.
    """

    name = "trend_following_v1"
    latest_row_only = True
    _required_columns = {"timestamp", "symbol", "close", "ema_20", "ema_50", "ema_200", "rsi_14", "volume_ratio_20"}

    def __init__(self, *, config: TrendFollowingV1Config | None = None) -> None:
        self.config = config or TrendFollowingV1Config()

    def generate_signal(self, market_data: pd.DataFrame, portfolio: Any | None = None) -> Signal:
        """Evaluate one symbol's latest completed feature row without mutation."""
        missing = self._required_columns - set(market_data.columns)
        if missing:
            raise ValueError(f"Strategy input is missing required columns: {sorted(missing)}")
        if market_data.empty:
            raise ValueError("Strategy input must contain at least one feature row")
        symbols = market_data["symbol"].dropna().astype(str).str.strip().str.upper().unique()
        if len(symbols) != 1 or not symbols[0]:
            raise ValueError("A strategy call must contain feature rows for exactly one symbol")

        ordered = market_data.copy()
        parsed_timestamps = []
        for value in ordered["timestamp"]:
            try:
                parsed = pd.Timestamp(value)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError("Strategy input timestamps must be valid and timezone-aware") from exc
            if pd.isna(parsed) or parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ValueError("Strategy input timestamps must be valid and timezone-aware")
            parsed_timestamps.append(parsed.tz_convert("UTC"))
        ordered["timestamp"] = parsed_timestamps
        row = ordered.sort_values("timestamp").iloc[-1]
        symbol = symbols[0]
        timestamp = row["timestamp"].to_pydatetime()
        values = {column: row[column] for column in self._required_columns - {"timestamp", "symbol"}}
        unavailable = sorted(column for column, value in values.items() if pd.isna(value))
        if unavailable:
            return self._hold(symbol, timestamp, f"HOLD: warm-up data unavailable for {', '.join(unavailable)}.", 0.0)

        if portfolio is not None and getattr(portfolio, "quantity", 0) > 0:
            if float(row["close"]) < float(row["ema_50"]) or float(row["ema_20"]) < float(row["ema_50"]):
                return Signal(
                    symbol=symbol,
                    action=SignalAction.SELL,
                    confidence=1.0,
                    reason="SELL: trend reversal (close < EMA50 or EMA20 < EMA50).",
                    timestamp=timestamp,
                    strategy=self.name,
                )
            return self._hold(symbol, timestamp, "HOLD: position open; trend remains intact.", 1.0)

        checks = [
            ("close_above_ema200", float(row["close"]) > float(row["ema_200"]), "close is not above EMA200"),
            ("ema20_above_ema50", float(row["ema_20"]) > float(row["ema_50"]), "EMA20 is not above EMA50"),
            ("rsi_in_range", self.config.rsi_minimum <= float(row["rsi_14"]) <= self.config.rsi_maximum,
             f"RSI14 is outside {self.config.rsi_minimum:g}-{self.config.rsi_maximum:g}"),
            ("volume_confirmed", float(row["volume_ratio_20"]) > self.config.minimum_volume_ratio,
             f"volume ratio is not above {self.config.minimum_volume_ratio:g}"),
        ]
        failed = [reason for _, passed, reason in checks if not passed]
        confidence = sum(passed for _, passed, _ in checks) / len(checks)
        if failed:
            return self._hold(symbol, timestamp, f"HOLD: {'; '.join(failed)}.", confidence)
        return Signal(
            symbol=symbol,
            action=SignalAction.BUY,
            confidence=1.0,
            reason="BUY: close > EMA200; EMA20 > EMA50; RSI14 is in range; volume ratio is confirmed.",
            timestamp=timestamp,
            strategy=self.name,
        )

    def _hold(self, symbol: str, timestamp, reason: str, confidence: float) -> Signal:
        return Signal(symbol, SignalAction.HOLD, confidence, reason, timestamp, self.name)

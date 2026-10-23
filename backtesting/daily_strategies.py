"""Fixed Study C-R2 strategy hypotheses, used only by offline research."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

import pandas as pd

from app.ai.features import build_features
from app.strategy.base import Signal, SignalAction, Strategy


def market_regime(spy_bars: pd.DataFrame) -> dict[pd.Timestamp, bool]:
    """One decision per completed SPY date, with no filling or future lookup."""
    if set(spy_bars["symbol"]) != {"SPY"}:
        raise ValueError("Market context must contain SPY only")
    features = build_features(spy_bars)
    return dict(zip(features["timestamp"], features["close"] > features["ema_200"]))


@dataclass(frozen=True)
class DailyRuleConfig:
    style: str = "trend"
    entry_sessions: int = 55
    exit_sessions: int = 20

    def __post_init__(self) -> None:
        if self.style not in {"trend", "breakout", "no_volume"}:
            raise ValueError("Unknown daily research style")
        for name in ("entry_sessions", "exit_sessions"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")


class DailyResearchStrategy(Strategy):
    """Price-only rules; history is supplied as a completed-bar prefix.

    The external regime dictionary is keyed by date and derived causally.
    Only the current completed date is read, including when SPY is excluded
    from the tradable universe in a concentration diagnostic.
    """

    latest_row_only = False

    def __init__(self, config: DailyRuleConfig, *, regime: dict[pd.Timestamp, bool] | None = None) -> None:
        if config.style != "no_volume" and regime is None:
            raise ValueError("A market-regime series is required")
        self.config, self.regime = config, dict(regime or {})
        self.name = f"daily_research_{config.style}"

    def generate_signal(self, market_data: pd.DataFrame, portfolio: Any | None = None) -> Signal:
        if market_data.empty or market_data["symbol"].nunique() != 1:
            raise ValueError("Daily research input must contain one symbol")
        if not market_data["timestamp"].is_monotonic_increasing:
            raise ValueError("Completed feature history must be ordered")
        row = market_data.iloc[-1]
        timestamp = pd.Timestamp(row["timestamp"])
        symbol = str(row["symbol"])
        holding = portfolio is not None and getattr(portfolio, "quantity", 0) > 0

        def signal(action: SignalAction, reason: str) -> Signal:
            return Signal(symbol, action, 1.0, reason, timestamp.to_pydatetime(), self.name)

        if self.config.style != "no_volume":
            if timestamp not in self.regime:
                raise ValueError(f"SPY regime missing on signal date {timestamp}")
            if not self.regime[timestamp]:
                return signal(SignalAction.SELL if holding else SignalAction.HOLD, "Broad-market trend is off")
        required = ("close", "ema_20", "ema_50", "ema_200", "rsi_14")
        if not all(pd.notna(row[name]) and isfinite(float(row[name])) for name in required):
            return signal(SignalAction.HOLD, "Indicator warmup unavailable")

        close, fast, medium, slow, rsi = (float(row[name]) for name in required)
        if self.config.style == "breakout":
            if holding:
                if len(market_data) <= self.config.exit_sessions:
                    return signal(SignalAction.HOLD, "Exit-channel warmup unavailable")
                prior_low = float(market_data.iloc[-self.config.exit_sessions - 1:-1]["low"].min())
                exit_now = close < prior_low or close < slow
                return signal(SignalAction.SELL if exit_now else SignalAction.HOLD, "Prior-low/long-trend exit" if exit_now else "Breakout position remains open")
            if len(market_data) <= self.config.entry_sessions:
                return signal(SignalAction.HOLD, "Entry-channel warmup unavailable")
            prior_high = float(market_data.iloc[-self.config.entry_sessions - 1:-1]["high"].max())
            buy = close > prior_high and close > slow
            return signal(SignalAction.BUY if buy else SignalAction.HOLD, "Prior-high breakout" if buy else "No prior-high breakout")

        if holding:
            exit_now = close < medium or fast < medium
            return signal(SignalAction.SELL if exit_now else SignalAction.HOLD, "Trend reversal" if exit_now else "Trend position remains open")
        buy = close > slow and fast > medium and rsi >= 50
        if self.config.style == "no_volume":
            buy = buy and rsi <= 70
        else:
            buy = buy and medium > slow
        return signal(SignalAction.BUY if buy else SignalAction.HOLD, "Price-only trend entry" if buy else "Price-only trend conditions not met")

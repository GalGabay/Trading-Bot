"""Causal stop rules for offline daily-bar research only.

A daily OHLC bar cannot reveal quote depth or the exact execution sequence.
These helpers model a stop-market proxy, never a guaranteed stop fill.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


def _positive_finite(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if isfinite(number) and number > 0 else None


@dataclass(frozen=True)
class ProtectiveExitConfig:
    """One fixed ATR trailing-stop design and its planned-risk ceiling."""

    atr_multiple: float = 2.0
    max_risk_per_trade: float = 0.01
    extra_stop_slippage_bps: float = 0.0
    trailing: bool = True
    trailing_atr_multiple: float | None = None

    def __post_init__(self) -> None:
        for name in ("atr_multiple", "max_risk_per_trade", "extra_stop_slippage_bps"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if self.atr_multiple <= 0:
            raise ValueError("atr_multiple must be positive")
        if not 0 < self.max_risk_per_trade <= 1:
            raise ValueError("max_risk_per_trade must be a fraction in (0, 1]")
        if self.extra_stop_slippage_bps < 0:
            raise ValueError("extra_stop_slippage_bps cannot be negative")
        if type(self.trailing) is not bool:
            raise ValueError("trailing must be a boolean")
        if self.trailing_atr_multiple is not None and _positive_finite(self.trailing_atr_multiple) is None:
            raise ValueError("trailing_atr_multiple must be finite and positive")


def initial_stop(close: float, atr: float, config: ProtectiveExitConfig) -> float | None:
    """Use only completed signal-bar values; reject unavailable/invalid ATR."""
    close_value = _positive_finite(close)
    atr_value = _positive_finite(atr)
    if close_value is None or atr_value is None:
        return None
    stop = close_value - config.atr_multiple * atr_value
    return stop if 0 < stop < close_value else None


def raised_stop(previous: float, close: float, atr: float, config: ProtectiveExitConfig) -> float:
    """Ratchet after a completed session; unavailable ATR leaves order level unchanged."""
    previous_value = _positive_finite(previous)
    if previous_value is None:
        raise ValueError("previous stop must be finite and positive")
    if not config.trailing:
        return previous_value
    close_value, atr_value = _positive_finite(close), _positive_finite(atr)
    if close_value is None or atr_value is None:
        return previous_value
    proposed = close_value - (config.trailing_atr_multiple or config.atr_multiple) * atr_value
    if proposed <= 0:
        return previous_value
    return max(previous_value, proposed) if proposed is not None else previous_value


def stop_reference(open_price: float, low: float, stop: float) -> tuple[float, bool] | None:
    """Return modeled sell reference and whether the open gapped below stop."""
    if open_price <= stop:
        return open_price, open_price < stop
    if low <= stop:
        return stop, False
    return None

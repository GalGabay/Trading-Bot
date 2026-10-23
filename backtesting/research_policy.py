"""Research-only allocation and halt policies; no broker or kill-switch I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite


@dataclass(frozen=True)
class AllocationPolicy:
    annualized_risk_contribution: float | None = None

    def __post_init__(self) -> None:
        value = self.annualized_risk_contribution
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value <= 0):
            raise ValueError("annualized_risk_contribution must be finite and positive")

    def fraction(self, maximum: float, annualized_volatility: float) -> float | None:
        """Use a completed-bar volatility estimate, with no leverage or fallback."""
        if self.annualized_risk_contribution is None:
            return maximum
        if not isfinite(annualized_volatility) or annualized_volatility <= 0:
            return None
        return min(maximum, self.annualized_risk_contribution / annualized_volatility)


@dataclass(frozen=True)
class HaltPolicy:
    """None keeps a daily halt latched; an integer enables offline review."""

    daily_pause_sessions: int | None = None

    def __post_init__(self) -> None:
        if self.daily_pause_sessions is not None and (
            type(self.daily_pause_sessions) is not int or self.daily_pause_sessions < 1
        ):
            raise ValueError("daily_pause_sessions must be a positive integer or None")


@dataclass
class ResearchHaltState:
    policy: HaltPolicy
    daily_limit: float
    drawdown_limit: float
    first_halted_at: str | None = None
    permanent_reason: str | None = None
    pause_until_index: int | None = None
    last_daily_breach_index: int | None = None
    blocked_at_open: int = 0
    events: list[dict] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.permanent_reason is not None or self.pause_until_index is not None

    def observe(
        self, *, index: int, timestamp: str, phase: str, equity: float,
        previous_close: float, peak: float, review_ready: bool = False,
    ) -> tuple[dict, ...]:
        """Check loss before an open-only restart; a drawdown never resets."""
        if self.permanent_reason is not None:
            return ()
        event = None
        # Compare dollar equity with the threshold directly. Subtracting 1
        # from a ratio can turn exactly 10% into 9.999999999999998%.
        if equity <= peak * (1 - self.drawdown_limit):
            self.permanent_reason = "maximum drawdown reached"
            self.pause_until_index = None
            event = {"kind": "drawdown_halt", "reason": self.permanent_reason}
        elif equity <= previous_close * (1 - self.daily_limit):
            if self.policy.daily_pause_sessions is None:
                self.permanent_reason = "daily loss limit reached"
            else:
                self.pause_until_index = index + self.policy.daily_pause_sessions
            if self.last_daily_breach_index != index:
                self.last_daily_breach_index = index
                event = {"kind": "daily_halt", "reason": "daily loss limit reached"}
        elif (phase == "open" and self.pause_until_index is not None
              and index > self.pause_until_index and review_ready):
            self.pause_until_index = None
            event = {"kind": "restart", "reason": "research prior-session market review passed"}
        if event is None:
            return ()
        event.update({"timestamp": timestamp, "session_index": index, "phase": phase,
                      "equity": equity, "previous_close": previous_close, "peak": peak,
                      "pause_through_session_index": self.pause_until_index})
        if event["kind"] != "restart" and self.first_halted_at is None:
            self.first_halted_at = timestamp
        self.events.append(event)
        return (event,)

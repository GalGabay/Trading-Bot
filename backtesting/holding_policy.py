"""Causal, research-only holding-age exits; no probability forecasts."""

from dataclasses import dataclass
from math import isfinite

import pandas as pd


@dataclass(frozen=True)
class HoldingEntry:
    session_index: int
    quantity: int
    cost_basis: float  # Actual entry notional plus commission.


@dataclass(frozen=True)
class HoldingPolicy:
    mode: str
    first_review: int = 30
    early_interval: int = 5
    extended_from: int = 60
    extended_interval: int = 30

    def __post_init__(self):
        if self.mode not in {"maximum", "continuation"}:
            raise ValueError("Unknown holding-age policy")
        for name in ("first_review", "early_interval", "extended_from", "extended_interval"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive session count")
        if self.extended_from < self.first_review:
            raise ValueError("Extended review cannot precede the first review")

    def due(self, age):
        if age < self.first_review:
            return False
        if self.mode == "maximum":
            return True
        if age < self.extended_from:
            return (age - self.first_review) % self.early_interval == 0
        return (age - self.extended_from) % self.extended_interval == 0

    def review(self, history, entry, index, *, market_on, sale_multiplier, sale_commission):
        """Inspect a completed prefix only; entry-fill session is age one.

        Continuation requires a fresh prior-20-session high, estimated net
        liquidation profit, and stock/SPY EMA200 filters. Beyond age 60,
        successful reviews continue every 30 sessions without a hard maximum.
        Ordinary exits and protective stops always remain active.
        """
        age = index - entry.session_index + 1
        if not self.due(age):
            return None
        if history.empty or not history["timestamp"].is_monotonic_increasing:
            raise ValueError("Holding review requires ordered completed history")
        row = history.iloc[-1]
        gates = {}
        if self.mode == "continuation":
            close, ema = float(row["close"]), float(row["ema_200"])
            high_values = history.iloc[-21:-1]["high"]
            gates = {
                "fresh_20_session_high": len(high_values) == 20 and high_values.notna().all() and close > float(high_values.max()),
                "positive_estimated_net_profit": isfinite(close) and entry.quantity * close * (1 - sale_multiplier) - sale_commission > entry.cost_basis,
                "stock_above_ema200": isfinite(close) and isfinite(ema) and close > ema,
                "market_above_ema200": bool(market_on),
            }
        retain = self.mode == "continuation" and all(gates.values())
        return {"timestamp": pd.Timestamp(row["timestamp"]).isoformat(), "symbol": str(row["symbol"]),
                "age_sessions": age, "decision": "retain" if retain else "exit",
                "gates": {name: bool(value) for name, value in gates.items()},
                "reason": ("HOLDING_CONTINUATION_CONFIRMED" if retain else "HOLDING_REVIEW_FAILED") if self.mode == "continuation" else f"HOLDING_MAXIMUM_{self.first_review}"}

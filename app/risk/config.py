"""Load explicitly accepted paper-trading limits from a local JSON file."""

from __future__ import annotations

import json
from pathlib import Path

from app.risk.risk_manager import RiskLimits


REQUIRED_LIMITS = frozenset({
    "max_portfolio_exposure", "max_single_position", "max_risk_per_trade",
    "max_daily_loss", "max_drawdown", "max_positions",
    "max_snapshot_age_seconds", "max_signal_age_seconds",
})
OPTIONAL_LIMITS = frozenset({"max_sector_exposure", "max_annualized_volatility"})


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate risk configuration key: {key}")
        result[key] = value
    return result


def load_paper_risk_limits(path: str | Path = "config/risk_limits.json") -> RiskLimits:
    """Require explicit approval and every core limit before paper execution.

    Phase 12 must call this loader before enabling paper order submission. A
    Markdown note or provisional Python default is not paper approval.
    """
    with Path(path).open(encoding="utf-8") as file:
        config = json.load(file, object_pairs_hook=_unique_keys)
    if not isinstance(config, dict) or config.get("approved_for_paper") is not True:
        raise ValueError("Paper risk limits must be explicitly approved in config/risk_limits.json")
    missing = REQUIRED_LIMITS - config.keys()
    unknown = config.keys() - REQUIRED_LIMITS - OPTIONAL_LIMITS - {"approved_for_paper"}
    if missing or unknown:
        raise ValueError(f"Risk configuration has missing keys {sorted(missing)} or unknown keys {sorted(unknown)}")
    values = {key: value for key, value in config.items() if key != "approved_for_paper"}
    return RiskLimits(**values)

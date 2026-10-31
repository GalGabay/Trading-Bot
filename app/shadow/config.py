"""Explicit shadow settings, deliberately independent of paper approval."""

from dataclasses import asdict, dataclass
import hashlib
import json
from math import isfinite
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config/shadow_observer.json"


def utc(value):
    import pandas as pd
    result = pd.Timestamp(value)
    if pd.isna(result) or result.tzinfo is None:
        raise ValueError("Shadow timestamps must be valid and timezone-aware")
    return result.tz_convert("UTC")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique)


def symbol(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Z][A-Z0-9.]{0,11}", value):
        raise ValueError("Watchlist symbols must be explicit uppercase stock symbols")
    return value


@dataclass(frozen=True)
class ShadowConfig:
    symbols: tuple[str, ...]
    history_start: str = "2026-01-01"
    reference_cash: float = 10000.0
    target_exposure: float = 0.70
    entry_ceiling: float = 0.85
    position_cap: float = 0.05
    planned_stop_risk: float = 0.005
    volatility_contribution: float = 0.01
    max_positions: int = 20
    close_settle_minutes: int = 15

    def __post_init__(self):
        import datetime
        if not isinstance(self.symbols, tuple) or not self.symbols or len(self.symbols) > 50 or len(set(self.symbols)) != len(self.symbols):
            raise ValueError("Shadow watchlist requires 1-50 unique symbols")
        for value in self.symbols:
            symbol(value)
        if "SPY" in self.symbols:
            raise ValueError("SPY is market context, not an allocation candidate")
        if not isinstance(self.history_start, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", self.history_start):
            raise ValueError("history_start must be an explicit YYYY-MM-DD date")
        if datetime.date.fromisoformat(self.history_start) < datetime.date(2026, 1, 1):
            raise ValueError("Shadow warmup must not access the reserved 2024-2025 history")
        if isinstance(self.reference_cash, bool) or not isinstance(self.reference_cash, (int, float)) or not isfinite(self.reference_cash) or self.reference_cash <= 0:
            raise ValueError("Reference cash must be positive and finite")
        for name in ("target_exposure", "entry_ceiling", "position_cap", "planned_stop_risk", "volatility_contribution"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not isfinite(value) or not 0 < value <= 1:
                raise ValueError(f"{name} must be a finite fraction in (0, 1]")
        if not self.position_cap <= self.target_exposure <= self.entry_ceiling:
            raise ValueError("Require position cap <= target <= entry ceiling")
        if type(self.max_positions) is not int or not 1 <= self.max_positions <= 50:
            raise ValueError("max_positions must be an integer from 1 to 50")
        if type(self.close_settle_minutes) is not int or not 0 <= self.close_settle_minutes <= 120:
            raise ValueError("close_settle_minutes must be an integer from 0 to 120")

    def record(self):
        return asdict(self)


def load_config(path=DEFAULT_CONFIG):
    raw = read_json(path)
    if not isinstance(raw, dict) or set(raw) - set(ShadowConfig.__dataclass_fields__):
        raise ValueError("Shadow config contains unsupported fields; it cannot enable orders")
    if not isinstance(raw.get("symbols"), list):
        raise ValueError("Shadow symbols must be a JSON array")
    raw["symbols"] = tuple(raw["symbols"])
    return ShadowConfig(**raw)


def implementation():
    paths = ["app/shadow/config.py", "app/shadow/data.py", "app/shadow/observer.py",
             "app/shadow/store.py", "app/ai/features.py", "app/data/market_data.py",
             "app/data/market_calendar.py", "app/strategy/base.py", "backtesting/daily_strategies.py",
             "backtesting/holding_policy.py", "backtesting/research_policy.py", "app/broker/alpaca_client.py"]
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths}

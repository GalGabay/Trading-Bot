"""Deterministic trading strategies and their common contract."""

from app.strategy.base import Signal, SignalAction, Strategy
from app.strategy.strategy_v1 import TrendFollowingV1, TrendFollowingV1Config

__all__ = ["Signal", "SignalAction", "Strategy", "TrendFollowingV1", "TrendFollowingV1Config"]

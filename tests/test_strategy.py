from __future__ import annotations

from datetime import UTC
from unittest import TestCase

import pandas as pd

from app.strategy import SignalAction, Strategy, TrendFollowingV1, TrendFollowingV1Config


def feature_rows(**overrides: object) -> pd.DataFrame:
    row: dict[str, object] = {
        "timestamp": pd.Timestamp("2026-01-02T16:00:00Z"), "symbol": "AAPL",
        "close": 210.0, "ema_20": 205.0, "ema_50": 200.0, "ema_200": 190.0,
        "rsi_14": 60.0, "volume_ratio_20": 1.2,
    }
    row.update(overrides)
    return pd.DataFrame([row])


class TrendFollowingV1Tests(TestCase):
    def setUp(self) -> None:
        self.strategy = TrendFollowingV1()

    def test_strategy_implements_the_shared_contract(self) -> None:
        self.assertIsInstance(self.strategy, Strategy)

    def test_all_rules_produce_an_explainable_buy_signal(self) -> None:
        signal = self.strategy.generate_signal(feature_rows())
        self.assertEqual(signal.action, SignalAction.BUY)
        self.assertEqual(signal.confidence, 1.0)
        self.assertEqual(signal.symbol, "AAPL")
        self.assertEqual(signal.timestamp.tzinfo, UTC)
        self.assertIn("EMA20 > EMA50", signal.reason)

    def test_each_failed_rule_produces_hold_with_reason(self) -> None:
        cases = [
            ({"close": 180.0}, "close is not above EMA200"),
            ({"ema_20": 199.0}, "EMA20 is not above EMA50"),
            ({"rsi_14": 75.0}, "RSI14 is outside"),
            ({"volume_ratio_20": 1.0}, "volume ratio is not above"),
        ]
        for overrides, explanation in cases:
            with self.subTest(overrides=overrides):
                signal = self.strategy.generate_signal(feature_rows(**overrides))
                self.assertEqual(signal.action, SignalAction.HOLD)
                self.assertIn(explanation, signal.reason)

    def test_warmup_nan_returns_hold_not_an_unsafe_signal(self) -> None:
        signal = self.strategy.generate_signal(feature_rows(ema_200=float("nan")))
        self.assertEqual(signal.action, SignalAction.HOLD)
        self.assertEqual(signal.confidence, 0.0)
        self.assertIn("warm-up data unavailable", signal.reason)

    def test_evaluates_the_latest_completed_feature_row(self) -> None:
        older = feature_rows(timestamp=pd.Timestamp("2026-01-02T15:00:00Z"))
        latest = feature_rows(timestamp=pd.Timestamp("2026-01-02T16:00:00Z"), rsi_14=80.0)
        signal = self.strategy.generate_signal(pd.concat([latest, older], ignore_index=True))
        self.assertEqual(signal.action, SignalAction.HOLD)
        self.assertEqual(signal.timestamp, pd.Timestamp("2026-01-02T16:00:00Z").to_pydatetime())

    def test_rejects_missing_or_mixed_symbol_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing required"):
            self.strategy.generate_signal(feature_rows().drop(columns=["rsi_14"]))
        mixed = pd.concat([feature_rows(), feature_rows(symbol="MSFT")], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "exactly one symbol"):
            self.strategy.generate_signal(mixed)

    def test_thresholds_are_configurable(self) -> None:
        strict = TrendFollowingV1(config=TrendFollowingV1Config(minimum_volume_ratio=1.5))
        signal = strict.generate_signal(feature_rows())
        self.assertEqual(signal.action, SignalAction.HOLD)

from __future__ import annotations

from unittest import TestCase

import numpy as np
import pandas as pd

from app.ai.features import FEATURE_VERSION, build_features


def trend_candles(symbol: str = "AAPL", count: int = 220) -> pd.DataFrame:
    timestamps = pd.date_range("2025-01-01T15:00:00Z", periods=count, freq="h")
    close = pd.Series(np.arange(100.0, 100.0 + count))
    return pd.DataFrame({
        "timestamp": timestamps, "symbol": [symbol] * count,
        "open": close - 0.5, "high": close + 1.0, "low": close - 1.0,
        "close": close, "volume": np.arange(1_000, 1_000 + count),
    })


class FeatureEngineeringTests(TestCase):
    def test_features_include_requested_explainable_indicators(self) -> None:
        features = build_features(trend_candles())
        expected = {
            "ema_20", "ema_50", "ema_200", "macd", "macd_signal", "macd_histogram",
            "adx_14", "rsi_14", "roc_10", "stochastic_k_14", "atr_14",
            "bollinger_upper_20", "bollinger_middle_20", "bollinger_lower_20",
            "historical_volatility_20", "volume_sma_20", "volume_ratio_20", "obv",
            "return_1", "return_5", "return_20", "distance_from_ema20",
            "distance_from_ema50", "distance_from_ema200",
        }
        self.assertTrue(expected.issubset(features.columns))
        self.assertTrue(pd.isna(features.loc[0, "ema_20"]))
        self.assertFalse(pd.isna(features.loc[199, "ema_200"]))
        self.assertGreater(features.loc[219, "return_1"], 0)

    def test_future_candle_cannot_change_prior_features(self) -> None:
        original = trend_candles()
        baseline = build_features(original)
        changed = original.copy()
        changed.loc[len(changed) - 1, ["open", "high", "low", "close", "volume"]] = [9_999, 10_000, 9_998, 9_999, 999_999]
        revised = build_features(changed)
        pd.testing.assert_frame_equal(
            baseline.iloc[:-1].reset_index(drop=True), revised.iloc[:-1].reset_index(drop=True), check_exact=True
        )

    def test_each_symbol_has_independent_indicator_history(self) -> None:
        aapl = trend_candles("AAPL", 25)
        msft = trend_candles("MSFT", 25)
        msft["close"] = 200.0
        msft["open"] = 199.5
        msft["high"] = 201.0
        msft["low"] = 199.0
        features = build_features(pd.concat([aapl, msft], ignore_index=True))
        first_msft = features.loc[features["symbol"] == "MSFT"].iloc[0]
        self.assertTrue(pd.isna(first_msft["ema_20"]))
        self.assertEqual(first_msft["obv"], 0.0)

    def test_feature_calculation_does_not_modify_input_or_fill_warmup_values(self) -> None:
        candles = trend_candles(count=30)
        original = candles.copy(deep=True)
        features = build_features(candles)
        pd.testing.assert_frame_equal(candles, original)
        self.assertTrue(features["ema_200"].isna().all())
        self.assertTrue(features["return_20"].iloc[:20].isna().all())

    def test_feature_version_is_explicit(self) -> None:
        self.assertEqual(FEATURE_VERSION, "technical_v1")

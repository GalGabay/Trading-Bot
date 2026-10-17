"""Causal, single-symbol supervised dataset for offline Phase 14 research."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import numpy as np
import pandas as pd

from app.ai.features import FeatureConfig, build_features


ML_FEATURES: tuple[str, ...] = (
    "rsi_14", "distance_from_ema20", "distance_from_ema50",
    "distance_from_ema200", "atr_14", "adx_14", "macd_histogram",
    "historical_volatility_20", "volume_ratio_20", "roc_10",
    "return_1", "return_5", "return_20",
)


@dataclass(frozen=True)
class TargetDefinition:
    """Close-to-close return strictly above a threshold after N observed bars.

    Five bars means five completed bars, not five sessions. The defaults are
    provisional research settings, not a promised return or trading policy.
    """

    horizon_bars: int = 5
    return_threshold: float = 0.005

    def __post_init__(self) -> None:
        if type(self.horizon_bars) is not int or self.horizon_bars < 1:
            raise ValueError("horizon_bars must be a positive integer")
        if not isfinite(self.return_threshold) or self.return_threshold <= -1:
            raise ValueError("return_threshold must be finite and greater than -1")


def build_ml_dataset(
    candles: pd.DataFrame, *, target: TargetDefinition | None = None,
    feature_config: FeatureConfig | None = None,
) -> pd.DataFrame:
    """Return completed feature rows and future labels, without filling data.

    Candle coverage must already have passed the downloader's market-calendar
    review. Labels use only future closes; every feature is computed separately
    per symbol from candles available no later than its own timestamp. Rows
    with indicator warm-up gaps or an unavailable future endpoint are removed.
    """
    target = target or TargetDefinition()
    frame = build_features(candles, config=feature_config)
    if frame["symbol"].nunique() != 1:
        raise ValueError("The Phase 14 prototype requires exactly one symbol")
    frame = frame.sort_values(["symbol", "timestamp"], ignore_index=True)
    future_close = frame.groupby("symbol", sort=False)["close"].shift(-target.horizon_bars)
    frame["label_end_timestamp"] = frame.groupby("symbol", sort=False)["timestamp"].shift(-target.horizon_bars)
    frame["future_return"] = future_close / frame["close"] - 1
    values = frame.loc[:, list(ML_FEATURES)].to_numpy(dtype=float)
    valid_features = np.isfinite(values).all(axis=1)
    valid_target = frame["label_end_timestamp"].notna() & np.isfinite(frame["future_return"].to_numpy(dtype=float))
    frame = frame.loc[valid_features & valid_target].copy()
    if frame.empty:
        raise ValueError("No labeled rows remain after feature warm-up and target construction")
    frame["target"] = (frame["future_return"] > target.return_threshold).astype(int)
    return frame.loc[:, ["timestamp", "symbol", *ML_FEATURES, "label_end_timestamp", "future_return", "target"]].reset_index(drop=True)

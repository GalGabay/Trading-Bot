"""Portable XGBoost research artifact and rule-signal filter; never trades."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from app.ai.features import FEATURE_VERSION
from app.ai.ml_dataset import ML_FEATURES
from app.strategy.base import Signal, SignalAction, Strategy


def _xgboost():
    try:
        import xgboost as xgb
    except ImportError as exc:
        raise RuntimeError("Phase 14 ML requires the optional requirements-ml.txt dependencies") from exc
    return xgb


@dataclass(frozen=True)
class ResearchModel:
    """Read-only model with explicit schema and sigmoid calibration metadata."""

    booster: Any
    metadata: Mapping[str, Any]

    @classmethod
    def load(cls, directory: str | Path) -> ResearchModel:
        directory = Path(directory)
        metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
        model_path = directory / "model.json"
        if metadata.get("model_sha256") != hashlib.sha256(model_path.read_bytes()).hexdigest():
            raise ValueError("ML model checksum does not match its metadata")
        if metadata.get("feature_version") != FEATURE_VERSION or metadata.get("features") != list(ML_FEATURES):
            raise ValueError("ML model feature schema differs from the current feature code")
        if metadata.get("research_only") is not True or metadata.get("model_family") != "xgboost_binary_classifier":
            raise ValueError("Unknown or nonresearch ML model metadata")
        booster = _xgboost().Booster()
        booster.load_model(str(model_path))
        if booster.feature_names != list(ML_FEATURES):
            raise ValueError("ML model's embedded feature names differ from metadata")
        return cls(booster, metadata)

    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        if features.empty:
            raise ValueError("ML input must contain at least one completed feature row")
        if "symbol" in features.columns and set(features["symbol"].astype(str).str.upper()) != {self.metadata["symbol"]}:
            raise ValueError("ML input symbol differs from the trained research symbol")
        missing = set(ML_FEATURES) - set(features.columns)
        if missing:
            raise ValueError(f"ML input is missing features: {sorted(missing)}")
        matrix = features.loc[:, list(ML_FEATURES)].to_numpy(dtype=float)
        if not np.isfinite(matrix).all():
            raise ValueError("ML input has missing or nonfinite feature values")
        margins = np.asarray(
            self.booster.predict(_xgboost().DMatrix(features.loc[:, list(ML_FEATURES)], feature_names=list(ML_FEATURES)), output_margin=True),
            dtype=float,
        )
        if not np.isfinite(margins).all():
            raise ValueError("ML model produced a nonfinite margin")
        calibration = self.metadata["calibration"]
        if calibration.get("method") != "sigmoid_on_raw_margin":
            raise ValueError("Unknown ML probability calibration method")
        slope, intercept = float(calibration["slope"]), float(calibration["intercept"])
        if not isfinite(slope) or not isfinite(intercept):
            raise ValueError("Invalid ML probability calibration parameters")
        z = slope * margins + intercept
        probabilities = np.where(z >= 0, 1 / (1 + np.exp(-np.clip(z, -700, 700))),
                                 np.exp(np.clip(z, -700, 700)) / (1 + np.exp(np.clip(z, -700, 700))))
        if not np.isfinite(probabilities).all():
            raise ValueError("ML model produced an invalid probability")
        return probabilities


class MLFilterStrategy(Strategy):
    """Filter only BUY candidates; preserve the deterministic exit signals.

    Scores are precomputed from completed candles. A missing score blocks an
    entry. This adapter is for offline backtesting, not paper-order execution.
    """

    name = "trend_following_v1_ml_filter"
    latest_row_only = True

    def __init__(self, baseline: Strategy, scores: Mapping[pd.Timestamp, float], *, threshold: float = 0.60) -> None:
        if not isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError("ML filter threshold must be between 0 and 1")
        self.baseline = baseline
        self.scores = scores
        self.threshold = threshold

    def generate_signal(self, market_data: pd.DataFrame, portfolio: Any | None = None) -> Signal:
        signal = self.baseline.generate_signal(market_data, portfolio)
        if signal.action != SignalAction.BUY:
            return signal
        timestamp = pd.Timestamp(signal.timestamp).tz_convert("UTC")
        probability = self.scores.get(timestamp)
        if probability is None or not isfinite(probability) or probability < self.threshold:
            reason = (
                "HOLD: ML research score unavailable" if probability is None or not isfinite(probability)
                else f"HOLD: ML research score {probability:.3f} below {self.threshold:.3f}"
            )
            return Signal(signal.symbol, SignalAction.HOLD, 0.0, reason, signal.timestamp, self.name)
        return Signal(signal.symbol, signal.action, probability,
                      f"{signal.reason} ML research score {probability:.3f}.",
                      signal.timestamp, self.name)

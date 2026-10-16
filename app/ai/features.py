"""Deterministic, past-only technical features for validated candles."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.data.market_data import CANONICAL_CANDLE_COLUMNS, validate_candles

FEATURE_VERSION = "technical_v1"


@dataclass(frozen=True)
class FeatureConfig:
    """Periods used by the initial explainable technical feature set."""

    ema_fast: int = 20
    ema_medium: int = 50
    ema_slow: int = 200
    rsi_period: int = 14
    atr_period: int = 14
    adx_period: int = 14
    stochastic_period: int = 14
    bollinger_period: int = 20
    volume_sma_period: int = 20
    historical_volatility_period: int = 20
    periods_per_year: int = 252


def _wilder(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def _features_for_symbol(candles: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    frame = candles.sort_values("timestamp").copy()
    close, high, low, volume = frame["close"], frame["high"], frame["low"], frame["volume"]

    frame["ema_20"] = close.ewm(span=config.ema_fast, adjust=False, min_periods=config.ema_fast).mean()
    frame["ema_50"] = close.ewm(span=config.ema_medium, adjust=False, min_periods=config.ema_medium).mean()
    frame["ema_200"] = close.ewm(span=config.ema_slow, adjust=False, min_periods=config.ema_slow).mean()
    macd_fast = close.ewm(span=12, adjust=False, min_periods=12).mean()
    macd_slow = close.ewm(span=26, adjust=False, min_periods=26).mean()
    frame["macd"] = macd_fast - macd_slow
    frame["macd_signal"] = frame["macd"].ewm(span=9, adjust=False, min_periods=9).mean()
    frame["macd_histogram"] = frame["macd"] - frame["macd_signal"]

    change = close.diff()
    gains, losses = change.clip(lower=0), -change.clip(upper=0)
    average_gain, average_loss = _wilder(gains, config.rsi_period), _wilder(losses, config.rsi_period)
    relative_strength = average_gain / average_loss
    frame["rsi_14"] = 100 - (100 / (1 + relative_strength))

    frame["roc_10"] = close.pct_change(10, fill_method=None)
    rolling_high = high.rolling(config.stochastic_period, min_periods=config.stochastic_period).max()
    rolling_low = low.rolling(config.stochastic_period, min_periods=config.stochastic_period).min()
    frame["stochastic_k_14"] = 100 * (close - rolling_low) / (rolling_high - rolling_low)

    previous_close = close.shift(1)
    true_range = pd.concat([high - low, (high - previous_close).abs(), (low - previous_close).abs()], axis=1).max(axis=1)
    frame["atr_14"] = _wilder(true_range, config.atr_period)
    upward_move, downward_move = high.diff(), -low.diff()
    plus_dm = upward_move.where((upward_move > downward_move) & (upward_move > 0), 0.0)
    minus_dm = downward_move.where((downward_move > upward_move) & (downward_move > 0), 0.0)
    plus_di = 100 * _wilder(plus_dm, config.adx_period) / frame["atr_14"]
    minus_di = 100 * _wilder(minus_dm, config.adx_period) / frame["atr_14"]
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    frame["adx_14"] = _wilder(dx, config.adx_period)

    middle = close.rolling(config.bollinger_period, min_periods=config.bollinger_period).mean()
    deviation = close.rolling(config.bollinger_period, min_periods=config.bollinger_period).std(ddof=0)
    frame["bollinger_middle_20"] = middle
    frame["bollinger_upper_20"] = middle + 2 * deviation
    frame["bollinger_lower_20"] = middle - 2 * deviation
    returns_1 = close.pct_change(fill_method=None)
    frame["historical_volatility_20"] = (
        returns_1.rolling(config.historical_volatility_period, min_periods=config.historical_volatility_period).std(ddof=0)
        * np.sqrt(config.periods_per_year)
    )

    frame["volume_sma_20"] = volume.rolling(config.volume_sma_period, min_periods=config.volume_sma_period).mean()
    frame["volume_ratio_20"] = volume / frame["volume_sma_20"]
    direction = np.sign(change).fillna(0)
    frame["obv"] = (direction * volume).cumsum()
    frame["return_1"] = returns_1
    frame["return_5"] = close.pct_change(5, fill_method=None)
    frame["return_20"] = close.pct_change(20, fill_method=None)
    frame["distance_from_ema20"] = close / frame["ema_20"] - 1
    frame["distance_from_ema50"] = close / frame["ema_50"] - 1
    frame["distance_from_ema200"] = close / frame["ema_200"] - 1
    return frame


def build_features(candles: pd.DataFrame, *, config: FeatureConfig | None = None) -> pd.DataFrame:
    """Return `technical_v1` features without changing or filling candle data.

    Input must already have passed calendar-aware validation in the market-data
    service. Structural validation runs here again; no operation reads a later
    candle or fills the natural indicator warm-up values.
    """
    config = config or FeatureConfig()
    validate_candles(candles)
    base = candles.loc[:, CANONICAL_CANDLE_COLUMNS].copy()
    base["timestamp"] = pd.to_datetime(base["timestamp"], utc=True)
    base["symbol"] = base["symbol"].astype(str).str.upper().str.strip()
    features = [_features_for_symbol(group, config) for _, group in base.groupby("symbol", sort=False)]
    return pd.concat(features, ignore_index=True).sort_values(["symbol", "timestamp"], ignore_index=True)

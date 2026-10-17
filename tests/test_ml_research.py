"""Offline Phase 14 tests; no Alpaca calls, training downloads, or orders."""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import numpy as np
import pandas as pd

from app.ai.features import FEATURE_VERSION
from app.ai.ml_dataset import ML_FEATURES, TargetDefinition, build_ml_dataset
from app.ai.ml_model import MLFilterStrategy, ResearchModel
from app.data.market_data import CandleValidationError
from app.strategy.base import Signal, SignalAction, Strategy
from backtesting.ml_research import MLWindows, _binary_metrics, _partition, run_ml_research


def candles(count: int = 260, *, symbol: str = "AAPL") -> pd.DataFrame:
    timestamps = pd.date_range("2023-01-02T15:00:00Z", periods=count, freq="B")
    close = 100 + np.arange(count) * 0.04 + 2 * np.sin(np.arange(count) / 3)
    return pd.DataFrame({
        "timestamp": timestamps, "symbol": symbol,
        "open": close - 0.2, "high": close + 1, "low": close - 1,
        "close": close, "volume": 1_000 + (np.arange(count) % 15) * 15,
    })


class DatasetTests(TestCase):
    def test_labels_use_future_close_and_purge_unavailable_tail(self) -> None:
        bars = candles()
        original = bars.copy(deep=True)
        result = build_ml_dataset(bars, target=TargetDefinition(3, 0.005))
        pd.testing.assert_frame_equal(bars, original)
        self.assertFalse(result.empty)
        self.assertEqual(result["label_end_timestamp"].iloc[-1], bars["timestamp"].iloc[-1])
        self.assertEqual(result["timestamp"].iloc[-1], bars["timestamp"].iloc[-4])
        self.assertTrue(np.isfinite(result.loc[:, list(ML_FEATURES)].to_numpy()).all())
        row = result.iloc[0]
        start = bars.loc[bars["timestamp"] == row["timestamp"]].index[0]
        expected = bars["close"].iloc[start + 3] / bars["close"].iloc[start] - 1
        self.assertAlmostEqual(row["future_return"], expected)
        self.assertEqual(row["target"], int(expected > 0.005))

    def test_future_price_changes_label_but_never_earlier_features(self) -> None:
        bars = candles()
        baseline = build_ml_dataset(bars, target=TargetDefinition(3, 0.005))
        revised = bars.copy()
        revised.loc[245, ["open", "high", "low", "close"]] *= 1.10
        changed = build_ml_dataset(revised, target=TargetDefinition(3, 0.005))
        before = baseline.loc[baseline["timestamp"] < bars["timestamp"].iloc[245]]
        after = changed.loc[changed["timestamp"] < bars["timestamp"].iloc[245]]
        pd.testing.assert_frame_equal(
            before.loc[:, list(ML_FEATURES)].reset_index(drop=True),
            after.loc[:, list(ML_FEATURES)].reset_index(drop=True),
        )
        label_time = bars["timestamp"].iloc[242]
        old_target = baseline.loc[baseline["timestamp"] == label_time, "future_return"].iloc[0]
        new_target = changed.loc[changed["timestamp"] == label_time, "future_return"].iloc[0]
        self.assertNotEqual(old_target, new_target)

    def test_invalid_input_and_missing_warmup_are_not_filled(self) -> None:
        with self.assertRaisesRegex(ValueError, "No labeled rows"):
            build_ml_dataset(candles(30))
        bad = candles()
        bad.loc[12, "low"] = -1
        with self.assertRaises(CandleValidationError):
            build_ml_dataset(bad)
        with self.assertRaisesRegex(ValueError, "exactly one symbol"):
            build_ml_dataset(pd.concat([candles(), candles(symbol="MSFT")], ignore_index=True))

    def test_target_definition_rejects_invalid_horizons_and_thresholds(self) -> None:
        for value in (0, -1, 1.5, True):
            with self.subTest(horizon=value), self.assertRaises(ValueError):
                TargetDefinition(horizon_bars=value)
        for value in (-1, float("nan"), float("inf")):
            with self.subTest(threshold=value), self.assertRaises(ValueError):
                TargetDefinition(return_threshold=value)


class WindowTests(TestCase):
    def test_chronological_boundaries_and_purging(self) -> None:
        with self.assertRaisesRegex(ValueError, "strictly chronological"):
            MLWindows("2021-01-01", "2020-01-01", "2022-01-01", "2023-01-01", "2024-01-01")
        frame = pd.DataFrame({
            "timestamp": pd.to_datetime(["2020-12-28T15:00Z", "2020-12-31T15:00Z", "2021-01-04T15:00Z"]),
            "label_end_timestamp": pd.to_datetime(["2020-12-30T15:00Z", "2021-01-04T15:00Z", "2021-01-05T15:00Z"]),
        })
        result = _partition(frame, "2020-01-01", "2021-01-01")
        self.assertEqual(result["timestamp"].tolist(), [frame["timestamp"].iloc[0]])
        with self.assertRaisesRegex(ValueError, "No complete labeled"):
            _partition(frame, "2019-01-01", "2020-01-01")

    def test_metrics_handle_one_class_without_claiming_auc(self) -> None:
        report = _binary_metrics(np.array([0, 0]), np.array([0.2, 0.3]))
        self.assertIsNone(report["roc_auc"])
        self.assertGreater(report["log_loss"], 0)


class StaticStrategy(Strategy):
    name = "test_rule"
    latest_row_only = True

    def __init__(self, action: SignalAction) -> None:
        self.action = action

    def generate_signal(self, market_data: pd.DataFrame, portfolio=None) -> Signal:
        row = market_data.iloc[-1]
        return Signal("AAPL", self.action, 1.0, "rule decision", row["timestamp"].to_pydatetime(), self.name)


class FilterTests(TestCase):
    def setUp(self) -> None:
        self.timestamp = pd.Timestamp("2024-01-02T15:00:00Z")
        self.row = pd.DataFrame({"timestamp": [self.timestamp], "symbol": ["AAPL"]})

    def test_only_buy_candidates_are_filtered(self) -> None:
        high = MLFilterStrategy(StaticStrategy(SignalAction.BUY), {self.timestamp: 0.8})
        self.assertEqual(high.generate_signal(self.row).action, SignalAction.BUY)
        low = MLFilterStrategy(StaticStrategy(SignalAction.BUY), {self.timestamp: 0.2})
        self.assertEqual(low.generate_signal(self.row).action, SignalAction.HOLD)
        missing = MLFilterStrategy(StaticStrategy(SignalAction.BUY), {})
        self.assertEqual(missing.generate_signal(self.row).action, SignalAction.HOLD)
        sell = MLFilterStrategy(StaticStrategy(SignalAction.SELL), {})
        self.assertEqual(sell.generate_signal(self.row).action, SignalAction.SELL)

    def test_nonfinite_score_blocks_buy_and_invalid_threshold_is_rejected(self) -> None:
        strategy = MLFilterStrategy(StaticStrategy(SignalAction.BUY), {self.timestamp: float("nan")})
        self.assertEqual(strategy.generate_signal(self.row).action, SignalAction.HOLD)
        for value in (-0.1, 1.1, float("nan")):
            with self.subTest(threshold=value), self.assertRaises(ValueError):
                MLFilterStrategy(StaticStrategy(SignalAction.BUY), {}, threshold=value)


class FakeBooster:
    feature_names = list(ML_FEATURES)

    def __init__(self, margins: list[float] | None = None) -> None:
        self.margins = margins or [-2.0, 2.0]

    def predict(self, matrix, *, output_margin: bool = False):
        return np.asarray(self.margins[:len(matrix)])

    def load_model(self, path: str) -> None:
        Path(path).read_bytes()


class FakeXGB:
    Booster = FakeBooster

    @staticmethod
    def DMatrix(frame, *, feature_names):
        return frame


class ModelTests(TestCase):
    def setUp(self) -> None:
        self.rows = pd.DataFrame({name: [0.1, 0.2] for name in ML_FEATURES})
        self.rows["symbol"] = "AAPL"
        self.metadata = {
            "symbol": "AAPL", "calibration": {"method": "sigmoid_on_raw_margin", "slope": 1.0, "intercept": 0.0},
        }

    def test_calibration_and_input_schema(self) -> None:
        model = ResearchModel(FakeBooster(), self.metadata)
        with patch("app.ai.ml_model._xgboost", return_value=FakeXGB):
            scores = model.predict_proba(self.rows)
            self.assertLess(scores[0], 0.5)
            self.assertGreater(scores[1], 0.5)
            with self.assertRaisesRegex(ValueError, "missing features"):
                model.predict_proba(self.rows.drop(columns=[ML_FEATURES[0]]))
            with self.assertRaisesRegex(ValueError, "symbol differs"):
                model.predict_proba(self.rows.assign(symbol="MSFT"))
            with self.assertRaisesRegex(ValueError, "nonfinite feature"):
                model.predict_proba(self.rows.assign(**{ML_FEATURES[0]: np.nan}))

    def test_model_load_checks_checksum_and_feature_version(self) -> None:
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            model_path = directory / "model.json"
            model_path.write_bytes(b"fake portable model")
            metadata = {
                "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
                "feature_version": FEATURE_VERSION, "features": list(ML_FEATURES),
                "model_family": "xgboost_binary_classifier", "research_only": True,
            }
            (directory / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            with patch("app.ai.ml_model._xgboost", return_value=FakeXGB):
                self.assertEqual(ResearchModel.load(directory).booster.feature_names, list(ML_FEATURES))
            model_path.write_bytes(b"tampered model")
            with self.assertRaisesRegex(ValueError, "checksum"):
                ResearchModel.load(directory)
            metadata["model_sha256"] = hashlib.sha256(model_path.read_bytes()).hexdigest()
            metadata["feature_version"] = "future_version"
            (directory / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "schema"):
                ResearchModel.load(directory)


class PipelineTests(TestCase):
    def test_runner_keeps_final_test_out_of_training_and_compares_same_costs(self) -> None:
        timestamps = pd.to_datetime([
            f"{year}-01-{day:02d}T15:00:00Z"
            for year in (2019, 2020, 2021, 2022) for day in range(2, 8)
        ])
        sample = pd.DataFrame({name: np.tile([0.1, 0.9, 0.2, 0.8, 0.3, 0.7], 4) for name in ML_FEATURES})
        sample["timestamp"] = timestamps
        sample["symbol"] = "AAPL"
        sample["label_end_timestamp"] = sample["timestamp"] + timedelta(days=1)
        sample["target"] = np.tile([0, 1, 0, 1, 0, 1], 4)
        sample["future_return"] = np.where(sample["target"] == 1, 0.01, -0.01)
        manifest = {
            "start_utc": "2019-01-01", "end_exclusive_utc": "2023-01-01",
            "timeframe": "15Min", "symbol": "AAPL", "sha256": "sample",
            "feed": "sip", "adjustment": "all", "universe_scope": "single_symbol_case_study",
        }
        training_labels = []
        comparisons = []

        class Matrix:
            def __init__(self, frame, *, feature_names, label=None):
                self.frame = frame
                self.label = label

        class Trained:
            def predict(self, matrix, *, output_margin=False):
                return np.asarray(matrix.frame[ML_FEATURES[0]], dtype=float) * 2 - 1 if output_margin else np.asarray(matrix.frame[ML_FEATURES[0]], dtype=float)

            def save_model(self, path):
                Path(path).write_bytes(b"fake model")

        class Trainer:
            DMatrix = Matrix

            @staticmethod
            def train(parameters, matrix, *, num_boost_round):
                training_labels.append(matrix.label.copy())
                return Trained()

        class Model:
            @staticmethod
            def predict_proba(frame):
                return np.asarray(frame[ML_FEATURES[0]], dtype=float)

        class Engine:
            def __init__(self, strategy, *, config):
                self.strategy = strategy
                self.config = config

            def run(self, bars, *, trade_start, trade_end):
                comparisons.append((self.strategy.name, self.config.slippage_bps, trade_start.year, trade_end.year))
                return SimpleNamespace()

        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "experiment"
            with (
                patch("backtesting.ml_research.load_dataset", return_value=(sample[["timestamp", "symbol"]], manifest)),
                patch("backtesting.ml_research.build_ml_dataset", return_value=sample),
                patch("backtesting.ml_research.build_features", return_value=sample),
                patch("backtesting.ml_research._xgboost", return_value=Trainer),
                patch("backtesting.ml_research.ResearchModel.load", return_value=Model()),
                patch("backtesting.ml_research.BacktestEngine", Engine),
                patch("backtesting.ml_research._strategy_metrics", return_value={"metrics": {"total_return": 0.01}}),
                patch("backtesting.ml_research.version", return_value="test-version"),
            ):
                report = run_ml_research(
                    Path("unused.csv"), artifact_dir=directory,
                    windows=MLWindows("2019-01-01", "2020-01-01", "2021-01-01", "2022-01-01", "2023-01-01"),
                )
            self.assertEqual(report["rows"], {"train": 6, "tune": 6, "calibration": 6, "test": 6})
            self.assertEqual(len(training_labels), 4)
            self.assertTrue(all(len(labels) == 6 for labels in training_labels))
            self.assertEqual(len(comparisons), 6)
            self.assertEqual(set(report["strategy_comparison"]), {"optimistic", "base", "pessimistic"})
            self.assertTrue(all(start == 2022 and end == 2023 for _, _, start, end in comparisons))
            self.assertTrue(report["research_only"])
            self.assertFalse(report["paper_submission_enabled"])
            self.assertTrue((directory / "metadata.json").exists())
            self.assertTrue((directory / "report.json").exists())
            with self.assertRaises(FileExistsError):
                run_ml_research(Path("unused.csv"), artifact_dir=directory,
                                windows=MLWindows("2019-01-01", "2020-01-01", "2021-01-01", "2022-01-01", "2023-01-01"))

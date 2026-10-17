"""Offline Phase 14 XGBoost research; no broker or order APIs are used.

Run ``python -m backtesting.ml_research --help``. All four period boundaries
must be stated before training. The final test period is evaluated once; reruns
or parameter changes after reading its results make it exploratory research.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

from app.ai.features import FEATURE_VERSION, FeatureConfig, build_features
from app.ai.ml_dataset import ML_FEATURES, TargetDefinition, build_ml_dataset
from app.ai.ml_model import MLFilterStrategy, ResearchModel, _xgboost
from app.strategy.strategy_v1 import TrendFollowingV1, TrendFollowingV1Config
from backtesting.engine import BacktestEngine, BacktestResult
from backtesting.metrics import calculate_metrics
from backtesting.research import COST_SCENARIOS, PERIODS_PER_YEAR, _utc_date, load_dataset


@dataclass(frozen=True)
class MLWindows:
    train_start: str
    tune_start: str
    calibration_start: str
    test_start: str
    test_end: str

    def __post_init__(self) -> None:
        dates = [_utc_date(value) for value in asdict(self).values()]
        if dates != sorted(set(dates)):
            raise ValueError("ML boundaries must be distinct and strictly chronological")


def _partition(frame: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Purge labels whose future endpoint crosses the next window boundary."""
    first, last = pd.Timestamp(_utc_date(start)), pd.Timestamp(_utc_date(end))
    part = frame.loc[
        (frame["timestamp"] >= first)
        & (frame["timestamp"] < last)
        & (frame["label_end_timestamp"] < last)
    ].copy()
    if part.empty:
        raise ValueError(f"No complete labeled ML rows in {start} to {end}; check warm-up and horizon")
    return part


def _binary_metrics(labels: np.ndarray, probabilities: np.ndarray) -> dict[str, float | None]:
    from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

    return {
        "log_loss": float(log_loss(labels, probabilities, labels=[0, 1])),
        "brier_score": float(brier_score_loss(labels, probabilities)),
        "roc_auc": float(roc_auc_score(labels, probabilities)) if len(np.unique(labels)) == 2 else None,
        "positive_rate": float(np.mean(labels)),
        "mean_prediction": float(np.mean(probabilities)),
    }


def _strategy_metrics(result: BacktestResult, periods_per_year: int) -> dict[str, object]:
    """Add turnover and month-to-month variation to the existing net metrics."""
    equity = pd.Series(
        [point.equity for point in result.equity_curve],
        index=pd.DatetimeIndex([point.timestamp for point in result.equity_curve]),
    )
    month_ends = equity.resample("ME").last().dropna()
    month_values = month_ends.to_numpy(dtype=float)
    month_returns = month_values / np.r_[result.config.initial_cash, month_values[:-1]] - 1
    return {
        "metrics": asdict(calculate_metrics(result, periods_per_year=periods_per_year)),
        "fill_count": len(result.fills),
        "turnover_notional_over_initial_equity": float(
            sum(fill.quantity * fill.fill_price for fill in result.fills) / result.config.initial_cash
        ),
        "positive_month_fraction": float((month_returns > 0).mean()),
        "monthly_return_std": float(month_returns.std(ddof=1)) if len(month_returns) > 1 else None,
    }


def run_ml_research(
    dataset_path: Path, *, windows: MLWindows, artifact_dir: Path,
    target: TargetDefinition | None = None, filter_threshold: float = 0.60,
) -> dict[str, object]:
    """Train, calibrate, and compare a fixed rule baseline against an ML filter.

    This is a single-symbol research artifact. It never writes a trading config,
    enables order submission, or selects a model for deployment automatically.
    """
    if artifact_dir.exists():
        raise FileExistsError("ML artifact directory already exists; choose a new experiment name")
    if not 0 <= filter_threshold <= 1:
        raise ValueError("filter_threshold must be between 0 and 1")
    target = target or TargetDefinition()
    bars, manifest = load_dataset(dataset_path)
    if not (manifest["start_utc"] <= windows.train_start < windows.test_end <= manifest["end_exclusive_utc"]):
        raise ValueError("ML windows must lie within the dataset manifest range")
    timeframe = str(manifest["timeframe"])
    if timeframe not in PERIODS_PER_YEAR:
        raise ValueError(f"Unsupported ML timeframe: {timeframe}")
    periods_per_year = PERIODS_PER_YEAR[timeframe]
    feature_config = FeatureConfig(periods_per_year=periods_per_year)
    labeled = build_ml_dataset(bars, target=target, feature_config=feature_config)
    train = _partition(labeled, windows.train_start, windows.tune_start)
    tune = _partition(labeled, windows.tune_start, windows.calibration_start)
    calibration = _partition(labeled, windows.calibration_start, windows.test_start)
    test = _partition(labeled, windows.test_start, windows.test_end)
    for name, part in (("train", train), ("calibration", calibration)):
        if part["target"].nunique() != 2:
            raise ValueError(f"{name} window needs both target classes; revise research scope before fitting")

    xgb = _xgboost()
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import log_loss

    def dmatrix(part: pd.DataFrame, *, with_label: bool = False):
        return xgb.DMatrix(
            part.loc[:, list(ML_FEATURES)], feature_names=list(ML_FEATURES),
            label=part["target"].to_numpy(dtype=int) if with_label else None,
        )

    train_matrix, tune_matrix = dmatrix(train, with_label=True), dmatrix(tune)
    candidates: list[dict[str, object]] = []
    selected = None
    for depth, rounds in ((2, 80), (2, 160), (3, 80), (3, 160)):
        parameters = {
            "objective": "binary:logistic", "eval_metric": "logloss",
            "tree_method": "hist", "max_depth": depth, "eta": 0.05,
            "subsample": 0.8, "colsample_bytree": 0.8,
            "seed": 17, "nthread": 2,
        }
        booster = xgb.train(parameters, train_matrix, num_boost_round=rounds)
        loss = float(log_loss(tune["target"], booster.predict(tune_matrix), labels=[0, 1]))
        candidates.append({"max_depth": depth, "rounds": rounds, "tune_log_loss": loss})
        if selected is None or loss < selected[0]:
            selected = (loss, depth, rounds, booster)
    if selected is None:
        raise RuntimeError("No ML candidate was trained")
    tune_loss, depth, rounds, booster = selected

    # Fit calibration only on the later calibration window. The final test
    # labels are not touched until both model and calibrator are frozen.
    calibration_margins = booster.predict(dmatrix(calibration), output_margin=True)
    sigmoid = LogisticRegression(random_state=17, max_iter=500)
    sigmoid.fit(np.asarray(calibration_margins).reshape(-1, 1), calibration["target"])

    artifact_dir.mkdir(parents=True)
    model_path = artifact_dir / "model.json"
    booster.save_model(str(model_path))
    metadata = {
        "model_version": artifact_dir.name,
        "model_family": "xgboost_binary_classifier", "research_only": True,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "feature_version": FEATURE_VERSION, "features": list(ML_FEATURES),
        "target_definition": asdict(target), "filter_threshold": filter_threshold,
        "windows": asdict(windows), "training_rows": len(train),
        "tuning_rows": len(tune), "calibration_rows": len(calibration),
        "test_rows": len(test), "parameters": {"max_depth": depth, "rounds": rounds, "eta": 0.05},
        "validation_metrics": {"tune_log_loss": tune_loss},
        "calibration": {
            "method": "sigmoid_on_raw_margin", "slope": float(sigmoid.coef_[0, 0]),
            "intercept": float(sigmoid.intercept_[0]),
        },
        "symbol": manifest["symbol"], "timeframe": timeframe,
        "periods_per_year": periods_per_year,
        "dataset_sha256": manifest["sha256"], "feed": manifest["feed"],
        "adjustment": manifest["adjustment"],
        "xgboost_version": version("xgboost"), "sklearn_version": version("scikit-learn"),
        "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
    }
    (artifact_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    model = ResearchModel.load(artifact_dir)
    test_probabilities = model.predict_proba(test)

    # Score every completed test candle, including the unlabeled tail; this
    # avoids changing trade eligibility just because no future label exists.
    feature_rows = build_features(bars, config=feature_config)
    test_features = feature_rows.loc[
        (feature_rows["timestamp"] >= pd.Timestamp(_utc_date(windows.test_start)))
        & (feature_rows["timestamp"] < pd.Timestamp(_utc_date(windows.test_end)))
    ].copy()
    finite = np.isfinite(test_features.loc[:, list(ML_FEATURES)].to_numpy(dtype=float)).all(axis=1)
    test_features = test_features.loc[finite]
    scores = dict(zip(test_features["timestamp"], model.predict_proba(test_features)))

    baseline_config = TrendFollowingV1Config()
    comparisons: dict[str, object] = {}
    history = bars.loc[bars["timestamp"] < pd.Timestamp(_utc_date(windows.test_end))]
    for name, cost in COST_SCENARIOS.items():
        scenario = replace(cost, periods_per_year=periods_per_year)
        baseline = BacktestEngine(TrendFollowingV1(config=baseline_config), config=scenario).run(
            history, trade_start=pd.Timestamp(_utc_date(windows.test_start)),
            trade_end=pd.Timestamp(_utc_date(windows.test_end)),
        )
        filtered = BacktestEngine(
            MLFilterStrategy(TrendFollowingV1(config=baseline_config), scores, threshold=filter_threshold),
            config=scenario,
        ).run(
            history, trade_start=pd.Timestamp(_utc_date(windows.test_start)),
            trade_end=pd.Timestamp(_utc_date(windows.test_end)),
        )
        comparisons[name] = {
            "assumptions": asdict(scenario),
            "rule_only": _strategy_metrics(baseline, periods_per_year),
            "rule_plus_ml": _strategy_metrics(filtered, periods_per_year),
        }
    report: dict[str, object] = {
        "research_only": True, "paper_submission_enabled": False,
        "dataset": str(dataset_path), "dataset_sha256": manifest["sha256"],
        "scope": manifest["universe_scope"], "symbol": manifest["symbol"],
        "timeframe": timeframe, "target_definition": asdict(target),
        "feature_version": FEATURE_VERSION, "windows": asdict(windows),
        "baseline_strategy": TrendFollowingV1.name,
        "baseline_strategy_config": asdict(baseline_config),
        "filter_threshold": filter_threshold,
        "rows": {"train": len(train), "tune": len(tune),
                 "calibration": len(calibration), "test": len(test)},
        "tuning_candidates": candidates, "selected_candidate": {"max_depth": depth, "rounds": rounds},
        "calibration_metrics": _binary_metrics(
            calibration["target"].to_numpy(dtype=int), model.predict_proba(calibration)
        ),
        "test_metrics": _binary_metrics(test["target"].to_numpy(dtype=int), test_probabilities),
        "strategy_comparison": comparisons,
        "limitations": [
            "Single current-symbol case study; survivorship and universe-selection bias remain.",
            "A five-bar label is not a five-day return, and close-to-close labels are not executable fills.",
            "Boundary rows whose future label crosses a split are purged; no missing candles are filled.",
            "Historical adjusted bars are a research proxy rather than executable prices.",
            "The test window stops being untouched after this report is inspected.",
            "Risk gates, broker exits/stops, broker fills, and multi-symbol portfolios are not simulated here.",
        ],
    }
    (artifact_dir / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--artifact-dir", required=True, type=Path)
    for name in ("train-start", "tune-start", "calibration-start", "test-start", "test-end"):
        parser.add_argument(f"--{name}", required=True, help="YYYY-MM-DD UTC; starts inclusive, end exclusive")
    parser.add_argument("--horizon-bars", type=int, default=5)
    parser.add_argument("--return-threshold", type=float, default=0.005)
    parser.add_argument("--filter-threshold", type=float, default=0.60)
    args = parser.parse_args()
    report = run_ml_research(
        args.dataset, artifact_dir=args.artifact_dir,
        windows=MLWindows(args.train_start, args.tune_start, args.calibration_start,
                          args.test_start, args.test_end),
        target=TargetDefinition(args.horizon_bars, args.return_threshold),
        filter_threshold=args.filter_threshold,
    )
    print(json.dumps({
        "artifact_dir": str(args.artifact_dir), "test_metrics": report["test_metrics"],
        "strategy_comparison": report["strategy_comparison"],
        "research_only": True,
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

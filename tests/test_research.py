from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.data.market_data import CandleValidationError
from backtesting.research import load_dataset


class ResearchDatasetTests(TestCase):
    def _dataset(self, directory: Path, timestamp: str) -> Path:
        path = directory / "sample.csv"
        path.write_text(
            "timestamp,symbol,open,high,low,close,volume\n"
            f"{timestamp},AAPL,100,102,99,101,1000\n",
            encoding="utf-8",
        )
        path.with_suffix(".manifest.json").write_text(json.dumps({
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "row_count": 1,
            "symbol": "AAPL",
            "universe_scope": "single_symbol_case_study",
        }), encoding="utf-8")
        return path

    def test_loader_accepts_verified_timezone_aware_dataset(self) -> None:
        with TemporaryDirectory() as directory:
            bars, _ = load_dataset(self._dataset(Path(directory), "2021-01-04T14:30:00Z"))
            self.assertEqual(len(bars), 1)
            self.assertEqual(str(bars["timestamp"].dt.tz), "UTC")

    def test_loader_rejects_naive_timestamp_even_with_matching_checksum(self) -> None:
        with TemporaryDirectory() as directory:
            path = self._dataset(Path(directory), "2021-01-04T14:30:00")
            with self.assertRaises(CandleValidationError) as context:
                load_dataset(path)
            self.assertEqual(context.exception.issues[0].code, "timezone_missing")

    def test_loader_rejects_modified_csv(self) -> None:
        with TemporaryDirectory() as directory:
            path = self._dataset(Path(directory), "2021-01-04T14:30:00Z")
            path.write_text(path.read_text(encoding="utf-8").replace("101,1000", "102,1000"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum"):
                load_dataset(path)

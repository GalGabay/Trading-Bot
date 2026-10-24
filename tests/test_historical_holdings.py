"""Offline public-filing extraction and publication-time safeguards."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from backtesting.historical_holdings import build_register, parse_common_holdings, require_available


def filing(names):
    header = "<tr><td>Common Stocks</td><td>Shares</td><td>Value</td></tr>"
    rows = "".join(f"<tr><td>{name}</td><td>10</td><td>1,000</td></tr>" for name in names)
    return f"<p>SPDR S&P 500 ETF Trust Schedule of Investments September 30, 2016</p><table>{header}{rows}<tr><td>Total Common Stocks</td><td>{len(names) * 1000:,}</td></tr></table>"


class HistoricalHoldingsTests(TestCase):
    def test_all_security_rows_retained_including_failed_names_and_share_classes(self):
        names = ["Failed Bank", "Bought Out Corp", "Example Class A", "Example Class C"]
        rows, total = parse_common_holdings(filing(names))
        self.assertEqual([r["source_name"] for r in rows], names)
        self.assertEqual(total, 4000)

    def test_repeated_page_headers_are_not_security_rows(self):
        text = filing(["A", "B"]).replace("<tr><td>B", "<tr><td>Common Stocks</td><td>Shares</td><td>Value</td></tr><tr><td>B")
        self.assertEqual(len(parse_common_holdings(text)[0]), 2)

    def test_missing_row_or_wrong_total_fails_reconciliation(self):
        with self.assertRaisesRegex(ValueError, "reconcile"):
            parse_common_holdings(filing(["A", "B"]).replace("2,000", "3,000"))

    def test_duplicate_names_require_share_class_review(self):
        with self.assertRaisesRegex(ValueError, "share-class"):
            parse_common_holdings(filing(["A", "A"]))

    def test_empty_source_is_not_a_valid_empty_universe(self):
        with self.assertRaises(ValueError):
            parse_common_holdings("<html>temporarily unavailable</html>")

    def test_build_register_verifies_publication_and_preserves_unresolved_rows(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            f, index = root / "filing.html", root / "index.html"
            f.write_text(filing([f"Security {i}" for i in range(400)]))
            index.write_text("SPDR S&amp;P 500 Filing Date 2016-11-28 Period of Report 2016-09-30")
            register = build_register(f, index, asof="2016-09-30", source_url="https://example.test/filing")
            self.assertEqual(register["security_count"], 400)
            self.assertEqual(register["not_before_utc"], "2016-11-30T00:00:00+00:00")
            self.assertFalse(register["backtest_ready"])
            self.assertTrue(all(row["historical_symbol"] is None for row in register["records"]))
            self.assertEqual(len({r["membership_key"] for r in register["records"]}), 400)
            require_available(register, "2017-01-01T00:00:00Z")
            for text in ("Wrong Fund Filing Date 2016-11-28 Period of Report 2016-09-30",
                         "SPDR S&P 500 Filing Date 2016-11-28 Period of Report 2015-09-30",
                         "SPDR S&P 500 Filing Date 2016-08-28 Period of Report 2016-09-30"):
                index.write_text(text)
                with self.subTest(index=text), self.assertRaises(ValueError):
                    build_register(f, index, asof="2016-09-30", source_url="https://example.test/filing")

    def test_filing_and_index_periods_must_both_match(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            f, index = root / "filing.html", root / "index.html"
            f.write_text(filing([f"Security {i}" for i in range(400)]).replace("September 30, 2016", "September 30, 2020"))
            index.write_text("SPDR S&P 500 Filing Date 2016-11-28 Period of Report 2016-09-30")
            with self.assertRaisesRegex(ValueError, "investment schedule"):
                build_register(f, index, asof="2016-09-30", source_url="https://example.test/filing")

    def test_report_date_is_not_public_availability(self):
        register = {"not_before_utc": "2020-12-02T00:00:00Z"}
        for start in ("2020-09-30T00:00:00Z", "2017-01-01T00:00:00Z", "2021-01-01"):
            with self.subTest(start=start), self.assertRaises(ValueError):
                require_available(register, start)
        require_available(register, "2021-01-01T00:00:00Z")

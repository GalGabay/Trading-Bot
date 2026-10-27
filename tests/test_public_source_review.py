"""Portable HTML/XLSX fixtures and offline reconciliation, never real sources."""

from contextlib import contextmanager
from copy import deepcopy
import hashlib
from html import escape
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET
import zipfile

from backtesting import public_source_review as review


HEADERS = ["FUND NAME", "TICKER", "CUSIP", "EX-DATE", "RECORD DATE", "PAYABLE DATE",
           "DIVIDEND ($)", "SHORT TERM CAPITAL GAIN ($)", "LONG TERM CAPITAL GAIN ($)", "FREQUENCY"]


def apple_rows():
    return [[f"{month} 1, {year}", f"{month} 10, {year}", f"{month} 20, {year}", "$0.50", "Regular Cash"]
            for year in range(2016, 2024) for month in ("January", "April", "July", "October")]


def html_table(rows, headings=None):
    headings = headings or ["Declared", "Record", "Payable", "Amount", "Type"]
    return "<table>" + "".join("<tr>"+"".join("<td>"+escape(cell)+"</td>" for cell in row)+"</tr>"
                               for row in [headings]+rows) + "</table>"


def spy_rows():
    rows = [["Fixture S&P 500 Fund", "SPY", "78462F103", f"{month:02}/19/{year}",
             f"{month:02}/22/{year}", f"{month:02}/28/{year}", "0.500000", "", "", "Quarterly"]
            for year in range(2016, 2024) for month in (1, 4, 7, 10)]
    rows[-1][5] = "01/31/2024"  # Payment metadata; no reserved prices exist in this fixture.
    return rows


def workbook(path, rows, *, headings=None, shared=True):
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    strings = []
    sheet = ET.Element(f"{{{ns}}}worksheet")
    data = ET.SubElement(sheet, f"{{{ns}}}sheetData")
    for index, values in enumerate([HEADERS if headings is None else headings]+rows, 1):
        row = ET.SubElement(data, f"{{{ns}}}row", r=str(index))
        for col, value in enumerate(values):
            cell = ET.SubElement(row, f"{{{ns}}}c", r=f"{chr(65+col)}{index}", t="s" if shared else "inlineStr")
            if shared:
                strings.append(value)
                ET.SubElement(cell, f"{{{ns}}}v").text = str(len(strings)-1)
            else:
                ET.SubElement(ET.SubElement(cell, f"{{{ns}}}is"), f"{{{ns}}}t").text = value
    sst = ET.Element(f"{{{ns}}}sst")
    for value in strings:
        ET.SubElement(ET.SubElement(sst, f"{{{ns}}}si"), f"{{{ns}}}t").text = value
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/worksheets/sheet1.xml", ET.tostring(sheet))
        if shared:
            archive.writestr("xl/sharedStrings.xml", ET.tostring(sst))


class SourceParserTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.enterContext(patch("socket.socket.connect", side_effect=AssertionError("Real network is forbidden")))

    def apple(self, rows=None, **kwargs):
        path = self.root/"apple.html"
        path.write_text(html_table(apple_rows() if rows is None else rows, **kwargs), encoding="utf-8")
        return review.apple_table(path)

    def spy(self, rows=None, **kwargs):
        path = self.root/"spy.xlsx"
        workbook(path, spy_rows() if rows is None else rows, **kwargs)
        return review.spy_table(path)

    def test_supported_date_formats_and_footnote(self):
        for value in ("January 2, 2020", "Jan 2, 2020", "01/02/2020", " January   2, 2020* "):
            with self.subTest(value=value):
                self.assertEqual(review.day(value), "2020-01-02")
        self.assertEqual(review.day("February 29, 2020"), "2020-02-29")

    def test_invalid_dates_are_not_normalized(self):
        for value in ("February 29, 2019", "02/30/2020", "", "yesterday", "2020-01-02"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                review.day(value)

    def test_apple_valid_nominal_rows_and_no_invented_ex_dates(self):
        rows = self.apple()
        self.assertEqual(len(rows), 32)
        self.assertTrue(all(r["ex_date"] is None and r["amount"] == "0.50" for r in rows))

    def test_apple_outside_years_ignored_without_changing_boundary_rows(self):
        rows = apple_rows()+[["odd dated label 2024", "", "", "$9", "Regular Cash"],
                            ["December 31, 2015", "", "", "$9", "Regular Cash"]]
        result = self.apple(rows)
        self.assertEqual(result[0]["declared"], "2016-01-01")
        self.assertEqual(result[-1]["declared"], "2023-10-01")

    def test_apple_missing_and_duplicate_records_rejected(self):
        original = apple_rows()
        for rows in (original[:-1], original+[original[0]], original[:-1]+[original[0]]):
            with self.subTest(size=len(rows)), self.assertRaises(ValueError):
                self.apple(rows)

    def test_apple_changed_headings_rejected(self):
        with self.assertRaises(ValueError):
            self.apple(headings=["Declaration", "Record", "Payable", "Amount", "Type"])

    def test_apple_unknown_in_window_distribution_requires_review(self):
        for kind in ("Special Cash", "Unknown Distribution", "2-for-1 Stock Split"):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.apple(apple_rows()+[["June 1, 2020", "June 10, 2020", "June 20, 2020", "$1", kind]])

    def test_apple_known_split_is_not_counted_as_cash(self):
        rows = self.apple(apple_rows()+[["July 30, 2020", "August 24, 2020", "August 31, 2020*", "N/A", "4-for-1 Stock Split"]])
        self.assertEqual(len(rows), 32)

    def test_known_split_with_wrong_date_or_duplicate_requires_review(self):
        split=["July 30, 2020", "August 24, 2020", "August 31, 2020*", "N/A", "4-for-1 Stock Split"]
        wrong=split.copy();wrong[0]="July 30, 2019"
        for extra in ([wrong],[split,split]):
            with self.subTest(extra=extra),self.assertRaises(ValueError):
                self.apple(apple_rows()+extra)

    def test_apple_invalid_amounts_rejected(self):
        for amount in ("$0", "$-0.50", "$NaN", "$Infinity", "$garbage"):
            rows = apple_rows(); rows[0][3] = amount
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                self.apple(rows)

    def test_apple_impossible_date_order_rejected(self):
        for index, value in ((1, "December 31, 2015"), (2, "January 9, 2016")):
            rows = apple_rows(); rows[0][index] = value
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.apple(rows)

    def test_spy_valid_rows_preserve_blank_capital_gains_and_late_payment(self):
        rows = self.spy()
        self.assertEqual(len(rows), 32)
        self.assertEqual(rows[-1]["payable"], "2024-01-31")
        self.assertTrue(all(r["short_term_gain"] == "" and r["long_term_gain"] == "" for r in rows))
        self.assertTrue(all(r["declared"] is None for r in rows))

    def test_spy_changed_column_headings_rejected(self):
        headings = HEADERS.copy(); headings[6] = "ADJUSTED DISTRIBUTION"
        with self.assertRaises(ValueError):
            self.spy(headings=headings)

    def test_spy_missing_and_duplicate_rows_rejected(self):
        rows = spy_rows()
        for values in (rows[:-1], rows+[rows[0]], rows[:-1]+[rows[0]]):
            with self.subTest(size=len(values)), self.assertRaises(ValueError):
                self.spy(values)

    def test_spy_identity_mismatch_rejected(self):
        for column, value in ((0, "Unrelated Fund"), (2, "BAD-CUSIP")):
            rows = spy_rows(); rows[0][column] = value
            with self.subTest(column=column), self.assertRaises(ValueError):
                self.spy(rows)

    def test_other_funds_and_outside_ex_years_are_not_attached(self):
        rows = spy_rows()+[["Other fund", "OTHER", "x", "not a date", "", "", "bad", "", "", ""]]
        rows.append(["S&P 500 Fund", "SPY", "78462F103", "01/02/2024", "bad", "bad", "bad", "", "", ""])
        self.assertEqual(len(self.spy(rows)), 32)

    def test_spy_invalid_amounts_and_date_order_rejected(self):
        for column, value in ((6, "0"), (6, "-1"), (6, "NaN"), (6, "Infinity"),
                              (4, "01/18/2016"), (5, "01/20/2016")):
            rows = spy_rows(); rows[0][column] = value
            with self.subTest(column=column, value=value), self.assertRaises(ValueError):
                self.spy(rows)

    def test_spy_unknown_inline_string_format_rejected_clearly(self):
        with self.assertRaises(ValueError):
            self.spy(shared=False)

    def test_malformed_workbook_rejected_clearly(self):
        path = self.root/"bad.xlsx"; path.write_bytes(b"not a zip")
        with self.assertRaises(ValueError):
            review.spy_table(path)

    def test_workbook_expansion_limit_rejected_before_reading_payloads(self):
        path=self.root/'large.xlsx';workbook(path,spy_rows())
        with patch.object(zipfile.ZipFile,'infolist',return_value=[Mock(file_size=65*1024*1024)]):
            with self.assertRaisesRegex(ValueError,'expansion'):
                review.spy_table(path)


class ReviewFixture(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.enterContext(patch("socket.socket.connect", side_effect=AssertionError("Real network is forbidden")))
        self.protocol = self.make_fixture()

    def save(self, name, value):
        path = self.root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) if not isinstance(value, str) else value, encoding="utf-8")
        return dict(path=name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())

    def repin(self, entry):
        entry["sha256"] = hashlib.sha256((self.root/entry["path"]).read_bytes()).hexdigest()

    def make_fixture(self):
        for name in ["backtesting/public_source_review.py", "backtesting/public_document_collection.py"]:
            self.save(name, Path(name).read_text(encoding="utf-8"))
        sources = {}
        apple = "Amounts not split adjusted. "+html_table(apple_rows())
        sources["apple_dividend_history"] = self.save("apple.html", apple)
        path = self.root/"spy.xlsx";workbook(path, spy_rows())
        sources["spy_historical_distributions"] = dict(path="spy.xlsx", sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        sources["jpm_2016_dividend"] = self.save("jpm16.html", "May 17, 2016: common stock 48 cents per share July 31, 2016 July 6, 2016")
        sources["jpm_2021_dividend"] = self.save("jpm21.html", "September 21, 2021: common stock $1.00 per share October 31, 2021 October 6, 2021")
        sources["cbre_2016_10k"] = self.save("cbre16.html", "Class A Common Stock New York Stock Exchange not declared or paid any cash dividends")
        sources["cbre_2023_10k"] = self.save("cbre23.html", "Class A common stock has traded March 19, 2018 CBG not declared or paid any cash dividends")
        for i in range(5): sources[f"index_{i}"] = self.save(f"index_{i}.html", "Synthetic index only")
        providers = {}
        providers["AAPL"] = [dict(id=f"apple-{i}", symbol="AAPL", ex_date=review.day(r[1])[:-2]+"09", rate=.5)
                             for i, r in enumerate(apple_rows())]
        providers["SPY"] = [dict(id=f"spy-{i}", symbol="SPY", ex_date=review.day(r[3]), rate=.5)
                            for i, r in enumerate(spy_rows()) if i not in (0, 9, 31)]
        providers["SPY"][3]["rate"] = .4999999
        providers["JPM"] = [dict(id=f"jpm-{year}-{month}",symbol="JPM",ex_date=f"{year}-{month:02}-04",rate=.5)
                            for year in range(2016,2024) for month in (1,4,7,10)]
        providers["JPM"][2].update(id="75900bb2-491a-4a38-b929-ea4998d023d6",ex_date="2016-07-01",rate=.48)
        providers["JPM"][23].update(id="fd7874f8-fb48-4ae8-9320-86e8b9560338",ex_date="2021-10-05",rate=1,
                                   record_date="2021-10-06",payable_date="2021-10-31")
        # Keep the frozen 32/32/29 provider universe and 48 omitted fields.
        for symbol, missing in [("AAPL",17),("SPY",14),("JPM",17)]:
            for row in providers[symbol][missing:]: row.setdefault("payable_date", "2021-10-31" if row['id'].startswith('fd787') else "2020-01-01")
        # Reviewed Apple/SPY present fields must agree with source dates.
        for i, row in enumerate(providers["AAPL"]):
            if "payable_date" in row: row["payable_date"] = review.day(apple_rows()[i][2])
        spy_by_ex={review.day(r[3]):r for r in spy_rows()}
        for row in providers["SPY"]:
            if "payable_date" in row: row["payable_date"]=review.day(spy_by_ex[row["ex_date"]][5])
        payloads={s:self.save(f"{s}.json",dict(next_page_token=None,corporate_actions=dict(cash_dividends=rows))) for s,rows in providers.items()}
        archive=self.save("collector.py", (self.root/"backtesting/public_document_collection.py").read_text(encoding="utf-8"))
        attempts=[dict(status="transport_or_size_failure_no_retry",id=f"fail{i}") for i in range(6)]
        for key, entry in sources.items(): attempts.append(dict(id=key,status="saved_unreviewed",file=entry['path'],sha256=entry['sha256']))
        attempts.append(dict(id="blocked",status="access_or_rate_barrier",status_code=403))
        queue=self.save("queue.json",dict(documents=[]))
        batch=self.save("batch.json",dict(network_http_attempts=18,attempts=attempts,stopped=True,code_sha256=archive['sha256'],queue_sha256=queue['sha256']))
        return dict(schema_version=1,scope="Synthetic source-review fixture",purchases_usd=0,ready_for_strategy_scoring=False,
                    assumptions_owner_approved=False,original_plan=self.save("plan.json",dict(max_public_document_get_attempts=40,max_public_discovery_tool_calls=12)),
                    prior_qualification=self.save("prior.json",{}),executed_collector=archive,batch_reports=[batch],queues=[queue],
                    discovery_evidence=[self.save("discovery.json",[dict(args={}) for _ in range(5)])],
                    sources=sources,provider_payloads=payloads,network=dict(public_discovery_tool_calls=5))

    @contextmanager
    def working(self):
        previous = Path.cwd()
        os.chdir(self.root)
        try: yield
        finally: os.chdir(previous)

    def run_review(self):
        self.save("review.json", self.protocol)
        with self.working():
            return review.review_sources(Path("out"),review_path=Path("review.json"))

    def change_provider(self, symbol, mutate):
        entry=self.protocol['provider_payloads'][symbol];path=self.root/entry['path']
        value=json.loads(path.read_text());mutate(value);path.write_text(json.dumps(value),encoding='utf-8');self.repin(entry)


class PublicSourceReconciliationTests(ReviewFixture):
    def test_full_synthetic_review_is_offline_and_never_approves_evidence(self):
        result=self.run_review()
        self.assertEqual(result['primary_dividend_rows'],66)
        self.assertEqual(result['source_dividend_counts'],dict(AAPL=32,SPY=32,JPM=2))
        self.assertEqual(len(result['source_only_spy']),3)
        self.assertEqual(len(result['amount_precision_discrepancies']),1)
        self.assertEqual(result['amount_precision_discrepancies'][0]['amount_difference_exact'],'-1/10000000')
        self.assertFalse(result['ready_for_strategy_scoring'])
        self.assertEqual(result['offline_review_network_requests'],0)
        rows=json.loads((self.root/'out/dividend_reconciliation.json').read_text())
        self.assertTrue(all(not r['broker_credit_verified'] and not r['assumptions_approved'] for r in rows))

    def test_exact_amount_has_zero_difference(self):
        self.change_provider('SPY',lambda p:[r.update(rate=.5) for r in p['corporate_actions']['cash_dividends']])
        self.assertEqual(self.run_review()['amount_precision_discrepancies'],[])

    def test_substantive_amount_conflict_is_not_called_display_precision(self):
        self.change_provider('SPY',lambda p:p['corporate_actions']['cash_dividends'][0].update(rate=.7))
        with self.assertRaises(ValueError):self.run_review()
        self.assertFalse((self.root/'out').exists())

    def test_positive_difference_within_half_display_unit_remains_unapproved_warning(self):
        self.change_provider('SPY',lambda p:p['corporate_actions']['cash_dividends'][3].update(rate=.5000005))
        row=self.run_review()['amount_precision_discrepancies'][0]
        self.assertEqual(row['amount_difference_exact'],'1/2000000')
        self.assertFalse(row['amount_exact_match'])
        self.assertFalse(row['ready_for_strategy_scoring'])

    def test_difference_beyond_half_display_unit_is_error(self):
        self.change_provider('SPY',lambda p:p['corporate_actions']['cash_dividends'][3].update(rate=.5000006))
        with self.assertRaisesRegex(ValueError,'display precision'):self.run_review()

    def test_duplicate_provider_event_rejected_even_outside_reviewed_jpm_subset(self):
        self.change_provider('JPM',lambda p:p['corporate_actions']['cash_dividends'].append(deepcopy(p['corporate_actions']['cash_dividends'][-1])))
        with self.assertRaises(ValueError):self.run_review()

    def test_apple_missing_or_ambiguous_provider_join_rejected(self):
        for mutate in (lambda p:p['corporate_actions']['cash_dividends'].pop(),
                       lambda p:p['corporate_actions']['cash_dividends'].append(deepcopy(p['corporate_actions']['cash_dividends'][0]))):
            with self.subTest(mutate=mutate):
                original=deepcopy(self.protocol['provider_payloads']['AAPL'])
                path=self.root/original['path'];body=path.read_bytes()
                self.change_provider('AAPL',mutate)
                with self.assertRaises(ValueError):self.run_review()
                path.write_bytes(body);self.protocol['provider_payloads']['AAPL']=original

    def test_provider_payment_conflict_rejected(self):
        self.change_provider('AAPL',lambda p:p['corporate_actions']['cash_dividends'][0].update(payable_date='2016-01-21'))
        with self.assertRaises(ValueError):self.run_review()

    def test_incomplete_provider_pagination_rejected(self):
        self.change_provider('SPY',lambda p:p.update(next_page_token='more'))
        with self.assertRaises(ValueError):self.run_review()

    def test_changed_source_hash_rejected_before_writing_output(self):
        (self.root/self.protocol['sources']['apple_dividend_history']['path']).write_text('changed')
        with self.assertRaisesRegex(ValueError,'checksum'):self.run_review()
        self.assertFalse((self.root/'out').exists())

    def test_source_path_escape_rejected(self):
        self.protocol['sources']['apple_dividend_history']['path']='../outside.html'
        with self.assertRaises(ValueError):self.run_review()

    def test_existing_output_preserved(self):
        (self.root/'out').mkdir();marker=self.root/'out/sentinel';marker.write_text('keep')
        with self.assertRaises(FileExistsError):self.run_review()
        self.assertEqual(marker.read_text(),'keep')

    def test_false_approval_and_boolean_schema_rejected(self):
        for field in ('schema_version','assumptions_owner_approved','ready_for_strategy_scoring'):
            original=self.protocol[field];self.protocol[field]=True
            with self.subTest(field=field),self.assertRaises(ValueError):self.run_review()
            self.protocol[field]=original

    def test_reported_request_count_must_match_attempts(self):
        entry=self.protocol['batch_reports'][0];value=json.loads((self.root/entry['path']).read_text())
        value['attempts'].pop(0);self.save(entry['path'],value);self.repin(entry)
        with self.assertRaises(ValueError):self.run_review()

    def test_earlier_barrier_followed_by_more_collection_rejected(self):
        entry=self.protocol['batch_reports'][0];value=json.loads((self.root/entry['path']).read_text())
        value['attempts'][0].update(status_code=403,status='access_or_rate_barrier')
        self.save(entry['path'],value);self.repin(entry)
        with self.assertRaises(ValueError):self.run_review()

    def test_underreported_discovery_calls_cannot_bypass_cap(self):
        entry=self.protocol['discovery_evidence'][0];self.save(entry['path'],[dict(args={}) for _ in range(13)]);self.repin(entry)
        with self.assertRaises(ValueError):self.run_review()

    def test_unknown_queue_hash_rejected(self):
        entry=self.protocol['batch_reports'][0];value=json.loads((self.root/entry['path']).read_text())
        value['queue_sha256']='0'*64;self.save(entry['path'],value);self.repin(entry)
        with self.assertRaises(ValueError):self.run_review()

    def test_archived_collector_hash_must_match_acquisition_log(self):
        entry=self.protocol['batch_reports'][0];value=json.loads((self.root/entry['path']).read_text())
        value['code_sha256']='0'*64;self.save(entry['path'],value);self.repin(entry)
        with self.assertRaises(ValueError):self.run_review()

    def test_catalog_source_hash_cannot_disagree_with_saved_response_log(self):
        entry=self.protocol['sources']['apple_dividend_history'];path=self.root/entry['path']
        path.write_text(path.read_text()+' harmless new text',encoding='utf-8');self.repin(entry)
        with self.assertRaises(ValueError):self.run_review()

    def test_final_access_barrier_must_be_marked_stopped(self):
        entry=self.protocol['batch_reports'][0];value=json.loads((self.root/entry['path']).read_text())
        value['stopped']=False;self.save(entry['path'],value);self.repin(entry)
        with self.assertRaises(ValueError):self.run_review()

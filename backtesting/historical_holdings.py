"""Extract a dated, fixed research basket from a public fund holdings filing.

This is a source membership register, not a ticker/security master or a
claim to cover every US stock. Every disclosed common-stock row is retained.
"""

import argparse
from datetime import UTC, date, datetime, timedelta
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import re


class FilingRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell, self.text = [], None, None, []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        if tag in {"td", "th"} and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        self.text.append(data)
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def parse_common_holdings(html: str) -> tuple[list[dict], int]:
    parser = FilingRows()
    parser.feed(html)
    active, total, rows = False, None, []
    for cells in parser.rows:
        if not cells:
            continue
        name = cells[0]
        if name.startswith("Common Stocks") and "Shares" in cells:
            active = True
            continue
        if not active:
            continue
        numbers = [int(value.replace(",", "")) for value in cells[1:] if re.fullmatch(r"[0-9][0-9,]*", value)]
        if name.lower().startswith("total common stocks"):
            if len(numbers) != 1:
                raise ValueError("Common-stock total must identify exactly one market value")
            total = numbers[0]
            break
        if len(numbers) == 2 and name:
            shares, value = numbers
            if shares <= 0 or value < 0:
                raise ValueError("Invalid disclosed common-stock holding")
            rows.append({"source_name": name, "reported_shares": shares, "reported_market_value_usd": value})
    if total is None or not rows or sum(row["reported_market_value_usd"] for row in rows) != total:
        raise ValueError("Holdings do not reconcile to the filing's complete common-stock total")
    if len({row["source_name"] for row in rows}) != len(rows):
        raise ValueError("Repeated source security names require explicit share-class review")
    return rows, total


def build_register(filing: Path, index: Path, *, asof: str, source_url: str) -> dict:
    source = filing.read_text(encoding="utf-8")
    document = FilingRows()
    document.feed(source)
    body = " ".join(" ".join(document.text).split())
    report_day = date.fromisoformat(asof)
    schedule = f"Schedule of Investments {report_day.strftime('%B')} {report_day.day}, {report_day.year} Common Stocks"
    if "SPDR S&P 500" not in body or schedule not in body:
        raise ValueError("Holdings document does not match the declared fund and dated investment schedule")
    parser = FilingRows()
    parser.feed(index.read_text(encoding="utf-8"))
    text = " ".join(" ".join(parser.text).split())
    match = re.search(r"Filing Date\s+(\d{4}-\d{2}-\d{2})", text)
    period = re.search(r"Period of Report\s+(\d{4}-\d{2}-\d{2})", text)
    if match is None or period is None or period[1] != asof or "SPDR S&P 500" not in text.replace("&amp;", "&"):
        raise ValueError("Filing index does not verify issuer, reporting period and public filing date")
    filed = date.fromisoformat(match[1])
    if filed < date.fromisoformat(asof):
        raise ValueError("Filing cannot predate its holdings report")
    rows, total = parse_common_holdings(source)
    if not 400 <= len(rows) <= 600:
        raise ValueError("Unexpected SPY common-stock count; investigate source/schema before use")
    digest = hashlib.sha256(filing.read_bytes()).hexdigest()
    for position, row in enumerate(rows, 1):
        row.update(source_row=position, membership_key=f"SPY-{asof}-{position:04d}",
                   historical_symbol=None, permanent_security_id=None, ready_for_execution=False)
    return {
        "scope": "fixed_disclosed_SPY_common_stock_holdings_not_entire_market_or_daily_index_history",
        "asof": asof, "filed_on": filed.isoformat(),
        "not_before_utc": datetime.combine(filed + timedelta(days=2), datetime.min.time(), UTC).isoformat(),
        "availability_convention": "Conservative two-calendar-day bound after SEC filing; never use report date as publication date",
        "source_url": source_url, "filing_sha256": digest,
        "filing_index_sha256": hashlib.sha256(index.read_bytes()).hexdigest(),
        "security_count": len(rows), "common_stock_market_value_usd": total,
        "all_disclosed_rows_retained": True, "records": rows,
        "source_row_keys_are_permanent_security_ids": False,
        "backtest_ready": False,
        "blockers": ["Resolve each security's historical symbol/share-class identity without survivor exclusions.",
                     "Audit listing/action/raw-price coverage and terminal outcomes for the retained cohort.",
                     "This is a fixed historical basket; daily full-market/index membership is not established."],
    }


def require_available(register: dict, trade_start: str) -> None:
    start = datetime.fromisoformat(trade_start)
    bound = datetime.fromisoformat(register["not_before_utc"])
    if start.tzinfo is None or bound.tzinfo is None or start < bound:
        raise ValueError("Historical basket was not yet disclosed at the proposed trade start")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--filing", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--asof", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    register = build_register(args.filing, args.index, asof=args.asof, source_url=args.source_url)
    with args.output.open("x", encoding="utf-8") as target:
        target.write(json.dumps(register, indent=2, allow_nan=False) + "\n")
    print(f"Retained {register['security_count']} security rows; backtest_ready=False")


if __name__ == "__main__":
    main()

"""Offline reconciliation of the bounded issuer/fund document collection.

The current issuer tables are retrospective evidence. Declaration dates are
not claims of exact historical publication, payable dates are not broker
credit, and blank capital-gain fields are preserved rather than made zero.
"""

import argparse
from collections import Counter
import csv
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

from backtesting.cohort_audit import checked_file, digest, source_text
from backtesting.historical_holdings import FilingRows

REVIEW = Path("docs/pilot_public_source_review.json")


def day(value):
    value = " ".join(value.replace("*", "").split())
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError("Unreviewed date format in primary document")


def apple_table(path):
    parser = FilingRows()
    parser.feed(path.read_text(encoding="utf-8"))
    if ["Declared", "Record", "Payable", "Amount", "Type"] not in parser.rows:
        raise ValueError("Apple source table headings changed")
    result = []
    for cells in parser.rows:
        if len(cells) != 5 or cells[4] != "Regular Cash":
            continue
        year = re.search(r"\b(\d{4})\b", cells[0])
        if year is None:
            raise ValueError("Apple declaration row has no year")
        if not 2016 <= int(year[1]) <= 2023:
            continue
        declared = day(cells[0])
        if not "2016-01-01" <= declared < "2024-01-01":
            continue
        result.append(dict(symbol="AAPL", declared=declared, record=day(cells[1]), payable=day(cells[2]),
                           amount=str(Decimal(cells[3].replace("$", "").replace(",", "").strip())),
                           ex_date=None, source="apple_dividend_history", basis="Issuer says amounts not split adjusted"))
    if len(result) != 32 or len({r["record"] for r in result}) != 32:
        raise ValueError("Expected 32 unique Apple regular-cash rows in the reviewed interval")
    return result


def spy_table(path):
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        if sum(i.file_size for i in archive.infolist()) > 64 * 1024 * 1024:
            raise ValueError("Workbook expansion exceeds audit limit")
        shared = ["".join(item.itertext()) for item in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("x:si", ns)]
        rows = ET.fromstring(archive.read("xl/worksheets/sheet1.xml")).findall(".//x:sheetData/x:row", ns)
        records = []
        for row in rows:
            values = {}
            for cell in row.findall("x:c", ns):
                node = cell.find("x:v", ns)
                value = node.text if node is not None else ""
                if cell.get("t") == "s":
                    value = shared[int(value)]
                values[re.sub("[0-9]", "", cell.get("r"))] = value.strip()
            if values.get("B") != "SPY":
                continue
            ex = day(values["D"])
            if not "2016-01-01" <= ex < "2024-01-01":
                continue
            if values["C"] != "78462F103" or "S&P 500" not in values["A"]:
                raise ValueError("Workbook row does not match reviewed SPY fund identity")
            records.append(dict(symbol="SPY", ex_date=ex, record=day(values["E"]), payable=day(values["F"]),
                declared=None, amount=str(Decimal(values["G"])), source="spy_historical_distributions",
                basis="USD dividend per fund unit as displayed; capital-gain cells kept separately",
                short_term_gain=values.get("H", ""), long_term_gain=values.get("I", "")))
    if len(records) != 32 or len({r["ex_date"] for r in records}) != 32:
        raise ValueError("Expected 32 distinct SPY distributions in reviewed interval")
    return records


def review_sources(output, *, review_path=REVIEW):
    if output.exists():
        raise FileExistsError("Choose a fresh source reconciliation directory")
    protocol = json.loads(review_path.read_text(encoding="utf-8"))
    if (protocol["schema_version"] != 1 or protocol["purchases_usd"] != 0
            or protocol["ready_for_strategy_scoring"] is not False or protocol["assumptions_owner_approved"] is not False):
        raise ValueError("Only the no-purchase, unapproved source review is supported")
    root, inputs = Path.cwd(), {review_path.as_posix(): digest(review_path)}

    def load(entry):
        path = checked_file(root, entry)
        inputs[path.relative_to(root).as_posix()] = digest(path)
        return path

    plan = json.loads(load(protocol["original_plan"]).read_text())
    load(protocol["prior_qualification"])
    load(protocol["executed_collector"])
    batches = [json.loads(load(entry).read_text()) for entry in protocol["batch_reports"]]
    for entry in protocol["queues"] + protocol["discovery_evidence"]:
        load(entry)
    attempts = [item for batch in batches for item in batch["attempts"]]
    if (sum(batch["network_http_attempts"] for batch in batches) != 18 or len(attempts) > plan["max_public_document_get_attempts"]
            or protocol["network"]["public_discovery_tool_calls"] > plan["max_public_discovery_tool_calls"]
            or attempts[-1].get("status_code") != 403 or any(item.get("status_code") in {401, 402, 403, 407, 429} for item in attempts[:-1])):
        raise ValueError("Recorded collection exceeds bounds or did not stop at its first access barrier")
    paths = {name: load(entry) for name, entry in protocol["sources"].items()}
    providers = {symbol: json.loads(load(entry).read_text())["corporate_actions"]["cash_dividends"]
                 for symbol, entry in protocol["provider_payloads"].items()}
    text = {name: source_text(path) for name, path in paths.items() if path.suffix == ".html"}
    if "not split adjusted" not in text["apple_dividend_history"]:
        raise ValueError("Apple nominal share-basis qualification changed")
    dividends = apple_table(paths["apple_dividend_history"]) + spy_table(paths["spy_historical_distributions"])
    declarations = [dict(source="jpm_2016_dividend", declared="2016-05-17", payable="2016-07-31", record="2016-07-06",
                         amount="0.48", event_id="75900bb2-491a-4a38-b929-ea4998d023d6", literal="48 cents per share"),
                    dict(source="jpm_2021_dividend", declared="2021-09-21", payable="2021-10-31", record="2021-10-06",
                         amount="1.00", event_id="fd7874f8-fb48-4ae8-9320-86e8b9560338")]
    # The second event is selected by its saved record/payable dates, never by a
    # settlement lag inferred from the record date or by a quarterly pattern.
    for decl in declarations:
        body = text[decl["source"]]
        for field in ("declared", "payable", "record"):
            parsed = datetime.strptime(decl[field], "%Y-%m-%d")
            if f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}" not in body:
                raise ValueError("JPMorgan primary declaration date terms changed")
        if decl.get("literal", "$1.00 per share") not in body or "common stock" not in body:
            raise ValueError("JPMorgan common-share amount/class terms changed")
        matches = [p for p in providers["JPM"] if p.get("record_date") == decl["record"] and p.get("payable_date") == decl["payable"]]
        if not matches:  # Explicit manual review for the older record without those provider fields.
            matches = [p for p in providers["JPM"] if p["id"] == decl["event_id"]]
        if (len(matches) != 1 or matches[0]["id"] != decl["event_id"]
                or Fraction(str(matches[0]["rate"])) != Fraction(decl["amount"])):
            raise ValueError("JPMorgan declaration/provider cross-reference is ambiguous")
        dividends.append(dict(symbol="JPM", source=decl["source"], declared=decl["declared"], payable=decl["payable"],
                              record=decl["record"], amount=decl["amount"],
                              ex_date=None, reviewed_provider_id=matches[0]["id"], basis="Dated common-share issuer declaration"))
    comparisons = []
    used = set()
    for row in dividends:
        symbol = row["symbol"]
        candidates = [p for p in providers[symbol] if
            (p["ex_date"] == row["ex_date"] if symbol == "SPY" else p["id"] == row["reviewed_provider_id"] if symbol == "JPM" else
             row["declared"] <= p["ex_date"] <= row["record"] and Fraction(str(p["rate"])) == Fraction(row["amount"]))]
        if len(candidates) > 1 or (not candidates and symbol != "SPY"):
            raise ValueError("Issuer/provider mapping requires a unique reviewed cross-reference")
        provider = candidates[0] if candidates else None
        key = (symbol, provider["id"]) if provider else None
        if key in used:
            raise ValueError("Two source rows mapped to one provider event")
        if key:
            used.add(key)
        for source_field, provider_field in [("record", "record_date"), ("payable", "payable_date")]:
            if provider and provider.get(provider_field) and provider[provider_field] != row[source_field]:
                raise ValueError("Provider and primary payment/record dates conflict")
        delta = Fraction(str(provider["rate"])) - Fraction(row["amount"]) if provider else None
        comparisons.append({**row, "provider_event_id": provider["id"] if provider else None,
            "provider_ex_date": provider["ex_date"] if provider else None,
            "provider_amount": str(provider["rate"]) if provider else None,
            "amount_difference_exact": str(delta) if delta is not None else None,
            "amount_exact_match": delta == 0 if delta is not None else None,
            "source_supplies_missing_provider_payable": bool(provider and not provider.get("payable_date")),
            "ex_date_independently_supplied": symbol == "SPY",
            "provider_join_basis": "Exact ex-date and SPY identity" if symbol == "SPY" else "Explicit declaration/date cross-reference" if symbol == "JPM" else "Unique nominal amount and declared <= provider ex-date <= issuer record; not independent ex-date certification",
            "source_only_event": provider is None, "source_retrieved_now_not_historical_release_proof": True,
            "broker_credit_verified": False, "assumptions_approved": False, "ready_for_strategy_scoring": False})
    cbre_facts = {}
    for name in ("cbre_2016_10k", "cbre_2023_10k"):
        body = text[name]
        required = ["Class A Common Stock", "New York Stock Exchange"] if name.endswith("2016_10k") else ["Class A common stock has traded", "March 19, 2018", "CBG"]
        if not all(term in body for term in required) or "not declared or paid any cash dividends" not in body:
            raise ValueError("CBRE listing/dividend-policy source changed")
        cbre_facts[name] = dict(common_class_and_listing_supported=True, no_cash_dividends_since_inception_supported=True,
                               retrospective_only=True, tax_reit_status_certified=False, complete_all_action_history_certified=False)
    output.mkdir(parents=True, exist_ok=False)
    fields = sorted({key for row in comparisons for key in row})
    with (output/"dividend_reconciliation.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(comparisons)
    (output/"dividend_reconciliation.json").write_text(json.dumps(comparisons, indent=2)+"\n", encoding="utf-8")
    result = dict(scope=protocol["scope"], input_sha256=inputs,
        code_sha256={name: digest(name) for name in ["backtesting/public_source_review.py", "backtesting/public_document_collection.py"]},
        network=protocol["network"], saved_files=len(paths), substantive_documents=6, index_pages=5,
        primary_dividend_rows=len(comparisons), source_dividend_counts=dict(Counter(row["symbol"] for row in comparisons)),
        source_supplied_provider_payables=sum(row["source_supplies_missing_provider_payable"] for row in comparisons),
        remaining_provider_payable_omissions=48-sum(row["source_supplies_missing_provider_payable"] for row in comparisons),
        source_only_spy=[row for row in comparisons if row["source_only_event"]],
        amount_precision_discrepancies=[row for row in comparisons if row["amount_exact_match"] is False],
        cbre_facts=cbre_facts, residual_gaps=["JPMorgan: 30 other provider events lack new primary declarations; complete history host returned 403",
            "Independent AAPL/JPM ex-date and full-period identity/action coverage review",
            "SPY source declaration/availability times and interpretation of blank capital-gain cells; one displayed amount precision difference",
            "CBRE tax subtype and action categories other than cash dividends",
            "Owner knowledge/payment assumptions and any later narrowed strategy scope remain unapproved"],
        ready_for_strategy_scoring=False, broker_credit_verified=False, purchases_usd=0, orders=0,
        broker_requests=0, account_requests=0, new_candle_requests=0, holdout_prices_read=False,
        collection_network_requests=18, offline_review_network_requests=0, unit_tests_run=0, strategy_simulations=0,
        output_sha256={p.name: digest(p) for p in output.iterdir()})
    (output/"report.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    r = review_sources(args.output)
    print(json.dumps({key: r[key] for key in ["saved_files", "source_dividend_counts", "source_supplied_provider_payables", "remaining_provider_payable_omissions", "ready_for_strategy_scoring"]}))


if __name__ == "__main__":
    main()

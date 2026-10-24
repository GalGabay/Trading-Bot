"""Bounded, read-only historical company-event access checks; no purchases.

Four predefined probes, at most five pages each, dates strictly before 2024.
Raw events are evidence to review, never automatic tradability or payment
instructions. In particular process_date cannot become historical known_at.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path

from app.broker.alpaca_client import AlpacaClient

PROBES = (("META", 2022), ("TWTR", 2022), ("ATVI", 2023), ("AAPL", 2020))


def run_probe(output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Choose a fresh source-access output directory")
    output.mkdir(parents=True)
    report = {
        "observed_at_utc": datetime.now(UTC).isoformat(), "spending_authorized": False,
        "scope": "existing_entitlement_read_only_event_access_not_billing_or_complete_history_audit",
        "probes": [], "source": "https://docs.alpaca.markets/us/reference/corporateactions-1",
        "limitations": ["Process date is not publication/payment date.",
                        "Provider does not guarantee when records become available.",
                        "Empty results do not establish that no historical event occurred."],
    }
    client = AlpacaClient()
    for symbol, year in PROBES:
        item = {"symbol": symbol, "process_start": f"{year}-01-01", "process_end": f"{year}-12-31"}
        pages, tokens, token = [], set(), None
        try:
            for index in range(5):
                page = client.get_corporate_actions_page(
                    symbols=[symbol], start=date(year, 1, 1), end=date(year, 12, 31), page_token=token,
                )
                path = output / f"{symbol}_{index + 1}.json"
                path.write_text(json.dumps(page, indent=2, allow_nan=False) + "\n", encoding="utf-8")
                pages.append({"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
                actions = page.get("corporate_actions")
                if not isinstance(actions, dict) or any(not isinstance(rows, list) for rows in actions.values()):
                    raise ValueError("Unexpected company-event schema")
                counts = item.setdefault("counts_by_type", {})
                for kind, rows in actions.items():
                    counts[kind] = counts.get(kind, 0) + len(rows)
                token = page.get("next_page_token")
                if token is None:
                    item["status"] = "accessible"
                    break
                if not isinstance(token, str) or token in tokens:
                    raise ValueError("Repeated or invalid company-event pagination token")
                tokens.add(token)
            else:
                item["status"] = "incomplete_page_budget"
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            item.update(status="unavailable_or_invalid", exception=type(exc).__name__,
                        http_status=status if isinstance(status, int) else None)
        item["pages"] = pages
        report["probes"].append(item)
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(item), flush=True)
    return report


def review_existing(directory: Path) -> dict:
    """Normalize saved public records into review candidates, never certified events.

    Preserve event identity fields, and deliberately leave publication/payment
    knowledge unknown. Current provider processing dates cannot certify those.
    This command is offline and verifies raw page hashes before reading them.
    """
    destination = directory / "candidates.json"
    if destination.exists():
        raise FileExistsError("Reviewed candidates already exist; preserve the evidence")
    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    candidates, seen = [], set()
    for probe in report["probes"]:
        if probe["status"] != "accessible":
            continue
        for page in probe["pages"]:
            path = directory / page["path"]
            if path.resolve().parent != directory.resolve():
                raise ValueError("Company-event page path must stay inside its snapshot directory")
            if hashlib.sha256(path.read_bytes()).hexdigest() != page["sha256"]:
                raise ValueError("Company-event evidence checksum differs from download")
            content = json.loads(path.read_text(encoding="utf-8"))
            for kind, rows in content["corporate_actions"].items():
                for record in rows:
                    event_id = record.get("id")
                    if not isinstance(event_id, str) or not event_id:
                        raise ValueError("Company-event record lacks an identifier")
                    identity = (kind, event_id)
                    if identity in seen:
                        continue
                    seen.add(identity)
                    candidates.append({
                        "event_id": event_id, "type": kind, "queried_symbol": probe["symbol"],
                        "raw_page": page["path"], "raw_page_sha256": page["sha256"],
                        "source_record": record, "instrument_id": None,
                        "historical_known_at": None, "cash_available_session": None,
                        "ready_for_simulation": False,
                        "review_required": "Verify security identity, historical publication, effective event, entitlement and actual cash/share availability.",
                    })
    result = {"schema_version": 1, "source_access_report_sha256": hashlib.sha256((directory / "report.json").read_bytes()).hexdigest(),
              "candidates": candidates, "automatic_universe_inference": False}
    destination.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"candidate_records": len(candidates), "ready_for_simulation": 0}), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    command = parser.add_mutually_exclusive_group(required=True)
    command.add_argument("--output", type=Path)
    command.add_argument("--review-existing", type=Path, help="Offline normalization of hashed raw event pages")
    args = parser.parse_args()
    if args.review_existing is not None:
        review_existing(args.review_existing)
    else:
        run_probe(args.output)


if __name__ == "__main__":
    main()

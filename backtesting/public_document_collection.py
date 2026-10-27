"""Bounded, credential-free archival of explicitly reviewed primary URLs.

No brokerage access, retries, redirects or automatic link following. A batch
stops on access/payment/rate barriers and never changes a subscription.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urlsplit

import requests


def collect(queue_path, output):
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    budget = queue.get("max_http_attempts")
    if (type(queue.get("purchases_budget_usd")) not in (int, float) or queue["purchases_budget_usd"] != 0
            or type(budget) is not int or not 1 <= budget <= 40):
        raise ValueError("Only the no-purchase bounded public-document protocol is supported")
    if output.exists():
        raise FileExistsError("Choose a fresh public-document batch directory")
    entries = queue.get("documents")
    if not isinstance(entries, list) or not entries or len(entries) > budget:
        raise ValueError("A nonempty document list must fit the request budget")
    domains = queue.get("allowed_domains")
    if not isinstance(domains, list) or not domains or any(not isinstance(d, str) or not re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)*", d) for d in domains):
        raise ValueError("Explicit public source domains are required")
    if any(not isinstance(e, dict) or not isinstance(e.get("id"), str) for e in entries) or len({e["id"].casefold() for e in entries}) != len(entries):
        raise ValueError("Duplicate IDs or too many queued requests")
    for entry in entries:
        if (not isinstance(entry.get("url"), str) or not isinstance(entry.get("targets"), list)
                or not entry["targets"] or any(not isinstance(t, str) or not t.strip() for t in entry["targets"])):
            raise ValueError("Every document needs an explicit URL and target metadata")
        url = urlsplit(entry["url"])
        if (url.scheme != "https" or not url.hostname or url.username or url.password or url.port or url.fragment
                or not any(url.hostname == d or url.hostname.endswith("." + d) for d in domains)
                or not re.fullmatch(r"[A-Za-z0-9_]+", entry["id"])
                or re.fullmatch(r"CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]|REPORT", entry["id"], re.I)):
            raise ValueError("Unreviewed public source URL/identifier")
    output.mkdir(parents=True, exist_ok=False)
    session = requests.Session()
    session.trust_env = False  # No ambient authentication, netrc or proxy credentials.
    report = dict(queue_sha256=hashlib.sha256(queue_path.read_bytes()).hexdigest(),
                  code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  attempts=[], network_http_attempts=0, purchases_usd=0, broker_requests=0,
                  orders=0, subscription_changes=0, stopped=False,
                  automatic_retries=False, automatic_redirects=False)
    try:
        for index, entry in enumerate(entries):
            if index:
                time.sleep(1.1)
            item = dict(id=entry["id"], url=entry["url"], targets=entry["targets"],
                        started_utc=datetime.now(timezone.utc).isoformat())
            report["network_http_attempts"] += 1
            try:
                with session.get(entry["url"], headers={"User-Agent": "HistoricalDataResearch/1.0 (public document archival)",
                                                      "Accept": "text/html,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*"},
                                 timeout=30, allow_redirects=False, stream=True) as response:
                    item["status_code"] = response.status_code
                    if 300 <= response.status_code < 400:
                        item.update(status="redirect_requires_review", location=response.headers.get("Location"))
                    elif response.status_code in {401, 402, 403, 407, 429}:
                        item["status"] = "access_or_rate_barrier"
                        report["stopped"] = True
                    elif response.status_code != 200:
                        item["status"] = "unavailable_no_retry"
                    else:
                        body = bytearray()
                        for chunk in response.iter_content(65536):
                            body.extend(chunk)
                            if len(body) > 16 * 1024 * 1024:
                                raise ValueError("Public document exceeds 16 MB limit")
                        content_type = response.headers.get("Content-Type", "")
                        suffix = ".pdf" if body.startswith(b"%PDF") else ".xlsx" if body.startswith(b"PK") else ".html"
                        name = entry["id"] + suffix
                        (output / name).write_bytes(body)
                        item.update(status="saved_unreviewed", file=name, bytes=len(body),
                                    content_type=content_type, sha256=hashlib.sha256(body).hexdigest())
            except (requests.RequestException, ValueError) as exc:
                item.update(status="transport_or_size_failure_no_retry", error_type=type(exc).__name__)
            report["attempts"].append(item)
            (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            if report["stopped"]:
                break
    finally:
        session.close()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = collect(args.queue, args.output)
    print(json.dumps(dict(attempts=report["network_http_attempts"], stopped=report["stopped"],
                          files_saved=sum(r["status"] == "saved_unreviewed" for r in report["attempts"]))))


if __name__ == "__main__":
    main()

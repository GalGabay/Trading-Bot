"""Single capped GET batch for explicitly queued historical successor quotes.

Reuse existing fixed query builders. Preserve exact payload bytes and a
durable request journal, with no account/trading routes, retries or upgrades.
"""

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.request import ProxyHandler, build_opener

from app.broker.research_client import HistoricalResearchClient, ResearchDataError, _NoRedirects
from backtesting.broad_collection import pin
from backtesting.cohort_audit import checked_file
from backtesting.pilot_readiness_review import write_json

PLAN = Path("docs/broad_successor_collection_plan.json")
OUTPUT = Path("data/reports/broad_successor_collection_v1")
JOURNAL = Path("data/reports/broad_successor_execution.json")


class BatchStop(RuntimeError):
    pass


class RecordedResponse:
    def __init__(self, response, path, item, save):
        self.response, self.path, self.item, self.save = response, path, item, save

    def __enter__(self):
        self.response.__enter__()
        return self

    def read(self, amount):
        payload = self.response.read(amount)
        self.path.write_bytes(payload)
        self.item.update(state="response_saved", source=pin(self.path), bytes=len(payload))
        self.save()
        return payload

    def __exit__(self, *args):
        return self.response.__exit__(*args)


class RecordedOpener:
    def __init__(self, report, save, limits):
        self.opener = build_opener(ProxyHandler({}), _NoRedirects())
        self.report, self.save, self.limits = report, save, limits
        self.started = time.monotonic()
        self.page_path = None
        self.probe_id = self.resource = None

    def open(self, request, timeout):
        now = time.monotonic()
        remaining = self.limits["max_elapsed_minutes"] * 60 - (now - self.started)
        if remaining <= 0 or len(self.report["attempts"]) >= self.limits["max_http_attempts"]:
            raise BatchStop("elapsed_or_request_cap")
        item = dict(number=len(self.report["attempts"]) + 1, probe_id=self.probe_id,
                    resource=self.resource, state="started", elapsed_seconds=round(now-self.started, 3))
        self.report["attempts"].append(item)
        self.save()
        try:
            response = self.opener.open(request, timeout=min(timeout, remaining))
            return RecordedResponse(response, self.page_path, item, self.save)
        except HTTPError as exc:
            item.update(state="http_error", http_status=exc.code)
            raise
        except (OSError, EOFError):
            item["state"] = "transport_failure"
            raise
        finally:
            self.save()


def load_plan():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    scope = json.loads(checked_file(Path.cwd(), plan["scope"]).read_text(encoding="utf-8"))
    if plan["limits"] != scope["price_collection_limits"] or plan["purchases_usd"] != 0:
        raise ValueError("Frozen no-purchase scope changed")
    probes = plan["probes"]
    if not 0 < len(probes) <= 32 or len({p["id"] for p in probes}) != len(probes):
        raise ValueError("Require unique finite probe intervals")
    for entry in plan["inputs"]:
        checked_file(Path.cwd(), entry)
    for path, sha in plan["execution_sha256"].items():
        checked_file(Path.cwd(), dict(path=path, sha256=sha))
    for p in probes:
        HistoricalResearchClient._symbol(p["symbol"])
        if p["symbol"] == "JPM" or not "2016-01-01" <= p["start"] < p["end_exclusive"] <= "2024-01-01":
            raise ValueError("Probe outside authorized development scope")
        for key in ("start", "end_exclusive"):
            datetime.strptime(p[key], "%Y-%m-%d")
    return plan


def collect():
    plan = load_plan()
    if OUTPUT.exists():
        raise FileExistsError("Original successor output cannot be overwritten")
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with JOURNAL.open("x", encoding="utf-8") as handle:
        json.dump(dict(plan=pin(PLAN), state="started_do_not_retry"), handle)
    OUTPUT.mkdir()
    write_json(OUTPUT / "frozen_plan.json", plan)
    report = dict(plan=pin(PLAN), attempts=[], probes=[], completed=False, stop_reason=None,
                  orders=0, purchases_usd=0, account_requests=0, strategy_runs=0)

    def save():
        write_json(OUTPUT / "report.json", report)

    save()
    try:
        client = HistoricalResearchClient()
        recorder = RecordedOpener(report, save, plan["limits"])
        client._opener = recorder
        for index, probe in enumerate(plan["probes"], 1):
            folder = OUTPUT / f"{index:03d}"
            folder.mkdir()
            item = dict(**probe, bars={"status":"pending"}, actions={"status":"pending"})
            report["probes"].append(item)
            for resource in ("bars", "actions"):
                result = item[resource] = dict(status="collecting", pages=[])
                token, tokens = None, set()
                try:
                    for number in range(plan["limits"]["max_pages_per_resource"]):
                        if len(report["attempts"]) >= plan["limits"]["max_http_attempts"]:
                            raise BatchStop("cumulative_request_cap")
                        recorder.page_path = folder / f"{resource}_{number+1}.json"
                        recorder.probe_id, recorder.resource = probe["id"], resource
                        if resource == "bars":
                            payload = client.bars_page(symbol=probe["symbol"],
                                start=datetime.fromisoformat(probe["start"]).replace(tzinfo=UTC),
                                end_exclusive=datetime.fromisoformat(probe["end_exclusive"]).replace(tzinfo=UTC), token=token)
                        else:
                            payload = client.actions_page(symbol=probe["symbol"], token=token)
                        result["pages"].append(pin(recorder.page_path))
                        token = payload.get("next_page_token")
                        if token is None:
                            result["status"] = "downloaded_candidate"
                            break
                        if not isinstance(token, str) or not token or token in tokens:
                            raise ValueError("invalid_or_repeated_pagination")
                        tokens.add(token)
                    else:
                        result["status"] = "incomplete_page_cap"
                except ResearchDataError as exc:
                    code = exc.status_code
                    result.update(status="unavailable_no_retry", http_status=code)
                    if code not in {400, 404, 422}:
                        report["stop_reason"] = "access_rate_server_or_transport_stop"
                        raise BatchStop(report["stop_reason"]) from None
                except (OSError, EOFError):
                    report["stop_reason"] = "response_transport_stop"
                    raise BatchStop(report["stop_reason"]) from None
                except ValueError:
                    result["status"] = "invalid_saved_response"
                finally:
                    save()
            print(json.dumps(dict(index=index, id=probe["id"], bars=item["bars"]["status"],
                                  actions=item["actions"]["status"], attempts=len(report["attempts"]))), flush=True)
        report["completed"] = True
    except BatchStop as exc:
        report["stop_reason"] = str(exc)
    except Exception as exc:
        report["stop_reason"] = "local_failure_" + type(exc).__name__
    finally:
        save()
        write_json(JOURNAL, dict(plan=pin(PLAN), report=pin(OUTPUT / "report.json"),
                                 state="closed_do_not_restart", actual_attempts=len(report["attempts"])))
    return dict(completed=report["completed"], attempts=len(report["attempts"]), stop_reason=report["stop_reason"])


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(collect(), indent=2))

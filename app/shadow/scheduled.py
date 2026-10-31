"""Local heartbeat/failure reports around one bounded shadow tick.

No notification transport or scheduler installation is provided here. Status
reads only local files. A tick delegates data access to the existing controller.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import uuid

from app.shadow import repeat
from app.shadow.config import ROOT, canonical, load_config, read_json, utc
from app.shadow.repeat_state import RepeatError, controller_lock

DEFAULT_REPORTS = ROOT / "data/shadow/schedule"


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                dir=path.parent, prefix=".heartbeat-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(canonical(value) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def publish(directory, event, phase):
    # Each phase is immutable; only the pointer is replaced atomically.
    from app.shadow.store import write_once
    path = Path(directory) / "runs" / f"{event['id']}.{phase}.json"
    write_once(path, canonical(event) + "\n")
    atomic_json(Path(directory) / "latest.json", dict(path=str(path.resolve()),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest()))


def controller_health(value):
    issues = []
    if not value["policy_matches"]:
        issues.append("policy_changed")
    if value["state"] in ("halted", "running"):
        issues.append("controller_" + value["state"])
    elif value["state"] in ("paused", "finished") or value["action"]["action"] == "finished":
        issues.append("controller_" + ("finished" if value["action"]["action"] == "finished" else value["state"]))
    if value["latest_global_blockers"]:
        issues.append("observation_blocked")
    if value["latest_unavailable_symbols"]:
        issues.append("symbols_unavailable")
    errors = {"policy_changed", "controller_halted", "controller_running", "observation_blocked"}
    return issues, 2 if errors.intersection(issues) else (3 if issues else 0)


def tick(directory, report_directory, config, repeat_config):
    with controller_lock(Path(report_directory) / "wrapper_lock"):
        event = dict(id=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex,
            started_at=now(), phase="started", mode="shadow_observation_only",
            campaign=str(Path(directory).resolve()), issues=[], exit_code=None,
            orders=0, simulated_fills=0)
        publish(report_directory, event, "started")
        try:
            before = repeat.status(directory, config, repeat_config)
            if before["policy_matches"]:
                repeat.tick(directory, config, repeat_config)
            after = repeat.status(directory, config, repeat_config)
            issues, exit_code = controller_health(after)
            event.update(controller=after, issues=issues, exit_code=exit_code)
        except (Exception, KeyboardInterrupt) as exc:
            # No raw client exceptions, request headers, tokens or credentials.
            event.update(issues=["tick_stopped"], exit_code=2, error_type=type(exc).__name__)
        event.update(phase="finished", finished_at=now())
        publish(report_directory, event, "finished")
        return event


def health(report_directory, *, stale_minutes=90):
    directory = Path(report_directory)
    result = dict(checked_at=now(), issues=[], exit_code=0, last_run=None,
        message="Local heartbeat only; scheduler registration is not inferred")
    try:
        pointer = read_json(directory / "latest.json")
        path = Path(pointer["path"])
        # Refuse arbitrary paths from a damaged pointer, including symlinks out.
        if path.resolve().parent != (directory / "runs").resolve():
            raise ValueError("Heartbeat pointer outside run archive")
        if hashlib.sha256(path.read_bytes()).hexdigest() != pointer["sha256"]:
            raise ValueError("Heartbeat checksum differs")
        event = read_json(path)
        if (not isinstance(event,dict) or event.get("phase") not in ("started","finished") or
                not isinstance(event.get("issues"),list) or
                any(not isinstance(issue,str) for issue in event["issues"]) or
                not isinstance(event.get("controller",{}),dict)):
            raise ValueError("Malformed heartbeat event")
        if event["phase"] == "finished":
            if type(event.get("exit_code")) is not int or event["exit_code"] not in (0,2,3):
                raise ValueError("Malformed heartbeat exit code")
        elif event.get("exit_code") is not None:
            raise ValueError("Started event must not claim a completion code")
        result["last_run"] = event
        started = utc(event["started_at"])
        ended = utc(event["finished_at"]) if event["phase"] == "finished" else started
        age = (utc(result["checked_at"]) - ended).total_seconds()
        if age < -5 or ended < started or (started-utc(result["checked_at"])).total_seconds() > 5:
            result.update(issues=["heartbeat_clock_inconsistent"], exit_code=2)
        elif event["phase"] == "started":
            result.update(issues=["interrupted_or_stuck" if age > 600 else "tick_in_progress"],
                exit_code=2 if age > 600 else 3)
        else:
            result.update(issues=list(event["issues"]), exit_code=event["exit_code"])
        controller = event.get("controller", {})
        if controller.get("expires_at") and utc(result["checked_at"]) >= utc(controller["expires_at"]):
            result["issues"].append("campaign_expired")
            if result["exit_code"] == 0:
                result["exit_code"] = 3
        if age > stale_minutes * 60:
            result["issues"].append("heartbeat_stale")
            if result["exit_code"] == 0:
                result["exit_code"] = 3
        result["heartbeat_age_seconds"] = age
    except FileNotFoundError:
        result.update(issues=["no_heartbeat_or_missing_artifact"], exit_code=3)
    except (ValueError, KeyError, TypeError, OSError):
        result.update(issues=["heartbeat_unreadable"], exit_code=2)
    # Launcher failures can happen before Python starts. A successful later
    # run supersedes that failure; older failure files remain as evidence.
    fallback = directory / "launcher_failure.json"
    if fallback.exists():
        try:
            failure = read_json(fallback)
            failure_time = utc(failure["failed_at"])
            last_time = None if result["last_run"] is None else utc(result["last_run"]["started_at"])
            if last_time is None or failure_time >= last_time:
                result.update(issues=[*result["issues"], "launcher_failed"], exit_code=2,
                    launcher_failure=failure)
        except (ValueError, KeyError, TypeError, OSError):
            result.update(issues=[*result["issues"], "launcher_failure_unreadable"], exit_code=2)
    return result


def render(value):
    if "last_run" in value:
        event = value["last_run"]
        session = None if not event else event.get("controller", {}).get("last_session")
        return (f"Shadow schedule health: {'OK' if not value['issues'] else ', '.join(value['issues'])}\n"
            f"Last session: {session} | heartbeat age: {value.get('heartbeat_age_seconds', 'unavailable')} seconds\n"
            f"{value['message']}\n")
    return f"Shadow scheduled tick: {value['phase']} | exit {value['exit_code']} | issues: {value['issues']}\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("tick", "status"))
    parser.add_argument("--directory", type=Path, default=repeat.DEFAULT_DIRECTORY)
    parser.add_argument("--report-directory", type=Path, default=DEFAULT_REPORTS)
    parser.add_argument("--config", type=Path, default=ROOT / "config/shadow_observer.json")
    parser.add_argument("--repeat-config", type=Path, default=ROOT / "config/shadow_repeat.json")
    parser.add_argument("--review-directory", type=Path, help="Verify prepared schedule/source pins before an OS-triggered tick")
    parser.add_argument("--stale-minutes", type=int, default=90)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        if not 30 <= args.stale_minutes <= 1440:
            raise ValueError("Heartbeat threshold must be 30-1440 minutes")
        if args.command == "status":
            result = health(args.report_directory, stale_minutes=args.stale_minutes)
        else:
            if args.review_directory is not None:
                from app.shadow.schedule import verify
                reviewed = verify(args.review_directory, require_ready=False)
                manifest = read_json(args.review_directory / "manifest.json")
                if Path(reviewed["campaign"]).resolve() != args.directory.resolve() or Path(manifest["reports"]).resolve() != args.report_directory.resolve():
                    raise ValueError("Runtime directories differ from reviewed schedule")
                # Prepared OS jobs use the pinned default configuration paths.
                if (args.config.resolve() != ROOT / "config/shadow_observer.json" or
                        args.repeat_config.resolve() != ROOT / "config/shadow_repeat.json"):
                    raise ValueError("OS task configuration paths differ from review")
            result = tick(args.directory, args.report_directory, load_config(args.config),
                repeat.load_repeat_config(args.repeat_config))
        print(canonical(result) if args.json else render(result), flush=True)
        return result["exit_code"]
    except (Exception, KeyboardInterrupt) as exc:
        print(f"Shadow schedule stopped ({type(exc).__name__}); inspect local reports and task result.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

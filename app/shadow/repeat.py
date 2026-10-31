"""Bounded, calendar-aware repeat observation; no scheduler or trading actions.

The controller never carries proposed buys into the reference book. Each daily
report uses the same flat reference as the one-shot observer. Requests are
reserved durably before credentials are loaded. Failed/uncertain reservations
remain charged, and a failure requires an explicit resume, never a retry loop.
"""

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
from importlib.metadata import version
from pathlib import Path
import sqlite3
import sys
import time

import pandas as pd

from app.shadow.config import ROOT, canonical, digest, implementation, load_config, read_json, utc
from app.shadow.observer import markdown, observe, sessions_from
from app.shadow.repeat_state import RepeatError, controller_lock, read_state, save_state
from app.shadow.store import ObservationStore, write_once

DEFAULT_DIRECTORY = ROOT / "data/shadow/repeat"


def clock():
    return utc(datetime.now(timezone.utc))


@dataclass(frozen=True)
class RepeatConfig:
    campaign_days: int = 30
    max_collection_attempts: int = 22
    max_calendar_attempts: int = 35
    max_reserved_requests: int = 2500
    poll_seconds: int = 300

    def __post_init__(self):
        bounds = dict(campaign_days=(1, 30), max_collection_attempts=(1, 30),
            max_calendar_attempts=(1, 35), max_reserved_requests=(1, 3500),
            poll_seconds=(60, 3600))
        for name, (low, high) in bounds.items():
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise RepeatError(f"{name} must be an integer between {low} and {high}")


def load_repeat_config(path):
    raw = read_json(path)
    if not isinstance(raw, dict) or set(raw) != set(RepeatConfig.__dataclass_fields__):
        raise RepeatError("Repeat config requires exactly the documented budget fields")
    return RepeatConfig(**raw)


def policy(config, repeat_config):
    sources = implementation()
    for name in ("app/shadow/repeat.py", "app/shadow/repeat_state.py"):
        sources[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    return dict(shadow=config.record(), repeat=asdict(repeat_config), implementation=sources,
        environment=dict(python=sys.version.split()[0], pandas=pd.__version__,
            numpy=version("numpy"), alpaca_py=version("alpaca-py")))


def pin(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def pinned_json(reference):
    if hashlib.sha256(Path(reference["path"]).read_bytes()).hexdigest() != reference["sha256"]:
        raise RepeatError("Saved repeat artifact checksum differs")
    return read_json(reference["path"])


def assert_policy(state, config, repeat_config):
    if digest(state["policy"]) != digest(policy(config, repeat_config)):
        raise RepeatError("Code/config/environment changed; retain this campaign and initialize a new directory")


def initialize(directory, config, repeat_config, seed_bundle, seed_database):
    """Adopt the already reviewed observation; no new data request or evaluation."""
    with controller_lock(directory):
        if (Path(directory) / "campaign.json").exists():
            raise RepeatError("Campaign already exists; init cannot reset its budgets")
        if (Path(directory) / "observations.sqlite3").exists():
            raise RepeatError("Choose a fresh controller directory; journal already exists")
        report = ObservationStore(seed_database).latest()
        if seed_bundle is None:
            seed_bundle = ROOT / "data/shadow/bundles" / (report["bundle_sha256"] + ".json")
        bundle = read_json(seed_bundle)
        current_policy = policy(config, repeat_config)
        if (digest(bundle) != report["bundle_sha256"] or
                digest(report["config"]) != digest(config.record()) or
                report["implementation"] != implementation() or
                report["environment"] != current_policy["environment"]):
            raise RepeatError("Seed must match the current observer code/config/environment and saved journal")
        if (report["mode"] != "shadow_observation_only" or report["reference"] is None or
                report["reference"]["positions"] or
                report["reference"]["cash"] != config.reference_cash or
                report["orders_submitted"] != 0 or report["simulated_fills"] != 0):
            raise RepeatError("Repeated observation requires the reviewed flat, no-fill reference")
        sessions_from(bundle["calendar"])
        now = clock()
        if utc(bundle["observed_at"]) > now:
            raise RepeatError("Seed observation is in the future")
        directory = Path(directory)
        destination = directory / "reports" / report["id"]
        write_once(destination.with_suffix(".json"), canonical(report) + "\n")
        write_once(destination.with_suffix(".md"), markdown(report))
        state = dict(schema_version=1, status="ready", created_at=now.isoformat(),
            expires_at=(now + timedelta(days=repeat_config.campaign_days)).isoformat(),
            policy=current_policy, last_session=report["session"],
            latest_report=pin(destination.with_suffix(".json")), seed_bundle=pin(seed_bundle),
            calendar=bundle["calendar"], calendar_checked_at=bundle["observed_at"],
            collection_attempts=0, calendar_attempts=0, reserved_requests=0,
            known_requests=0, pending=None, events=[], reason=None)
        save_state(directory, state)
        return state


def plan(state, config, now):
    """No network. Use actual cached sessions; never guess holidays or missed bars."""
    now = utc(now)
    if state["status"] != "ready":
        return dict(action=state["status"], reason=state.get("reason"), next_at=None)
    if now >= utc(state["expires_at"]):
        return dict(action="finished", reason="Campaign duration exhausted", next_at=None)
    sessions = sessions_from(state["calendar"])
    # A once-per-New-York-date refresh also catches revised early closes/closures.
    # Never treat the absence of a future session as evidence of a holiday.
    local_day = now.tz_convert("America/New_York").date()
    if (local_day > utc(state["calendar_checked_at"]).tz_convert("America/New_York").date()
            or local_day > sessions[-1].opens_at.tz_convert("America/New_York").date()):
        return dict(action="refresh_calendar", reason="Calendar needs a current-date refresh", next_at=now.isoformat())
    settled = [(s, s.closes_at + timedelta(minutes=config.close_settle_minutes)) for s in sessions]
    completed = [s for s, ready in settled if ready <= now]
    future = [ready for _, ready in settled if ready > now]
    midnight = (now.tz_convert("America/New_York").normalize() + pd.DateOffset(days=1)).tz_convert("UTC")
    next_at = min([midnight, utc(state["expires_at"]), *future]).isoformat()
    if not completed or completed[-1].opens_at.date().isoformat() <= state["last_session"]:
        return dict(action="waiting", reason="No new completed, settled session", next_at=next_at)
    latest = completed[-1]
    following = [s for s in sessions if s.opens_at > latest.closes_at]
    if not following:
        return dict(action="halted", reason="Calendar has no following session; cannot establish signal expiry", next_at=None)
    if now >= following[0].opens_at:
        return dict(action="waiting", reason="Missed session signal already expired; wait for a new settled close",
            next_at=next_at, expired_session=latest.opens_at.date().isoformat())
    return dict(action="collect", reason="New completed session", next_at=now.isoformat(),
        session=latest.opens_at.date().isoformat(), missed_sessions=[s.opens_at.date().isoformat()
            for s in completed if state["last_session"] < s.opens_at.date().isoformat() < latest.opens_at.date().isoformat()])


def reserve(directory, state, repeat_config, operation, target=None, missed=None):
    cost = 110 if operation == "collect" else 1
    field = "collection_attempts" if operation == "collect" else "calendar_attempts"
    limit = repeat_config.max_collection_attempts if operation == "collect" else repeat_config.max_calendar_attempts
    if state[field] >= limit or state["reserved_requests"] + cost > repeat_config.max_reserved_requests:
        state.update(status="finished", reason="Campaign attempt/request reservation budget exhausted")
        save_state(directory, state)
        return False
    state[field] += 1
    state["reserved_requests"] += cost
    state.update(status="running", reason=None, pending=dict(operation=operation, target=target,
        missed_sessions=missed or [], started_at=clock().isoformat(), reserved_requests=cost,
        known_requests=None, phase="reserved"))
    save_state(directory, state)
    return True


def client_for(state):
    from app.shadow.data import ShadowDataClient, ShadowDataError

    class CampaignClient(ShadowDataClient):
        def _get(self, path, params=None):
            if self.request_count >= state["pending"]["reserved_requests"] or clock() >= utc(state["expires_at"]):
                raise ShadowDataError("Repeat request reservation or campaign deadline exhausted")
            return super()._get(path, params)

    return CampaignClient()


def halt(directory, state, exc):
    # Do not persist exception strings from network/client libraries or credentials.
    from app.shadow.data import ShadowDataError
    detail = str(exc) if isinstance(exc, (RepeatError, ShadowDataError)) else "operation stopped"
    state.update(status="halted", reason=f"{type(exc).__name__}: {detail}; inspect artifacts, then resume explicitly")
    save_state(directory, state)


def complete_pending(directory, state, event):
    pending = state["pending"]
    if pending["known_requests"] is not None:
        state["known_requests"] += pending["known_requests"]
    state["events"].append(dict(pending, result=event, finished_at=clock().isoformat()))
    state.update(pending=None, status="ready", reason=None)
    save_state(directory, state)


def finalize_collection(directory, state, config):
    """Recover purely from an immutable collected bundle, including after a crash."""
    pending = state["pending"]
    assert_policy(state, config, RepeatConfig(**state["policy"]["repeat"]))
    bundle = pinned_json(pending["bundle"])
    report = observe(bundle, config)
    if report["session"] != pending["target"]:
        raise RepeatError("Collected completed session differs from the reserved session")
    assert_policy(state, config, RepeatConfig(**state["policy"]["repeat"]))
    destination = Path(directory) / "reports" / report["id"]
    write_once(destination.with_suffix(".json"), canonical(report) + "\n")
    write_once(destination.with_suffix(".md"), markdown(report))
    # This DB is separate from both trading and the reviewed one-shot journal.
    ObservationStore(Path(directory) / "observations.sqlite3").record(report)
    state.update(last_session=report["session"], latest_report=pin(destination.with_suffix(".json")),
        calendar=bundle["calendar"], calendar_checked_at=bundle["observed_at"])
    pending["report"] = state["latest_report"]
    pending["global_blockers"] = report["global_blockers"]
    pending["unavailable_symbols"] = [r["symbol"] for r in report["signals"] if r["signal"] == "UNAVAILABLE"]
    # Data blockers remain visible in the day's report. No second collection is
    # used to erase a bad-data result; the next new session may be observed.
    complete_pending(directory, state, "recorded")


def tick(directory, config, repeat_config):
    with controller_lock(directory):
        state = read_state(directory)
        assert_policy(state, config, repeat_config)
        if state["status"] == "running":
            if state["pending"].get("bundle"):
                try:
                    finalize_collection(directory, state, config)
                except (Exception, KeyboardInterrupt) as exc:
                    halt(directory, state, exc)
                return state
            halt(directory, state, RepeatError("Interrupted request; remote outcome unknown"))
            return state
        action = plan(state, config, clock())
        if action["action"] in ("halted", "finished"):
            state.update(status=action["action"], reason=action["reason"])
            save_state(directory, state)
            return state
        if action["action"] not in ("refresh_calendar", "collect"):
            return state
        # At most one calendar refresh followed by one full collection per tick.
        for _ in range(2):
            operation = action["action"]
            if not reserve(directory, state, repeat_config, operation,
                    action.get("session"), action.get("missed_sessions")):
                return state
            client = None
            try:
                client = client_for(state)
                if operation == "refresh_calendar":
                    now = clock()
                    rows = client._get("/v2/calendar", dict(start=config.history_start,
                        end=(now + timedelta(days=14)).date().isoformat()))
                    if not isinstance(rows, list) or not rows or len(rows) > 5000:
                        raise RepeatError("Invalid or oversized calendar")
                    sessions = sessions_from(rows)
                    if (sessions[0].opens_at.date().isoformat() < config.history_start or
                            sessions[-1].opens_at <= now or
                            not any(s.opens_at.date().isoformat() == state["last_session"] for s in sessions)):
                        raise RepeatError("Calendar does not cover the current campaign and following sessions")
                    state.update(calendar=rows, calendar_checked_at=now.isoformat())
                    state["pending"]["known_requests"] = client.request_count
                    complete_pending(directory, state, "calendar_refreshed")
                    action = plan(state, config, clock())
                    if action["action"] == "collect":
                        continue
                    if action["action"] in ("halted", "finished"):
                        state.update(status=action["action"], reason=action["reason"])
                        save_state(directory, state)
                    return state
                bundle = client.collect(config)
                path = Path(directory) / "bundles" / (digest(bundle) + ".json")
                write_once(path, canonical(bundle) + "\n")
                state["pending"].update(bundle=pin(path), phase="bundle_saved", known_requests=client.request_count)
                save_state(directory, state)
                finalize_collection(directory, state, config)
                return state
            except (Exception, KeyboardInterrupt) as exc:
                if client is not None and state.get("pending") is not None:
                    state["pending"]["known_requests"] = client.request_count
                halt(directory, state, exc)
                return state
        return state


def change_status(directory, config, repeat_config, command):
    with controller_lock(directory):
        state = read_state(directory)
        assert_policy(state, config, repeat_config)
        if state["status"] == "running":
            raise RepeatError("Run tick first to reconcile an interrupted operation")
        if command == "pause":
            state.update(status="paused", reason="Paused explicitly")
        elif state["status"] in ("halted", "paused"):
            if clock() >= utc(state["expires_at"]):
                raise RepeatError("Campaign expired; resume cannot extend it")
            if state["pending"]:
                if state["pending"].get("bundle"):
                    # Recover this same immutable observation; never recollect it.
                    state.update(status="running", reason=None)
                    save_state(directory, state)
                    return state
                state["events"].append(dict(state["pending"], result="abandoned_explicitly",
                    finished_at=clock().isoformat()))
                if state["pending"]["known_requests"] is not None:
                    state["known_requests"] += state["pending"]["known_requests"]
            state.update(status="ready", reason=None, pending=None)
        else:
            raise RepeatError("Only a halted or paused campaign can resume; finished budgets cannot reset")
        save_state(directory, state)
        return state


def status(directory, config, repeat_config):
    state = read_state(directory)
    now = clock()
    current = digest(state["policy"]) == digest(policy(config, repeat_config))
    report = pinned_json(state["latest_report"])
    expiry = report["next_session_open"]
    return dict(mode="shadow_observation_only", now=now.isoformat(), state=state["status"],
        policy_matches=current, action=plan(state, config, now) if current else
            dict(action="halted", reason="Code/config/environment differs; use a new campaign", next_at=None),
        expires_at=state["expires_at"], last_session=state["last_session"],
        report_observed_at=report["observed_at"], signal_expires_at=expiry,
        signals_expired=expiry is None or now >= utc(expiry), latest_report=state["latest_report"]["path"],
        reserved_requests=state["reserved_requests"], request_limit=repeat_config.max_reserved_requests,
        known_requests=state["known_requests"] + ((state["pending"]["known_requests"] or 0) if state["pending"] else 0),
        pending=state["pending"],
        unknown_request_attempts=sum(e["known_requests"] is None for e in state["events"]) +
            int(state["pending"] is not None and state["pending"]["known_requests"] is None),
        collection_attempts=state["collection_attempts"], collection_limit=repeat_config.max_collection_attempts,
        calendar_attempts=state["calendar_attempts"], calendar_limit=repeat_config.max_calendar_attempts,
        recent_events=state["events"][-5:], orders=0, simulated_fills=0,
        latest_global_blockers=report["global_blockers"],
        latest_unavailable_symbols=[row["symbol"] for row in report["signals"] if row["signal"] == "UNAVAILABLE"],
        scheduler_installed_by_this_controller=False)


def render(value):
    action = value["action"]
    return (f"Shadow repeat: {value['state']} | policy matches: {value['policy_matches']}\n"
        f"Last session: {value['last_session']} | signals expired: {value['signals_expired']}\n"
        f"Next action: {action['action']} | {action.get('reason')}\n"
        f"Next check: {action.get('next_at')} | campaign ends: {value['expires_at']}\n"
        f"Collections: {value['collection_attempts']}/{value['collection_limit']} | "
        f"calendar refreshes: {value['calendar_attempts']}/{value['calendar_limit']}\n"
        f"Reserved requests: {value['reserved_requests']}/{value['request_limit']} | "
        f"known requests: {value['known_requests']} | unknown attempts: {value['unknown_request_attempts']}\n"
        f"Report blockers: {value['latest_global_blockers']} | unavailable: {value['latest_unavailable_symbols']}\n"
        f"Report: {value['latest_report']}\n"
        "No orders, fills, carried positions or P&L. No OS scheduler installed.\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "tick", "run", "status", "latest", "pause", "resume"))
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY)
    parser.add_argument("--config", type=Path, default=ROOT / "config/shadow_observer.json")
    parser.add_argument("--repeat-config", type=Path, default=ROOT / "config/shadow_repeat.json")
    parser.add_argument("--seed-bundle", type=Path)
    parser.add_argument("--seed-database", type=Path, default=ROOT / "data/shadow/observer.sqlite3")
    parser.add_argument("--hours", type=float, default=8, help="Foreground run duration, >0 and <=24 hours")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        config, repeat_config = load_config(args.config), load_repeat_config(args.repeat_config)
        if not 0 < args.hours <= 24:
            raise RepeatError("Foreground duration must be >0 and <=24 hours")
        if args.command == "init":
            initialize(args.directory, config, repeat_config, args.seed_bundle, args.seed_database)
        elif args.command in ("pause", "resume"):
            change_status(args.directory, config, repeat_config, args.command)
        elif args.command == "latest":
            print(markdown(pinned_json(read_state(args.directory)["latest_report"])))
            return
        elif args.command in ("tick", "run"):
            until = time.monotonic() + args.hours * 3600
            while True:
                tick(args.directory, config, repeat_config)
                value = status(args.directory, config, repeat_config)
                print(canonical(value) if args.json else render(value), flush=True)
                if args.command == "tick" or value["state"] in ("halted", "finished", "paused"):
                    if value["state"] == "halted":
                        return 2
                    return 0
                remaining = until - time.monotonic()
                if remaining <= 0:
                    return 0
                next_at = value["action"].get("next_at")
                delay = repeat_config.poll_seconds
                if next_at is not None:
                    delay = min(delay, max(1, (utc(next_at) - clock()).total_seconds()))
                deadline = time.monotonic() + min(delay, remaining)
                while time.monotonic() < deadline:
                    time.sleep(min(60, max(0, deadline - time.monotonic())))
        value = status(args.directory, config, repeat_config)
        print(canonical(value) if args.json else render(value))
        return 0
    except KeyboardInterrupt:
        print("Foreground observer stopped. Saved state is retained; no background task remains.", file=sys.stderr)
        return 130
    except RepeatError as exc:
        parser.exit(2, f"Shadow repeat stopped: {exc}\n")
    except FileNotFoundError:
        parser.exit(2, "Shadow repeat stopped: required config/state/artifact is missing. Run init once for a new campaign; retain existing budgets.\n")
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, sqlite3.Error) as exc:
        # Avoid leaking headers/credentials from low-level exception contents.
        parser.exit(2, f"Shadow repeat stopped ({type(exc).__name__}); inspect saved status/artifacts.\n")


if __name__ == "__main__":
    raise SystemExit(main())

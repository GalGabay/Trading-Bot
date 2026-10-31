"""Crash-safe local controller state and a process lock for Windows/Linux."""

from contextlib import contextmanager
import os
from pathlib import Path
import tempfile

from app.shadow.config import canonical, digest, read_json


class RepeatError(ValueError):
    """Controller-owned messages that contain no transport headers or secrets."""


@contextmanager
def controller_lock(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "controller.lock").open("a+b") as handle:
        handle.seek(0, 2)
        if not handle.tell():
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RepeatError("Another repeat controller is running; no concurrent collection allowed") from None
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def read_state(directory):
    envelope = read_json(Path(directory) / "campaign.json")
    if set(envelope) != {"payload", "sha256"} or digest(envelope["payload"]) != envelope["sha256"]:
        raise RepeatError("Repeat state checksum differs; restore the saved state, never reset budgets")
    state = envelope["payload"]
    if state.get("schema_version") != 1:
        raise RepeatError("Unsupported repeat campaign version")
    return state


def save_state(directory, state):
    """Atomic replacement; a failed write leaves the preceding reservation intact."""
    directory = Path(directory)
    payload = canonical(dict(payload=state, sha256=digest(state))) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                prefix=".campaign-", suffix=".tmp", dir=directory, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, directory / "campaign.json")
        if os.name != "nt":
            descriptor = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

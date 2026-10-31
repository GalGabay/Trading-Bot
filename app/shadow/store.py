"""Separate append-only observation journal and immutable human-readable exports."""

from datetime import datetime, timezone
from contextlib import closing
from pathlib import Path
import sqlite3

from app.shadow.config import canonical, digest


def write_once(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    except FileExistsError:
        if path.read_text(encoding="utf-8") != text:
            raise ValueError("Shadow export already exists with different content") from None


class ObservationStore:
    def __init__(self, path):
        self.path = Path(path)

    def record(self, report):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = canonical(report)
        policy = digest(dict(config=report["config"], implementation=report["implementation"], environment=report["environment"]))
        with closing(sqlite3.connect(self.path, timeout=30)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if tables - {"shadow_meta", "shadow_observations"}:
                raise ValueError("Choose a separate shadow database; existing non-shadow tables will not be changed")
            db.execute("CREATE TABLE IF NOT EXISTS shadow_meta (singleton INTEGER PRIMARY KEY CHECK(singleton=1), policy TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS shadow_observations (id TEXT PRIMARY KEY, observed_at TEXT NOT NULL, recorded_at TEXT NOT NULL, payload TEXT NOT NULL, payload_sha256 TEXT NOT NULL)")
            existing = db.execute("SELECT policy FROM shadow_meta WHERE singleton=1").fetchone()
            if existing is not None and existing[0] != policy:
                raise ValueError("Observer config/code changed; use a new shadow database for the new version")
            db.execute("INSERT OR IGNORE INTO shadow_meta VALUES (1, ?)", (policy,))
            previous = db.execute("SELECT payload, payload_sha256 FROM shadow_observations WHERE id=?", (report["id"],)).fetchone()
            if previous is not None and (previous[0] != payload or previous[1] != digest(report)):
                raise ValueError("Observation identity conflicts with saved content")
            db.execute("INSERT OR IGNORE INTO shadow_observations VALUES (?, ?, ?, ?, ?)",
                (report["id"], report["observed_at"], datetime.now(timezone.utc).isoformat(), payload, digest(report)))
        return previous is None

    def latest(self):
        import json
        if not self.path.exists():
            raise ValueError("No shadow observation database exists yet")
        with closing(sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            row = db.execute("SELECT payload, payload_sha256 FROM shadow_observations ORDER BY observed_at DESC, recorded_at DESC LIMIT 1").fetchone()
        if row is None:
            raise ValueError("No shadow observation has been recorded")
        report = json.loads(row[0])
        if digest(report) != row[1]:
            raise ValueError("Saved observation payload checksum differs")
        return report

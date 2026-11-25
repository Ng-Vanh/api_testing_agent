"""Append-only records, immutable per-attempt JSONL and crash reconciliation."""

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.contracts import RunManifest

RecordKind = Literal["case", "step", "attempt", "assertion", "coverage", "defect", "report"]
KINDS = {"case", "step", "attempt", "assertion", "coverage", "defect", "report"}
SENSITIVE = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "password",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "apikey",
    "secret",
    "x_api_key",
}


def redact(value):
    if isinstance(value, dict):
        return {
            k: "[REDACTED]"
            if k.lower().replace("-", "_") in {s.replace("-", "_") for s in SENSITIVE}
            else redact(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(x) for x in value]
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        parts = urlsplit(value)
        query = [
            (k, "[REDACTED]" if k.lower() in SENSITIVE else v)
            for k, v in parse_qsl(parts.query, keep_blank_values=True)
        ]
        return urlunsplit(
            (parts.scheme, parts.netloc.rsplit("@", 1)[-1], parts.path, urlencode(query), "")
        )
    return value


class Store:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.database = self.directory / "tool.sqlite"
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY);
                INSERT OR IGNORE INTO schema_version VALUES (1);
                CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS records (
                  run_id TEXT REFERENCES runs(id), kind TEXT, id TEXT, payload TEXT NOT NULL,
                  digest TEXT NOT NULL, artifact TEXT NOT NULL,
                  PRIMARY KEY(run_id, kind, id));
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=5)
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def save_run(self, run: RunManifest):
        with self.connect() as db:
            db.execute("INSERT INTO runs VALUES (?, ?)", (run.run_id, run.model_dump_json()))

    def get_run(self, run_id):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM runs WHERE id=?", (run_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def finish_run(self, run_id, status):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM runs WHERE id=?", (run_id,)).fetchone()
            if row is None:
                raise ValueError("Unknown run")
            run = RunManifest.model_validate_json(row[0])
            run.status = status
            # Revalidate assignment before saving so invalid statuses cannot reach the DB.
            run = RunManifest.model_validate(run.model_dump())
            db.execute("UPDATE runs SET payload=? WHERE id=?", (run.model_dump_json(), run_id))
        return run

    def append(self, run_id: str, kind: RecordKind, record_id: str, payload: dict):
        if kind not in KINDS:
            raise ValueError("Unknown record kind")
        # Validate run identifier before constructing a filesystem path.
        run = self.get_run(run_id)
        if not run:
            raise ValueError("Unknown run")
        RunManifest.model_validate(run)
        serialized = json.dumps(redact(payload), ensure_ascii=False, sort_keys=True) + "\n"
        digest = hashlib.sha256(serialized.encode()).hexdigest()
        key = hashlib.sha256(f"{kind}:{record_id}".encode()).hexdigest()
        artifact = f"artifacts/{run_id}/{key}.jsonl"
        try:
            with self.connect() as db:
                db.execute(
                    "INSERT INTO records VALUES (?,?,?,?,?,?)",
                    (run_id, kind, record_id, serialized, digest, artifact),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Record exists; append a new attempt/event ID") from exc
        # Intent is committed before artifact write. Recovery detects incomplete writes.
        self._write_artifact(self.directory / artifact, serialized)

    @staticmethod
    def _write_artifact(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())

    def records(self, run_id, kind):
        with self.connect() as db:
            rows = db.execute(
                "SELECT payload FROM records WHERE run_id=? AND kind=? ORDER BY rowid",
                (run_id, kind),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def reconcile(self, run_id):
        issues = []
        with self.connect() as db:
            rows = db.execute(
                "SELECT artifact,digest FROM records WHERE run_id=?", (run_id,)
            ).fetchall()
        for artifact, digest in rows:
            path = self.directory / artifact
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                issues.append(f"Missing/corrupt artifact: {artifact}")
        return issues

"""Persist the same JSON report for CLI and future web consumers."""

import json
from pathlib import Path

from app.contracts import RunReport
from app.storage import Store


def write_report(store: Store, report: RunReport) -> dict:
    payload = report.model_dump(mode="json")
    # Store performs the final redaction; use exactly that view for JSON export and stdout.
    store.append(report.run.run_id, "report", "final", payload)
    payload = store.records(report.run.run_id, "report")[0]
    path = store.directory / report.report_file
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
    return payload


def read_report(directory: Path, run_id: str) -> dict:
    store = Store(directory)
    rows = store.records(run_id, "report")
    if len(rows) != 1:
        raise ValueError("No completed report for this run")
    payload = rows[0]
    # Validate without adding new default fields to previously exported reports.
    RunReport.model_validate(payload)
    if store.reconcile(run_id):
        raise ValueError("Run has missing/corrupt artifacts; cannot trust the exported report")
    expected_path = f"artifacts/{payload['run']['run_id']}/report.json"
    if payload["report_file"] != expected_path:
        raise ValueError("Invalid report path")
    file = store.directory / expected_path
    if not file.is_file() or json.loads(file.read_text(encoding="utf-8")) != payload:
        raise ValueError("Report export is missing or differs from its immutable record")
    return payload

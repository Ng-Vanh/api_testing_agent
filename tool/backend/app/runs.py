"""Shared CLI/web service entry point. No HTTP route or job queue in M1."""

import hashlib
import platform
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver

from app.config import TargetProfile
from app.contracts import RunManifest
from app.engine.reporting import read_report
from app.orchestration.graph import build_graph
from app.storage import Store, redact


def run(spec_path: Path, profile: TargetProfile, operation_id: str, directory: Path) -> dict:
    spec_path, directory = Path(spec_path), Path(directory)
    manifest = RunManifest(
        run_id=uuid4().hex,
        spec_digest=hashlib.sha256(spec_path.read_bytes()).hexdigest(),
        base_url=redact(profile.base_url),
        status="running",
        versions={"python": platform.python_version(), "langgraph": version("langgraph")},
        config_snapshot=redact(profile.model_dump(mode="json")),
    )
    store = Store(directory)
    store.save_run(manifest)
    try:
        with SqliteSaver.from_conn_string(str(directory / "checkpoints.sqlite")) as saver:
            graph = build_graph(spec_path, profile, operation_id, store).compile(checkpointer=saver)
            result = graph.invoke(
                {"run_id": manifest.run_id}, {"configurable": {"thread_id": manifest.run_id}}
            )
        return result["report"]
    except Exception:
        store.finish_run(manifest.run_id, "failed")
        raise


def load_report(directory: Path, run_id: str) -> dict:
    return read_report(directory, run_id)

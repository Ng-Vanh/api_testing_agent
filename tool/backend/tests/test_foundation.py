import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.contracts import ExecutionPlan, PlanStep, RunManifest, ValidationResult, case_verdict
from app.engine.spec import analyze
from app.main import app
from app.storage import Store

SPEC = Path(__file__).resolve().parents[3] / "QAirline/specs/qairline_openapi.json"


def test_health():
    assert TestClient(app).get("/health").json()["status"] == "ok"


def test_plan_roundtrip_and_ordered_binding():
    plan = ExecutionPlan(
        case_id="case1",
        steps=[
            PlanStep(step_id="setup", role="setup", operation_id="createFlight"),
            PlanStep(
                step_id="action", role="action", operation_id="createBooking", depends_on=["setup"]
            ),
        ],
    )
    assert ExecutionPlan.model_validate_json(plan.model_dump_json()) == plan
    with pytest.raises(ValidationError):
        ExecutionPlan(
            case_id="x",
            steps=[PlanStep(step_id="a", role="action", operation_id="x", depends_on=["missing"])],
        )


def test_missing_or_untrusted_oracle_cannot_pass():
    with pytest.raises(ValidationError):
        ValidationResult(assertion_id="x", verdict="PASS")
    with pytest.raises(ValidationError):
        ValidationResult(
            assertion_id="x",
            verdict="FAIL",
            expected=400,
            oracle={"basis": "llm", "source": "model"},
        )
    assert case_verdict(setup_ok=False, assertions=[]) == "BLOCKED"
    assert case_verdict(setup_ok=True, assertions=[]) == "UNKNOWN"


def test_storage_reopen_immutable_redacted_and_reconcile(tmp_path):
    store = Store(tmp_path)
    store.save_run(RunManifest(run_id="r1", spec_digest="abc", base_url="http://localhost:5000"))
    store.append(
        "r1", "attempt", "a1", {"headers": {"Authorization": "secret"}, "body": {"password": "pw"}}
    )
    reopened = Store(tmp_path)
    assert reopened.get_run("r1")["run_id"] == "r1"
    row = reopened.records("r1", "attempt")[0]
    assert row["body"]["password"] == "[REDACTED]"
    with pytest.raises(ValueError):
        reopened.append("r1", "attempt", "a1", {})
    assert reopened.reconcile("r1") == []
    artifact = next((tmp_path / "artifacts").rglob("*.jsonl"))
    artifact.write_text("broken")
    assert reopened.reconcile("r1")
    assert reopened.records("other", "attempt") == []


def test_storage_crash_before_artifact_is_detected(tmp_path, monkeypatch):
    store = Store(tmp_path)
    store.save_run(RunManifest(run_id="r", spec_digest="x", base_url="http://localhost:5000"))
    monkeypatch.setattr(
        store, "_write_artifact", lambda *args: (_ for _ in ()).throw(OSError("crash"))
    )
    with pytest.raises(OSError):
        store.append("r", "attempt", "a", {"status": "prepared"})
    assert Store(tmp_path).reconcile("r")


def test_parser_qairline_without_benchmark_input():
    endpoints = analyze(SPEC)
    assert len(endpoints) == 48
    # Scope selection is target configuration, not a QAirline name list in the parser.
    core_tags = {"Users", "Airports", "Aircrafts", "Flights", "Passengers", "Bookings"}
    assert sum(bool(set(e.tags) & core_tags) for e in endpoints) == 34
    airport = next(e for e in endpoints if e.operation_id == "createAirport")
    assert airport.request_body and airport.responses["201"]


def test_parser_rejects_external_refs_and_duplicate_ids(tmp_path):
    spec = json.loads(SPEC.read_text())
    spec["paths"]["/api/airports"]["get"]["responses"]["200"] = {
        "$ref": "https://evil.test/spec.json"
    }
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match="external"):
        analyze(p)
    spec = json.loads(SPEC.read_text())
    spec["paths"]["/api/airports"]["post"]["operationId"] = "listAirports"
    p.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match="operationId|unique"):
        analyze(p)


def test_storage_redacts_query_and_custom_api_key(tmp_path):
    store = Store(tmp_path)
    store.save_run(RunManifest(run_id="r", spec_digest="x", base_url="http://localhost:5000"))
    store.append(
        "r",
        "attempt",
        "a",
        {"url": "http://localhost/?token=topsecret&name=ok", "headers": {"X-API-Key": "keysecret"}},
    )
    artifact = next((tmp_path / "artifacts").rglob("*.jsonl")).read_text()
    assert "topsecret" not in artifact and "keysecret" not in artifact


def test_parser_yaml_local_refs_and_parameter_override(tmp_path):
    import yaml

    spec = json.loads(SPEC.read_text())
    spec["paths"]["/api/airports"]["parameters"] = [
        {"name": "q", "in": "query", "schema": {"type": "string"}}
    ]
    spec["paths"]["/api/airports"]["get"]["parameters"] = [
        {"name": "q", "in": "query", "schema": {"type": "integer"}}
    ]
    path = tmp_path / "spec.yaml"
    path.write_text(yaml.safe_dump(spec))
    endpoint = next(e for e in analyze(path) if e.operation_id == "listAirports")
    assert endpoint.parameters[0]["schema"]["type"] == "integer"


def test_invalid_schema_reports_location(tmp_path):
    spec = json.loads(SPEC.read_text())
    spec["paths"]["/api/airports"]["get"]["responses"]["200"] = {
        "description": "x",
        "content": {"application/json": {"schema": {"type": "not_a_type"}}},
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match="Invalid OpenAPI"):
        analyze(path)


def test_checkpoint_survives_reopening(tmp_path):
    from typing import TypedDict

    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.graph import END, START, StateGraph

    class State(TypedDict):
        count: int

    config = {"configurable": {"thread_id": "test-run"}}
    graph = StateGraph(State)
    graph.add_node("increment", lambda state: {"count": state["count"] + 1})
    graph.add_edge(START, "increment")
    graph.add_edge("increment", END)
    path = str(tmp_path / "checkpoints.sqlite")
    with SqliteSaver.from_conn_string(path) as saver:
        assert graph.compile(checkpointer=saver).invoke({"count": 0}, config)["count"] == 1
    with SqliteSaver.from_conn_string(path) as saver:
        assert graph.compile(checkpointer=saver).get_state(config).values["count"] == 1


def test_single_case_and_generated_schema_round_trip():
    from app.contracts import AbstractTestCase
    from app.contracts import TestObjective as Objective

    case = AbstractTestCase(
        case_id="airports.valid",
        objective=Objective(
            target_id="list.valid",
            operation_id="listAirports",
            intent="valid",
            description="List airports",
        ),
    )
    assert AbstractTestCase.model_validate_json(case.model_dump_json()) == case
    assert "steps" in ExecutionPlan.model_json_schema()["properties"]

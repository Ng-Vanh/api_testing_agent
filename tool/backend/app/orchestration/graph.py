"""M1 graph: normalize -> preflight -> single read case -> execute/validate -> report.

Only redacted traces enter graph state. CLI resume is intentionally unavailable until T14.
"""

import os
import time
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.config import TargetProfile
from app.contracts import (
    AbstractTestCase,
    ConcreteRequest,
    ExecutionPlan,
    Oracle,
    PlanStep,
    RunReport,
    TestObjective,
    case_verdict,
)
from app.engine.execution.http_executor import execute, public_trace
from app.engine.preflight import check
from app.engine.reporting import write_report
from app.engine.spec import analyze
from app.engine.validation import validate_response
from app.storage import Store


class RunState(TypedDict, total=False):
    run_id: str
    verdict: str
    preflight: dict
    reasons: list[str]
    traces: list[dict]
    assertions: list[dict]
    report: dict


def build_graph(spec_path, profile: TargetProfile, operation_id: str, store: Store):
    selected = {}
    started = time.monotonic()

    def prepare(state):
        try:
            endpoints = analyze(spec_path)
            endpoint = next((e for e in endpoints if e.operation_id == operation_id), None)
            if endpoint is None:
                return {"verdict": "BLOCKED", "reasons": ["Operation ID not found in spec"]}
            selected["endpoint"] = endpoint
            return {}
        except (ValueError, OSError):
            return {
                "verdict": "ERROR",
                "reasons": ["Spec validation failed; use the spec command for details"],
            }

    def preflight(state):
        if state.get("verdict"):
            return {}
        remaining = profile.time_budget_seconds - (time.monotonic() - started)
        if remaining <= 0:
            return {"verdict": "SKIPPED", "reasons": ["Time budget exhausted before preflight"]}
        limited = profile.model_copy(
            update={"timeout_seconds": min(profile.timeout_seconds, remaining)}
        )
        result = check(limited)
        update = {"preflight": result.model_dump(mode="json")}
        if not result.ready:
            update.update(verdict="BLOCKED", reasons=result.issues)
        return update

    def create_case(state):
        if state.get("verdict"):
            return {}
        endpoint = selected["endpoint"]
        if (
            endpoint.method != "GET"
            or "{" in endpoint.path
            or endpoint.request_body
            or any(p.get("required") for p in endpoint.parameters)
        ):
            return {
                "verdict": "BLOCKED",
                "reasons": [
                    "M1 supports a GET without required parameters or body; data/scenario generation follows later"
                ],
            }
        objective = TestObjective(
            target_id=endpoint.operation_id + ".contract_smoke",
            operation_id=operation_id,
            intent="valid",
            description="Read-only contract smoke",
        )
        case = AbstractTestCase(
            case_id="case-1",
            objective=objective,
            oracle=Oracle(basis="contract", source=endpoint.provenance),
        )
        plan = ExecutionPlan(
            case_id=case.case_id,
            steps=[PlanStep(step_id="action", role="action", operation_id=operation_id)],
        )
        store.append(state["run_id"], "case", case.case_id, case.model_dump(mode="json"))
        store.append(state["run_id"], "step", "action", plan.model_dump(mode="json"))
        return {}

    def execute_case(state):
        if state.get("verdict"):
            return {}
        if store.records(state["run_id"], "attempt"):
            return {
                "verdict": "ERROR",
                "reasons": [
                    "An attempt already exists. M1 refuses automatic re-execution; inspect its delivery state."
                ],
            }
        remaining = profile.time_budget_seconds - (time.monotonic() - started)
        if remaining <= 0 or profile.request_budget < 2:
            return {
                "verdict": "SKIPPED",
                "reasons": ["Request/time budget exhausted after preflight"],
            }
        endpoint = selected["endpoint"]
        headers = {"Accept": "application/json"}
        if profile.auth_env and os.getenv(profile.auth_env):
            headers["Authorization"] = os.environ[profile.auth_env]
        request = ConcreteRequest(
            method="GET", url=profile.base_url.rstrip("/") + endpoint.path, headers=headers
        )
        limited = profile.model_copy(
            update={"timeout_seconds": min(profile.timeout_seconds, remaining)}
        )
        trace = execute(
            request,
            limited,
            run_id=state["run_id"],
            case_id="case-1",
            step_id="action",
            store=store,
        )
        assertions = validate_response(endpoint, trace)
        for assertion in assertions:
            store.append(
                state["run_id"],
                "assertion",
                assertion.assertion_id,
                assertion.model_dump(mode="json"),
            )
        return {
            "verdict": case_verdict(setup_ok=True, assertions=assertions),
            "traces": [public_trace(trace)],
            "assertions": [a.model_dump(mode="json") for a in assertions],
        }

    def report(state):
        verdict = state.get("verdict", "ERROR")
        status = "failed" if verdict in ("ERROR", "BLOCKED") else "completed"
        manifest = store.finish_run(state["run_id"], status)
        result = RunReport(
            run=manifest,
            verdict=verdict,
            operation_id=operation_id,
            preflight=state.get("preflight", {}),
            traces=state.get("traces", []),
            assertions=state.get("assertions", []),
            reasons=state.get("reasons", []),
            duration_seconds=time.monotonic() - started,
            report_file=f"artifacts/{state['run_id']}/report.json",
        )
        return {"report": write_report(store, result)}

    graph = StateGraph(RunState)
    for name, node in [
        ("prepare", prepare),
        ("preflight", preflight),
        ("create_case", create_case),
        ("execute_validate", execute_case),
        ("report", report),
    ]:
        graph.add_node(name, node)
    for before, after in [
        (START, "prepare"),
        ("prepare", "preflight"),
        ("preflight", "create_case"),
        ("create_case", "execute_validate"),
        ("execute_validate", "report"),
        ("report", END),
    ]:
        graph.add_edge(before, after)
    return graph

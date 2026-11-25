"""Versioned data boundary shared by CLI, worker and web API."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Verdict = Literal["PASS", "FAIL", "UNKNOWN", "BLOCKED", "ERROR", "SKIPPED"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: Literal["1"] = "1"


class Oracle(Contract):
    basis: Literal["contract", "business_rule", "llm", "observed"]
    source: str = Field(min_length=1)
    approved: bool = False

    @property
    def trusted(self):
        return self.basis == "contract" or (self.basis == "business_rule" and self.approved)


class EndpointSpec(Contract):
    operation_id: str
    method: str
    path: str
    tags: list[str] = Field(default_factory=list)
    parameters: list[dict[str, Any]] = Field(default_factory=list)
    request_body: dict[str, Any] | None = None
    responses: dict[str, Any]
    security: list[dict[str, Any]] = Field(default_factory=list)
    provenance: str
    contract_gaps: list[str] = Field(default_factory=list)
    openapi_version: str = "3.0.0"
    components: dict[str, Any] = Field(default_factory=dict)


class TestObjective(Contract):
    target_id: str
    operation_id: str
    intent: Literal["valid", "invalid", "boundary", "stateful"]
    description: str


class AbstractTestCase(Contract):
    case_id: str
    objective: TestObjective
    preconditions: list[str] = Field(default_factory=list)
    oracle: Oracle | None = None


class AssertionSpec(Contract):
    assertion_id: str
    kind: Literal["status", "schema", "state", "business_rule"]
    expected: Any = None
    oracle: Oracle | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class PlanStep(Contract):
    step_id: str
    role: Literal["setup", "action", "observation", "cleanup"]
    operation_id: str
    depends_on: list[str] = Field(default_factory=list)
    bindings: dict[str, str] = Field(default_factory=dict)
    capture: dict[str, str] = Field(default_factory=dict)
    request_template: dict[str, Any] = Field(default_factory=dict)
    assertions: list[AssertionSpec] = Field(default_factory=list)


class ExecutionPlan(Contract):
    case_id: str
    steps: list[PlanStep] = Field(min_length=1)

    @model_validator(mode="after")
    def ordered_steps(self):
        seen = set()
        for step in self.steps:
            if step.step_id in seen or not set(step.depends_on) <= seen:
                raise ValueError("Step IDs must be unique and depend only on earlier steps")
            seen.add(step.step_id)
        if not any(s.role == "action" for s in self.steps):
            raise ValueError("Plan needs an action")
        return self


class ConcreteRequest(Contract):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"]
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    query: dict[str, Any] = Field(default_factory=dict)
    body: Any = None


class ExecutionTrace(Contract):
    run_id: str
    case_id: str
    step_id: str
    attempt_id: str
    request: ConcreteRequest
    delivery: Literal["prepared", "response_received", "not_sent", "delivery_unknown"]
    response: dict[str, Any] | None = None
    elapsed_ms: float | None = Field(default=None, ge=0)
    error: str | None = None


class ValidationResult(Contract):
    assertion_id: str
    verdict: Verdict
    expected: Any = None
    actual: Any = None
    oracle: Oracle | None = None
    reason: str = ""

    @model_validator(mode="after")
    def evidence_required(self):
        if self.verdict in ("PASS", "FAIL") and (
            self.expected is None or not self.oracle or not self.oracle.trusted
        ):
            raise ValueError("PASS/FAIL require an expected value and a trusted oracle")
        return self


def case_verdict(*, setup_ok: bool, assertions: list[ValidationResult]) -> Verdict:
    if not setup_ok:
        return "BLOCKED"
    for status in ("FAIL", "ERROR", "BLOCKED", "UNKNOWN"):
        if any(a.verdict == status for a in assertions):
            return status
    if assertions and all(a.verdict == "PASS" for a in assertions):
        return "PASS"
    return "UNKNOWN"


class CoverageSnapshot(Contract):
    generated: list[str] = Field(default_factory=list)
    executed: list[str] = Field(default_factory=list)
    verified: list[str] = Field(default_factory=list)
    total_targets: int = Field(ge=0)


class RunManifest(Contract):
    run_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")
    spec_digest: str
    base_url: str
    mode: Literal["schema-only", "agent-assisted"] = "schema-only"
    seed: int = 0
    status: Literal["queued", "running", "completed", "failed", "cancelled"] = "queued"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    versions: dict[str, str] = Field(default_factory=dict)
    config_snapshot: dict[str, Any] = Field(default_factory=dict)


class RunReport(Contract):
    run: RunManifest
    verdict: Verdict
    operation_id: str
    preflight: dict[str, Any]
    assertions: list[ValidationResult] = Field(default_factory=list)
    traces: list[ExecutionTrace] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    duration_seconds: float = Field(ge=0)
    report_file: str

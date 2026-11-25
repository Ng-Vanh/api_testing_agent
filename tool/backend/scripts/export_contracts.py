"""Run from tool/backend: python -m scripts.export_contracts."""

import json
from pathlib import Path

from app.contracts import (
    AbstractTestCase,
    ConcreteRequest,
    CoverageSnapshot,
    EndpointSpec,
    ExecutionPlan,
    ExecutionTrace,
    PlanStep,
    RunManifest,
    RunReport,
    TestObjective,
    ValidationResult,
)

models = (
    AbstractTestCase,
    ConcreteRequest,
    CoverageSnapshot,
    EndpointSpec,
    ExecutionPlan,
    ExecutionTrace,
    PlanStep,
    RunManifest,
    RunReport,
    TestObjective,
    ValidationResult,
)
output = Path(__file__).resolve().parents[1] / "examples"
output.mkdir(exist_ok=True)
(output / "contracts.schema.json").write_text(
    json.dumps({m.__name__: m.model_json_schema() for m in models}, indent=2), encoding="utf-8"
)
plan = ExecutionPlan(
    case_id="booking.cancel_restores_seats",
    steps=[
        PlanStep(
            step_id="read_before",
            role="setup",
            operation_id="getFlight",
            capture={"seats_before": "/flight/seatsAvailable"},
        ),
        PlanStep(
            step_id="create",
            role="setup",
            operation_id="createBooking",
            depends_on=["read_before"],
            capture={"booking_id": "/booking/_id"},
        ),
        PlanStep(
            step_id="cancel",
            role="action",
            operation_id="deleteBooking",
            depends_on=["create"],
            bindings={"path.id": "create.booking_id"},
        ),
        PlanStep(
            step_id="read_after",
            role="observation",
            operation_id="getFlight",
            depends_on=["cancel"],
        ),
    ],
)
(output / "booking-plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")

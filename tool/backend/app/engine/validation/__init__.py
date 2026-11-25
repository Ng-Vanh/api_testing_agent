"""Contract conformance only. Observed errors do not become business ground truth."""

import json

from openapi_schema_validator import OAS30ReadValidator, OAS31Validator
from referencing import Registry

from app.contracts import EndpointSpec, ExecutionTrace, Oracle, ValidationResult


def validate_response(endpoint: EndpointSpec, trace: ExecutionTrace) -> list[ValidationResult]:
    source = Oracle(basis="contract", source=endpoint.provenance)
    results = []

    def result(name, verdict, expected=None, actual=None, reason=""):
        results.append(
            ValidationResult(
                assertion_id=f"{trace.attempt_id}.{name}",
                verdict=verdict,
                expected=expected,
                actual=actual,
                oracle=source,
                reason=reason,
            )
        )

    if trace.error or not trace.response:
        result("transport", "ERROR", reason=trace.error or "No HTTP response")
        return results
    response = trace.response
    code = str(response["status"])
    definition = endpoint.responses.get(
        code, endpoint.responses.get(code[0] + "XX", endpoint.responses.get("default"))
    )
    if definition is None:
        result("status", "UNKNOWN", actual=code, reason="Status is not described by this contract")
        return results
    result("status", "PASS", expected=list(endpoint.responses), actual=code)
    if not code.startswith("2"):
        result(
            "positive_intent",
            "UNKNOWN",
            actual=code,
            reason="Documented non-success response; conditions for positive-case success need an oracle",
        )
    content = definition.get("content", {})
    if not content:
        return results
    media = response["headers"].get("content-type", "").split(";", 1)[0].strip().lower()
    matched = content.get(media)
    if matched is None:
        matched = content.get(media.split("/")[0] + "/*", content.get("*/*"))
    if matched is None:
        result("content_type", "FAIL", expected=list(content), actual=media)
        return results
    result("content_type", "PASS", expected=list(content), actual=media)
    if endpoint.contract_gaps:
        result("schema", "UNKNOWN", reason="Contract gap: schema validation suspended")
        return results
    if not response.get("body_complete", True):
        result("schema", "ERROR", reason="Incomplete response; schema cannot be evaluated")
        return results
    schema = matched.get("schema")
    if schema is None:
        result("schema", "UNKNOWN", reason="Response schema is absent")
        return results
    if not (media == "application/json" or media.endswith("+json")):
        result("schema", "UNKNOWN", reason="M1 validates JSON response bodies only")
        return results
    encoding = response["headers"].get("content-encoding", "identity").lower()
    if encoding != "identity":
        result("schema", "UNKNOWN", reason="Compressed response decoding is not supported in M1")
        return results
    try:
        body = json.loads(response["body"])
    except (ValueError, TypeError):
        result("json", "FAIL", expected="valid JSON", actual="malformed JSON")
        return results
    try:
        cls = OAS31Validator if endpoint.openapi_version.startswith("3.1") else OAS30ReadValidator
        root = {**schema, "components": endpoint.components} if isinstance(schema, dict) else schema
        errors = list(
            cls(root, format_checker=cls.FORMAT_CHECKER, registry=Registry()).iter_errors(body)
        )
        # Paths/keywords provide evidence without persisting the offending secret values.
        details = [{"path": list(e.path), "keyword": e.validator} for e in errors]
        result("schema", "FAIL" if errors else "PASS", expected=schema, actual=details)
    except Exception as exc:
        result("schema", "UNKNOWN", reason=f"Schema cannot be evaluated: {type(exc).__name__}")
    return results

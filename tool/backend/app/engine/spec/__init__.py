"""Offline OpenAPI normalization: local JSON pointers only, cyclic refs retained."""

import copy
from pathlib import Path

import yaml
from openapi_spec_validator import validate

from app.contracts import EndpointSpec

METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
MAX_SPEC_BYTES = 5 * 1024 * 1024


def analyze(path: Path) -> list[EndpointSpec]:
    path = Path(path)
    if path.stat().st_size > MAX_SPEC_BYTES:
        raise ValueError("Spec exceeds 5 MiB limit")
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (ValueError, yaml.YAMLError) as exc:
        raise ValueError(f"Invalid spec: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError("Spec root must be an object")

    def reject_external(node, stack=frozenset(), location="#"):
        if isinstance(node, (list, dict)):
            if id(node) in stack:
                raise ValueError(f"Cyclic YAML alias at {location}")
            stack = stack | {id(node)}
            items = node.items() if isinstance(node, dict) else enumerate(node)
            for key, value in items:
                if key in ("$ref", "$dynamicRef") and (
                    not isinstance(value, str) or not value.startswith("#/")
                ):
                    raise ValueError(f"external/unsupported ref at {location}/{key}")
                reject_external(value, stack, f"{location}/{key}")

    reject_external(document)
    try:
        validate(document)
    except Exception as exc:
        raise ValueError(f"Invalid OpenAPI: {exc}") from exc

    def pointer(ref):
        node = document
        try:
            for part in ref[2:].split("/"):
                node = node[part.replace("~1", "/").replace("~0", "~")]
            return node
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Unresolved ref {ref}") from exc

    def expand(node, chain=()):
        if isinstance(node, list):
            return [expand(x, chain) for x in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            ref = node["$ref"]
            if ref in chain:
                return {"$ref": ref}  # Preserve recursion; never silently truncate schema.
            result = expand(copy.deepcopy(pointer(ref)), (*chain, ref))
            if document["openapi"].startswith("3.1"):
                result.update({k: expand(v, chain) for k, v in node.items() if k != "$ref"})
            return result
        return {k: expand(v, chain) for k, v in node.items()}

    result, identifiers = [], set()
    for route, raw_item in document.get("paths", {}).items():
        item = expand(raw_item)
        for method in METHODS & item.keys():
            operation = item[method]
            op_id = operation.get("operationId", f"{method.upper()} {route}")
            if op_id in identifiers:
                raise ValueError(f"Duplicate operationId {op_id} at {route}")
            identifiers.add(op_id)
            # Operation-level parameters override matching path-level parameters.
            params = {(p["name"], p["in"]): p for p in item.get("parameters", [])}
            params.update({(p["name"], p["in"]): p for p in operation.get("parameters", [])})
            gaps = operation.get("x-contract-gaps", [])
            result.append(
                EndpointSpec(
                    operation_id=op_id,
                    method=method.upper(),
                    path=route,
                    tags=operation.get("tags", []),
                    parameters=list(params.values()),
                    request_body=operation.get("requestBody"),
                    responses=operation["responses"],
                    security=operation.get("security", document.get("security", [])),
                    provenance=f"{path.name}#/paths/{route.replace('~', '~0').replace('/', '~1')}/{method}",
                    contract_gaps=gaps if isinstance(gaps, list) else [str(gaps)],
                    openapi_version=document["openapi"],
                    components=document.get("components", {}),
                )
            )
    return sorted(result, key=lambda e: (e.path, e.method))

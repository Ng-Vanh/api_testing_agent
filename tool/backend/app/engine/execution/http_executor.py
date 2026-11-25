"""One pinned HTTP transaction. No redirect following or automatic retry."""

import hashlib
import http.client
import json
import socket
import ssl
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

from app.config import TargetProfile
from app.contracts import ConcreteRequest, ExecutionTrace
from app.engine.preflight import origin, validate_target
from app.storage import SENSITIVE, Store, redact


def public_trace(trace: ExecutionTrace) -> dict:
    """Validation consumes the raw in-memory trace; disk/checkpoint gets this view."""
    secrets = []

    def collect(value):
        if isinstance(value, dict):
            for key, val in value.items():
                if key.lower().replace("-", "_") in {s.replace("-", "_") for s in SENSITIVE}:
                    if isinstance(val, str) and val:
                        secrets.append(val)
                else:
                    collect(val)
        elif isinstance(value, list):
            for val in value:
                collect(val)

    collect(trace.request.model_dump())
    for key, val in parse_qsl(urlsplit(trace.request.url).query):
        if key.lower() in SENSITIVE and val:
            secrets.append(val)
    payload = redact(trace.model_dump(mode="json"))
    if payload["response"]:
        body = payload["response"].get("body", "")
        try:
            original = json.loads(body)
            cleaned = redact(original)
            if cleaned != original:
                payload["response"]["body"] = json.dumps(cleaned, ensure_ascii=False)
        except (ValueError, TypeError):
            pass
        payload["response"]["redacted"] = True

    def replace(value):
        if isinstance(value, str):
            for secret in sorted(secrets, key=len, reverse=True):
                value = value.replace(secret, "[REDACTED]")
            return value
        if isinstance(value, dict):
            return {k: replace(v) for k, v in value.items()}
        if isinstance(value, list):
            return [replace(v) for v in value]
        return value

    # Redact echoed secrets in payload fields without changing structural IDs/enums.
    for key in ("headers", "body", "query", "url"):
        payload["request"][key] = replace(payload["request"][key])
    if payload["response"]:
        for key in ("headers", "body"):
            payload["response"][key] = replace(payload["response"][key])
    return payload


def execute(
    request: ConcreteRequest,
    profile: TargetProfile,
    *,
    run_id: str,
    case_id: str,
    step_id: str,
    store: Store | None = None,
) -> ExecutionTrace:
    trace = ExecutionTrace(
        run_id=run_id,
        case_id=case_id,
        step_id=step_id,
        attempt_id=uuid4().hex,
        request=request,
        delivery="prepared",
    )
    started = time.monotonic()
    deadline = started + min(profile.timeout_seconds, profile.time_budget_seconds)
    connection, sock, sent = None, None, False
    if store:
        store.append(run_id, "attempt", trace.attempt_id + ".prepared", public_trace(trace))
    try:
        parts = urlsplit(request.url)
        if parts.fragment:
            raise ValueError("Request URL fragments are not supported")
        checked_url = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        addresses = validate_target(profile, url=checked_url)
        scheme, host, port = origin(checked_url)
        query = [*parse_qsl(parts.query, keep_blank_values=True), *request.query.items()]
        path = parts.path or "/"
        if query:
            path += "?" + urlencode(query, doseq=True)
        headers = dict(request.headers)
        forbidden = {"host", "content-length", "transfer-encoding", "connection"}
        if any(k.lower() in forbidden for k in headers):
            raise ValueError("Transport headers cannot be overridden")
        body = None
        if request.body is not None:
            body = json.dumps(request.body, ensure_ascii=False, allow_nan=False).encode()
            if not any(k.lower() == "content-type" for k in headers):
                headers["Content-Type"] = "application/json"
            if len(body) > profile.max_response_bytes:
                raise ValueError("Request body exceeds configured size limit")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Deadline exceeded before sending")
        sock = socket.create_connection((addresses[0], port), timeout=remaining)
        if scheme == "https":
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
        connection = http.client.HTTPConnection(host, port, timeout=remaining)
        connection.sock = sock
        sent = True  # A send failure can still mean the server received part/all of the request.
        connection.request(request.method, path, body=body, headers=headers)
        sock.settimeout(max(0.001, deadline - time.monotonic()))
        response = connection.getresponse()
        chunks, size = [], 0
        while size <= profile.max_response_bytes:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Response deadline exceeded")
            sock.settimeout(remaining)
            chunk = response.read1(min(65536, profile.max_response_bytes + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if response.isclosed():
                break
        raw = b"".join(chunks)
        trace.delivery = "response_received"
        trace.response = {
            "status": response.status,
            "headers": {k.lower(): v for k, v in response.getheaders()},
            "body": raw[: profile.max_response_bytes].decode("utf-8", errors="replace"),
            "body_complete": size <= profile.max_response_bytes,
            "captured_body_sha256": hashlib.sha256(raw).hexdigest(),
        }
        if size > profile.max_response_bytes:
            trace.error = "ResponseSizeLimit"
    except (OSError, ValueError, TypeError, http.client.HTTPException) as exc:
        trace.delivery = "delivery_unknown" if sent else "not_sent"
        trace.error = type(exc).__name__  # Exception messages may contain credentials or payloads.
    finally:
        if connection:
            connection.close()
        if sock:
            sock.close()
    trace.elapsed_ms = (time.monotonic() - started) * 1000
    if store:
        store.append(run_id, "attempt", trace.attempt_id + ".result", public_trace(trace))
    return trace

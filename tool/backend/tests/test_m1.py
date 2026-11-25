import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from app.config import TargetProfile
from app.contracts import ConcreteRequest, EndpointSpec, ExecutionTrace
from app.engine.execution.http_executor import execute
from app.engine.validation import validate_response
from app.runs import load_report, run
from app.storage import Store


@pytest.fixture
def api():
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            received.append((self.command, self.path))
            if self.path == "/slow":
                time.sleep(0.15)
            if self.path == "/drop":
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            status = 302 if self.path == "/redirect" else 400 if self.path == "/bad" else 200
            payload = {"airports": []} if self.path != "/invalid" else {"airports": "wrong"}
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Set-Cookie", "session=must-not-leak")
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            received.append((self.command, self.path))
            data = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    profile = TargetProfile(base_url=base, allowed_origins=[base], allowed_ips=["127.0.0.1"])
    yield profile, received
    server.shutdown()
    server.server_close()
    worker.join()


def endpoint():
    return EndpointSpec(
        operation_id="list",
        method="GET",
        path="/",
        provenance="spec#/paths/~1/get",
        responses={
            "200": {
                "description": "OK",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["airports"],
                            "properties": {"airports": {"type": "array"}},
                        }
                    }
                },
            }
        },
    )


def trace(body, status=200, headers=None):
    return ExecutionTrace(
        run_id="r",
        case_id="c",
        step_id="a",
        attempt_id="t",
        request=ConcreteRequest(method="GET", url="http://localhost/"),
        delivery="response_received",
        response={
            "status": status,
            "headers": headers or {"content-type": "application/json"},
            "body": json.dumps(body),
            "body_complete": True,
        },
    )


def write_spec(tmp_path, path="/"):
    p = tmp_path / "spec.json"
    p.write_text(
        json.dumps(
            {
                "openapi": "3.0.0",
                "info": {"title": "Local", "version": "1"},
                "paths": {
                    path: {"get": {"operationId": "list", "responses": endpoint().responses}}
                },
            }
        )
    )
    return p


def test_executor_get_post_redaction_and_no_redirect(api, tmp_path):
    profile, received = api
    store = Store(tmp_path)
    from app.contracts import RunManifest

    store.save_run(RunManifest(run_id="r", spec_digest="x", base_url=profile.base_url))
    result = execute(
        ConcreteRequest(
            method="POST",
            url=profile.base_url + "/",
            body={"password": "must-not-leak"},
            headers={"Authorization": "must-not-leak"},
        ),
        profile,
        store=store,
        run_id="r",
        case_id="c",
        step_id="a",
    )
    assert result.delivery == "response_received" and result.response["status"] == 201
    rows = store.records("r", "attempt")
    assert len(rows) == 2  # prepared and completed events share attempt_id, never overwrite
    assert "must-not-leak" not in json.dumps(rows)
    redirect = execute(
        ConcreteRequest(method="GET", url=profile.base_url + "/redirect"),
        profile,
        store=store,
        run_id="r",
        case_id="c",
        step_id="b",
    )
    assert redirect.response["status"] == 302
    assert received == [("POST", "/"), ("GET", "/redirect")]
    bad = execute(
        ConcreteRequest(method="GET", url=profile.base_url + "/bad"),
        profile,
        run_id="r",
        case_id="c",
        step_id="c",
    )
    assert bad.delivery == "response_received" and bad.response["status"] == 400
    assert bad.error is None


@pytest.mark.parametrize("path", ["/slow", "/drop"])
def test_executor_timeout_or_lost_ack_never_retries(api, tmp_path, path):
    profile, received = api
    profile.timeout_seconds = 0.03
    result = execute(
        ConcreteRequest(method="GET", url=profile.base_url + path),
        profile,
        run_id="r",
        case_id="c",
        step_id="a",
    )
    assert result.delivery == "delivery_unknown" and result.error
    assert len(received) == 1


def test_executor_rejects_wrong_target_before_send(api):
    profile, received = api
    result = execute(
        ConcreteRequest(method="GET", url="http://evil.test/"),
        profile,
        run_id="r",
        case_id="c",
        step_id="a",
    )
    assert result.delivery == "not_sent" and not received


def test_validator_schema_fail_unknown_status_and_nullable():
    ep = endpoint()
    assert all(r.verdict == "PASS" for r in validate_response(ep, trace({"airports": []})))
    assert any(r.verdict == "FAIL" for r in validate_response(ep, trace({"airports": "bad"})))
    assert any(r.verdict == "UNKNOWN" for r in validate_response(ep, trace({}, 418)))
    ep.responses["200"]["content"]["application/json"]["schema"] = {
        "type": "string",
        "nullable": True,
    }
    assert all(r.verdict == "PASS" for r in validate_response(ep, trace(None)))


def test_validator_refuses_schema_on_gap_and_wrong_media():
    ep = endpoint()
    ep.contract_gaps = ["schema not yet reviewed"]
    assert any(r.verdict == "UNKNOWN" for r in validate_response(ep, trace({"airports": "wrong"})))
    ep.contract_gaps = []
    assert any(
        r.verdict == "FAIL"
        for r in validate_response(ep, trace({}, headers={"content-type": "text/html"}))
    )
    broken = trace({})
    broken.response["body"] = "{broken"
    assert any(r.verdict == "FAIL" for r in validate_response(ep, broken))
    broken.response["body_complete"] = False
    assert all(r.verdict != "FAIL" for r in validate_response(ep, broken))


def test_run_report_reopen_without_sending_again(api, tmp_path):
    profile, received = api
    spec = write_spec(tmp_path)
    report = run(spec, profile, "list", tmp_path / "data")
    assert report["verdict"] == "PASS" and report["run"]["status"] == "completed"
    assert len(received) == 2  # safe preflight, then the actual test request
    run_id = report["run"]["run_id"]
    assert load_report(tmp_path / "data", run_id) == report
    assert len(received) == 2
    assert not Store(tmp_path / "data").reconcile(run_id)
    assert report["traces"][0]["attempt_id"]
    # Checkpoint contains redacted state only.
    assert b"must-not-leak" not in (tmp_path / "data/checkpoints.sqlite").read_bytes()


def test_failed_preflight_reports_blocked_without_test_request(api, tmp_path):
    profile, received = api
    profile.required_fixtures = ["missing"]
    report = run(write_spec(tmp_path), profile, "list", tmp_path / "data")
    assert report["verdict"] == "BLOCKED"
    assert len(received) <= 1
    assert not report["traces"]


def test_cli_run_and_show_use_shared_service(api, tmp_path, capsys):
    import subprocess
    import sys

    profile, _ = api
    spec = write_spec(tmp_path)
    config = tmp_path / "profile.json"
    config.write_text(profile.model_dump_json())
    args = [sys.executable, "-m", "app.cli"]
    first = subprocess.run(
        args
        + [
            "run",
            "--spec",
            str(spec),
            "--profile",
            str(config),
            "--operation",
            "list",
            "--output",
            str(tmp_path / "data"),
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert first.returncode == 0, first.stderr
    report = json.loads(first.stdout)
    second = subprocess.run(
        args + ["show", report["run"]["run_id"], "--output", str(tmp_path / "data")],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert json.loads(second.stdout) == report


def test_report_corruption_is_not_shown_as_pass(api, tmp_path):
    profile, _ = api
    data = tmp_path / "data"
    report = run(write_spec(tmp_path), profile, "list", data)
    (data / report["report_file"]).write_text("{}")
    with pytest.raises(ValueError, match="differs"):
        load_report(data, report["run"]["run_id"])


def test_write_operation_is_blocked_by_m1_before_action(api, tmp_path):
    profile, received = api
    spec = write_spec(tmp_path)
    document = json.loads(spec.read_text())
    document["paths"]["/"]["post"] = document["paths"]["/"].pop("get")
    spec.write_text(json.dumps(document))
    report = run(spec, profile, "list", tmp_path / "data")
    assert report["verdict"] == "BLOCKED"
    assert all(method == "GET" for method, _ in received)
    assert not report["traces"]


def test_single_request_budget_skips_action(api, tmp_path):
    profile, received = api
    profile.request_budget = 1
    report = run(write_spec(tmp_path), profile, "list", tmp_path / "data")
    assert report["verdict"] == "SKIPPED" and len(received) == 1


def test_compressed_body_is_not_misreported_as_schema_failure():
    sample = trace({})
    sample.response["headers"]["content-encoding"] = "gzip"
    sample.response["body"] = "compressed bytes"
    result = validate_response(endpoint(), sample)
    assert not any(r.verdict == "FAIL" for r in result)
    assert any(r.verdict == "UNKNOWN" for r in result)


def test_response_limit_keeps_evidence_and_errors(api):
    profile, _ = api
    profile.max_response_bytes = 4
    result = execute(
        ConcreteRequest(method="GET", url=profile.base_url + "/"),
        profile,
        run_id="r",
        case_id="c",
        step_id="a",
    )
    assert result.delivery == "response_received"
    assert result.response["body_complete"] is False and result.error == "ResponseSizeLimit"
    assert any(r.verdict == "ERROR" for r in validate_response(endpoint(), result))

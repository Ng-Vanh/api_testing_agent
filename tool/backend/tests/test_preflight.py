import pytest

from app.config import TargetProfile
from app.engine.preflight import check, validate_target


def profile(**kwargs):
    return TargetProfile(
        base_url="http://localhost:5000",
        allowed_origins=["http://localhost:5000"],
        allowed_ips=["127.0.0.1"],
        **kwargs,
    )


def resolve(host, port):
    return ["127.0.0.1"]


def test_target_denies_host_dns_rebind_and_credentials():
    assert validate_target(profile(), resolver=resolve)
    with pytest.raises(ValueError):
        validate_target(profile(), url="http://evil.test", resolver=resolve)
    with pytest.raises(ValueError):
        validate_target(profile(), resolver=lambda *args: ["169.254.169.254"])
    with pytest.raises(ValueError):
        validate_target(profile(), url="http://user:pw@localhost:5000", resolver=resolve)


def test_preflight_reports_missing_fixture_and_unknown_auth():
    result = check(profile(required_fixtures=["seeded"]), resolver=resolve, probe=lambda *args: 200)
    assert not result.ready
    assert result.auth == "unverified"
    assert "seeded" in " ".join(result.issues)


def test_preflight_rejects_redirect_and_never_writes():
    seen = []

    def probe(url, headers, timeout):
        seen.append(url)
        return 302

    result = check(profile(), resolver=resolve, probe=probe)
    assert not result.ready
    assert len(seen) == 1


def test_real_read_only_probe_pins_ip_and_refuses_redirect():
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302 if self.path == "/redirect" else 200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    p = TargetProfile(base_url=url, allowed_origins=[url], allowed_ips=["127.0.0.1"])
    try:
        assert check(p).ready
        assert not check(p.model_copy(update={"probe_path": "/redirect"})).ready
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_preflight_required_auth_is_not_assumed_ready(monkeypatch):
    monkeypatch.delenv("M0_TEST_AUTH", raising=False)
    result = check(
        profile(auth_env="M0_TEST_AUTH", auth_required=True),
        resolver=resolve,
        probe=lambda *args: 200,
    )
    assert not result.ready and result.auth == "unverified"

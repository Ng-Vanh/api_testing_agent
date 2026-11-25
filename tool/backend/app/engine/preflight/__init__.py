"""Safe read-only readiness probe. Never follows redirects or loads remote refs."""

import http.client
import ipaddress
import os
import socket
import ssl
from urllib.parse import urlsplit

from pydantic import Field

from app.config import TargetProfile
from app.contracts import Contract


class PreflightResult(Contract):
    ready: bool
    auth: str = "unverified"
    issues: list[str] = Field(default_factory=list)
    addresses: list[str] = Field(default_factory=list)


def resolve(host, port):
    return sorted({r[4][0] for r in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})


def origin(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.query
    ):
        raise ValueError("Target must be an HTTP(S) URL without credentials, query or fragment")
    return (
        parsed.scheme,
        parsed.hostname.lower(),
        parsed.port or (443 if parsed.scheme == "https" else 80),
    )


def validate_target(profile: TargetProfile, url=None, resolver=resolve):
    target = url or profile.base_url
    if origin(target) not in {origin(u) for u in profile.allowed_origins}:
        raise ValueError("Target origin is outside allowlist")
    _scheme, host, port = origin(target)
    addresses = resolver(host, port)
    allowed = {ipaddress.ip_address(ip) for ip in profile.allowed_ips}
    if not addresses or any(ipaddress.ip_address(ip) not in allowed for ip in addresses):
        raise ValueError("Resolved IP is outside allowlist")
    return addresses


def probe_readonly(url, headers, timeout, addresses):
    parsed = urlsplit(url)
    scheme, host, port = origin(url)
    # Connect to validated IP without a second DNS lookup; TLS still verifies hostname.
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    sock = socket.create_connection((addresses[0], port), timeout=timeout)
    try:
        if scheme == "https":
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
        conn.sock = sock
        conn.request("GET", parsed.path or "/", headers=headers)
        response = conn.getresponse()
        return response.status
    finally:
        conn.close()
        sock.close()


def check(profile: TargetProfile, resolver=resolve, probe=None):
    issues = []
    addresses = []
    auth = "unverified"
    try:
        addresses = validate_target(profile, resolver=resolver)
        missing = set(profile.required_fixtures) - set(profile.ready_fixtures)
        if missing:
            issues.append(f"Missing fixtures: {sorted(missing)}")
        headers = {}
        if profile.auth_env:
            secret = os.getenv(profile.auth_env)
            if not secret:
                issues.append("Auth environment variable is not available")
            else:
                headers["Authorization"] = secret
        elif profile.auth_required:
            issues.append("Required auth is not configured")
        path = profile.auth_probe_path or profile.probe_path
        if not path.startswith("/") or path.startswith("//") or any(c in path for c in "\r\n?#"):
            raise ValueError("Probe must be an absolute local path without query/fragment")
        url = profile.base_url.rstrip("/") + path
        validate_target(profile, url=url, resolver=lambda *args: addresses)
        status = (
            probe(url, headers, profile.timeout_seconds)
            if probe
            else probe_readonly(url, headers, profile.timeout_seconds, addresses)
        )
        if 300 <= status < 400:
            issues.append("Probe redirect refused")
        elif status >= 400:
            issues.append(f"Probe returned HTTP {status}")
        elif profile.auth_probe_path and headers:
            auth = "verified"
        if profile.auth_required and auth != "verified":
            issues.append("Required auth has not been verified by a safe probe")
    except (ValueError, OSError, http.client.HTTPException) as exc:
        issues.append(f"Preflight failed: {type(exc).__name__}: {exc}")
    return PreflightResult(ready=not issues, auth=auth, issues=issues, addresses=addresses)

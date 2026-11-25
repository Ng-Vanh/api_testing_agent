"""Reproducible M1 smoke on a disposable MongoDB + a separate QAirline backend.

Run from tool/backend with conda apitesting; requires Docker and QAirline npm dependencies.
"""

import json
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

from app.config import DATA_DIR, TargetProfile
from app.runs import load_report, run


def main():
    repo = Path(__file__).resolve().parents[3]
    name = "apitesting-m1-" + uuid4().hex[:12]
    created, backend = False, None
    with tempfile.TemporaryFile(mode="w+") as log:
        try:
            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-d",
                    "--name",
                    name,
                    "-p",
                    "127.0.0.1::27017",
                    "mongo:7",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            created = True
            mapping = subprocess.check_output(
                ["docker", "port", name, "27017/tcp"], text=True
            ).strip()
            mongo_port = int(mapping.rsplit(":", 1)[1])
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                api_port = sock.getsockname()[1]
            env = {
                **os.environ,
                "MONGO_URI": f"mongodb://127.0.0.1:{mongo_port}/qairline",
                "PORT": str(api_port),
            }
            backend = subprocess.Popen(
                ["node", "server.js"],
                cwd=repo / "QAirline/backend",
                env=env,
                stdout=log,
                stderr=log,
            )
            base = f"http://127.0.0.1:{api_port}"
            for _ in range(60):
                if backend.poll() is not None:
                    raise RuntimeError("Isolated QAirline backend exited before readiness")
                try:
                    with urlopen(base + "/api/airports", timeout=1) as response:
                        if response.status == 200:
                            break
                except (OSError, URLError):
                    time.sleep(0.2)
            else:
                raise RuntimeError("Isolated QAirline did not become ready")
            profile = TargetProfile(
                base_url=base,
                allowed_origins=[base],
                allowed_ips=["127.0.0.1"],
                probe_path="/api/airports",
            )
            report = run(
                repo / "QAirline/specs/qairline_openapi.json", profile, "listAirports", DATA_DIR
            )
            assert report["verdict"] == "PASS", report["verdict"]
            assert load_report(DATA_DIR, report["run"]["run_id"]) == report
            print(
                json.dumps(
                    {
                        "run_id": report["run"]["run_id"],
                        "verdict": report["verdict"],
                        "report": str(DATA_DIR / report["report_file"]),
                        "fixture": "disposable empty MongoDB",
                    },
                    indent=2,
                )
            )
        finally:
            if backend:
                backend.terminate()
                backend.wait(timeout=10)
            if created:
                subprocess.run(
                    ["docker", "stop", "-t", "2", name], check=True, stdout=subprocess.DEVNULL
                )


if __name__ == "__main__":
    main()

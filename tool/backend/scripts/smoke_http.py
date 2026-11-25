"""Check the running backend + Vite proxy; neither starts a test run nor mutates QAirline."""

import json
from urllib.request import urlopen

for url in ("http://127.0.0.1:8111/health", "http://127.0.0.1:5173/api/health"):
    with urlopen(url, timeout=5) as response:
        assert json.load(response)["status"] == "ok"
    print(f"OK {url}")

"""M1 CLI is available; web run management arrives in T10."""

from fastapi import FastAPI

app = FastAPI(title="API Testing Tool", version="0.2.0")


@app.get("/health")
def health():
    return {"status": "ok", "milestone": "M1", "contract_version": "1"}

import json
import os
from pathlib import Path

from pydantic import Field

from app.contracts import Contract

DATA_DIR = Path(os.getenv("APITEST_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))


class TargetProfile(Contract):
    base_url: str
    allowed_origins: list[str] = Field(min_length=1)
    allowed_ips: list[str] = Field(min_length=1)
    probe_path: str = "/"
    timeout_seconds: float = Field(default=5, gt=0, le=60)
    required_fixtures: list[str] = Field(default_factory=list)
    ready_fixtures: list[str] = Field(default_factory=list)
    auth_env: str | None = None
    auth_required: bool = False
    auth_probe_path: str | None = None
    reset_available: bool = False
    request_budget: int = Field(default=100, gt=0)
    time_budget_seconds: int = Field(default=60, gt=0)
    max_response_bytes: int = Field(default=1048576, gt=0, le=10485760)

    @classmethod
    def load(cls, path: Path):
        return cls.model_validate(json.loads(path.read_text(encoding="utf-8")))

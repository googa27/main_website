"""The portfolio API must stay inert with real process-global telemetry installed."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


@pytest.mark.parametrize("mode", ["globals", "environment"])
@pytest.mark.parametrize("enabled_control", [False, True])
def test_native_telemetry_policy_with_real_sdk(
    mode: str, enabled_control: bool, tmp_path: Path
) -> None:
    api = Path(__file__).parents[1]
    command = [
        sys.executable,
        "-I",
        "-B",
        str(api / "tests/telemetry_scenario.py"),
        "--source",
        str(api),
        "--mode",
        mode,
    ]
    if enabled_control:
        command.append("--enabled-control")
    environment = {k: v for k, v in os.environ.items() if not k.startswith("OTEL_")}
    environment.update(
        DATABASE_URL="sqlite://",
        CONTACT_ADMIN_TOKEN="PUBLIC_SYNTHETIC_ADMINISTRATOR_TOKEN_244",
        SECRET_KEY="PUBLIC_SYNTHETIC_SECRET_244",
        OPENAI_API_KEY="",
        HTTP_PROXY="",
        HTTPS_PROXY="",
        ALL_PROXY="",
        NO_PROXY="127.0.0.1",
        no_proxy="127.0.0.1",
        http_proxy="",
        https_proxy="",
        all_proxy="",
    )
    completed = subprocess.run(
        command,
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=40,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stderr == ""
    result: dict[str, Any] = json.loads(completed.stdout)
    assert result["global_identity_preserved"]
    assert result["lifespan_events"] == ["startup", "shutdown", "startup", "shutdown"]
    assert result["statuses"] == [[200, 422, 401, 500], [200, 422, 401, 500]]
    assert all(
        result["calls"][signal + "_shutdown"] == 0
        for signal in ["trace", "metric", "log"]
    )
    if enabled_control:
        assert (
            result["spans"] > 0 and result["logs"] > 0 and result["metric_points"] > 0
        )
        assert all(
            result["calls"][signal + "_get"] > 0
            for signal in ["trace", "metric", "log"]
        )
        if mode == "environment":
            assert all(
                result["calls"][signal + "_register"] == 1
                for signal in ["trace", "metric", "log"]
            )
            assert {
                item["path"] for item in result["exports"] if item["records"] > 0
            } == {
                "/v1/traces",
                "/v1/metrics",
                "/v1/logs",
            }
        else:
            assert result["exports"] == []
    else:
        assert (
            result["spans"] == 0
            and result["logs"] == 0
            and result["metric_points"] == 0
        )
        assert all(value == 0 for value in result["calls"].values())
        assert result["exports"] == []

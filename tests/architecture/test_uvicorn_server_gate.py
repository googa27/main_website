"""Keep actual public-server controls in the normal installed release gate."""

from __future__ import annotations

import copy
import json
import shlex
import tomllib
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TEST_PATH = "apps/api/tests/test_uvicorn_server_contract.py"
COMMAND = [
    "$RUNNER_TEMP/api-wheel-env/bin/python",
    "-I",
    TEST_PATH,
    "--require-installed",
]


def check_gate(workflow: dict) -> None:
    job = workflow["jobs"]["quality-checks"]
    if job.get("if") or job.get("continue-on-error"):
        raise ValueError("quality gate must be required")
    steps = [
        step
        for step in job["steps"]
        if step.get("name") == "Verify installed API artifact"
    ]
    if len(steps) != 1:
        raise ValueError("exactly one normal installed artifact step is required")
    step = steps[0]
    if step.get("if") or step.get("continue-on-error") or step.get("working-directory"):
        raise ValueError("normal installed server gate must run unconditionally at root")
    lines = step["run"].splitlines()
    if sum(shlex.split(line) == COMMAND for line in lines if line.strip()) != 1:
        raise ValueError("exact isolated normal-wheel server command is required")


def workflow() -> dict:
    return yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())


def test_normal_installed_server_command_is_required() -> None:
    check_gate(workflow())


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "wrong-interpreter",
        "source-visible",
        "no-installed-identity",
        "allow-failure",
        "conditional",
        "wrong-cwd",
    ],
)
def test_weakened_normal_server_gate_is_rejected(mutation: str) -> None:
    changed = copy.deepcopy(workflow())
    step = next(
        item
        for item in changed["jobs"]["quality-checks"]["steps"]
        if item.get("name") == "Verify installed API artifact"
    )
    line = next(
        line
        for line in step["run"].splitlines()
        if shlex.split(line) == COMMAND
    )
    if mutation == "missing":
        step["run"] = step["run"].replace(line, "")
    elif mutation == "duplicate":
        step["run"] += "\n" + line
    elif mutation == "wrong-interpreter":
        step["run"] = step["run"].replace(line, line.replace(COMMAND[0], "python"))
    elif mutation == "source-visible":
        step["run"] = step["run"].replace(line, line.replace(" -I ", " "))
    elif mutation == "no-installed-identity":
        step["run"] = step["run"].replace(line, line.replace(" --require-installed", ""))
    elif mutation == "allow-failure":
        step["continue-on-error"] = True
    elif mutation == "conditional":
        step["if"] = "false"
    elif mutation == "wrong-cwd":
        step["working-directory"] = "apps/api"
    with pytest.raises(ValueError):
        check_gate(changed)


def test_canonical_server_policy_matches_runtime_pins_and_gate() -> None:
    architecture = json.loads((ROOT / "docs/ARCHITECTURE.yaml").read_text())
    policy = architecture["tests"]["uvicorn_server_policy"]
    selected = policy["selected_version"]
    project = tomllib.loads((ROOT / "apps/api/pyproject.toml").read_text())
    expected = f"uvicorn[standard]=={selected}"
    assert expected in project["project"]["dependencies"]
    assert expected in (ROOT / "apps/api/requirements.txt").read_text().splitlines()
    assert policy["installed_command"] == COMMAND
    assert policy["source_test"] == TEST_PATH

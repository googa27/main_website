"""Selected dotenv records and normal-wheel consumer commands stay coherent."""

import copy
import json
import shlex
from pathlib import Path

import pytest
import tomllib
import yaml

ROOT = Path(__file__).resolve().parents[2]
COMMANDS = [
    [
        "$RUNNER_TEMP/api-wheel-env/bin/python",
        "-I",
        "apps/api/tests/test_dotenv_release_contract.py",
    ],
    [
        "$RUNNER_TEMP/api-wheel-env/bin/python",
        "-I",
        "apps/api/tests/test_dotenv_settings_contract.py",
        "--require-installed",
    ],
]


def check_gate(workflow):
    job = workflow["jobs"]["quality-checks"]
    if job.get("if") or job.get("continue-on-error"):
        raise ValueError("Required quality job cannot be conditional or ignored")
    steps = [
        s for s in job["steps"] if s.get("name") == "Verify installed API artifact"
    ]
    if len(steps) != 1:
        raise ValueError("One normal artifact step required")
    step = steps[0]
    if any(step.get(key) for key in ("if", "continue-on-error", "working-directory")):
        raise ValueError("Normal artifact step must run unconditionally at root")
    lines = [shlex.split(line) for line in step["run"].splitlines() if line.strip()]
    if any(lines.count(command) != 1 for command in COMMANDS):
        raise ValueError("Both isolated normal-wheel dotenv commands required")


def workflow():
    return yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())


def test_both_normal_installed_dotenv_commands_are_required():
    check_gate(workflow())


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "source-interpreter",
        "source-visible",
        "missing-origin-check",
        "conditional",
        "allow-failure",
    ],
)
def test_weakened_normal_dotenv_gate_is_rejected(mutation):
    changed = copy.deepcopy(workflow())
    step = next(
        s
        for s in changed["jobs"]["quality-checks"]["steps"]
        if s.get("name") == "Verify installed API artifact"
    )
    command = COMMANDS[1]
    line = next(
        line for line in step["run"].splitlines() if shlex.split(line) == command
    )
    if mutation == "missing":
        step["run"] = step["run"].replace(line, "")
    elif mutation == "duplicate":
        step["run"] += "\n" + line
    elif mutation == "source-interpreter":
        step["run"] = step["run"].replace(line, line.replace(command[0], "python"))
    elif mutation == "source-visible":
        step["run"] = step["run"].replace(line, line.replace(" -I ", " "))
    elif mutation == "missing-origin-check":
        step["run"] = step["run"].replace(
            line, line.replace(" --require-installed", "")
        )
    elif mutation == "conditional":
        step["if"] = "false"
    else:
        step["continue-on-error"] = True
    with pytest.raises(ValueError):
        check_gate(changed)


def selected_record():
    architecture = json.loads((ROOT / "docs/ARCHITECTURE.yaml").read_text())
    records = [
        row
        for row in architecture["libraries"]["decisions"]
        if row["capability"] == "Environment-file parsing and settings precedence"
    ]
    assert len(records) == 1
    return records[0], architecture["tests"]["dotenv_contract"]


def check_selected(versions):
    assert set(versions) == {"python-dotenv", "pydantic-settings"}
    project = tomllib.loads((ROOT / "apps/api/pyproject.toml").read_text())["project"]
    requirements = (ROOT / "apps/api/requirements.txt").read_text().splitlines()
    for name, version in versions.items():
        declaration = f"{name}=={version}"
        assert declaration in project["dependencies"]
        assert declaration in requirements


def test_selected_dotenv_stack_and_canonical_commands_match():
    decision, policy = selected_record()
    check_selected(decision["selected_versions"])
    assert policy["installed_commands"] == COMMANDS
    assert policy["source_tests"] == [command[2] for command in COMMANDS]


@pytest.mark.parametrize("name", ["python-dotenv", "pydantic-settings"])
def test_selected_dotenv_version_drift_is_refused(name):
    decision, _ = selected_record()
    with pytest.raises(AssertionError):
        check_selected({**decision["selected_versions"], name: "999.0.0"})

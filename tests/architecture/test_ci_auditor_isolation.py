"""Keep the reviewed auditor and API graphs independently consistent in CI."""

import copy
import shlex
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
AUDITOR = "$RUNNER_TEMP/api-audit-env/bin/python"
WHEEL = "$RUNNER_TEMP/api-wheel-env/bin/python"
BEFORE = "$RUNNER_TEMP/api-dev-before-audit.txt"
AFTER = "$RUNNER_TEMP/api-dev-after-audit.txt"


def verify_isolation(workflow):
    commands = [
        shlex.split(line)
        for step in workflow["jobs"]["quality-checks"]["steps"]
        for line in step.get("run", "").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    installs = [
        command
        for command in commands
        if "install" in command and "requirements-security.txt" in command
    ]
    assert len(installs) == 1, "one explicit pinned auditor installation required"
    assert installs[0][:4] == [AUDITOR, "-m", "pip", "install"], (
        "auditor installation must not mutate the API interpreter"
    )
    audits = [
        command
        for command in commands
        if "scripts/check_installed_api_dependencies.py" in command
    ]
    assert len(audits) == 1
    audit = audits[0]
    assert audit[audit.index("--python") + 1] == WHEEL
    assert audit[audit.index("--audit-python") + 1] == AUDITOR
    checks = [
        index
        for index, command in enumerate(commands)
        if command == ["python", "-m", "pip", "check"]
    ]
    assert len(checks) == 2, "API consistency must pass before and after auditing"
    ordered = [
        checks[0],
        commands.index(["python", "-m", "pip", "freeze", "--all", ">", BEFORE]),
        commands.index(["python", "-m", "venv", "$RUNNER_TEMP/api-audit-env"]),
        commands.index(
            [
                AUDITOR,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "-r",
                "requirements-bootstrap.txt",
            ]
        ),
        commands.index(installs[0]),
        commands.index([AUDITOR, "-m", "pip", "check"]),
        commands.index(audit),
        checks[1],
        commands.index(["python", "-m", "pip", "freeze", "--all", ">", AFTER]),
        commands.index(["cmp", BEFORE, AFTER]),
    ]
    assert ordered == sorted(set(ordered)), (
        "check both graphs and compare the complete API freeze after the audit"
    )


def isolated_workflow():
    return {
        "jobs": {
            "quality-checks": {
                "steps": [
                    {
                        "run": "\n".join(
                            [
                                "python -m pip check",
                                f'python -m pip freeze --all > "{BEFORE}"',
                                'python -m venv "$RUNNER_TEMP/api-audit-env"',
                                f'"{AUDITOR}" -m pip install --upgrade -r requirements-bootstrap.txt',
                                f'"{AUDITOR}" -m pip install -r requirements-security.txt',
                                f'"{AUDITOR}" -m pip check',
                                (
                                    "python scripts/check_installed_api_dependencies.py "
                                    f'--python "{WHEEL}" --audit-python "{AUDITOR}" '
                                    '--report-dir "$RUNNER_TEMP/api-installed-audit"'
                                ),
                                "python -m pip check",
                                f'python -m pip freeze --all > "{AFTER}"',
                                f'cmp "{BEFORE}" "{AFTER}"',
                            ]
                        )
                    }
                ]
            }
        }
    }


def test_current_workflow_preserves_api_graph_during_isolated_audit():
    verify_isolation(yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text()))


def test_independently_pinned_auditor_and_api_profiles_are_supported():
    verify_isolation(isolated_workflow())


@pytest.mark.parametrize(
    "old,new",
    [
        (f'"{AUDITOR}" -m pip install', "python -m pip install"),
        (f'--audit-python "{AUDITOR}"', f'--audit-python "{WHEEL}"'),
        ("python -m pip check\n", ""),
        (f'"{AUDITOR}" -m pip check\n', ""),
        (f'cmp "{BEFORE}" "{AFTER}"', ""),
        ('python -m venv "$RUNNER_TEMP/api-audit-env"', ""),
        (f'"{AUDITOR}" -m pip install --upgrade -r requirements-bootstrap.txt', ""),
        (f'python -m pip freeze --all > "{BEFORE}"', ""),
        (f'python -m pip freeze --all > "{AFTER}"', ""),
    ],
)
def test_shared_or_incomplete_audit_workflow_is_rejected(old, new):
    workflow = copy.deepcopy(isolated_workflow())
    step = workflow["jobs"]["quality-checks"]["steps"][0]
    assert old in step["run"]
    step["run"] = step["run"].replace(old, new)
    with pytest.raises((AssertionError, ValueError)):
        verify_isolation(workflow)

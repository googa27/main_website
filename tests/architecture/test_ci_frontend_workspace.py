"""CI must execute the canonical whole-workspace frontend task graph."""

import copy
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TASKS = ("lint", "typecheck", "build")


def _current() -> tuple[dict, dict]:
    return (
        yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text()),
        json.loads((ROOT / "package.json").read_text()),
    )


def _assert_workspace_gates(workflow: dict, package: dict) -> None:
    job = workflow["jobs"]["quality-checks"]
    assert "if" not in job, "Workspace job must not be conditional"
    assert job.get("continue-on-error", False) is False, "Workspace failure hidden"
    for owner in (workflow, job):
        assert (
            owner.get("defaults", {}).get("run", {}).get("working-directory", ".")
            == "."
        ), "Workspace default must run at root"
    for task in TASKS:
        assert package["scripts"][task] == f"turbo {task}", "Canonical graph bypassed"
        command = f"pnpm run {task} --force"
        matches = [
            step
            for step in job["steps"]
            if isinstance(step.get("run"), str) and step["run"].strip() == command
        ]
        assert len(matches) == 1, f"Workspace {task} gate absent or duplicated"
        step = matches[0]
        assert "if" not in step, "Workspace step must not be conditional"
        assert step.get("continue-on-error", False) is False, "Task failure hidden"
        assert step.get("working-directory", ".") == ".", "Task must run at root"


def _coherent_fixture() -> tuple[dict, dict]:
    workflow, package = copy.deepcopy(_current())
    for step in workflow["jobs"]["quality-checks"]["steps"]:
        for task in TASKS:
            if step.get("run") == f"pnpm --filter web {task}":
                step["run"] = f"pnpm run {task} --force"
    return workflow, package


def test_actual_ci_runs_the_canonical_complete_workspace() -> None:
    _assert_workspace_gates(*_current())


def test_coherent_root_task_fixture_is_accepted() -> None:
    _assert_workspace_gates(*_coherent_fixture())


@pytest.mark.parametrize(
    "mutation",
    [
        "web-only-lint",
        "web-only-typecheck",
        "web-only-build",
        "unforced",
        "duplicate",
        "conditional-step",
        "allowed-step-failure",
        "child-step-directory",
        "conditional-job",
        "allowed-job-failure",
        "child-job-default",
        "child-workflow-default",
        "bypassed-lint-script",
        "bypassed-typecheck-script",
        "bypassed-build-script",
    ],
)
def test_narrowed_or_nonexecuting_workspace_gates_are_refused(mutation: str) -> None:
    workflow, package = _coherent_fixture()
    _assert_workspace_gates(workflow, package)
    job = workflow["jobs"]["quality-checks"]
    lint = next(s for s in job["steps"] if s.get("run") == "pnpm run lint --force")
    if mutation.startswith("web-only-"):
        task = mutation.removeprefix("web-only-")
        step = next(
            s for s in job["steps"] if s.get("run") == f"pnpm run {task} --force"
        )
        step["run"] = f"pnpm --filter web {task}"
    elif mutation == "unforced":
        lint["run"] = "pnpm run lint"
    elif mutation == "duplicate":
        job["steps"].append(copy.deepcopy(lint))
    elif mutation == "conditional-step":
        lint["if"] = "false"
    elif mutation == "allowed-step-failure":
        lint["continue-on-error"] = True
    elif mutation == "child-step-directory":
        lint["working-directory"] = "apps/web"
    elif mutation == "conditional-job":
        job["if"] = "false"
    elif mutation == "allowed-job-failure":
        job["continue-on-error"] = True
    elif mutation in ("child-job-default", "child-workflow-default"):
        owner = job if mutation == "child-job-default" else workflow
        owner["defaults"] = {"run": {"working-directory": "apps/web"}}
    elif mutation.startswith("bypassed-"):
        task = mutation.removeprefix("bypassed-").removesuffix("-script")
        package["scripts"][task] = "echo passed"
    else:
        raise AssertionError(f"Unimplemented mutation: {mutation}")
    with pytest.raises(AssertionError):
        _assert_workspace_gates(workflow, package)

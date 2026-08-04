from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "apps" / "api"


def test_python_security_floors_are_synchronized_across_manifests() -> None:
    runtime_requirements = (API / "requirements.txt").read_text(encoding="utf-8")
    dev_requirements = (API / "requirements-dev.txt").read_text(encoding="utf-8")
    pyproject = tomllib.loads((API / "pyproject.toml").read_text(encoding="utf-8"))

    runtime_floors = {"idna==3.15", "Mako==1.3.12"}
    dev_floors = {"Pygments==2.20.0"}
    project_runtime = set(pyproject["project"]["dependencies"])
    project_dev = set(pyproject["project"]["optional-dependencies"]["dev"])

    assert runtime_floors <= set(runtime_requirements.splitlines())
    assert runtime_floors <= project_runtime
    assert dev_floors <= set(dev_requirements.splitlines())
    assert dev_floors <= project_dev


def test_postcss_security_floor_is_owned_by_override_and_lock() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    workspace = (ROOT / "pnpm-workspace.yaml").read_text(encoding="utf-8")
    lock = (ROOT / "pnpm-lock.yaml").read_text(encoding="utf-8")

    assert package["pnpm"]["overrides"]["postcss@<8.5.23"] == "8.5.23"
    assert "postcss@" not in workspace
    assert "postcss@8.5.23:" in lock
    assert "postcss@8.5.19:" not in lock

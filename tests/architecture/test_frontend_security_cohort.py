"""Bind the current frontend repair and explicit unsuppressed glob disposition."""

import copy
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SELECTOR = "zod@>=4.0.0 <4.6.6"
COMMAND = "node --test tests/node/frontend-security-cohort.test.mjs"


def _current() -> tuple[dict, dict, dict]:
    return (
        json.loads((ROOT / "package.json").read_text()),
        yaml.safe_load((ROOT / "pnpm-lock.yaml").read_text()),
        json.loads((ROOT / "docs/ARCHITECTURE.yaml").read_text())["architecture"][
            "frontend_security_cohort"
        ],
    )


def _assert_cohort(package: dict, lock: dict, policy: dict) -> None:
    selected = package["pnpm"]["overrides"].get(SELECTOR)
    assert selected == "4.6.6", "Unreviewed Zod repair"
    assert lock["overrides"].get(SELECTOR) == selected, "Zod override mismatch"
    assert policy["zod"] == selected, "Zod policy mismatch"
    for section in ["packages", "snapshots"]:
        assert {key for key in lock[section] if key.startswith("zod@")} == {
            "zod@4.6.6"
        }, "Unreviewed parallel Zod branch"
    commands = {
        part.strip()
        for part in package["scripts"]["check:dependency-build-policy"].split("&&")
    }
    assert COMMAND in commands, "Frontend consumer gate absent"
    assert policy["consumer_command"] == COMMAND, "Frontend consumer policy mismatch"
    disposition = policy["minimatch_disposition"]
    assert disposition["audit_status"] == "retained-unsuppressed"
    assert disposition["advisory"] == "GHSA-g3hv-75wg-m249"
    versions = {"3.1.5", "10.2.5", "10.2.6"}
    assert set(disposition["versions"]) == versions
    assert {
        key.removeprefix("minimatch@")
        for key in lock["packages"]
        if key.startswith("minimatch@")
    } == versions, "Glob cohort needs renewed consumer review"
    assert not any("minimatch" in key for key in package["pnpm"]["overrides"]), (
        "Incompatible glob major override"
    )
    actual_consumers = {
        key.split("(")[0]: snapshot["dependencies"]["minimatch"]
        for key, snapshot in lock["snapshots"].items()
        if "minimatch" in snapshot.get("dependencies", {})
    }
    assert actual_consumers == disposition["consumers"], "Unreviewed glob consumer"
    assert len(disposition["caller_files"]) == 3
    assert all(len(entry["sha256"]) == 64 for entry in disposition["caller_files"])


def test_current_frontend_cohort() -> None:
    _assert_cohort(*_current())


def test_synchronized_vulnerable_zod_is_refused() -> None:
    package, lock, policy = copy.deepcopy(_current())
    package["pnpm"]["overrides"][SELECTOR] = "4.6.4"
    lock["overrides"][SELECTOR] = "4.6.4"
    policy["zod"] = "4.6.4"
    with pytest.raises(AssertionError, match="Unreviewed Zod repair"):
        _assert_cohort(package, lock, policy)


def test_parallel_vulnerable_zod_is_refused() -> None:
    package, lock, policy = copy.deepcopy(_current())
    lock["packages"]["zod@4.6.4"] = {}
    with pytest.raises(AssertionError, match="Unreviewed parallel Zod branch"):
        _assert_cohort(package, lock, policy)


def test_glob_major_forcing_is_refused() -> None:
    package, lock, policy = copy.deepcopy(_current())
    package["pnpm"]["overrides"]["minimatch@<11.0.1"] = "11.0.1"
    with pytest.raises(AssertionError, match="Incompatible glob major override"):
        _assert_cohort(package, lock, policy)


@pytest.mark.parametrize("replacement", ["", "echo " + COMMAND, COMMAND + ".backup"])
def test_frontend_gate_cannot_be_replaced(replacement: str) -> None:
    package, lock, policy = copy.deepcopy(_current())
    package["scripts"]["check:dependency-build-policy"] = package["scripts"][
        "check:dependency-build-policy"
    ].replace(COMMAND, replacement)
    with pytest.raises(AssertionError, match="Frontend consumer gate absent"):
        _assert_cohort(package, lock, policy)

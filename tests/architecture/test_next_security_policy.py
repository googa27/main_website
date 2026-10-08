"""Admit maintained Next cohorts without losing compiler and installer controls."""

import copy
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SELECTOR = "next@>=16.0.0 <16.3.8"
CONSUMER = "node --test tests/node/next-security.test.mjs tests/node/next-process-ownership.test.mjs"


def _current() -> tuple[dict, dict, dict, dict]:
    return (
        json.loads((ROOT / "package.json").read_text()),
        json.loads((ROOT / "apps/web/package.json").read_text()),
        yaml.safe_load((ROOT / "pnpm-lock.yaml").read_text()),
        json.loads((ROOT / "docs/ARCHITECTURE.yaml").read_text())["architecture"].get(
            "next_security_policy", {}
        ),
    )


def _version(value: str) -> tuple[int, ...]:
    parts = value.split(".")
    assert len(parts) == 3 and all(x.isdecimal() for x in parts), "Unreviewed release"
    return tuple(int(x) for x in parts)


def _assert_policy(package: dict, web: dict, lock: dict, policy: dict) -> None:
    selected = package["pnpm"]["overrides"].get(SELECTOR)
    assert selected is not None, "Patched Next override absent"
    assert _version(selected) >= (16, 3, 8), "Unpatched Next selection"
    assert lock["overrides"].get(SELECTOR) == selected, "Next manifest/lock mismatch"
    assert policy.get("version") == selected, "Unreviewed Next selection"
    importer = lock["importers"]["apps/web"]
    for section, name in [
        ("dependencies", "next"),
        ("devDependencies", "eslint-config-next"),
    ]:
        assert web[section][name] == selected, "Uncoupled Next/config declaration"
        entry = importer[section][name]
        assert entry["specifier"] == selected, "Uncoupled importer declaration"
        assert entry["version"].split("(")[0] == selected, (
            "Uncoupled importer resolution"
        )
    for section in ["packages", "snapshots"]:
        for name in [
            "next",
            "eslint-config-next",
            "@next/env",
            "@next/eslint-plugin-next",
        ]:
            versions = {
                key.removeprefix(name + "@").split("(")[0]
                for key in lock[section]
                if key.startswith(name + "@")
            }
            assert versions == {selected}, "Unreviewed parallel Next cohort"
    for key, snapshot in lock["snapshots"].items():
        if key.startswith("next@"):
            actual = {
                name: version
                for name, version in snapshot.get("optionalDependencies", {}).items()
                if name.startswith("@next/swc-")
            }
            assert actual == policy["optional_compilers"], (
                "Unreviewed compiler snapshot"
            )
    for name, expected in policy["optional_compilers"].items():
        versions = {
            key.removeprefix(name + "@").split("(")[0]
            for key in lock["packages"]
            if key.startswith(name + "@")
        }
        assert versions == {selected} == {expected}, "Uncoupled optional compiler"
    for name, integrity in policy["published_integrities"].items():
        assert (
            lock["packages"][name + "@" + selected]["resolution"]["integrity"]
            == integrity
        )
    commands = {
        value.strip()
        for value in package["scripts"]["check:dependency-build-policy"].split("&&")
    }
    assert CONSUMER in commands, "Actual Next consumer gate missing"


def test_current_next_path_is_patched_coupled_and_exercised() -> None:
    _assert_policy(*_current())


def test_synchronized_vulnerable_next_selection_is_refused() -> None:
    package, web, lock, policy = copy.deepcopy(_current())
    package["pnpm"]["overrides"][SELECTOR] = "16.3.5"
    lock["overrides"][SELECTOR] = "16.3.5"
    policy["version"] = "16.3.5"
    with pytest.raises(AssertionError, match="Unpatched Next selection"):
        _assert_policy(package, web, lock, policy)


def test_parallel_vulnerable_next_package_is_refused() -> None:
    package, web, lock, policy = copy.deepcopy(_current())
    lock["packages"]["next@16.3.5"] = {}
    with pytest.raises(AssertionError, match="Unreviewed parallel Next cohort"):
        _assert_policy(package, web, lock, policy)


def test_uncoupled_lint_config_is_refused() -> None:
    package, web, lock, policy = copy.deepcopy(_current())
    web["devDependencies"]["eslint-config-next"] = "16.3.5"
    with pytest.raises(AssertionError, match="Uncoupled Next/config declaration"):
        _assert_policy(package, web, lock, policy)


@pytest.mark.parametrize("replacement", ["16.3.5", None])
def test_changed_native_snapshot_is_refused(replacement: str | None) -> None:
    package, web, lock, policy = copy.deepcopy(_current())
    key = next(name for name in lock["snapshots"] if name.startswith("next@"))
    optional = lock["snapshots"][key]["optionalDependencies"]
    if replacement is None:
        del optional["@next/swc-linux-x64-gnu"]
    else:
        optional["@next/swc-linux-x64-gnu"] = replacement
    with pytest.raises(AssertionError, match="Unreviewed compiler snapshot"):
        _assert_policy(package, web, lock, policy)


@pytest.mark.parametrize("replacement", [CONSUMER + ".backup", "echo " + CONSUMER, ""])
def test_lookalike_or_removed_real_consumer_gate_is_refused(replacement: str) -> None:
    package, web, lock, policy = copy.deepcopy(_current())
    package["scripts"]["check:dependency-build-policy"] = package["scripts"][
        "check:dependency-build-policy"
    ].replace(CONSUMER, replacement)
    with pytest.raises(AssertionError, match="Actual Next consumer gate missing"):
        _assert_policy(package, web, lock, policy)

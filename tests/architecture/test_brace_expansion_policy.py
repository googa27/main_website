"""Bind the reviewed brace-expansion route to manifests and parsed pnpm state."""

import copy
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PATCHED_OVERRIDES = {
    "brace-expansion@<2.0.0": "1.1.21",
    "brace-expansion@>=2.0.0 <3.0.0": "2.1.7",
    "brace-expansion@>=4.0.0 <5.0.12": "5.0.12",
}


def _assert_policy(package: dict, lock: dict, policy: dict) -> None:
    assert set(policy["brace_versions"]) == {
        PATCHED_OVERRIDES["brace-expansion@<2.0.0"],
        PATCHED_OVERRIDES["brace-expansion@>=4.0.0 <5.0.12"],
    }, "Unreviewed brace-expansion architecture selection"
    overrides = {
        name: version
        for name, version in package["pnpm"]["overrides"].items()
        if name.startswith("brace-expansion@")
    }
    assert overrides == PATCHED_OVERRIDES, "Unpatched brace-expansion override"
    assert {
        name: version
        for name, version in lock["overrides"].items()
        if name.startswith("brace-expansion@")
    } == overrides, "Manifest/lock override mismatch"
    expected = {f"brace-expansion@{version}" for version in policy["brace_versions"]}
    for section in ["packages", "snapshots"]:
        actual = {name for name in lock[section] if name.startswith("brace-expansion@")}
        assert actual == expected, "Unreviewed brace-expansion lock selection"
    parents = {
        name.removeprefix("minimatch@")
        for name in lock["snapshots"]
        if name.startswith("minimatch@")
    }
    assert parents == set(policy["minimatch_versions"]), "Untested minimatch parent"
    for version in parents:
        dependency = lock["snapshots"][f"minimatch@{version}"]["dependencies"]
        assert dependency["brace-expansion"] in policy["brace_versions"]
    assert package["scripts"]["check:dependency-build-policy"].endswith(
        "&& node --test tests/node/brace-expansion.test.mjs"
    ), "Consumer gate is absent from the required dependency policy command"


def _current() -> tuple[dict, dict, dict]:
    package = json.loads((ROOT / "package.json").read_text())
    lock = yaml.safe_load((ROOT / "pnpm-lock.yaml").read_text())
    policy = json.loads((ROOT / "docs/ARCHITECTURE.yaml").read_text())["architecture"][
        "brace_expansion_policy"
    ]
    return package, lock, policy


def test_selected_brace_expansion_route_is_patched_and_exercised() -> None:
    _assert_policy(*_current())


@pytest.mark.parametrize(
    ("selector", "vulnerable"),
    [
        ("brace-expansion@<2.0.0", "1.1.18"),
        ("brace-expansion@>=2.0.0 <3.0.0", "2.1.4"),
        ("brace-expansion@>=4.0.0 <5.0.12", "5.0.9"),
    ],
)
def test_synchronized_unpatched_overrides_are_refused(
    selector: str, vulnerable: str
) -> None:
    package, lock, policy = copy.deepcopy(_current())
    package["pnpm"]["overrides"][selector] = vulnerable
    lock["overrides"][selector] = vulnerable
    with pytest.raises(AssertionError, match="Unpatched brace-expansion override"):
        _assert_policy(package, lock, policy)


def test_an_additional_unreviewed_lock_branch_is_refused() -> None:
    package, lock, policy = copy.deepcopy(_current())
    lock["packages"]["brace-expansion@3.0.6"] = {}
    with pytest.raises(
        AssertionError, match="Unreviewed brace-expansion lock selection"
    ):
        _assert_policy(package, lock, policy)


def test_an_additional_parent_requires_consumer_coverage() -> None:
    package, lock, policy = copy.deepcopy(_current())
    lock["snapshots"]["minimatch@10.2.7"] = {
        "dependencies": {"brace-expansion": "5.0.12"}
    }
    with pytest.raises(AssertionError, match="Untested minimatch parent"):
        _assert_policy(package, lock, policy)

"""Refuse vulnerable or unreviewed source-map-js dependency routes."""

import copy
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SELECTOR = "source-map-js@<1.2.2"
PATCHED = "1.2.2"


def _current() -> tuple[dict, dict, dict]:
    package = json.loads((ROOT / "package.json").read_text())
    lock = yaml.safe_load((ROOT / "pnpm-lock.yaml").read_text())
    policy = json.loads((ROOT / "docs/ARCHITECTURE.yaml").read_text())["architecture"][
        "source_map_policy"
    ]
    return package, lock, policy


def _assert_policy(package: dict, lock: dict, policy: dict) -> None:
    assert package["pnpm"]["overrides"].get(SELECTOR) == PATCHED, (
        "Unpatched source-map-js override"
    )
    assert lock["overrides"].get(SELECTOR) == PATCHED, "Manifest/lock override mismatch"
    assert policy["version"] == PATCHED, "Unpatched architecture selection"
    for section in ["packages", "snapshots"]:
        actual = {name for name in lock[section] if name.startswith("source-map-js@")}
        assert actual == {f"source-map-js@{PATCHED}"}, "Unreviewed source-map lock"
    parents = {
        name: entry["dependencies"]["source-map-js"]
        for name, entry in lock["snapshots"].items()
        if "source-map-js" in entry.get("dependencies", {})
    }
    assert set(parents) == set(policy["parents"]), "Untested source-map parent"
    assert all(version == PATCHED for version in parents.values())
    commands = {
        command.strip()
        for command in package["scripts"]["check:dependency-build-policy"].split("&&")
    }
    assert "node --test tests/node/source-map-offsets.test.mjs" in commands, (
        "Public consumer gate is absent"
    )


def test_selected_source_map_route_is_patched_and_exercised() -> None:
    _assert_policy(*_current())


def test_a_synchronized_vulnerable_selection_is_refused() -> None:
    package, lock, policy = copy.deepcopy(_current())
    package["pnpm"]["overrides"][SELECTOR] = "1.2.1"
    lock["overrides"][SELECTOR] = "1.2.1"
    policy["version"] = "1.2.1"
    with pytest.raises(AssertionError, match="Unpatched source-map-js override"):
        _assert_policy(package, lock, policy)


def test_the_lock_cannot_weaken_the_manifest_floor() -> None:
    package, lock, policy = copy.deepcopy(_current())
    lock["overrides"][SELECTOR] = "1.2.1"
    with pytest.raises(AssertionError, match="Manifest/lock override mismatch"):
        _assert_policy(package, lock, policy)


def test_an_additional_vulnerable_lock_branch_is_refused() -> None:
    package, lock, policy = copy.deepcopy(_current())
    lock["packages"]["source-map-js@1.2.1"] = {}
    with pytest.raises(AssertionError, match="Unreviewed source-map lock"):
        _assert_policy(package, lock, policy)


def test_an_additional_parent_requires_review_and_consumer_coverage() -> None:
    package, lock, policy = copy.deepcopy(_current())
    lock["snapshots"]["other-parent@1.0.0"] = {
        "dependencies": {"source-map-js": PATCHED}
    }
    with pytest.raises(AssertionError, match="Untested source-map parent"):
        _assert_policy(package, lock, policy)


def test_the_required_consumer_gate_cannot_be_removed() -> None:
    package, lock, policy = copy.deepcopy(_current())
    package["scripts"]["check:dependency-build-policy"] = (
        "node scripts/check-dependency-build-policy.mjs"
    )
    with pytest.raises(AssertionError, match="Public consumer gate is absent"):
        _assert_policy(package, lock, policy)


@pytest.mark.parametrize(
    "replacement",
    [
        "node --test tests/node/source-map-offsets.test.mjs.backup",
        "node --test tests/node/source-map-offsets.test.mjs-other",
        "echo node --test tests/node/source-map-offsets.test.mjs",
    ],
)
def test_a_similar_filename_or_echo_cannot_replace_the_consumer_gate(
    replacement: str,
) -> None:
    package, lock, policy = copy.deepcopy(_current())
    package["scripts"]["check:dependency-build-policy"] = package["scripts"][
        "check:dependency-build-policy"
    ].replace("node --test tests/node/source-map-offsets.test.mjs", replacement)
    with pytest.raises(AssertionError, match="Public consumer gate is absent"):
        _assert_policy(package, lock, policy)

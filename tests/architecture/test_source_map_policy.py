"""Refuse vulnerable or unreviewed source-map-js dependency routes."""

import copy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SELECTOR = "source-map-js@<1.2.2"
PATCHED = "1.2.2"
PATCH_KEY = f"source-map-js@{PATCHED}"
PATCH_PATH = "patches/source-map-js@1.2.2.patch"


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
    patch = policy["correctness_patch"]
    assert patch["path"] == PATCH_PATH, "Unreviewed source-map patch path"
    assert package["pnpm"]["patchedDependencies"].get(PATCH_KEY) == PATCH_PATH, (
        "Source-map correctness patch is absent"
    )
    assert lock["patchedDependencies"].get(PATCH_KEY) == {
        "hash": patch["sha256"],
        "path": PATCH_PATH,
    }, "Source-map patch lock mismatch"
    patched_version = f"{PATCHED}(patch_hash={patch['sha256']})"
    for section in ["packages", "snapshots"]:
        actual = {name for name in lock[section] if name.startswith("source-map-js@")}
        expected = PATCHED if section == "packages" else patched_version
        assert actual == {f"source-map-js@{expected}"}, "Unreviewed source-map lock"
    parents = {
        name: entry["dependencies"]["source-map-js"]
        for name, entry in lock["snapshots"].items()
        if "source-map-js" in entry.get("dependencies", {})
    }
    assert set(parents) == set(policy["parents"]), "Untested source-map parent"
    assert all(version == patched_version for version in parents.values()), (
        "Unpatched source-map parent"
    )
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


def test_source_map_patch_bytes_bind_the_reviewed_selection() -> None:
    _, _, policy = _current()
    patch = policy["correctness_patch"]
    actual = (ROOT / PATCH_PATH).read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(actual).hexdigest() == patch["sha256"]


def test_the_correctness_patch_declaration_cannot_be_removed() -> None:
    package, lock, policy = copy.deepcopy(_current())
    del package["pnpm"]["patchedDependencies"][PATCH_KEY]
    with pytest.raises(AssertionError, match="Source-map correctness patch is absent"):
        _assert_policy(package, lock, policy)


def test_patch_metadata_cannot_disagree_with_the_lock() -> None:
    package, lock, policy = copy.deepcopy(_current())
    lock["patchedDependencies"][PATCH_KEY]["hash"] = "0" * 64
    with pytest.raises(AssertionError, match="Source-map patch lock mismatch"):
        _assert_policy(package, lock, policy)


def test_an_unpatched_snapshot_cannot_replace_the_patched_route() -> None:
    package, lock, policy = copy.deepcopy(_current())
    key = f"{PATCH_KEY}(patch_hash={policy['correctness_patch']['sha256']})"
    lock["snapshots"][PATCH_KEY] = lock["snapshots"].pop(key)
    with pytest.raises(AssertionError, match="Unreviewed source-map lock"):
        _assert_policy(package, lock, policy)


def test_a_parent_cannot_resolve_the_unpatched_copy() -> None:
    package, lock, policy = copy.deepcopy(_current())
    parent = policy["parents"][0]
    lock["snapshots"][parent]["dependencies"]["source-map-js"] = PATCHED
    with pytest.raises(AssertionError, match="Unpatched source-map parent"):
        _assert_policy(package, lock, policy)

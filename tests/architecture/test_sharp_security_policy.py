"""Keep the real Next image dependency on a maintained, exercised native cohort."""

import copy
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SELECTOR = "sharp@<0.35.5"
CONSUMER_COMMAND = "node --test tests/node/sharp-svg-security.test.mjs"


def _current() -> tuple[dict, dict, dict]:
    return (
        json.loads((ROOT / "package.json").read_text()),
        yaml.safe_load((ROOT / "pnpm-lock.yaml").read_text()),
        json.loads((ROOT / "docs/ARCHITECTURE.yaml").read_text())["architecture"].get(
            "sharp_policy", {}
        ),
    )


def _version(value: str) -> tuple[int, ...]:
    parts = value.split(".")
    assert len(parts) == 3 and all(x.isdecimal() for x in parts), "Unreviewed version"
    return tuple(int(x) for x in parts)


def _assert_policy(package: dict, lock: dict, policy: dict) -> None:
    selected = package["pnpm"]["overrides"].get(SELECTOR)
    assert selected is not None, "Patched Sharp override absent"
    assert _version(selected) >= (0, 35, 5), "Unpatched Sharp route"
    assert lock["overrides"].get(SELECTOR) == selected, "Manifest/lock Sharp mismatch"
    assert policy.get("version") == selected, "Unreviewed Sharp selection"
    assert _version(policy["minimum_rsvg"]) >= (2, 63, 2), "Unpatched SVG library floor"
    for section in ["packages", "snapshots"]:
        actual = {x.split("(")[0] for x in lock[section] if x.startswith("sharp@")}
        assert actual == {"sharp@" + selected}, "Unreviewed Sharp lock branch"
    parents = {
        name: {
            **entry.get("dependencies", {}),
            **entry.get("optionalDependencies", {}),
        }["sharp"]
        for name, entry in lock["snapshots"].items()
        if "sharp"
        in {**entry.get("dependencies", {}), **entry.get("optionalDependencies", {})}
    }
    assert set(parents) == set(policy["parents"]), "Untested Sharp parent"
    assert all(x.split("(")[0] == selected for x in parents.values()), (
        "Unpatched parent resolution"
    )
    for key, snapshot in lock["snapshots"].items():
        if key.startswith("sharp@"):
            actual = {
                name: version
                for name, version in snapshot.get("optionalDependencies", {}).items()
                if name.startswith("@img/sharp-")
            }
            assert actual == policy["optional_dependencies"], (
                "Unreviewed native snapshot resolution"
            )
    for name, expected in policy["optional_dependencies"].items():
        versions = {
            x.removeprefix(name + "@").split("(")[0]
            for x in lock["packages"]
            if x.startswith(name + "@")
        }
        assert versions == {expected}, "Unreviewed optional native cohort"
    for name, integrity in policy["published_integrities"].items():
        version = selected if name == "sharp" else policy["optional_dependencies"][name]
        assert (
            lock["packages"][name + "@" + version]["resolution"]["integrity"]
            == integrity
        ), "Unreviewed published native integrity"
    commands = {
        x.strip()
        for x in package["scripts"]["check:dependency-build-policy"].split("&&")
    }
    assert CONSUMER_COMMAND in commands, "Public native consumer gate is absent"


def test_selected_native_image_route_is_patched_and_exercised() -> None:
    _assert_policy(*_current())


def test_a_synchronized_vulnerable_route_is_refused() -> None:
    package, lock, policy = copy.deepcopy(_current())
    package["pnpm"]["overrides"][SELECTOR] = "0.35.4"
    lock["overrides"][SELECTOR] = "0.35.4"
    policy["version"] = "0.35.4"
    with pytest.raises(AssertionError, match="Unpatched Sharp route"):
        _assert_policy(package, lock, policy)


def test_the_lock_cannot_weaken_the_manifest_floor() -> None:
    package, lock, policy = copy.deepcopy(_current())
    lock["overrides"][SELECTOR] = "0.35.4"
    with pytest.raises(AssertionError, match="Manifest/lock Sharp mismatch"):
        _assert_policy(package, lock, policy)


def test_a_vulnerable_parallel_lock_branch_is_refused() -> None:
    package, lock, policy = copy.deepcopy(_current())
    lock["packages"]["sharp@0.35.4"] = {}
    with pytest.raises(AssertionError, match="Unreviewed Sharp lock branch"):
        _assert_policy(package, lock, policy)


def test_an_additional_image_parent_needs_real_consumer_review() -> None:
    package, lock, policy = copy.deepcopy(_current())
    lock["snapshots"]["other-parent@1.0.0"] = {
        "optionalDependencies": {"sharp": "0.35.5"}
    }
    with pytest.raises(AssertionError, match="Untested Sharp parent"):
        _assert_policy(package, lock, policy)


@pytest.mark.parametrize(
    "replacement", [CONSUMER_COMMAND + ".backup", "echo " + CONSUMER_COMMAND]
)
def test_a_similar_filename_or_echo_cannot_replace_the_native_gate(
    replacement: str,
) -> None:
    package, lock, policy = copy.deepcopy(_current())
    package["scripts"]["check:dependency-build-policy"] = package["scripts"][
        "check:dependency-build-policy"
    ].replace(CONSUMER_COMMAND, replacement)
    with pytest.raises(AssertionError, match="Public native consumer gate is absent"):
        _assert_policy(package, lock, policy)


@pytest.mark.parametrize("replacement", ["0.35.4", None])
def test_native_snapshot_resolution_cannot_be_weakened_or_removed(
    replacement: str | None,
) -> None:
    package, lock, policy = copy.deepcopy(_current())
    key = next(x for x in lock["snapshots"] if x.startswith("sharp@"))
    optional = lock["snapshots"][key]["optionalDependencies"]
    if replacement is None:
        del optional["@img/sharp-linux-x64"]
    else:
        optional["@img/sharp-linux-x64"] = replacement
    with pytest.raises(AssertionError, match="Unreviewed native snapshot resolution"):
        _assert_policy(package, lock, policy)

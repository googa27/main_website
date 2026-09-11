"""Executable monorepo tooling and dependency-lifecycle contracts."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_ACTIONS = {
    "actions/checkout": (
        "3d3c42e5aac5ba805825da76410c181273ba90b1",
        "v7.0.1",
    ),
    "actions/setup-node": (
        "820762786026740c76f36085b0efc47a31fe5020",
        "v7.0.0",
    ),
    "actions/setup-python": (
        "5fda3b95a4ea91299a34e894583c3862153e4b97",
        "v7.0.0",
    ),
    "pnpm/action-setup": (
        "0977fd99725f1db4007ccb2928dbb4e90d06cc86",
        "v6.0.10",
    ),
}

EXPECTED_DENIED_BUILDS = {
    "@tailwindcss/oxide": {
        "version": "4.1.12",
        "decision": "deny",
        "lifecycle_command": "node ./scripts/install.js",
        "manifest_sha256": "19e31a0bc5fa826d5f4c1a73fa2d7e821e3ed826f86d28987618bc18c0a3a656",
        "script_sha256": "df8750369bdc91787de5baec99eaaf27b7d8d2952acb25cf1a0b0aa511185b2a",
    },
    "unrs-resolver": {
        "version": "1.11.1",
        "decision": "deny",
        "lifecycle_command": "napi-postinstall unrs-resolver 1.11.1 check",
        "manifest_sha256": "0510c5611b2c4436d12364dff5ddd0f227dacd174cadd62141b226bce1fa4b19",
        "script_sha256": "2d79f5b3ee7566309a587c267ab8363881f5ebe97a728b0271fb530569b1f356",
        "support_package": {
            "name": "napi-postinstall",
            "version": "0.3.3",
            "manifest_sha256": "94d75d361fd158062dd3888ca0bd3abc90d67ef0f5f746d4b7b0de9065a384bd",
            "lib_files": [
                "lib/cli.js",
                "lib/constants.js",
                "lib/fallback.js",
                "lib/helpers.js",
                "lib/index.js",
                "lib/target.js",
                "lib/types.js",
            ],
            "lib_tree_sha256": "f2b5f747776727b0bf13220d49407cd0523d180842a09df3bc2e2f2e9116e3d8",
            "cli_sha256": "2d79f5b3ee7566309a587c267ab8363881f5ebe97a728b0271fb530569b1f356",
        },
    },
}


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_node_and_pnpm_runtimes_are_exact_and_managed() -> None:
    package = _json("package.json")

    assert package["packageManager"] == "pnpm@10.34.5"
    assert package["devEngines"]["runtime"] == {
        "name": "node",
        "version": "24.19.0",
        "onFail": "download",
    }
    assert package["scripts"]["prepare"] == "husky"
    assert package["scripts"]["check:dependency-build-policy"] == (
        "node scripts/check-dependency-build-policy.mjs"
    )


def test_dependency_build_scripts_are_explicitly_denied_and_pinned() -> None:
    package = _json("package.json")
    architecture = _json("docs/ARCHITECTURE.yaml")
    policy = architecture["architecture"]["dependency_lifecycle_policy"]

    assert set(package["pnpm"]["ignoredBuiltDependencies"]) == set(
        EXPECTED_DENIED_BUILDS
    )
    assert policy["package_manager"] == "pnpm@10.34.5"
    assert policy["denied_packages"] == EXPECTED_DENIED_BUILDS
    assert policy["verification_command"] == "pnpm run check:dependency-build-policy"

    lock = (ROOT / "pnpm-lock.yaml").read_text(encoding="utf-8")
    for name, evidence in EXPECTED_DENIED_BUILDS.items():
        escaped = re.escape(name)
        versions = set(
            re.findall(rf"^  ['\"]?{escaped}@([^'\":]+)['\"]?:$", lock, re.MULTILINE)
        )
        assert versions == {evidence["version"]}, (name, versions)


def test_dependency_policy_checker_validates_reviewed_bytes_and_pnpm_state() -> None:
    checker = (ROOT / "scripts/check-dependency-build-policy.mjs").read_text(
        encoding="utf-8"
    )

    for required_guard in (
        "createHash",
        "manifest_sha256",
        "script_sha256",
        "support_package",
        "lib_tree_sha256",
        "lib_files",
        "npm_execpath",
        "ignored-builds",
        ".modules.yaml",
        "pendingBuilds",
        "dangerouslyAllowAllBuilds",
        "onlyBuiltDependencies",
        "allowBuilds",
    ):
        assert required_guard in checker


def test_ci_checks_dependency_build_policy_after_each_workspace_install() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert workflow.count("pnpm install --frozen-lockfile") == 2
    assert workflow.count("pnpm run check:dependency-build-policy") == 2
    assert workflow.count("version: 10.34.5") == 2
    assert workflow.count("node-version: 24.19.0") == 2


def test_optional_api_has_no_placeholder_build_task() -> None:
    api_package = _json("apps/api/package.json")

    assert "build" not in api_package["scripts"]


def test_machine_architecture_json_is_not_reformatted_as_yaml() -> None:
    ignored = (ROOT / ".prettierignore").read_text(encoding="utf-8").splitlines()

    assert {"docs/ARCHITECTURE.yaml", "pnpm-lock.yaml"} <= set(ignored)


def test_workflow_actions_use_reviewed_node24_releases() -> None:
    workflow_paths = sorted((ROOT / ".github/workflows").glob("*.yml"))
    seen: dict[str, list[tuple[str, str, str]]] = {
        action: [] for action in EXPECTED_ACTIONS
    }

    pattern = re.compile(
        r"uses:\s*([\w.-]+/[\w.-]+)@([0-9a-f]{40})\s+#\s+(v[^\s]+)"
    )
    for path in workflow_paths:
        for action, sha, tag in pattern.findall(path.read_text(encoding="utf-8")):
            if action in seen:
                seen[action].append((sha, tag, path.name))

    for action, (expected_sha, expected_tag) in EXPECTED_ACTIONS.items():
        assert seen[action], f"{action} is not used"
        assert all(
            sha == expected_sha and tag == expected_tag
            for sha, tag, _path in seen[action]
        ), (action, seen[action])


def test_node26_tailwind_blocker_and_removal_trigger_are_documented() -> None:
    architecture = _json("docs/ARCHITECTURE.yaml")
    runtime = architecture["architecture"]["node_runtime_policy"]
    prose = (ROOT / "docs/ARCHITECTURE.md").read_text(encoding="utf-8")

    assert runtime == {
        "managed_runtime": "node@24.19.0",
        "reason": "Tailwind CSS 4 emits Node DEP0205 under Node 26",
        "upstream_issue": "https://github.com/tailwindlabs/tailwindcss/issues/19893",
        "removal_trigger": (
            "upgrade after a stable Tailwind release replaces module.register and the "
            "Node 26 strict build is warning-free"
        ),
    }
    assert runtime["upstream_issue"] in prose

"""Executable monorepo tooling and dependency-lifecycle contracts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

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
        "version": "1.12.2",
        "decision": "deny",
        "lifecycle_command": "node postinstall.js",
        "script_path": "postinstall.js",
        "manifest_sha256": "3ef3f74675fe31a88dc490e4136178a5fd8f96142df0c565d66be9a894543adf",
        "script_sha256": "446a0aeed55eeb28eadd9ac31f0b71654265aba8ca5a99dbc22dab0b26a02469",
        "support_package": {
            "name": "napi-postinstall",
            "version": "0.3.4",
            "manifest_sha256": "1bc0ea8874adb494c2b21ec47b9a434ae067ad65d6908c090299b1aa9e266687",
            "lib_files": [
                "lib/cli.js",
                "lib/constants.js",
                "lib/fallback.js",
                "lib/helpers.js",
                "lib/index.js",
                "lib/target.js",
                "lib/types.js",
            ],
            "lib_tree_sha256": "0bc066b4ad4eef5e5f4c5c8fee2fb6ab758acfcfd82d3021665cb560c295023d",
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
        "script_path",
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


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ("postinstall.js", "unrs-resolver postinstall.js SHA-256"),
        ("lib/helpers.js", "napi-postinstall executable tree SHA-256"),
        ("lib/cli.js", "napi-postinstall lib/cli.js SHA-256"),
        ("lock", "lock versions"),
        ("pending", "unreviewed pending builds"),
    ],
)
def test_dependency_checker_refuses_changed_install_paths(
    tmp_path: Path, mutation: str, expected_error: str
) -> None:
    """Synthetic layout checks guards; it never imports an installer or binding."""
    node = shutil.which("node")
    assert node is not None, "Node is required for the executable lifecycle contract"

    def put(relative: str, text: str) -> Path:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    host = "node_modules/.pnpm/unrs-resolver@1.12.2/node_modules/unrs-resolver"
    support = "node_modules/.pnpm/napi-postinstall@0.3.4/node_modules/napi-postinstall"
    host_manifest = put(
        f"{host}/package.json",
        json.dumps({"scripts": {"postinstall": "node postinstall.js"}}),
    )
    host_script = put(f"{host}/postinstall.js", "throw Error('must not execute');\n")
    support_manifest = put(f"{support}/package.json", "{}\n")
    lib_files = ["lib/cli.js", "lib/helpers.js"]
    tree_hash = hashlib.sha256()
    for relative in lib_files:
        path = put(f"{support}/{relative}", "throw Error('must not execute');\n")
        tree_hash.update(relative.encode() + b"\0" + path.read_bytes() + b"\0")
    denied = {
        "unrs-resolver": {
            "version": "1.12.2",
            "decision": "deny",
            "lifecycle_command": "node postinstall.js",
            "manifest_sha256": digest(host_manifest),
            "script_path": "postinstall.js",
            "script_sha256": digest(host_script),
            "support_package": {
                "name": "napi-postinstall",
                "version": "0.3.4",
                "manifest_sha256": digest(support_manifest),
                "lib_files": lib_files,
                "lib_tree_sha256": tree_hash.hexdigest(),
                "cli_sha256": digest(tmp_path / support / "lib/cli.js"),
            },
        }
    }
    package = _json("package.json")
    package["pnpm"] = {"ignoredBuiltDependencies": list(denied)}
    put("package.json", json.dumps(package))
    architecture = _json("docs/ARCHITECTURE.yaml")
    architecture["architecture"]["dependency_lifecycle_policy"]["denied_packages"] = (
        denied
    )
    put("docs/ARCHITECTURE.yaml", json.dumps(architecture))
    put("pnpm-workspace.yaml", "packages: []\n")
    lock = put("pnpm-lock.yaml", "  unrs-resolver@1.12.2:\n  napi-postinstall@0.3.4:\n")
    state = put(
        "node_modules/.modules.yaml",
        json.dumps({"packageManager": package["packageManager"], "pendingBuilds": []}),
    )
    checker = put(
        "scripts/check-dependency-build-policy.mjs",
        (ROOT / "scripts/check-dependency-build-policy.mjs").read_text(),
    )
    stub = put(
        "pnpm-stub.cjs",
        f"#!{node}\n"
        "if (process.argv[2] !== 'ignored-builds') process.exit(2);\n"
        "console.log('Automatically ignored builds during installation: None');\n"
        "console.log('unrs-resolver');\n",
    )
    stub.chmod(0o700)
    env = {
        **os.environ,
        "npm_execpath": str(stub),
        "npm_config_user_agent": "pnpm/10.34.5 ",
    }

    def run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [node, str(checker)],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )

    baseline = run()
    assert baseline.returncode == 0, baseline.stderr
    assert "dependency build policy OK" in baseline.stdout
    if mutation == "lock":
        lock.write_text(lock.read_text().replace("1.12.2", "1.12.3"))
    elif mutation == "pending":
        state.write_text(
            json.dumps(
                {
                    "packageManager": package["packageManager"],
                    "pendingBuilds": ["unexpected"],
                }
            )
        )
    else:
        target = (
            host_script
            if mutation == "postinstall.js"
            else tmp_path / support / mutation
        )
        target.write_text(target.read_text() + "// changed byte\n")
    refused = run()
    assert refused.returncode != 0
    assert expected_error in refused.stderr
    assert "dependency build policy OK" not in refused.stdout


def test_ci_checks_dependency_build_policy_after_each_workspace_install() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert workflow.count("pnpm install --frozen-lockfile") == 2
    assert workflow.count("pnpm run check:dependency-build-policy") == 2
    assert workflow.count("version: 10.34.5") == 2
    assert workflow.count("node-version: 24.19.0") == 2


def test_dependabot_owns_the_root_workspace_and_groups_react_updates() -> None:
    architecture = _json("docs/ARCHITECTURE.yaml")
    policy = architecture["architecture"]["dependency_update_policy"]
    dependabot = yaml.safe_load(
        (ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")
    )
    workspace = yaml.safe_load(
        (ROOT / "pnpm-workspace.yaml").read_text(encoding="utf-8")
    )
    updates = dependabot["updates"]
    npm_updates = [update for update in updates if update["package-ecosystem"] == "npm"]
    pip_updates = [update for update in updates if update["package-ecosystem"] == "pip"]

    assert set(workspace["packages"]) == {"apps/*", "packages/*"}
    assert (ROOT / "pnpm-lock.yaml").is_file()
    assert not list((ROOT / "apps").glob("*/pnpm-lock.yaml"))
    assert not list((ROOT / "packages").glob("*/pnpm-lock.yaml"))
    assert len(npm_updates) == 1

    npm = npm_updates[0]
    assert npm["directory"] == policy["npm_directory"]
    assert policy["workspace_lockfile"] == "pnpm-lock.yaml"
    assert npm["schedule"] == {"interval": policy["schedule"]["interval"]}
    assert npm["cooldown"] == {"default-days": policy["schedule"]["cooldown_days"]}
    assert "ignore" not in npm

    react_groups = [
        group
        for group in npm["groups"].values()
        if set(group.get("patterns", [])) == set(policy["coupled_react_group"])
    ]
    assert len(react_groups) == 1
    assert policy["dependency_kinds"] == ["production", "development"]
    assert "dependency-type" not in react_groups[0]
    assert "applies-to" not in react_groups[0]

    assert pip_updates == [
        {
            "package-ecosystem": "pip",
            "directory": "/apps/api",
            "schedule": {"interval": "weekly"},
            "cooldown": {"default-days": 7},
        }
    ]


def test_react_runtime_and_declarations_resolve_as_one_reviewed_cohort() -> None:
    expected = {
        "runtime": {
            "react": "19.2.8",
            "react-dom": "19.2.8",
        },
        "declarations": {
            "@types/react": "19.2.18",
            "@types/react-dom": "19.2.7",
        },
        "importers": ["apps/web", "packages/ui"],
    }
    architecture = _json("docs/ARCHITECTURE.yaml")
    policy = architecture["architecture"]["dependency_update_policy"]
    lock = yaml.safe_load((ROOT / "pnpm-lock.yaml").read_text(encoding="utf-8"))
    manifests = {
        "apps/web": _json("apps/web/package.json"),
        "packages/ui": _json("packages/ui/package.json"),
    }

    for importer, manifest in manifests.items():
        runtime_dependencies = (
            manifest["dependencies"]
            if importer == "apps/web"
            else manifest["devDependencies"]
        )
        assert {
            name: runtime_dependencies[name] for name in expected["runtime"]
        } == expected["runtime"]
        assert {
            name: manifest["devDependencies"][name] for name in expected["declarations"]
        } == {name: f"^{version}" for name, version in expected["declarations"].items()}

        locked = lock["importers"][importer]
        assert {
            name: locked[
                "dependencies" if importer == "apps/web" else "devDependencies"
            ][name]["version"].split("(", 1)[0]
            for name in expected["runtime"]
        } == expected["runtime"]
        assert {
            name: locked["devDependencies"][name]["version"].split("(", 1)[0]
            for name in expected["declarations"]
        } == expected["declarations"]

    assert policy["react_cohort"] == expected


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

    pattern = re.compile(r"uses:\s*([\w.-]+/[\w.-]+)@([0-9a-f]{40})\s+#\s+(v[^\s]+)")
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

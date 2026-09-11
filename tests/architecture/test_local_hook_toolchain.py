"""Prevent hook mirrors from diverging from the reviewed runtime toolchain."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_hooks_use_existing_workspace_and_api_configuration():
    source = (ROOT / ".pre-commit-config.yaml").read_text()
    assert "repo: local" in source
    assert "https://" not in source
    assert "additional_dependencies" not in source
    assert source.count("language: system") == 5
    for entry in (
        "ruff check --fix",
        "ruff format",
        "corepack pnpm --filter api typecheck",
        "corepack pnpm --filter web lint",
        "corepack pnpm exec prettier --write",
    ):
        assert f"entry: {entry}" in source
    scripts = json.loads((ROOT / "apps/api/package.json").read_text())["scripts"]
    assert scripts["typecheck"] == "mypy ."
    assert scripts["format"] == "ruff format ."
    contract = json.loads((ROOT / "docs/ARCHITECTURE.yaml").read_text())
    assert contract["architecture"]["local_hook_toolchain"]["runner"] == "pre-commit==4.6.2"
    assert "pre-commit run --all-files" in (ROOT / "AGENTS.md").read_text()

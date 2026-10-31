"""One upstream package owns atomic shared TypeScript ESLint updates."""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = "@typescript-eslint/eslint-plugin"
PARSER = "@typescript-eslint/parser"


def test_shared_typescript_eslint_has_one_atomic_update_declaration() -> None:
    manifest = json.loads((ROOT / "packages/config/package.json").read_text())
    declarations = manifest["devDependencies"]
    assert "typescript-eslint" in declarations, (
        "Use the upstream atomic dependency unit"
    )
    assert PLUGIN not in declarations and PARSER not in declarations


def test_shared_typescript_eslint_lock_binds_the_same_parser_peer() -> None:
    lock = yaml.safe_load((ROOT / "pnpm-lock.yaml").read_text())
    dependencies = lock["importers"]["packages/config"]["devDependencies"]
    assert "typescript-eslint" in dependencies
    umbrella = dependencies["typescript-eslint"]["version"]
    snapshot = lock["snapshots"][f"typescript-eslint@{umbrella}"]["dependencies"]
    plugin = snapshot[PLUGIN]
    parser = snapshot[PARSER]
    # pnpm appends resolved peer identities in parenthesized version suffixes.
    version = parser.split("(", 1)[0]
    assert umbrella.split("(", 1)[0] == version
    assert plugin.split("(", 1)[0] == version
    assert f"({PARSER}@{parser})" in plugin

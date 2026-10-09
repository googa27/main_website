"""Shared TypeScript ESLint version identity follows upstream's release contract."""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = "@typescript-eslint/eslint-plugin"
PARSER = "@typescript-eslint/parser"


def test_shared_typescript_eslint_declarations_are_one_cohort() -> None:
    manifest = json.loads((ROOT / "packages/config/package.json").read_text())
    declarations = manifest["devDependencies"]
    assert declarations[PLUGIN] == declarations[PARSER], (
        "Update the shared plugin and parser together; a grouped PR may be partial"
    )


def test_shared_typescript_eslint_lock_binds_the_same_parser_peer() -> None:
    lock = yaml.safe_load((ROOT / "pnpm-lock.yaml").read_text())
    dependencies = lock["importers"]["packages/config"]["devDependencies"]
    plugin = dependencies[PLUGIN]["version"]
    parser = dependencies[PARSER]["version"]
    # pnpm appends resolved peer identities in parenthesized version suffixes.
    version = parser.split("(", 1)[0]
    assert plugin.split("(", 1)[0] == version
    assert f"({PARSER}@{parser})" in plugin

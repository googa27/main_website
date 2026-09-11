"""Keep identifier discovery tied to the executable API contract."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_project_identity_policy_has_documented_routes_and_executable_boundaries():
    contract = json.loads((ROOT / "docs/ARCHITECTURE.yaml").read_text())
    policy = contract["architecture"]["project_read_identity"]
    documentation = (ROOT / policy["documentation"]).read_text()
    for name in ("local_route", "provider_route", "legacy_route"):
        assert policy[name] in documentation
    assert policy["documentation"] in (ROOT / "AGENTS.md").read_text()
    assert "never guess" in policy["legacy_policy"]
    for path in policy["fitness_tests"]:
        assert (ROOT / path).is_file()

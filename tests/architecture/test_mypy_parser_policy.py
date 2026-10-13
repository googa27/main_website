"""Owned API source cannot silently lose control-flow type comments."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps/api"
SPEC = importlib.util.spec_from_file_location(
    "api_ast_contract", ROOT / "tests/architecture/api_ast_contract.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "source,expected",
    [
        ("for item in values:  # type: int\n    pass\n", [1]),
        ("with manager as item:  # type: int\n    pass\n", [1]),
        ("async def use():\n    async for item in values:  # type: int\n        pass\n", [2]),
        ("async def use():\n    async with manager as item:  # type: int\n        pass\n", [2]),
        (
            "for item in values:  # type: int\n"
            "    with manager as value:  # type: str\n"
            "        pass\n",
            [1, 2],
        ),
        ("item: int\nfor item in values:\n    pass\n", []),
        ("item: int\nwith manager as item:\n    pass\n", []),
        ("item = 1  # type: int\n", []),
        ("def use(item):\n    # type: (int) -> str\n    return str(item)\n", []),
        ("for item in values:  # type: ignore[assignment]\n    pass\n", []),
        ("with manager as item:  # type: ignore[assignment]\n    pass\n", []),
    ],
)
def test_ignored_type_comment_policy(source, expected):
    check = getattr(MODULE, "ignored_control_flow_type_comments", None)
    assert callable(check), "The control-flow type-comment source policy is missing"
    assert check(source) == expected


def test_owned_api_sources_avoid_silently_ignored_control_flow_type_comments():
    check = getattr(MODULE, "ignored_control_flow_type_comments", None)
    assert callable(check), "The control-flow type-comment source policy is missing"
    sources = list(API_ROOT.glob("*.py"))
    for root in (API_ROOT / "app", API_ROOT / "tests", API_ROOT / "alembic"):
        sources.extend(root.rglob("*.py"))
    violations = [
        f"{path.relative_to(API_ROOT)}:{line}:ignored control-flow type comment"
        for path in sorted(sources)
        for line in check(path.read_text(encoding="utf-8"))
    ]
    assert violations == []

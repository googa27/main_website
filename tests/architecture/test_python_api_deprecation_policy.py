"""The API deprecation gate distinguishes stdlib patching from model calls."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "api_ast_contract", ROOT / "apps/api/tests/api_ast_contract.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize("name", ["patch", "environment_patch"])
def test_unshadowed_stdlib_patch_dictionary_context_is_allowed(name):
    source = f"from unittest.mock import patch as {name}\n{name}.dict(environ, {{}})"
    assert MODULE.deprecated_dict_calls(source) == []


@pytest.mark.parametrize(
    "source",
    [
        "model.dict()",
        "from other import patch\npatch.dict()",
        "from unittest.mock import patch\npatch = model\npatch.dict()",
        "from unittest.mock import patch\ndef use(patch):\n return patch.dict()",
        "from unittest.mock import patch\nfrom other import *\npatch.dict()",
        "from unittest.mock import patch\ndel patch\npatch.dict()",
        "from unittest.mock import patch\ndef patch(): pass\npatch.dict()",
        "from unittest.mock import patch\nmatch model:\n case patch: patch.dict()",
    ],
)
def test_model_unknown_and_shadowed_dictionary_calls_remain_refused(source):
    assert len(MODULE.deprecated_dict_calls(source)) == 1


@pytest.mark.parametrize(
    "source,expected",
    [
        (
            "from unittest.mock import patch\npatch.dict({}, {})\ndef helper(patch): pass",
            [],
        ),
        (
            "from unittest.mock import patch\npatch.dict({}, {})\ndef helper(patch):\n patch.dict({}, {})",
            [4],
        ),
        (
            "def outer():\n from unittest.mock import patch\n patch.dict({}, {})\n def helper(patch): pass",
            [],
        ),
        (
            "def one():\n from unittest.mock import patch\n patch.dict({}, {})\ndef two():\n from other import patch\n patch.dict({}, {})",
            [6],
        ),
        (
            "from unittest.mock import patch\nclass Example:\n patch=object()\n def helper(self):\n  patch.dict({}, {})",
            [],
        ),
        (
            "from unittest.mock import patch\npatch.dict({}, {})\nuse=lambda patch: patch.dict({}, {})",
            [3],
        ),
        (
            "from unittest.mock import patch\npatch.dict({}, {})\nitems=[patch.dict({}, {}) for patch in providers]",
            [3],
        ),
        (
            "from unittest.mock import patch\nitems=[patch for patch in [patch.dict({}, {})]]",
            [],
        ),
        (
            "from unittest.mock import patch\ndef helper(patch=patch.dict({}, {})): pass",
            [],
        ),
        (
            "from unittest.mock import patch\nitems=(patch for patch in [patch.dict({}, {})])",
            [],
        ),
        (
            "from unittest.mock import patch\ndef helper():\n global patch\n patch=model\npatch.dict({}, {})",
            [5],
        ),
        (
            "def outer():\n from unittest.mock import patch\n def helper():\n  nonlocal patch\n  patch=model\n patch.dict({}, {})",
            [6],
        ),
        (
            "from unittest.mock import patch\nitems=[(patch:=model) for item in providers]\npatch.dict({}, {})",
            [3],
        ),
        (
            "from unittest.mock import patch\ndef helper():\n global patch\n patch.dict({}, {})",
            [],
        ),
        (
            "from unittest.mock import patch\npatch.dict({}, {})\ndef helper():\n from unittest.mock import patch\n patch.dict({}, {})",
            [],
        ),
        (
            "from unittest.mock import patch\nclass Example:\n patch=model\n patch.dict({}, {})\n def helper(self):\n  patch.dict({}, {})",
            [4],
        ),
        (
            "from unittest.mock import patch\npatch.dict({}, {})\nitems={patch.dict({}, {}) for patch in providers}",
            [3],
        ),
        (
            "from unittest.mock import patch\npatch.dict({}, {})\nitems={item:patch.dict({}, {}) for patch in providers for item in keys}",
            [3],
        ),
        (
            "from unittest.mock import patch\nitems=(lambda patch: patch.dict({}, {}), lambda: patch.dict({}, {}))",
            [2],
        ),
        (
            "from unittest.mock import patch\npatch.dict({}, {})\nitems=[lambda: patch.dict({}, {}) for patch in providers]",
            [3],
        ),
        (
            "def outer():\n from unittest.mock import patch\n def helper():\n  nonlocal patch\n  patch.dict({}, {})",
            [],
        ),
        (
            "from unittest.mock import patch\nasync def helper(patch):\n patch.dict({}, {})\npatch.dict({}, {})",
            [3],
        ),
    ],
)
def test_patch_binding_is_resolved_in_its_actual_lexical_scope(source, expected):
    assert MODULE.deprecated_dict_calls(source) == expected

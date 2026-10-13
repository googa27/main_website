"""The API deprecation gate distinguishes stdlib patching from model calls."""

import ast
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
    assert MODULE.deprecated_dict_calls(ast.parse(source)) == []


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
    assert len(MODULE.deprecated_dict_calls(ast.parse(source))) == 1

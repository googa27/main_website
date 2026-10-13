"""The API deprecation gate distinguishes stdlib patching from model calls."""

import ast
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "api_ast_contract", ROOT / "tests/architecture/api_ast_contract.py"
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


@pytest.mark.parametrize("form", ["list", "set", "dict", "generator"])
@pytest.mark.parametrize("module_import", [False, True])
def test_class_comprehension_body_skips_class_namespace(form, module_import):
    expressions = {
        "list": "[patch.dict({}, {}) for item in providers]",
        "set": "{patch.dict({}, {}) for item in providers}",
        "dict": "{item: patch.dict({}, {}) for item in providers}",
        "generator": "(patch.dict({}, {}) for item in providers)",
    }
    outer = "from unittest.mock import patch" if module_import else "patch = model"
    inner = "patch = model" if module_import else "from unittest.mock import patch"
    source = f"{outer}\nclass C:\n {inner}\n values = {expressions[form]}"
    assert MODULE.deprecated_dict_calls(source) == ([] if module_import else [4])


@pytest.mark.parametrize("class_import", [False, True])
def test_class_comprehension_first_iterator_uses_class_namespace(class_import):
    outer = "patch = model" if class_import else "from unittest.mock import patch"
    inner = "from unittest.mock import patch" if class_import else "patch = model"
    source = f"{outer}\nclass C:\n {inner}\n values = [item for item in [patch.dict({{}}, {{}})]]"
    assert MODULE.deprecated_dict_calls(source) == ([] if class_import else [4])


def test_real_class_comprehension_runtime_resolves_module_receiver():
    path = ROOT / "tests/architecture/fixtures/class_comprehension_model.py"
    spec = importlib.util.spec_from_file_location("class_comprehension_model", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.C.values == ["synthetic-module-model"]
    assert MODULE.deprecated_dict_calls(path.read_text()) == [15]


API_ROOT = ROOT / "apps/api"


def test_api_python_avoids_deprecated_datetime_and_pydantic_apis() -> None:
    violations: list[str] = []
    for root in (API_ROOT / "app", API_ROOT / "tests"):
        for path in sorted(root.rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            for lineno in MODULE.deprecated_dict_calls(source):
                violations.append(
                    f"{path.relative_to(API_ROOT)}:{lineno}:deprecated .dict()"
                )
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr in {
                    "utcnow",
                    "__fields__",
                }:
                    violations.append(
                        f"{path.relative_to(API_ROOT)}:{node.lineno}:{node.attr}"
                    )
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "datetime"
                    and node.func.attr == "now"
                    and path != API_ROOT / "app/core/time.py"
                ):
                    violations.append(
                        f"{path.relative_to(API_ROOT)}:{node.lineno}:direct datetime.now()"
                    )

    assert violations == []


@pytest.mark.parametrize(
    "source",
    [
        "from unittest.mock import patch\nother=object()\ndel other\npatch.dict({}, {})",
        "from unittest.mock import patch\nother=(value:=model)\npatch.dict({}, {})",
        "from unittest.mock import patch\nmatch model:\n case other: pass\npatch.dict({}, {})",
    ],
)
def test_unrelated_unsupported_binding_names_preserve_the_exemption(source):
    assert MODULE.deprecated_dict_calls(source) == []


def test_unsupported_mutations_conservatively_disable_the_alias_across_the_file():
    source = (
        "from unittest.mock import patch\ndef helper():\n del patch\npatch.dict({}, {})"
    )
    assert MODULE.deprecated_dict_calls(source) == [4]

"""Refuse regressions of the distinct issue263 Python dependency profiles."""

import json
from pathlib import Path

import pytest
import tomllib
from test_dependency_security_floors import (
    _SECURITY_MINIMUMS,
    ROOT,
    _declarations_by_name,
    _replace_declaration,
    _requirements_lines,
    manifests,
)
from test_dependency_security_floors import (
    test_python_security_floors_are_synchronized_across_manifests as check_api_profiles,
)

# Reuse the actual manifest-copy fixture rather than a second policy implementation.
__all__ = ["manifests"]


def _security_tool_declarations(text: str):
    pins = _declarations_by_name(
        _requirements_lines(text, include_file="requirements-bootstrap.txt")
    )
    assert _SECURITY_MINIMUMS["security"].keys() <= pins.keys(), (
        "Missing protected security-tool pin"
    )
    return pins


def test_selected_security_tool_profile_meets_security_floors():
    _security_tool_declarations((ROOT / "requirements-security.txt").read_text())


def test_recorded_python_profile_versions_match_actual_declarations():
    contract = json.loads((ROOT / "docs/ARCHITECTURE.yaml").read_text())
    selected = contract["tests"]["python_optional_profile_security"][
        "selected_versions"
    ]
    assert selected.keys() == {
        "black",
        "pypdf",
        "reportlab",
        "pillow",
        "certifi",
        "filelock",
    }
    extras = tomllib.loads((ROOT / "apps/api/pyproject.toml").read_text())["project"][
        "optional-dependencies"
    ]
    api = _declarations_by_name(extras["dev"] + extras["pdf"])
    tools = _security_tool_declarations(
        (ROOT / "requirements-security.txt").read_text()
    )
    for name, version in selected.items():
        owner = tools if name in _SECURITY_MINIMUMS["security"] else api
        assert str(owner[name].specifier) == f"=={version}", (
            f"Architecture selection differs from actual {name} pin"
        )


@pytest.mark.parametrize(
    "owner,patched,affected",
    [
        ("dev", "black==26.10.1", "black==26.5.1"),
        ("dev", "pypdf==6.21.4", "pypdf==6.21.3"),
        ("pdf", "pillow==13.0.0", "pillow==12.3.0"),
    ],
)
def test_synchronized_insecure_profile_downgrades_fail(
    manifests: Path, owner: str, patched: str, affected: str
):
    check_api_profiles()
    _replace_declaration(manifests, patched, affected, owner)
    with pytest.raises(AssertionError, match="Below security minimum"):
        check_api_profiles()


@pytest.mark.parametrize(
    "pin", ["black==26.10.1", "pypdf==6.21.4", "pillow==13.0.0", "reportlab==5.0.1"]
)
def test_optional_packages_cannot_be_duplicated_into_runtime(manifests: Path, pin: str):
    check_api_profiles()
    requirements = manifests / "requirements.txt"
    requirements.write_text(requirements.read_text() + pin + "\n")
    project = manifests / "pyproject.toml"
    project.write_text(
        project.read_text().replace(
            "dependencies = [", f"dependencies = [{json.dumps(pin)},", 1
        )
    )
    with pytest.raises(AssertionError, match="must not be declared in runtime"):
        check_api_profiles()


@pytest.mark.parametrize(
    "patched,affected",
    [
        ("certifi==2026.10.18", "certifi==2026.7.22"),
        ("filelock==4.2.1", "filelock==4.0.12"),
    ],
)
def test_security_tool_advisory_boundary(patched: str, affected: str):
    # Literal primary-advisory boundaries, independent of the minimum map.
    _declarations_by_name([patched])
    with pytest.raises(AssertionError, match="Below security minimum"):
        _declarations_by_name([affected])


@pytest.mark.parametrize("name", ["certifi", "filelock"])
def test_security_tool_profile_cannot_omit_a_protected_pin(name: str):
    text = (ROOT / "requirements-security.txt").read_text()
    missing = "\n".join(
        line for line in text.splitlines() if not line.startswith(name + "==")
    )
    with pytest.raises(AssertionError, match="Missing protected security-tool pin"):
        _security_tool_declarations(missing)


@pytest.mark.parametrize(
    "replacement",
    [
        "",
        "-r requirements-bootstrap.txt\n-r requirements-bootstrap.txt",
        "-c other.txt",
    ],
)
def test_security_tool_profile_preserves_its_bootstrap_include(replacement: str):
    text = (ROOT / "requirements-security.txt").read_text()
    with pytest.raises(AssertionError):
        _security_tool_declarations(
            text.replace("-r requirements-bootstrap.txt", replacement)
        )

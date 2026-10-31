"""Require the CA security boundary in every API dependency representation."""

import json
from pathlib import Path

import pytest
from test_dependency_security_floors import (
    _SECURITY_MINIMUMS,
    _declarations_by_name,
    _replace_declaration,
    manifests,
)
from test_dependency_security_floors import (
    test_python_security_floors_are_synchronized_across_manifests as check_profiles,
)

__all__ = ["manifests"]


@pytest.mark.parametrize("version", ["2026.10.18", "2026.10.23"])
def test_runtime_certifi_accepts_patched_minimum_and_selected_release(
    manifests: Path, version: str
):
    _replace_declaration(manifests, "certifi==2026.10.18", f"certifi=={version}")
    check_profiles()


def test_runtime_certifi_refuses_synchronized_vulnerable_selection(manifests: Path):
    _replace_declaration(manifests, "certifi==2026.10.18", "certifi==2026.7.22")
    with pytest.raises(AssertionError, match="Below security minimum: certifi"):
        check_profiles()


def test_runtime_certifi_cannot_be_removed_from_both_manifests(manifests: Path):
    for name in ("requirements.txt", "pyproject.toml"):
        path = manifests / name
        lines = path.read_text().splitlines(keepends=True)
        path.write_text("".join(line for line in lines if "certifi==" not in line))
    with pytest.raises(AssertionError, match="Missing protected runtime"):
        check_profiles()


@pytest.mark.parametrize("owner", ["dev", "pdf"])
def test_certifi_is_inherited_by_optional_profiles_without_override(
    manifests: Path, owner: str
):
    pin = "certifi==2026.10.18"
    path = manifests / f"requirements-{owner}.txt"
    path.write_text(path.read_text() + pin + "\n")
    project = manifests / "pyproject.toml"
    project.write_text(
        project.read_text().replace(f"{owner} = [", f"{owner} = [{json.dumps(pin)},", 1)
    )
    with pytest.raises(AssertionError, match="must not be declared in runtime"):
        check_profiles()


def test_runtime_and_auditor_cannot_disagree_about_shared_security_minimum(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setitem(_SECURITY_MINIMUMS["security"], "certifi", "2026.10.23")
    with pytest.raises(AssertionError, match="Conflicting security minimum: certifi"):
        _declarations_by_name(["certifi==2026.10.23"])

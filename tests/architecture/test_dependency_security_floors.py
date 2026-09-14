from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Iterable
from pathlib import Path

import pytest
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "apps" / "api"


# Minimum acceptable versions, not the currently selected dependency versions.
_SECURITY_MINIMUMS = {
    "runtime": {"idna": "3.18", "mako": "1.3.12", "httpx": "0.28.1"},
    "dev": {"pygments": "2.20.0", "httpx2": "2.12.0"},
}


def _requirements_lines(text: str, *, include_runtime: bool = False) -> list[str]:
    declarations = []
    includes = 0
    for line in text.splitlines():
        line = re.split(r"\s+#", line, maxsplit=1)[0].strip()
        if not line or line.startswith("#"):
            continue
        if line == "-r requirements.txt" and include_runtime:
            includes += 1
            continue
        assert not line.startswith("-"), f"Unsupported requirement directive: {line}"
        declarations.append(line)
    assert includes == int(include_runtime), (
        "Development must include runtime exactly once"
    )
    return declarations


def _declarations_by_name(declarations: Iterable[str]) -> dict[str, Requirement]:
    minimums = {
        name: minimum
        for group in _SECURITY_MINIMUMS.values()
        for name, minimum in group.items()
    }
    parsed: dict[str, Requirement] = {}
    for declaration in declarations:
        assert isinstance(declaration, str), "Requirement declarations must be strings"
        try:
            requirement = Requirement(declaration)
        except InvalidRequirement as error:
            raise AssertionError(f"Invalid requirement: {declaration}") from error
        name = canonicalize_name(requirement.name)
        assert name not in parsed, f"Duplicate requirement name: {name}"
        if name in minimums:
            assert requirement.url is None, f"Protected pin cannot use a URL: {name}"
            assert requirement.marker is None, (
                f"Protected pin cannot be conditional: {name}"
            )
            assert not requirement.extras and "[" not in declaration, (
                f"Protected pin cannot request extras: {name}"
            )
            specifiers = list(requirement.specifier)
            assert len(specifiers) == 1, (
                f"Protected pin must have one exact version: {name}"
            )
            specifier = specifiers[0]
            assert specifier.operator == "==" and "*" not in specifier.version, (
                f"Protected pin must have one exact version: {name}"
            )
            version = Version(specifier.version)
            assert (
                not version.is_prerelease
                and not version.is_devrelease
                and version.local is None
            ), f"Protected pin must be a stable public version: {name}"
            assert version >= Version(minimums[name]), f"Below security minimum: {name}"
        parsed[name] = requirement
    return parsed


def test_python_security_floors_are_synchronized_across_manifests() -> None:
    runtime = _requirements_lines(
        (API / "requirements.txt").read_text(encoding="utf-8")
    )
    development = _requirements_lines(
        (API / "requirements-dev.txt").read_text(encoding="utf-8"), include_runtime=True
    )
    project = tomllib.loads((API / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    for owner, requirements, declarations in (
        ("runtime", runtime, project["dependencies"]),
        ("dev", development, project["optional-dependencies"]["dev"]),
    ):
        manifest = _declarations_by_name(requirements)
        metadata = _declarations_by_name(declarations)
        assert _SECURITY_MINIMUMS[owner].keys() <= manifest.keys(), (
            f"Missing protected {owner} pin"
        )
        assert _SECURITY_MINIMUMS[owner].keys() <= metadata.keys(), (
            f"Missing protected {owner} metadata"
        )
        assert manifest == metadata, f"Full {owner} manifest parity differs"


def test_ci_audits_runtime_and_development_python_dependencies() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "pip-audit -r apps/api/requirements.txt" in workflow
    assert "pip-audit -r apps/api/requirements-dev.txt" in workflow


def test_postcss_security_floor_is_owned_by_override_and_lock() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    workspace = (ROOT / "pnpm-workspace.yaml").read_text(encoding="utf-8")
    lock = (ROOT / "pnpm-lock.yaml").read_text(encoding="utf-8")

    assert package["pnpm"]["overrides"]["postcss@<8.5.23"] == "8.5.23"
    assert "postcss@" not in workspace
    assert "postcss@8.5.23:" in lock
    assert "postcss@8.5.19:" not in lock


@pytest.fixture
def manifests(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Exercise the real repository checker against owned manifest copies."""
    for name in ("requirements.txt", "requirements-dev.txt", "pyproject.toml"):
        (tmp_path / name).write_bytes((API / name).read_bytes())
    monkeypatch.setitem(globals(), "API", tmp_path)
    return tmp_path


def _replace_declaration(
    manifests: Path, original: str, replacement: str, owner: str = "runtime"
) -> None:
    filename = "requirements.txt" if owner == "runtime" else "requirements-dev.txt"
    path = manifests / filename
    assert original in path.read_text()
    path.write_text(path.read_text().replace(original, replacement))
    project = manifests / "pyproject.toml"
    assert original in project.read_text()
    # JSON quoting is valid for these TOML basic strings, including marker quotes.
    project.write_text(
        project.read_text().replace(json.dumps(original), json.dumps(replacement))
    )


@pytest.mark.parametrize(
    "old,new", [("idna==3.18", "idna==3.19"), ("Mako==1.3.12", "Mako==1.4.1")]
)
def test_synchronized_newer_pins_are_not_rejected_as_old_exact_pins(
    manifests: Path, old: str, new: str
) -> None:
    _replace_declaration(manifests, old, new)
    test_python_security_floors_are_synchronized_across_manifests()


def test_exact_minimum_pins_are_accepted(manifests: Path) -> None:
    test_python_security_floors_are_synchronized_across_manifests()


@pytest.mark.parametrize(
    "owner,old,below",
    [
        ("runtime", "idna==3.18", "idna==3.17"),
        ("runtime", "Mako==1.3.12", "Mako==1.3.11"),
        ("runtime", "httpx==0.28.1", "httpx==0.28.0"),
        ("dev", "Pygments==2.20.0", "Pygments==2.19.2"),
        ("dev", "httpx2==2.12.0", "httpx2==2.11.0"),
    ],
)
def test_each_security_minimum_refuses_a_synchronized_downgrade(
    manifests: Path, owner: str, old: str, below: str
) -> None:
    _replace_declaration(manifests, old, below, owner)
    with pytest.raises(AssertionError):
        test_python_security_floors_are_synchronized_across_manifests()


@pytest.mark.parametrize(
    "declaration",
    [
        "idna @ https://example.invalid/idna.whl",
        "idna==3.18.*",
        "idna>=3.18",
        "idna==3.18,!=3.17",
        "idna==3.18,==3.18",
        "idna===3.18",
        'idna==3.18; python_version >= "3.9"',
        "idna[extra]==3.18",
        "idna[]==3.18",
        "idna==3.19rc1",
        "idna==3.19.dev1",
        "idna==3.19+local",
        "idna",
        "idna==",
    ],
)
def test_protected_pins_refuse_ambiguous_or_nonstable_forms(
    manifests: Path, declaration: str
) -> None:
    _replace_declaration(manifests, "idna==3.18", declaration)
    with pytest.raises(AssertionError):
        test_python_security_floors_are_synchronized_across_manifests()


@pytest.mark.parametrize(
    "filename", ["requirements.txt", "requirements-dev.txt", "pyproject.toml"]
)
def test_missing_protected_declaration_is_refused(
    manifests: Path, filename: str
) -> None:
    path = manifests / filename
    pin = "Pygments==2.20.0" if filename == "requirements-dev.txt" else "idna==3.18"
    text = path.read_text()
    line = next(line for line in text.splitlines(keepends=True) if pin in line)
    path.write_text(text.replace(line, ""))
    with pytest.raises(AssertionError):
        test_python_security_floors_are_synchronized_across_manifests()


@pytest.mark.parametrize(
    "filename,pin",
    [
        ("requirements.txt", "idna==3.18"),
        ("requirements.txt", "IDNA==3.18"),
        ("requirements-dev.txt", "pygments==2.20.0"),
        ("requirements-dev.txt", "pytest_asyncio==1.4.0"),
        ("pyproject.toml", "IDNA==3.18"),
    ],
)
def test_duplicate_normalized_names_cannot_hide_in_manifest_sets(
    manifests: Path, filename: str, pin: str
) -> None:
    path = manifests / filename
    if filename == "pyproject.toml":
        path.write_text(
            path.read_text().replace(
                '"idna==3.18",', '"idna==3.18",\n    ' + json.dumps(pin) + ","
            )
        )
    else:
        path.write_text(path.read_text() + pin + "\n")
    with pytest.raises(AssertionError):
        test_python_security_floors_are_synchronized_across_manifests()


@pytest.mark.parametrize(
    "owner,pin", [("runtime", "fastapi==0.139.0"), ("dev", "ruff==0.16.0")]
)
def test_full_manifest_parity_includes_unprotected_dependencies(
    manifests: Path, owner: str, pin: str
) -> None:
    path = manifests / (
        "requirements.txt" if owner == "runtime" else "requirements-dev.txt"
    )
    path.write_text(path.read_text().replace(pin, pin.replace("==", ">=")))
    with pytest.raises(AssertionError):
        test_python_security_floors_are_synchronized_across_manifests()


def test_comments_blank_lines_and_canonical_names_preserve_parity(
    manifests: Path,
) -> None:
    path = manifests / "requirements.txt"
    path.write_text(
        "# runtime dependencies\n\n"
        + path.read_text().replace("idna==3.18", "IDNA==3.18 # reviewed minimum")
    )
    test_python_security_floors_are_synchronized_across_manifests()


@pytest.mark.parametrize(
    "include",
    [
        "",
        "-r requirements.txt\n-r requirements.txt",
        "-r other.txt",
        "--requirement requirements.txt",
    ],
)
def test_development_include_must_be_the_single_owned_runtime_file(
    manifests: Path, include: str
) -> None:
    path = manifests / "requirements-dev.txt"
    path.write_text(path.read_text().replace("-r requirements.txt", include))
    with pytest.raises(AssertionError):
        test_python_security_floors_are_synchronized_across_manifests()

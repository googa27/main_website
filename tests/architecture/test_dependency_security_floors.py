from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

import pytest
import tomllib
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "apps" / "api"


# Minimum acceptable versions, not the currently selected dependency versions.
_SECURITY_MINIMUMS = {
    "runtime": {
        "idna": "3.18",
        "mako": "1.4.2",
        "httpx": "0.28.1",
        "anyio": "4.14.2",
    },
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


def _selected_alembic_stack() -> tuple[str, dict[str, str]]:
    architecture = json.loads((ROOT / "docs/ARCHITECTURE.yaml").read_text())
    decisions = [
        decision
        for decision in architecture["libraries"]["decisions"]
        if decision["capability"] == "Alembic revision template rendering"
    ]
    assert len(decisions) == 1
    assert len(decisions[0]["selected"]) == 1
    return decisions[0]["selected"][0], decisions[0]["selected_versions"]


def _assert_selected_alembic_stack_matches_manifests(
    selected: str, versions: dict[str, str]
) -> None:
    display_names = {"mako": "Mako", "alembic": "Alembic", "sqlalchemy": "SQLAlchemy"}
    assert versions.keys() == display_names.keys()
    assert not re.search(r"\d", selected), (
        "Architecture selection prose must remain version-free"
    )
    for display_name in display_names.values():
        assert re.search(rf"\b{display_name}\b", selected), (
            f"Architecture prose omits {display_name}"
        )
    for name, version in versions.items():
        assert re.fullmatch(r"\d+\.\d+\.\d+", version), (
            f"Invalid structured {name} version: {version}"
        )
    project = tomllib.loads((API / "pyproject.toml").read_text(encoding="utf-8"))
    for source, declarations in (
        (
            "requirements.txt",
            _requirements_lines((API / "requirements.txt").read_text()),
        ),
        ("pyproject.toml", project["project"]["dependencies"]),
    ):
        dependencies = _declarations_by_name(declarations)
        for name, version in versions.items():
            requirement = dependencies.get(name)
            assert requirement is not None, f"{source} omits selected {name}"
            assert requirement.url is None and requirement.marker is None
            assert (
                not requirement.extras and str(requirement.specifier) == f"=={version}"
            ), f"{source} {name} differs from architecture selection"


def test_selected_alembic_stack_matches_both_runtime_manifests() -> None:
    selected, versions = _selected_alembic_stack()
    _assert_selected_alembic_stack_matches_manifests(selected, versions)


@pytest.mark.parametrize("name", ["mako", "alembic", "sqlalchemy"])
def test_selected_alembic_stack_refuses_structured_version_drift(name: str) -> None:
    selected, versions = _selected_alembic_stack()
    altered = {**versions, name: "99.0.0"}
    with pytest.raises(AssertionError, match="differs from architecture selection"):
        _assert_selected_alembic_stack_matches_manifests(selected, altered)


def test_selected_alembic_stack_keeps_prose_version_free() -> None:
    selected, versions = _selected_alembic_stack()
    with pytest.raises(
        AssertionError, match="selection prose must remain version-free"
    ):
        _assert_selected_alembic_stack_matches_manifests(
            selected + f" (superseding Mako {versions['mako']}+local)", versions
        )


@pytest.mark.parametrize("name", ["Mako", "Alembic", "SQLAlchemy"])
def test_selected_alembic_stack_requires_each_library_name(name: str) -> None:
    selected, versions = _selected_alembic_stack()
    altered = selected.replace(name, "")
    assert altered != selected
    with pytest.raises(AssertionError, match=f"Architecture prose omits {name}"):
        _assert_selected_alembic_stack_matches_manifests(altered, versions)


def test_selected_alembic_stack_refuses_synchronized_manifest_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("requirements.txt", "pyproject.toml"):
        (tmp_path / name).write_bytes((API / name).read_bytes())
    monkeypatch.setitem(globals(), "API", tmp_path)
    selected, versions = _selected_alembic_stack()
    _replace_declaration(tmp_path, f"alembic=={versions['alembic']}", "alembic==99.0.0")
    with pytest.raises(AssertionError, match="differs from architecture selection"):
        _assert_selected_alembic_stack_matches_manifests(selected, versions)


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
    # Policy controls own exact minimum fixtures independently of selected pins.
    project = tomllib.loads((tmp_path / "pyproject.toml").read_text())["project"]
    for owner, declarations in (
        ("runtime", project["dependencies"]),
        ("dev", project["optional-dependencies"]["dev"]),
    ):
        for declaration in declarations:
            requirement = Requirement(declaration)
            minimum = _SECURITY_MINIMUMS[owner].get(canonicalize_name(requirement.name))
            if minimum is not None:
                _replace_declaration(
                    tmp_path, declaration, f"{requirement.name}=={minimum}", owner
                )
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
    "old,new",
    [
        ("idna==3.18", "idna==3.19"),
        ("Mako==1.4.2", "Mako==1.4.3"),
        ("anyio==4.14.2", "anyio==4.15.1"),
    ],
)
def test_synchronized_newer_pins_are_not_rejected_as_old_exact_pins(
    manifests: Path, old: str, new: str
) -> None:
    _replace_declaration(manifests, old, new)
    test_python_security_floors_are_synchronized_across_manifests()


def test_exact_minimum_pins_are_accepted(manifests: Path) -> None:
    test_python_security_floors_are_synchronized_across_manifests()


@pytest.mark.parametrize("version", ["1.4.2", "1.4.3"])
def test_mako_advisory_patched_releases_meet_security_policy(version: str) -> None:
    # Literal upstream advisory boundaries are independent of the policy map.
    _declarations_by_name([f"Mako=={version}"])


def test_mako_advisory_last_affected_release_is_refused() -> None:
    with pytest.raises(AssertionError, match="Below security minimum: mako"):
        _declarations_by_name(["Mako==1.4.1"])


@pytest.mark.parametrize(
    "owner,old,below",
    [
        ("runtime", "idna==3.18", "idna==3.17"),
        ("runtime", "Mako==1.4.2", "Mako==1.4.1"),
        ("runtime", "httpx==0.28.1", "httpx==0.28.0"),
        ("runtime", "anyio==4.14.2", "anyio==4.14.1"),
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


@pytest.mark.parametrize("owner,name", [("runtime", "fastapi"), ("dev", "ruff")])
@pytest.mark.parametrize("selected_version", [None, "999.0"])
def test_full_manifest_parity_includes_unprotected_dependencies(
    manifests: Path, owner: str, name: str, selected_version: str | None
) -> None:
    path = manifests / (
        "requirements.txt" if owner == "runtime" else "requirements-dev.txt"
    )
    declarations = _requirements_lines(path.read_text(), include_runtime=owner == "dev")
    matches = [
        declaration
        for declaration in declarations
        if canonicalize_name(Requirement(declaration).name) == canonicalize_name(name)
    ]
    assert len(matches) == 1, f"Expected exactly one declaration for {name}"
    pin = matches[0]
    if selected_version is not None:
        replacement = f"{Requirement(pin).name}=={selected_version}"
        _replace_declaration(manifests, pin, replacement, owner)
        pin = replacement
    test_python_security_floors_are_synchronized_across_manifests()
    before = Requirement(pin)
    replacement = pin.replace("==", ">=", 1)
    after = Requirement(replacement)
    assert before.name == after.name and before.specifier != after.specifier
    text = path.read_text()
    assert text.count(pin) == 1
    path.write_text(text.replace(pin, replacement, 1))
    with pytest.raises(AssertionError, match=f"Full {owner} manifest parity differs"):
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


@pytest.mark.parametrize("directive", ["-r requirements.txt", "-c constraints.txt"])
def test_runtime_requirements_refuse_recursive_or_constraint_directives(
    manifests: Path, directive: str
) -> None:
    path = manifests / "requirements.txt"
    path.write_text(path.read_text() + directive + "\n")
    with pytest.raises(AssertionError):
        test_python_security_floors_are_synchronized_across_manifests()

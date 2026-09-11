"""Offline export resources, optional dependency ownership and static preview."""

import ast
import hashlib
import json
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[2]


def test_official_resume_schema_is_pinned_and_packaged():
    contract = json.loads((ROOT / "docs/ARCHITECTURE.yaml").read_text())
    policy = contract["architecture"]["public_cv_exports"]
    schema = ROOT / "apps/api/app/static/schemas/jsonresume-1.3.1.json"
    assert hashlib.sha256(schema.read_bytes()).hexdigest() == policy["schema_sha256"]
    assert (
        json.loads(schema.read_text())["$schema"]
        == "http://json-schema.org/draft-07/schema#"
    )
    assert "MIT" in (schema.parent / "JSONRESUME-LICENSE.md").read_text()
    project = tomllib.loads((ROOT / "apps/api/pyproject.toml").read_text())
    data = project["tool"]["setuptools"]["package-data"]["app"]
    assert "static/schemas/*.json" in data and "static/schemas/*.md" in data
    assert (
        project["project"]["scripts"]["portfolio-cv"] == "app.services.cv.export:main"
    )
    for path in policy["fitness_tests"]:
        assert (ROOT / path).is_file()


def test_export_projection_has_no_acquisition_or_database_owner():
    forbidden = (
        "requests",
        "httpx",
        "sqlalchemy",
        "app.routers",
        "app.models",
        "app.services.linkedin",
    )
    for name in ("resume", "projects", "pdf"):
        tree = ast.parse((ROOT / f"apps/api/app/services/cv/{name}.py").read_text())
        for node in ast.walk(tree):
            modules = []
            if isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
                assert not node.level, "exports must use explicit absolute ownership"
            elif isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            assert not any(module.startswith(forbidden) for module in modules)


def test_pdf_stays_optional_and_profile_audit_includes_it():
    project = tomllib.loads((ROOT / "apps/api/pyproject.toml").read_text())["project"]
    assert not any(item.startswith("reportlab") for item in project["dependencies"])
    assert project["optional-dependencies"]["pdf"] == ["reportlab==5.0.1"]
    for name in ("pdf", "export", "service"):
        tree = ast.parse((ROOT / f"apps/api/app/services/cv/{name}.py").read_text())
        assert not any(
            isinstance(node, ast.ImportFrom)
            and (node.module or "").startswith("reportlab")
            for node in tree.body
        )
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    assert 'pip install -e ".[dev,pdf]"' in workflow
    assert "pip-audit -r apps/api/requirements-pdf.txt" in workflow


def test_preview_composes_current_static_cv_without_build_time_provider_calls():
    source = (ROOT / "apps/web/src/app/cv/preview/page.tsx").read_text()
    assert 'import AboutPage from "../../about/page"' in source
    assert "<AboutPage />" in source
    assert "fetch(" not in source and "localhost" not in source
    assert "includePrivate" not in source and "include_private" not in source
    assert not (ROOT / "apps/api/app/static/cv/resume.json").exists()
    assert not (ROOT / "apps/app/static/cv/resume.json").exists()


def test_api_license_expression_uses_a_supporting_build_backend():
    project = tomllib.loads((ROOT / "apps/api/pyproject.toml").read_text())
    assert project["project"]["license"] == "MIT"
    assert "setuptools>=77.0.3" in project["build-system"]["requires"]

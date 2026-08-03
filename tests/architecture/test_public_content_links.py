from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_CONTENT = ROOT / "apps" / "web" / "src" / "lib" / "content.ts"
CONTACT_PAGE = ROOT / "apps" / "web" / "src" / "app" / "contact" / "page.tsx"
RESUME_JSON = ROOT / "apps" / "web" / "src" / "data" / "react-folio-resume.json"
SHOWCASE_SERVICE = ROOT / "apps" / "api" / "app" / "services" / "showcase_service.py"
PROJECT_SCHEMAS = ROOT / "apps" / "api" / "app" / "schemas" / "project.py"
ARCHITECTURE_CONTRACT = ROOT / "docs" / "ARCHITECTURE.yaml"
README = ROOT / "README.md"

FRONTEND_REQUIRED_URLS = {
    "https://github.com/googa27/finite_difference_options",
    "https://github.com/googa27/django-optimization-app",
    "https://github.com/googa27/main_website",
}
API_REQUIRED_URLS = {
    "https://github.com/googa27/finite_difference_options",
    "https://github.com/googa27/finite_element_options",
    "https://github.com/googa27/django-optimization-app",
}
INVALID_PROJECT_URLS = {
    "https://github.com/googa27/finite-difference-options",
    "https://github.com/googa27/finite-element-options",
    '"https://github.com/googa27/django-optimization"',
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_frontend_project_links_use_existing_repository_slugs() -> None:
    frontend_content = read_text(FRONTEND_CONTENT)

    for expected_url in FRONTEND_REQUIRED_URLS:
        assert expected_url in frontend_content
    for invalid_url in INVALID_PROJECT_URLS:
        assert invalid_url not in frontend_content


def test_api_project_links_use_existing_repository_slugs() -> None:
    showcase_service = read_text(SHOWCASE_SERVICE)

    for expected_url in API_REQUIRED_URLS:
        assert expected_url in showcase_service
    for invalid_url in INVALID_PROJECT_URLS:
        assert invalid_url not in showcase_service


def test_showcase_service_does_not_publish_unverified_demo_or_doc_urls() -> None:
    showcase_service = read_text(SHOWCASE_SERVICE)

    assert "https://django-optimization.herokuapp.com" not in showcase_service
    assert "https://django-optimization.readthedocs.io" not in showcase_service
    assert "https://finite-diff-options.readthedocs.io" not in showcase_service
    assert 'name="Django Optimization App"' in showcase_service
    assert "has_live_demo=False" in showcase_service


def test_public_contact_email_policy_matches_deployment_surfaces() -> None:
    readme = read_text(README)
    contact_page = read_text(CONTACT_PAGE)
    content_adapter = read_text(FRONTEND_CONTENT)
    resume = json.loads(read_text(RESUME_JSON))
    public_email = resume["basics"].get("email")

    assert "yourusername" not in readme
    assert "your.email@example.com" not in readme
    assert "redacted resume email" not in readme
    assert "intentionally publishes the curated resume email" in readme
    assert re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", readme) is None
    assert public_email and "@" in public_email
    assert "phone" not in resume["basics"]
    assert "email: resume.basics.email" in content_adapter
    assert "mailto:${email}" in contact_page
    assert "{email}" in contact_page


def test_architecture_contract_documents_nullable_api_github_url() -> None:
    contract = json.loads(read_text(ARCHITECTURE_CONTRACT))
    schema_source = read_text(PROJECT_SCHEMAS)

    contracts = contract["architecture"]["public_response_contracts"]
    showcase_contract = next(
        item for item in contracts if item["surface"] == "/api/projects/showcase*"
    )

    assert "ProjectShowcase" in "\n".join(showcase_contract["schemas"])
    assert "ShowcaseProject" in "\n".join(showcase_contract["schemas"])
    assert "github_url" in showcase_contract["fields"]
    assert "JSON null" in showcase_contract["fields"]["github_url"]
    assert "Optional[HttpUrl] = None" in schema_source
    assert "github_url: Optional[HttpUrl]" in schema_source


def test_readme_documents_lockfile_based_pnpm_install() -> None:
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text(encoding="utf-8")

    assert "pnpm install --frozen-lockfile" in readme
    assert "pnpm install\n" not in readme

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_CONTENT = ROOT / "apps" / "web" / "src" / "lib" / "content.ts"
CONTACT_PAGE = ROOT / "apps" / "web" / "src" / "app" / "contact" / "page.tsx"
RESUME_JSON = ROOT / "apps" / "web" / "src" / "data" / "react-folio-resume.json"
SHOWCASE_SERVICE = ROOT / "apps" / "api" / "app" / "services" / "showcase_service.py"
PROJECT_SCHEMAS = ROOT / "apps" / "api" / "app" / "schemas" / "project.py"
ARCHITECTURE_CONTRACT = ROOT / "docs" / "ARCHITECTURE.yaml"
README = ROOT / "README.md"

FRONTEND_PROJECT_GITHUB_URLS = {
    "Finite Difference Options Pricing": "https://github.com/googa27/finite_difference_options",
    "Django Optimization App": "https://github.com/googa27/django-optimization-app",
    "Static-first Portfolio Site": "https://github.com/googa27/main_website",
}
API_PROJECT_GITHUB_URLS = {
    "Finite Difference Options Pricing": "https://github.com/googa27/finite_difference_options",
    "Django Optimization App": "https://github.com/googa27/django-optimization-app",
    "Finite Element Options Pricing": "https://github.com/googa27/finite_element_options",
    "ML/MLflow Integration": None,
}
INVALID_PROJECT_URLS = {
    "https://github.com/googa27/finite-difference-options",
    "https://github.com/googa27/finite-element-options",
    '"https://github.com/googa27/django-optimization"',
}
SHOWCASE_CONTRACT_SCHEMA_PATHS = [
    "apps/api/app/schemas/project.py::ProjectShowcase",
    "apps/api/app/schemas/project.py::ShowcaseProject",
]
SHOWCASE_GITHUB_URL_CONTRACT = (
    "HttpUrl or JSON null; planned or unverified projects must not publish fabricated "
    "repository URLs"
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def literal_keyword(call: ast.Call, name: str) -> object:
    for keyword in call.keywords:
        if keyword.arg == name:
            return ast.literal_eval(keyword.value)
    raise AssertionError(f"missing keyword: {name}")


def top_level_object_blocks(source: str, declaration: str) -> list[str]:
    """Extract top-level object literals from a TypeScript array declaration."""

    declaration_start = source.index(declaration)
    assignment_start = source.index("=", declaration_start)
    array_start = source.index("[", assignment_start)
    square_depth = 0
    curly_depth = 0
    object_start: int | None = None
    quote: str | None = None
    escaped = False
    blocks: list[str] = []

    for index, char in enumerate(source[array_start:], start=array_start):
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue

        if char in {'"', "'", "`"}:
            quote = char
        elif char == "[":
            square_depth += 1
        elif char == "]":
            square_depth -= 1
            if square_depth == 0:
                break
        elif char == "{":
            if square_depth == 1 and curly_depth == 0:
                object_start = index
            curly_depth += 1
        elif char == "}":
            curly_depth -= 1
            if square_depth == 1 and curly_depth == 0 and object_start is not None:
                blocks.append(source[object_start : index + 1])
                object_start = None

    return blocks


def frontend_project_github_urls_by_title() -> dict[str, str | None]:
    projects: dict[str, str | None] = {}
    for block in top_level_object_blocks(
        read_text(FRONTEND_CONTENT), "curatedProjects"
    ):
        title_match = re.search(r'\btitle:\s*"([^"]+)"', block)
        if title_match is None:
            continue
        github_match = re.search(r'\bgithub:\s*"([^"]+)"', block)
        projects[title_match.group(1)] = github_match.group(1) if github_match else None
    return projects


def showcase_project_named(project_name: str) -> ast.Call:
    tree = ast.parse(read_text(SHOWCASE_SERVICE))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "ProjectShowcase":
            continue
        if literal_keyword(node, "name") == project_name:
            return node
    raise AssertionError(f"missing ProjectShowcase record: {project_name}")


def api_project_github_urls_by_name() -> dict[str, str | None]:
    return {
        project_name: cast(
            str | None,
            literal_keyword(showcase_project_named(project_name), "github_url"),
        )
        for project_name in API_PROJECT_GITHUB_URLS
    }


def class_field_annotation(class_name: str, field_name: str) -> tuple[str, str]:
    tree = ast.parse(read_text(PROJECT_SCHEMAS))
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign):
                continue
            if not isinstance(statement.target, ast.Name):
                continue
            if statement.target.id == field_name:
                default = (
                    ast.unparse(statement.value)
                    if statement.value is not None
                    else "required"
                )
                return ast.unparse(statement.annotation), default
        raise AssertionError(f"missing field {class_name}.{field_name}")
    raise AssertionError(f"missing schema class: {class_name}")


def test_frontend_project_links_use_existing_repository_slugs() -> None:
    frontend_project_urls = frontend_project_github_urls_by_title()

    assert frontend_project_urls == FRONTEND_PROJECT_GITHUB_URLS
    for invalid_url in INVALID_PROJECT_URLS:
        assert invalid_url not in read_text(FRONTEND_CONTENT)


def test_api_project_links_use_existing_repository_slugs() -> None:
    api_project_urls = api_project_github_urls_by_name()

    assert api_project_urls == API_PROJECT_GITHUB_URLS
    for invalid_url in INVALID_PROJECT_URLS:
        assert invalid_url not in read_text(SHOWCASE_SERVICE)


def test_showcase_service_does_not_publish_unverified_demo_or_doc_urls() -> None:
    showcase_service = read_text(SHOWCASE_SERVICE)
    django_project = showcase_project_named("Django Optimization App")

    assert "https://django-optimization.herokuapp.com" not in showcase_service
    assert "https://django-optimization.readthedocs.io" not in showcase_service
    assert "https://finite-diff-options.readthedocs.io" not in showcase_service
    assert literal_keyword(django_project, "has_live_demo") is False
    assert literal_keyword(django_project, "demo_url") is None
    assert literal_keyword(django_project, "demo_type") is None


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

    contracts = contract["architecture"]["public_response_contracts"]
    showcase_contract = next(
        item for item in contracts if item["surface"] == "/api/projects/showcase*"
    )

    assert showcase_contract["schemas"] == SHOWCASE_CONTRACT_SCHEMA_PATHS
    assert showcase_contract["fields"] == {"github_url": SHOWCASE_GITHUB_URL_CONTRACT}
    assert class_field_annotation("ProjectShowcase", "github_url") == (
        "Optional[HttpUrl]",
        "None",
    )
    assert class_field_annotation("ShowcaseProject", "github_url") == (
        "Optional[HttpUrl]",
        "required",
    )


def test_readme_documents_lockfile_based_pnpm_install() -> None:
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text(
        encoding="utf-8"
    )

    assert "pnpm install --frozen-lockfile" in readme
    assert "pnpm install\n" not in readme

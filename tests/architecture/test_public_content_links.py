from __future__ import annotations

from pathlib import Path


def test_curated_project_links_use_existing_repository_slugs() -> None:
    root = Path(__file__).resolve().parents[2]
    public_content = "\n".join(
        [
            (root / "apps" / "web" / "src" / "lib" / "content.ts").read_text(
                encoding="utf-8"
            ),
            (root / "apps" / "api" / "app" / "services" / "showcase_service.py").read_text(
                encoding="utf-8"
            ),
        ]
    )

    assert "https://github.com/googa27/finite_difference_options" in public_content
    assert "https://github.com/googa27/finite-difference-options" not in public_content
    assert "https://github.com/googa27/finite_element_options" in public_content
    assert "https://github.com/googa27/finite-element-options" not in public_content
    assert "https://github.com/googa27/django-optimization-app" in public_content
    assert '"https://github.com/googa27/django-optimization"' not in public_content


def test_showcase_service_does_not_publish_unverified_demo_or_doc_urls() -> None:
    root = Path(__file__).resolve().parents[2]
    showcase_service = (
        root / "apps" / "api" / "app" / "services" / "showcase_service.py"
    ).read_text(encoding="utf-8")

    assert "https://django-optimization.herokuapp.com" not in showcase_service
    assert "https://django-optimization.readthedocs.io" not in showcase_service
    assert "https://finite-diff-options.readthedocs.io" not in showcase_service
    assert 'name="Django Optimization App"' in showcase_service
    assert "has_live_demo=False" in showcase_service


def test_readme_contact_security_caveat_matches_static_contact_page() -> None:
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text(encoding="utf-8")

    assert "yourusername" not in readme
    assert "your.email@example.com" not in readme
    assert "static contact page uses redacted resume email and profile defaults" in readme


def test_readme_documents_lockfile_based_pnpm_install() -> None:
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text(encoding="utf-8")

    assert "pnpm install --frozen-lockfile" in readme
    assert "pnpm install\n" not in readme

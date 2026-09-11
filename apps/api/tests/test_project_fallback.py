"""Curated pagination and request-level read-only fallback invariants."""

from pathlib import Path

import httpx
import pytest
from sqlalchemy import event
from sqlalchemy.exc import OperationalError

from app.core.database import get_db
from app.main import app
from app.schemas.cv import CVProfile, ProfileProject
from app.services.cv import CVService
from app.services.cv.projects import curated_project_page
from app.services.project_service import ProjectService


@pytest.fixture
def profile():
    result = CVProfile.model_validate_json(
        (Path(__file__).parent / "fixtures/public_cv.json").read_text()
    )
    result.projects = [
        ProfileProject(name="Regular", url="https://example.test/a", description="A"),
        ProfileProject(
            name="Second",
            url="https://example.test/b",
            description="B",
            is_featured=True,
            display_priority=2,
        ),
        ProfileProject(
            name="First",
            url="https://example.test/c",
            description="C",
            is_featured=True,
            display_priority=1,
        ),
    ]
    return result


def test_curated_order_pagination_and_metrics_provenance(profile):
    before = profile.model_dump_json()
    page = curated_project_page(profile, limit=1)
    assert page.total == 3 and page.projects[0].name == "First"
    assert page.source == "curated_cv" and not page.metrics_available
    assert page.timestamp_kind == "profile_last_updated"
    assert all(
        -(2**48) <= item.id < 0 for item in curated_project_page(profile).projects
    )
    assert curated_project_page(profile, skip=1, limit=1).projects[0].name == "Second"
    assert curated_project_page(profile, skip=3).projects == []
    assert profile.model_dump_json() == before
    original_ids = {str(p.url): p.id for p in curated_project_page(profile).projects}
    profile.projects.reverse()
    assert {
        str(p.url): p.id for p in curated_project_page(profile).projects
    } == original_ids


@pytest.mark.parametrize("skip,limit", [(-1, 10), (0, 0), (0, 101)])
def test_curated_page_refuses_invalid_bounds(profile, skip, limit):
    with pytest.raises(ValueError):
        curated_project_page(profile, skip=skip, limit=limit)


def test_duplicate_curated_url_and_empty_profile_are_explicit(profile):
    profile.projects.append(profile.projects[0])
    with pytest.raises(ValueError, match="unique"):
        curated_project_page(profile)
    assert curated_project_page(None).projects == []
    assert curated_project_page(None).total == 0


async def test_project_get_fallback_never_acquires_or_persists(
    profile, db_session, monkeypatch
):
    from app.routers import projects

    def forbidden(*args, **kwargs):
        raise AssertionError("GET attempted acquisition or persistence")

    service = CVService()
    service._current_profile = profile
    monkeypatch.setattr(projects, "cv_service", service)
    monkeypatch.setattr(projects.github_service, "sync_projects_to_database", forbidden)
    monkeypatch.setattr(projects.github_service, "fetch_user_repos", forbidden)
    monkeypatch.setattr(db_session, "commit", forbidden)
    app.dependency_overrides[get_db] = lambda: db_session
    statements = []

    def record(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement.strip().upper())

    event.listen(db_session.bind, "before_cursor_execute", record)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            result = await client.get("/api/projects", params={"skip": 1, "limit": 1})
        assert result.status_code == 200
        assert result.json()["projects"][0]["name"] == "Second"
        assert result.json()["total"] == 3 and not result.json()["metrics_available"]
        assert statements and all(
            statement.startswith("SELECT") for statement in statements
        )
    finally:
        event.remove(db_session.bind, "before_cursor_execute", record)
        app.dependency_overrides.pop(get_db, None)


async def test_database_error_uses_curated_snapshot(profile, db_session, monkeypatch):
    from app.routers import projects

    service = CVService()
    service._current_profile = profile
    monkeypatch.setattr(projects, "cv_service", service)

    def failed_count(db):
        raise OperationalError("SELECT", {}, Exception("synthetic offline database"))

    monkeypatch.setattr(ProjectService, "count_projects", failed_count)
    result = await projects.get_projects(skip=0, limit=100, db=db_session)
    assert result.source == "curated_cv" and result.total == 3


async def test_database_pagination_has_stable_featured_order_and_no_false_fallback(
    db_session, monkeypatch
):
    from app.routers import projects

    for index, featured in enumerate([False, True, True], start=1):
        ProjectService.create_or_update_project(
            db_session,
            {
                "github_id": index,
                "name": f"Example{index}",
                "url": f"https://example.test/{index}",
                "description": "Synthetic",
                "stars": 0,
                "forks": 0,
                "topics": [],
                "is_featured": featured,
            },
        )

    async def forbidden_profile():
        raise AssertionError("nonempty database incorrectly triggered fallback")

    monkeypatch.setattr(projects.cv_service, "get_current_cv", forbidden_profile)
    first = await projects.get_projects(skip=0, limit=1, db=db_session)
    assert first.total == 3 and first.projects[0].is_featured
    assert first.source == "database" and first.metrics_available
    last = await projects.get_projects(skip=2, limit=1, db=db_session)
    assert last.total == 3 and not last.projects[0].is_featured
    beyond = await projects.get_projects(skip=5, limit=1, db=db_session)
    assert beyond.total == 3 and beyond.projects == []

"""Actual HTTP contracts for distinct stored and provider project identities."""

import httpx
import pytest
from sqlalchemy import event

from app.core.database import get_db
from app.main import app
from app.schemas.cv import CVProfile, ProfileProject
from app.services.cv import CVService
from app.services.project_service import ProjectService


@pytest.fixture
def project_client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        yield httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        )
    finally:
        app.dependency_overrides.pop(get_db, None)


def add_project(db_session, github_id, name, featured=False):
    return ProjectService.create_or_update_project(
        db_session,
        {
            "github_id": github_id,
            "name": name,
            "url": f"https://example.test/{name}",
            "description": "Synthetic identity contract",
            "language": "Python",
            "stars": 7,
            "forks": 3,
            "topics": ["synthetic", "identity"],
            "is_featured": featured,
        },
    )


async def test_colliding_namespaces_preserve_legacy_and_explicit_reads(
    db_session, project_client, monkeypatch
):
    from app.routers import projects

    first = add_project(db_session, 987654321, "First", featured=True)
    second = add_project(db_session, first.id, "Second")
    first_id, second_id = first.id, second.id
    assert first_id != second_id != 987654321

    def forbidden(*args, **kwargs):
        raise AssertionError("identity read attempted acquisition or persistence")

    monkeypatch.setattr(projects.github_service, "sync_projects_to_database", forbidden)
    monkeypatch.setattr(projects.github_service, "fetch_user_repos", forbidden)
    monkeypatch.setattr(db_session, "commit", forbidden)
    statements = []

    def record(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement.strip().upper())

    event.listen(db_session.bind, "before_cursor_execute", record)
    try:
        async with project_client as client:
            collection = await client.get("/api/projects")
            items = {item["id"]: item for item in collection.json()["projects"]}
            assert items[first_id]["github_id"] == 987654321
            assert items[second_id]["github_id"] == first_id
            for stored_id, item in items.items():
                local = await client.get(f"/api/projects/by-id/{stored_id}")
                provider = await client.get(
                    f"/api/projects/by-github/{item['github_id']}"
                )
                legacy = await client.get(f"/api/projects/{item['github_id']}")
                assert (
                    local.status_code
                    == provider.status_code
                    == legacy.status_code
                    == 200
                )
                assert local.json() == provider.json() == legacy.json() == item
            collision = await client.get(f"/api/projects/{first_id}")
            assert collision.json()["id"] == second_id
            score = await client.get(f"/api/projects/{first_id}/score")
            assert score.status_code == 200
            assert score.json()["project_name"] == "First"
        assert statements and all(
            statement.startswith("SELECT") for statement in statements
        )
    finally:
        event.remove(db_session.bind, "before_cursor_execute", record)


@pytest.mark.parametrize("path", ["by-id", "by-github"])
async def test_missing_identifier_is_not_guessed_from_other_namespace(
    db_session, project_client, path
):
    stored = add_project(db_session, 987654321, "Only")
    wrong_namespace_id = 987654321 if path == "by-id" else stored.id
    async with project_client as client:
        response = await client.get(f"/api/projects/{path}/{wrong_namespace_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}


@pytest.mark.parametrize("path", ["by-id", "by-github"])
@pytest.mark.parametrize("identifier", ["not-an-id", "0", "-1", str(2**63)])
async def test_explicit_identifier_refuses_invalid_values_before_lookup(
    project_client, monkeypatch, path, identifier
):
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid identity reached a database lookup")

    monkeypatch.setattr(ProjectService, "get_project_by_id", forbidden)
    monkeypatch.setattr(ProjectService, "get_project_by_github_id", forbidden)
    async with project_client as client:
        response = await client.get(f"/api/projects/{path}/{identifier}")
    assert response.status_code == 422


async def test_curated_display_ids_have_no_database_or_provider_identity(
    project_client, monkeypatch
):
    from app.routers import projects

    service = CVService()
    profile = CVProfile.model_validate_json(service.cv_data_file.read_text())
    profile.projects = [
        ProfileProject(
            name="Curated",
            description="Display only",
            url="https://example.test/curated",
        )
    ]
    service._current_profile = profile
    monkeypatch.setattr(projects, "cv_service", service)
    async with project_client as client:
        response = await client.get("/api/projects")
        item = response.json()["projects"][0]
        assert response.json()["source"] == "curated_cv"
        assert item["id"] < 0 and item["github_id"] is None
        detail = await client.get(f"/api/projects/by-id/{item['id']}")
        assert detail.status_code == 422


async def test_stored_project_without_provider_id_remains_readable(
    db_session, project_client
):
    stored = add_project(db_session, None, "Local")
    async with project_client as client:
        collection = await client.get("/api/projects")
        detail = await client.get(f"/api/projects/by-id/{stored.id}")
    assert detail.status_code == 200
    assert detail.json() == collection.json()["projects"][0]
    assert detail.json()["github_id"] is None


def test_openapi_declares_namespaces_and_legacy_deprecation():
    paths = app.openapi()["paths"]
    legacy = paths["/api/projects/{project_id}"]["get"]
    assert legacy["deprecated"] is True
    assert "GitHub" in legacy["parameters"][0]["description"]
    for path in (
        "/api/projects/by-id/{project_id}",
        "/api/projects/by-github/{github_id}",
    ):
        operation = paths[path]["get"]
        assert not operation.get("deprecated", False)
        parameter = operation["parameters"][0]
        assert parameter["schema"]["exclusiveMinimum"] == 0
        assert parameter["schema"]["maximum"] == 2**63 - 1
    schema = app.openapi()["components"]["schemas"]["Project"]["properties"]
    assert "database" in schema["id"]["description"]
    assert "GitHub" in schema["github_id"]["description"]

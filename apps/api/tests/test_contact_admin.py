"""Administrative contact routes must authorize before accessing the inbox."""

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.database import Contact

ADMIN_TOKEN = "synthetic-admin-test-token-with-32-characters"


@pytest.fixture
def inbox_client(db_session, monkeypatch):
    contact = Contact(
        name="Synthetic visitor",
        email="visitor@example.test",
        message="Private message",
    )
    db_session.add(contact)
    db_session.commit()
    monkeypatch.setattr(settings, "CONTACT_ADMIN_TOKEN", SecretStr(ADMIN_TOKEN))
    calls = []

    def database():
        calls.append(True)
        return db_session

    app.dependency_overrides[get_db] = database
    client = TestClient(app)
    try:
        yield client, contact, calls
    finally:
        client.close()
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.parametrize(
    "authorization", [None, "Bearer wrong", "Basic invalid", "Bearer"]
)
def test_anonymous_or_invalid_credentials_never_access_inbox(
    inbox_client, authorization
):
    client, contact, calls = inbox_client
    headers = {} if authorization is None else {"Authorization": authorization}
    for method, suffix in [("GET", ""), ("PUT", "/read")]:
        response = client.request(
            method, f"/api/contact/{contact.id}{suffix}", headers=headers
        )
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
        assert "visitor@example.test" not in response.text
    assert calls == []
    assert contact.is_read is False


@pytest.mark.parametrize("configured", [None, "", "short", " " * 40])
def test_unconfigured_administration_fails_closed(
    inbox_client, monkeypatch, configured
):
    client, contact, calls = inbox_client
    monkeypatch.setattr(
        settings,
        "CONTACT_ADMIN_TOKEN",
        None if configured is None else SecretStr(configured),
    )
    for method, suffix in [("GET", ""), ("PUT", "/read")]:
        response = client.request(
            method,
            f"/api/contact/{contact.id}{suffix}",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
        assert response.status_code == 503
    assert calls == []
    assert contact.is_read is False


def test_authorized_read_and_mutation_preserve_missing_id_semantics(
    inbox_client, db_session
):
    client, contact, calls = inbox_client
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
    response = client.get(f"/api/contact/{contact.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "visitor@example.test"
    assert (
        client.put(f"/api/contact/{contact.id}/read", headers=headers).status_code
        == 200
    )
    db_session.refresh(contact)
    assert contact.is_read is True
    for method, suffix in [("GET", ""), ("PUT", "/read")]:
        assert (
            client.request(
                method, "/api/contact/999999" + suffix, headers=headers
            ).status_code
            == 404
        )
    assert len(calls) == 4


def test_openapi_marks_only_contact_administration_as_secured():
    paths = app.openapi()["paths"]
    assert paths["/api/contact/{contact_id}"]["get"]["security"]
    assert paths["/api/contact/{contact_id}/read"]["put"]["security"]
    assert "security" not in paths["/api/contact"]["post"]


def test_public_submission_does_not_require_admin_token(inbox_client, monkeypatch):
    client, _, _ = inbox_client
    monkeypatch.setattr(settings, "CONTACT_ADMIN_TOKEN", None)

    async def synthetic_email(_contact):
        return True

    monkeypatch.setattr("app.routers.contact.send_contact_email", synthetic_email)
    response = client.post(
        "/api/contact",
        json={
            "name": "Synthetic visitor",
            "email": "visitor@example.com",
            "message": "A public synthetic contact submission.",
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

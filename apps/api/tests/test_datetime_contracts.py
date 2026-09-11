"""UTC timestamp and deprecation contract regressions for the optional API."""

import ast
from datetime import datetime
from pathlib import Path
from typing import Callable, cast

from sqlalchemy import text

from app.models.database import CVDownload, ChatMessage, ChatSession, Contact, Project
from app.schemas.cv import CVProfile, Skills

API_ROOT = Path(__file__).resolve().parents[1]
TIMESTAMP_COLUMNS = (
    (Project, "created_at"),
    (Project, "updated_at"),
    (Contact, "created_at"),
    (ChatSession, "created_at"),
    (ChatSession, "last_activity"),
    (ChatMessage, "timestamp"),
    (CVDownload, "download_date"),
)


def _assert_aware_utc(value: datetime) -> None:
    assert value.tzinfo is not None
    offset = value.utcoffset()
    assert offset is not None
    assert offset.total_seconds() == 0


def test_api_python_avoids_deprecated_datetime_and_pydantic_apis() -> None:
    violations: list[str] = []
    for root in (API_ROOT / "app", API_ROOT / "tests"):
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr in {
                    "utcnow",
                    "__fields__",
                }:
                    violations.append(
                        f"{path.relative_to(API_ROOT)}:{node.lineno}:{node.attr}"
                    )
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "datetime"
                    and node.func.attr == "now"
                    and path != API_ROOT / "app/core/time.py"
                ):
                    violations.append(
                        f"{path.relative_to(API_ROOT)}:{node.lineno}:direct datetime.now()"
                    )
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "dict"
                ):
                    violations.append(
                        f"{path.relative_to(API_ROOT)}:{node.lineno}:deprecated .dict()"
                    )

    assert violations == []


def test_database_timestamp_columns_declare_timezone_support() -> None:
    for model, attribute in TIMESTAMP_COLUMNS:
        column = getattr(model, attribute).property.columns[0]
        column_type = column.type
        timezone = getattr(column_type, "timezone", None)
        if timezone is None:
            timezone = getattr(getattr(column_type, "impl", None), "timezone", None)
        assert timezone is True, f"{model.__name__}.{attribute} must preserve timezone"


def test_database_timestamp_round_trips_are_aware_utc(db_session) -> None:
    records = (
        (
            Project(github_id=1, name="clock", url="https://example.com"),
            ("created_at", "updated_at"),
        ),
        (
            Contact(name="Clock", email="clock@example.com", message="test"),
            ("created_at",),
        ),
        (ChatSession(session_id="clock"), ("created_at", "last_activity")),
        (ChatMessage(role="user", content="clock"), ("timestamp",)),
        (CVDownload(), ("download_date",)),
    )

    for record, attributes in records:
        db_session.add(record)
        db_session.commit()
        db_session.refresh(record)
        for attribute in attributes:
            _assert_aware_utc(getattr(record, attribute))


def test_legacy_naive_database_timestamp_is_read_as_utc(db_session) -> None:
    db_session.execute(
        text(
            "INSERT INTO contacts "
            "(name, email, message, created_at, is_read) "
            "VALUES ('Legacy', 'legacy@example.com', 'test', "
            "'2024-01-02 03:04:05', 0)"
        )
    )
    db_session.commit()

    contact = (
        db_session.query(Contact).filter(Contact.email == "legacy@example.com").one()
    )
    _assert_aware_utc(contact.created_at)
    assert contact.created_at.isoformat() == "2024-01-02T03:04:05+00:00"


def test_cv_default_and_legacy_timestamp_are_utc_aware() -> None:
    field = CVProfile.model_fields["last_updated"]
    factory = cast(Callable[[], datetime], field.default_factory)
    _assert_aware_utc(factory())

    profile = CVProfile.model_validate(
        {
            "personal_info": {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "location": "Santiago, Chile",
                "linkedin_url": "https://www.linkedin.com/in/test",
                "summary": "Test profile",
            },
            "skills": {},
            "last_updated": datetime(2024, 1, 1),
            "linkedin_url": "https://www.linkedin.com/in/test",
        }
    )
    _assert_aware_utc(profile.last_updated)


def test_pydantic_helpers_are_warning_free() -> None:
    assert Skills().get_all_skills() == []


def test_starlette_testclient_uses_httpx2() -> None:
    import starlette.testclient as testclient

    assert testclient.httpx.__name__ == "httpx2"

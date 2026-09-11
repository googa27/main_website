"""The checked-in public CV must load through the API's actual data model."""

from pathlib import Path
import json

import pytest

from app.schemas.cv import CVProfile, WorkExperience, CVExportRequest
from app.services.ai_service import LocalAIService
from app.services.cv import CVService


def test_public_cv_fixture_loads_with_current_and_historical_roles():
    fixture = Path(__file__).parents[1] / "app/static/cv/cv_profile.json"
    profile = CVProfile.model_validate_json(fixture.read_text())

    current = [role for role in profile.experience if role.is_current]
    assert len(current) == 1
    assert current[0].end_date is None
    historical = [role for role in profile.experience if not role.is_current]
    assert historical
    assert all(role.end_date is not None for role in historical)
    assert profile.personal_info.phone is None


@pytest.mark.parametrize(
    "end_date,explicit_status,expected",
    [
        (None, None, True),
        ("2024-03-01T00:00:00", None, False),
        ("2024-03-01T00:00:00", True, False),
    ],
)
def test_current_role_is_derived_even_without_explicit_status(
    end_date, explicit_status, expected
):
    role = dict(
        company="Example",
        position="Analyst",
        location="Chile",
        start_date="2023-01-01T00:00:00",
        description="Example role",
    )
    if end_date is not None:
        role["end_date"] = end_date
    if explicit_status is not None:
        role["is_current"] = explicit_status
    assert WorkExperience(**role).is_current is expected


async def test_json_export_preserves_project_evidence_and_awards():
    service = CVService()
    result = await service.export_cv(CVExportRequest(format="json"))
    exported = json.loads(result.content)
    assert len(exported["projects"]) == 3
    assert exported["projects"][0]["url"].endswith("/finite_element_options")
    assert "offline" in " ".join(exported["projects"][0]["highlights"])
    assert exported["awards"][0]["title"] == "Eiffel Excellence Scholarship"


async def test_json_export_uses_application_storage_from_unrelated_cwd(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    result = await CVService().export_cv(CVExportRequest(format="json"))
    exported = json.loads(result.content)
    assert exported["projects"][0]["url"].endswith("/finite_element_options")
    assert not (tmp_path / "app").exists()


def test_resume_chat_context_and_offline_answers_use_verified_profile():
    service = LocalAIService()
    context = json.loads(service.cv_context)
    assert "phone" not in context["personal_info"]
    assert "email" not in context["personal_info"]
    assert "Deloitte" in service._fallback_response("work experience")
    assert "École Polytechnique" in service._fallback_response("education")
    assert "SQL (beginner)" in service._fallback_response("programming skills")
    assert "Finite Element Options" in service._fallback_response("projects")
    for false_claim in [
        "Universidad de Chile",
        "Quantitative Finance Solutions",
        "Financial Technology Startup",
    ]:
        assert false_claim not in service.cv_context


async def test_model_outage_uses_question_instead_of_matching_full_cv(monkeypatch):
    def offline_session():
        raise OSError("offline test")

    monkeypatch.setattr(
        "app.services.ai_service.aiohttp.ClientSession", offline_session
    )
    response = await LocalAIService().chat_with_resume(
        "Which university did Cristobal attend?"
    )
    assert "École Polytechnique" in response.message
    assert "Deloitte" not in response.message

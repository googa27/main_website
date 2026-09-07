"""The checked-in public CV must load through the API's actual data model."""

from pathlib import Path

from app.schemas.cv import CVProfile


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

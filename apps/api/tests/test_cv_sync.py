"""Offline provider sync must preserve curated data and the last valid storage."""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.schemas.cv import CVProfile, LinkedInSyncRequest
from app.services.cv import CVService
from app.services.linkedin import linkedin_service


@pytest.fixture
def stored_cv(tmp_path):
    fixture = Path(__file__).parents[1] / "app/static/cv/cv_profile.json"
    service = CVService()
    service.cv_data_dir = tmp_path
    service.cv_data_file = tmp_path / "cv_profile.json"
    service.cv_data_file.write_bytes(fixture.read_bytes())
    profile = CVProfile.model_validate_json(fixture.read_text())
    return service, profile


def configure_provider(monkeypatch, profile):
    monkeypatch.setattr(linkedin_service, "is_configured", lambda: True)
    monkeypatch.setattr(
        linkedin_service, "sync_profile_data", AsyncMock(return_value=profile)
    )
    monkeypatch.setattr(
        linkedin_service, "get_sync_status", lambda: {"last_sync": None}
    )


@pytest.mark.parametrize("explicit_empty", [False, True])
async def test_sync_preserves_omitted_curated_sections(
    stored_cv, monkeypatch, explicit_empty
):
    service, current = stored_cv
    data = current.model_dump(exclude={"projects", "awards", "date_precision_note"})
    data["personal_info"]["summary"] = "Updated provider summary"
    if explicit_empty:
        data.update(projects=[], awards=[], date_precision_note=None)
    incoming = CVProfile.model_validate(data)
    configure_provider(monkeypatch, incoming)

    result = await service.sync_from_linkedin(LinkedInSyncRequest(force_refresh=True))

    assert result.success
    assert result.data_updated
    saved = CVProfile.model_validate_json(service.cv_data_file.read_text())
    assert saved.personal_info.summary == "Updated provider summary"
    assert saved.projects == ([] if explicit_empty else current.projects)
    assert saved.awards == ([] if explicit_empty else current.awards)
    assert saved.date_precision_note == (
        None if explicit_empty else current.date_precision_note
    )
    assert incoming.projects == []
    assert await service.get_current_cv() == saved


async def test_storage_roundtrip_preserves_urls_dates_and_date_looking_text(stored_cv):
    service, profile = stored_cv
    data = profile.model_dump()
    data["projects"][0]["name"] = "2026-09-11"
    profile = CVProfile.model_validate(data)

    assert await service._save_cv_to_storage(profile)
    assert await service._load_cv_from_storage() == profile
    assert (
        json.loads(service.cv_data_file.read_text())["projects"][0]["name"]
        == "2026-09-11"
    )


@pytest.mark.parametrize("failure_mode", ["serialize", "replace"])
async def test_failed_save_preserves_file_and_cached_profile(
    stored_cv, monkeypatch, failure_mode
):
    service, current = stored_cv
    original_bytes = service.cv_data_file.read_bytes()
    await service.get_current_cv()
    data = current.model_dump()
    data["personal_info"]["summary"] = "Unsaved provider summary"
    configure_provider(monkeypatch, CVProfile.model_validate(data))

    def fail_replace(self, target):
        raise OSError("simulated replacement failure")

    if failure_mode == "replace":
        monkeypatch.setattr(Path, "replace", fail_replace)
    else:

        def fail_serialize(self, **kwargs):
            raise ValueError("simulated serialization failure")

        monkeypatch.setattr(CVProfile, "model_dump_json", fail_serialize)
    result = await service.sync_from_linkedin(LinkedInSyncRequest())

    assert not result.success
    assert not result.data_updated
    assert service.cv_data_file.read_bytes() == original_bytes
    assert await service.get_current_cv() == current
    assert list(service.cv_data_dir.iterdir()) == [service.cv_data_file]

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
    if not explicit_empty:
        data["personal_info"]["summary"] = "Updated provider summary"
    if explicit_empty:
        data.update(projects=[], awards=[], date_precision_note=None)
    incoming = CVProfile.model_validate(data)
    configure_provider(monkeypatch, incoming)

    result = await service.sync_from_linkedin(LinkedInSyncRequest(force_refresh=True))

    assert result.success
    assert result.data_updated
    saved = CVProfile.model_validate_json(service.cv_data_file.read_text())
    assert saved.personal_info.summary == data["personal_info"]["summary"]
    if explicit_empty:
        assert result.changes["projects_updated"]
        assert result.changes["awards_updated"]
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


async def test_cv_reads_allow_event_loop_progress(stored_cv, monkeypatch):
    import asyncio
    import threading

    from app.services.cv import service as implementation

    service, current = stored_cv
    started, release = threading.Event(), threading.Event()
    original = implementation.load_profile
    main_thread = threading.get_ident()

    def slow_read(path):
        assert threading.get_ident() != main_thread
        started.set()
        assert release.wait(timeout=2)
        return original(path)

    monkeypatch.setattr(implementation, "load_profile", slow_read)
    task = asyncio.create_task(service.get_current_cv())
    try:
        assert await asyncio.to_thread(started.wait, 1)
        await asyncio.sleep(0)
        assert not task.done()
    finally:
        release.set()
    assert await asyncio.wait_for(task, timeout=2) == current


async def test_cancelled_write_cannot_reorder_cache_or_lose_curated_data(
    stored_cv, monkeypatch
):
    import asyncio
    import threading

    from app.services.cv import service as implementation

    service, current = stored_cv
    await service.get_current_cv()
    first_data = current.model_dump()
    first_data["projects"][0]["name"] = "First committed curated project"
    first_data["personal_info"]["summary"] = "First provider"
    first = CVProfile.model_validate(first_data)
    second_data = current.model_dump(
        exclude={"projects", "awards", "date_precision_note"}
    )
    second_data["personal_info"]["summary"] = "Second provider"
    second = CVProfile.model_validate(second_data)
    configure_provider(monkeypatch, first)
    monkeypatch.setattr(
        linkedin_service, "sync_profile_data", AsyncMock(side_effect=[first, second])
    )
    started, release = threading.Event(), threading.Event()
    writes = []
    original = implementation.save_profile

    def delayed_first(profile, directory, path):
        writes.append(profile.projects[0].name)
        if len(writes) == 1:
            started.set()
            assert release.wait(timeout=2)
        return original(profile, directory, path)

    monkeypatch.setattr(implementation, "save_profile", delayed_first)
    initial = asyncio.create_task(service.sync_from_linkedin(LinkedInSyncRequest()))
    following = None
    try:
        assert await asyncio.to_thread(started.wait, 1)
        initial.cancel()
        with pytest.raises(asyncio.CancelledError):
            await initial
        following = asyncio.create_task(
            service.sync_from_linkedin(LinkedInSyncRequest())
        )
        await asyncio.sleep(0)
    finally:
        release.set()
    assert following is not None
    assert (await asyncio.wait_for(following, timeout=2)).success
    cached = await service.get_current_cv()
    saved = CVProfile.model_validate_json(service.cv_data_file.read_text())
    assert cached == saved
    assert saved.personal_info.summary == "Second provider"
    assert saved.projects[0].name == "First committed curated project"
    assert writes == ["First committed curated project"] * 2

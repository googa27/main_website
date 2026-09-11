"""Actual provider state follows successful CV persistence and cancellation."""

import asyncio
import threading
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.schemas.cv import CVProfile, LinkedInSyncRequest
from app.services.cv import CVService
from app.services.cv import service as implementation
from app.services.linkedin import LinkedInService


@pytest.fixture
def actual_sync(tmp_path, monkeypatch):
    provider = LinkedInService()
    provider.client_id = provider.client_secret = provider.access_token = "synthetic"
    profile = CVProfile.model_validate_json(
        (Path(__file__).parents[1] / "app/static/cv/cv_profile.json").read_text()
    )
    acquisition = AsyncMock(return_value={"synthetic": True})
    monkeypatch.setattr(provider, "_fetch_profile_data", acquisition)
    monkeypatch.setattr(
        provider, "_transform_to_cv_profile", AsyncMock(return_value=profile)
    )
    monkeypatch.setattr(implementation, "linkedin_service", provider)
    service = CVService()
    service.cv_data_dir = tmp_path
    service.cv_data_file = tmp_path / "cv_profile.json"
    service.cv_data_file.write_text(profile.model_dump_json())
    return service, provider, acquisition, profile


async def test_failed_persistence_allows_normal_retry(actual_sync, monkeypatch):
    service, provider, acquisition, _ = actual_sync
    with monkeypatch.context() as context:
        context.setattr(implementation, "save_profile", lambda *_: False)
        assert not (await service.sync_from_linkedin(LinkedInSyncRequest())).success
    assert provider.last_sync is None and provider.needs_sync()
    assert (await service.sync_from_linkedin(LinkedInSyncRequest())).success
    assert acquisition.await_count == 2
    assert provider.last_sync is not None and not provider.needs_sync()


async def test_success_retains_throttle_and_direct_provider_compatibility(actual_sync):
    service, provider, acquisition, _ = actual_sync
    assert (await service.sync_from_linkedin(LinkedInSyncRequest())).success
    timestamp = provider.last_sync
    assert not (await service.sync_from_linkedin(LinkedInSyncRequest())).success
    assert acquisition.await_count == 1 and provider.last_sync == timestamp
    provider.last_sync = None
    assert await provider.sync_profile_data() is not None
    assert provider.last_sync is not None and acquisition.await_count == 2


async def test_cancellation_during_acquisition_does_not_publish_completion(
    actual_sync, monkeypatch
):
    service, provider, _, _ = actual_sync
    started = asyncio.Event()

    async def acquisition():
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(provider, "_fetch_profile_data", acquisition)
    task = asyncio.create_task(service.sync_from_linkedin(LinkedInSyncRequest()))
    await asyncio.wait_for(started.wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert provider.last_sync is None and provider.needs_sync()


@pytest.mark.parametrize("persisted", [False, True])
async def test_cancelled_worker_publishes_only_successful_completion(
    actual_sync, monkeypatch, persisted
):
    service, provider, _, _ = actual_sync
    started, release = threading.Event(), threading.Event()
    save = implementation.save_profile

    def delayed_save(*args):
        started.set()
        assert release.wait(timeout=2)
        return save(*args) if persisted else False

    monkeypatch.setattr(implementation, "save_profile", delayed_save)
    task = asyncio.create_task(service.sync_from_linkedin(LinkedInSyncRequest()))
    try:
        assert await asyncio.to_thread(started.wait, 1)
        assert provider.last_sync is None
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        release.set()
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    await asyncio.wait_for(service.get_current_cv(), timeout=2)
    assert (provider.last_sync is not None) is persisted
    assert provider.needs_sync() is not persisted


async def test_older_failed_request_cannot_overwrite_newer_success(
    actual_sync, monkeypatch
):
    service, provider, _, profile = actual_sync
    started, release = asyncio.Event(), asyncio.Event()
    calls = 0

    async def acquisition():
        nonlocal calls
        calls += 1
        request_id = calls
        if request_id == 1:
            started.set()
            await release.wait()
        return {"request_id": request_id}

    async def transform(data):
        payload = profile.model_dump()
        payload["personal_info"]["summary"] = str(data["request_id"])
        return CVProfile.model_validate(payload)

    save = implementation.save_profile
    monkeypatch.setattr(provider, "_fetch_profile_data", acquisition)
    monkeypatch.setattr(provider, "_transform_to_cv_profile", transform)
    monkeypatch.setattr(
        implementation,
        "save_profile",
        lambda current, *args: (
            False if current.personal_info.summary == "1" else save(current, *args)
        ),
    )
    older = asyncio.create_task(service.sync_from_linkedin(LinkedInSyncRequest()))
    try:
        await asyncio.wait_for(started.wait(), timeout=2)
        assert (await service.sync_from_linkedin(LinkedInSyncRequest())).success
        completed = provider.last_sync
    finally:
        release.set()
    assert not (await asyncio.wait_for(older, timeout=2)).success
    assert calls == 2 and provider.last_sync == completed
    assert (await service.get_current_cv()).personal_info.summary == "2"


def test_concurrent_completion_clock_never_moves_backwards(actual_sync, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from datetime import UTC, datetime, timedelta

    from app.services import linkedin

    _, provider, _, _ = actual_sync
    latest = datetime(2026, 9, 11, 12, tzinfo=UTC)
    instants = iter(latest - timedelta(seconds=i) for i in range(12))
    monkeypatch.setattr(linkedin, "utc_now", lambda: next(instants))
    with ThreadPoolExecutor(max_workers=4) as workers:
        calls = [workers.submit(provider.mark_sync_completed) for _ in range(12)]
        for call in calls:
            call.result(timeout=2)
    assert provider.last_sync == latest
    status = provider.get_sync_status()
    assert status["last_sync"] == latest.isoformat()
    assert status["next_sync"] == (latest + timedelta(hours=24)).isoformat()

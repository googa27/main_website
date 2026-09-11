"""Synthetic transports verify bounded, asynchronous provider acquisition."""

import asyncio

import httpx

from app.services import linkedin


def install_transport(monkeypatch, handler):
    real_client = httpx.AsyncClient
    clients = []

    def factory(**kwargs):
        client = real_client(transport=httpx.MockTransport(handler), **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(linkedin.httpx, "AsyncClient", factory)
    service = linkedin.LinkedInService()
    service.access_token = "synthetic-provider-token"
    return service, clients


async def test_profile_and_sections_use_one_async_client_with_timeouts(monkeypatch):
    requests = []

    async def handler(request):
        await asyncio.sleep(0)
        requests.append(request)
        return httpx.Response(200, json={"source": request.url.path})

    service, clients = install_transport(monkeypatch, handler)
    result = await service._fetch_profile_data()
    assert result["source"] == "/v2/me"
    assert set(result) == {
        "source",
        "positions",
        "educations",
        "skills",
        "certifications",
    }
    assert len(requests) == 5
    assert len(clients) == 1 and clients[0].is_closed
    assert all(
        r.headers["Authorization"] == "Bearer synthetic-provider-token"
        for r in requests
    )
    assert all(
        r.extensions["timeout"]
        == {"connect": 5.0, "read": 10.0, "write": 10.0, "pool": 10.0}
        for r in requests
    )


async def test_optional_timeout_retains_successfully_fetched_sections(monkeypatch):
    async def handler(request):
        if request.url.path.endswith("educations"):
            raise httpx.ReadTimeout("synthetic timeout", request=request)
        return httpx.Response(200, json={"source": request.url.path})

    service, clients = install_transport(monkeypatch, handler)
    result = await service._fetch_profile_data()
    assert set(result) == {"source", "positions"}
    assert clients[0].is_closed


async def test_total_deadline_cancels_a_stalled_transport(monkeypatch):
    async def handler(_request):
        await asyncio.Event().wait()

    service, clients = install_transport(monkeypatch, handler)
    monkeypatch.setattr(linkedin, "ACQUISITION_DEADLINE_SECONDS", 0.01)
    assert await asyncio.wait_for(service._fetch_profile_data(), timeout=1.0) is None
    assert clients[0].is_closed


async def test_failed_primary_profile_does_not_fetch_optional_sections(monkeypatch):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(401, json={"message": "synthetic refusal"})

    service, clients = install_transport(monkeypatch, handler)
    assert await service._fetch_profile_data() is None
    assert len(requests) == 1 and clients[0].is_closed


async def test_redirects_remain_supported_without_forwarding_cross_origin_auth(
    monkeypatch,
):
    requests = []

    async def handler(request):
        requests.append(request)
        if request.url.host == "api.linkedin.com" and request.url.path == "/v2/me":
            return httpx.Response(
                302, headers={"Location": "https://synthetic.example/profile"}
            )
        return httpx.Response(200, json={"source": request.url.path})

    service, clients = install_transport(monkeypatch, handler)
    result = await service._fetch_profile_data()
    assert result["source"] == "/profile"
    redirected = [r for r in requests if r.url.host == "synthetic.example"]
    assert len(redirected) == 1
    assert "Authorization" not in redirected[0].headers
    assert clients[0].is_closed

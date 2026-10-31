"""Exercise both Ollama adapters through the maintained HTTP client on loopback."""

import socket

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from app.services.ai_service import LocalAIService


@pytest.mark.parametrize("http_status", [200, 503])
async def test_ollama_client_preserves_json_and_error_contracts(
    http_status: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse_dns(*args: object, **kwargs: object) -> None:
        raise AssertionError("Transport controls must stay on literal loopback")

    monkeypatch.setattr(socket, "getaddrinfo", refuse_dns)
    observed: list[tuple[str, object]] = []

    async def generate(request: web.Request) -> web.Response:
        observed.append((request.path, await request.json()))
        return web.json_response(
            {"response": "Synthetic model answer"}, status=http_status
        )

    async def tags(request: web.Request) -> web.Response:
        observed.append((request.path, request.method))
        return web.json_response(
            {"models": [{"name": "synthetic-model"}]}, status=http_status
        )

    application = web.Application()
    application.router.add_post("/api/generate", generate)
    application.router.add_get("/api/tags", tags)
    async with TestServer(application, host="127.0.0.1") as server:
        service = LocalAIService()
        service.ollama_base_url = str(server.make_url("")).rstrip("/")
        answer = await service._call_ollama(
            "Synthetic prompt", "synthetic-model", question="education"
        )
        status = await service.check_ollama_status()
        if http_status == 200:
            assert answer == "Synthetic model answer"
            assert status == {
                "status": "running",
                "models": ["synthetic-model"],
                "default_model": service.default_model,
                "base_url": service.ollama_base_url,
            }
        else:
            assert answer == service._fallback_response("education")
            assert status == {"status": "error", "message": "HTTP 503"}

    assert observed == [
        (
            "/api/generate",
            {
                "model": "synthetic-model",
                "prompt": "Synthetic prompt",
                "stream": False,
                "options": {"temperature": 0.7, "top_p": 0.9, "max_tokens": 500},
            },
        ),
        ("/api/tags", "GET"),
    ]

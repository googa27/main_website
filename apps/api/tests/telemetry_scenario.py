"""Isolated real-SDK telemetry scenarios; all inputs and destinations are local."""

import argparse
import asyncio
import json
import logging
import os
import socket
import sys
import threading
from contextlib import asynccontextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib.metadata import distributions, version
from pathlib import Path
from typing import Any

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path)
parser.add_argument(
    "--mode", choices=["globals", "environment", "normal"], required=True
)
parser.add_argument("--enabled-control", action="store_true")
args = parser.parse_args()
if args.source:
    sys.path.insert(0, str(args.source))
for key in list(os.environ):
    if key.startswith("OTEL_"):
        del os.environ[key]
os.environ.update(
    DATABASE_URL="sqlite://",
    CONTACT_ADMIN_TOKEN="PUBLIC_SYNTHETIC_ADMINISTRATOR_TOKEN_244",
    SECRET_KEY="PUBLIC_SYNTHETIC_SECRET_244",
    OPENAI_API_KEY="",
    HTTP_PROXY="",
    HTTPS_PROXY="",
    ALL_PROXY="",
    NO_PROXY="127.0.0.1",
    no_proxy="127.0.0.1",
    http_proxy="",
    https_proxy="",
    all_proxy="",
)

calls: dict[str, int] = {}
exports: list[dict[str, Any]] = []
providers: list[Any] = []
reader: Any = None
span_exporter: Any = None
log_exporter: Any = None
collector: HTTPServer | None = None
thread: threading.Thread | None = None


def spy(provider: Any, name: str, key: str) -> None:
    original = getattr(provider, name)
    calls[key] = 0

    def observed(*values: Any, **kwargs: Any) -> Any:
        calls[key] += 1
        return original(*values, **kwargs)

    setattr(provider, name, observed)


if args.mode != "normal":
    from opentelemetry import _logs, metrics, trace
    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk._logs.export import (
        InMemoryLogRecordExporter,
        SimpleLogRecordProcessor,
    )
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import InMemoryMetricReader
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        SimpleSpanProcessor,
    )
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    span_exporter = InMemorySpanExporter()
    tracer = TracerProvider(shutdown_on_exit=False)
    tracer.add_span_processor(SimpleSpanProcessor(span_exporter))
    reader = InMemoryMetricReader()
    meter = MeterProvider(metric_readers=[reader], shutdown_on_exit=False)
    log_exporter = InMemoryLogRecordExporter()
    logger = LoggerProvider(shutdown_on_exit=False)
    logger.add_log_record_processor(SimpleLogRecordProcessor(log_exporter))
    providers = [tracer, meter, logger]
    trace.set_tracer_provider(tracer)
    metrics.set_meter_provider(meter)
    _logs.set_logger_provider(logger)
    for provider, signal, get_name, add_name in [
        (tracer, "trace", "get_tracer", "add_span_processor"),
        (meter, "metric", "get_meter", "add_metric_reader"),
        (logger, "log", "get_logger", "add_log_record_processor"),
    ]:
        spy(provider, get_name, signal + "_get")
        spy(provider, add_name, signal + "_register")
        spy(provider, "shutdown", signal + "_shutdown")

    if args.mode == "environment":
        from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
            ExportLogsServiceRequest,
        )
        from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
            ExportMetricsServiceRequest,
        )
        from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
            ExportTraceServiceRequest,
        )

        class Collector(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                size = int(self.headers["Content-Length"])
                assert 0 < size < 1048576
                body = self.rfile.read(size)
                if self.path == "/v1/traces":
                    payload = ExportTraceServiceRequest.FromString(body)
                    count = sum(
                        len(s.spans)
                        for r in payload.resource_spans
                        for s in r.scope_spans
                    )
                elif self.path == "/v1/logs":
                    payload = ExportLogsServiceRequest.FromString(body)
                    count = sum(
                        len(s.log_records)
                        for r in payload.resource_logs
                        for s in r.scope_logs
                    )
                else:
                    assert self.path == "/v1/metrics"
                    payload = ExportMetricsServiceRequest.FromString(body)
                    count = sum(
                        len(s.metrics)
                        for r in payload.resource_metrics
                        for s in r.scope_metrics
                    )
                exports.append({"path": self.path, "bytes": size, "records": count})
                self.send_response(200)
                self.send_header("Content-Type", "application/x-protobuf")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, format: str, *values: Any) -> None:
                pass

        collector = HTTPServer(("127.0.0.1", 0), Collector)
        thread = threading.Thread(
            target=collector.serve_forever, kwargs={"poll_interval": 0.01}
        )
        thread.start()
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = (
            f"http://127.0.0.1:{collector.server_port}"
        )
        os.environ["OTEL_EXPORTER_OTLP_PROTOCOL"] = "http/protobuf"
        os.environ["OTEL_EXPORTER_OTLP_TIMEOUT"] = "1"
        for signal in ["TRACES", "METRICS", "LOGS"]:
            os.environ[f"OTEL_{signal}_EXPORTER"] = "otlp"
else:
    names = {d.metadata["Name"].lower() for d in distributions()}
    assert not any(
        n == "opentelemetry-sdk" or n.startswith("opentelemetry-exporter-")
        for n in names
    )
    # Explicit environment settings must remain inert in the normal profile too.
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://127.0.0.1:9"
    os.environ["OTEL_EXPORTER_OTLP_PROTOCOL"] = "http/protobuf"

original_connect = socket.socket.connect
original_connect_ex = socket.socket.connect_ex
original_dns = socket.getaddrinfo


def allowed(address: Any) -> bool:
    return collector is not None and address == ("127.0.0.1", collector.server_port)


def connect(sock: socket.socket, address: Any) -> Any:
    assert allowed(address), f"Unintended network connection: {address!r}"
    return original_connect(sock, address)


def connect_ex(sock: socket.socket, address: Any) -> Any:
    assert allowed(address), f"Unintended network connection: {address!r}"
    return original_connect_ex(sock, address)


def dns(host: Any, port: Any, *values: Any, **kwargs: Any) -> Any:
    assert allowed((host, port)), f"Unintended DNS: {host!r}:{port!r}"
    return original_dns(host, port, *values, **kwargs)


setattr(socket.socket, "connect", connect)
setattr(socket.socket, "connect_ex", connect_ex)
setattr(socket, "getaddrinfo", dns)

try:
    import httpx
    from fastapi import FastAPI

    # Ignore only this unrelated credential diagnostic during fixture import.
    # Restore the logger before exercising requests and telemetry.
    linkedin_logger = logging.getLogger("app.services.linkedin")
    linkedin_disabled = linkedin_logger.disabled
    linkedin_logger.disabled = True
    try:
        import app.main as owned
    finally:
        linkedin_logger.disabled = linkedin_disabled

    application = owned.app
    if not args.source:
        assert Path(owned.__file__).is_relative_to(Path(sys.prefix))
    if args.enabled_control:
        # Separate, deliberately enabled FastAPI with the actual public handlers.
        application = FastAPI()
        application.include_router(owned.app.router)

    @application.get("/__telemetry_fixture/failure")
    async def fixture_failure() -> None:
        raise RuntimeError("PUBLIC_SYNTHETIC_EXCEPTION_244")

    events: list[str] = []
    original_lifespan = application.router.lifespan_context

    @asynccontextmanager
    async def observed_lifespan(app: Any) -> Any:
        async with original_lifespan(app) as state:
            events.append("startup")
            yield state
        events.append("shutdown")

    application.router.lifespan_context = observed_lifespan

    async def exercise() -> list[list[int]]:
        statuses = []
        for _ in range(2):
            incoming: asyncio.Queue[Any] = asyncio.Queue()
            outgoing: asyncio.Queue[Any] = asyncio.Queue()
            task = asyncio.create_task(
                application(
                    {
                        "type": "lifespan",
                        "asgi": {"version": "3.0", "spec_version": "2.0"},
                        "state": {},
                    },
                    incoming.get,
                    outgoing.put,
                )
            )
            await incoming.put({"type": "lifespan.startup"})
            assert (await asyncio.wait_for(outgoing.get(), 5))[
                "type"
            ] == "lifespan.startup.complete"
            try:
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(
                        app=application, raise_app_exceptions=False
                    ),
                    base_url="http://public-fixture",
                ) as client:
                    root = await client.get("/?public_note=PUBLIC_SYNTHETIC_QUERY_244")
                    assert root.json()["message"] == "Cristobal Portfolio API"
                    assert (await client.get("/api/health")).json()[
                        "status"
                    ] == "healthy"
                    invalid = await client.post(
                        "/api/contact", json={"email": "PUBLIC_SYNTHETIC_INVALID"}
                    )
                    unauthorized = await client.get("/api/contact/1")
                    failure = await client.get("/__telemetry_fixture/failure")
                    statuses.append(
                        [
                            root.status_code,
                            invalid.status_code,
                            unauthorized.status_code,
                            failure.status_code,
                        ]
                    )
            finally:
                await incoming.put({"type": "lifespan.shutdown"})
                assert (await asyncio.wait_for(outgoing.get(), 5))[
                    "type"
                ] == "lifespan.shutdown.complete"
                await asyncio.wait_for(task, 5)
        return statuses

    statuses = asyncio.run(exercise())
    assert statuses == [[200, 422, 401, 500], [200, 422, 401, 500]]
    assert events == ["startup", "shutdown", "startup", "shutdown"]

    spans = logs = points = 0
    global_identity_preserved = True
    if providers:
        for provider in providers:
            assert provider.force_flush() is not False
        spans = len(span_exporter.get_finished_spans())
        logs = len(log_exporter.get_finished_logs())
        data = reader.get_metrics_data()
        if data is not None:
            points = sum(
                len(m.data.data_points)
                for r in data.resource_metrics
                for s in r.scope_metrics
                for m in s.metrics
            )
        global_identity_preserved = (
            trace.get_tracer_provider() is providers[0]
            and metrics.get_meter_provider() is providers[1]
            and _logs.get_logger_provider() is providers[2]
        )
    result = {
        "mode": args.mode,
        "enabled_control": args.enabled_control,
        "application_file": owned.__file__,
        "calls": dict(calls),
        "spans": spans,
        "logs": logs,
        "metric_points": points,
        "exports": list(exports),
        "global_identity_preserved": global_identity_preserved,
        "lifespan_events": events,
        "statuses": statuses,
    }
    print(json.dumps(result, sort_keys=True))
    assert global_identity_preserved
    assert (
        all(calls[signal + "_shutdown"] == 0 for signal in ["trace", "metric", "log"])
        if providers
        else True
    )
    if args.enabled_control:
        assert spans > 0 and logs > 0 and points > 0
        if args.mode == "environment":
            assert {item["path"] for item in exports if item["records"] > 0} == {
                "/v1/traces",
                "/v1/metrics",
                "/v1/logs",
            }
            assert all(
                calls[signal + "_register"] == 1
                for signal in ["trace", "metric", "log"]
            )
    else:
        assert spans == 0 and logs == 0 and points == 0
        assert not any(calls.values()) and exports == []
finally:
    if providers:
        from fastapi.telemetry import _runtime

        # FastAPI 0.142.2 has no public close API for environment-owned components.
        # This pinned test-only adapter closes them before the loopback collector;
        # the real SDK observations above remain the independent policy oracle.
        assert version("fastapi") == "0.142.2"
        _runtime._shutdown()
        for provider in providers:
            provider.shutdown()
    if collector is not None:
        collector.shutdown()
        collector.server_close()
    if thread is not None:
        thread.join(timeout=5)
        assert not thread.is_alive()

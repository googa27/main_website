"""Real loopback Uvicorn controls, also runnable against a normal API wheel."""

from __future__ import annotations

import http.client
import json
import os
import select
import signal
import socket
import subprocess
import sys
import time
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from websockets.sync.client import connect

REQUIRE_INSTALLED = "--require-installed" in sys.argv

SERVER = r"""
import asyncio
import json
import socket
import sys
from pathlib import Path

import uvicorn

options = json.loads(sys.argv[1])
portfolio = None
if options["portfolio"]:
    import app.main
    portfolio = app.main.app
    if options["require_installed"]:
        if not Path(app.main.__file__).is_relative_to(Path(sys.prefix)):
            raise RuntimeError("portfolio app is visible from the source tree")

async def application(scope, receive, send):
    async def tracked_send(message):
        await send(message)
        if message["type"] in {
            "lifespan.startup.complete", "lifespan.shutdown.complete"
        }:
            print(json.dumps({"event": message["type"]}), flush=True)

    if portfolio is not None:
        return await portfolio(scope, receive, tracked_send)
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await tracked_send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await tracked_send({"type": "lifespan.shutdown.complete"})
                return
    elif scope["type"] == "http":
        body = json.dumps({
            "client": scope["client"][0],
            "scheme": scope["scheme"],
            "loop": type(asyncio.get_running_loop()).__module__,
        }).encode()
        await send({
            "type": "http.response.start", "status": 200,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({"type": "http.response.body", "body": body})
    elif scope["type"] == "websocket":
        await receive()
        await send({"type": "websocket.accept"})
        while True:
            message = await receive()
            if message["type"] == "websocket.disconnect":
                return
            if message["type"] == "websocket.receive":
                await send({
                    "type": "websocket.send", "text": message["text"]
                })

kwargs = {}
if options["deny_forwarding"]:
    kwargs["forwarded_allow_ips"] = ""
config = uvicorn.Config(
    application, http=options["http"], loop=options["loop"],
    ws="websockets-sansio", lifespan="on", timeout_keep_alive=1,
    log_config=None, access_log=False, **kwargs,
)
# Preserve the actual IPv4/IPv6 family of the prebound public socket.
with socket.socket(fileno=options["fd"]) as listener:
    try:
        uvicorn.Server(config).run(sockets=[listener])
    except KeyboardInterrupt:
        pass
"""


@contextmanager
def server(
    *,
    protocol: str = "auto",
    loop: str = "auto",
    ipv6: bool = False,
    deny_forwarding: bool = False,
    portfolio: bool = False,
) -> Iterator[tuple[str, int]]:
    """Own one child and prebound loopback socket; require graceful completion."""
    host = "::1" if ipv6 else "127.0.0.1"
    family = socket.AF_INET6 if ipv6 else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as listener:
        listener.bind((host, 0))
        listener.listen(8)
        port = listener.getsockname()[1]
        options = {
            "fd": listener.fileno(),
            "http": protocol,
            "loop": loop,
            "deny_forwarding": deny_forwarding,
            "portfolio": portfolio,
            "require_installed": REQUIRE_INSTALLED,
        }
        # Never inherit forwarding trust or unrelated provider credentials.
        environment = {
            key: value
            for key, value in os.environ.items()
            if key in {"PATH", "LANG", "LC_ALL", "SYSTEMROOT"}
        }
        environment["DATABASE_URL"] = "sqlite:///:memory:"
        child = subprocess.Popen(
            [sys.executable, "-I", "-B", "-u", "-c", SERVER, json.dumps(options)],
            pass_fds=(listener.fileno(),),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
    first = b""
    try:
        if child.stdout is None:
            raise AssertionError("child stdout was not captured")
        ready, _, _ = select.select([child.stdout], [], [], 10)
        if not ready:
            raise AssertionError("server did not report startup within 10 seconds")
        first = child.stdout.readline()
        if first != b'{"event": "lifespan.startup.complete"}\n':
            raise AssertionError(f"unexpected startup: {first!r}")
        yield host, port
    finally:
        if child.poll() is None:
            child.send_signal(signal.SIGINT)
        try:
            output, errors = child.communicate(timeout=10)
        except subprocess.TimeoutExpired as exc:
            child.kill()
            output, errors = child.communicate(timeout=10)
            raise AssertionError(
                f"graceful shutdown failed; killed owned child: {errors[-4096:]!r}"
            ) from exc
        events = [
            json.loads(line)["event"] for line in (first + output).splitlines() if line
        ]
        if child.returncode != 0 or events != [
            "lifespan.startup.complete",
            "lifespan.shutdown.complete",
        ]:
            raise AssertionError(
                f"child exit={child.returncode}; events={events}; "
                f"stderr={errors[-4096:]!r}"
            )


def request(
    peer: tuple[str, int], connection: socket.socket, headers: str = ""
) -> dict[str, Any]:
    """Use the standard HTTP response parser and literal independent outcomes."""
    connection.sendall(
        (f"GET / HTTP/1.1\r\nHost: localhost:{peer[1]}\r\n{headers}\r\n").encode(
            "ascii"
        )
    )
    response = http.client.HTTPResponse(connection)
    response.begin()
    if response.status != 200:
        raise AssertionError(f"HTTP status {response.status}")
    return json.loads(response.read())


@unittest.skipUnless(os.name == "posix", "prebound-descriptor gate is POSIX-only")
class UvicornServerContractTests(unittest.TestCase):
    def test_connection_close_is_a_case_insensitive_list_token(self) -> None:
        for protocol in ("h11", "httptools"):
            with (
                self.subTest(protocol=protocol),
                server(protocol=protocol, loop="asyncio") as peer,
            ):
                for tokens in ("close", "keep-alive, ClOsE", "CLOSE, keep-alive"):
                    with self.subTest(tokens=tokens):
                        with socket.create_connection(peer, timeout=5) as client:
                            payload = request(peer, client, f"Connection: {tokens}\r\n")
                            self.assertEqual(payload["client"], "127.0.0.1")
                            # Must close after the complete body, before the
                            # separate one-second HTTP idle timeout.
                            client.settimeout(0.5)
                            self.assertEqual(client.recv(1), b"")

    def test_websocket_upgrade_outlives_http_keepalive(self) -> None:
        for protocol in ("h11", "httptools"):
            with (
                self.subTest(protocol=protocol),
                server(protocol=protocol, loop="asyncio") as peer,
            ):
                with socket.create_connection(peer, timeout=5) as client:
                    request(peer, client, "Connection: keep-alive\r\n")
                    with connect(
                        f"ws://127.0.0.1:{peer[1]}/ws",
                        sock=client,
                        proxy=None,
                        ping_interval=None,
                        open_timeout=5,
                    ) as websocket:
                        # Reuse the same HTTP connection so its prior idle
                        # timer is armed before the actual WebSocket upgrade.
                        time.sleep(1.5)
                        websocket.send("survives-http-idle-timeout")
                        self.assertEqual(
                            websocket.recv(timeout=5), "survives-http-idle-timeout"
                        )

    def test_forwarding_trust_has_explicit_positive_and_negative_peers(self) -> None:
        for ipv6 in (False, True):
            for denied in (False, True):
                with (
                    self.subTest(ipv6=ipv6, denied=denied),
                    server(ipv6=ipv6, deny_forwarding=denied, loop="asyncio") as peer,
                ):
                    with socket.create_connection(peer, timeout=5) as client:
                        payload = request(
                            peer,
                            client,
                            "X-Forwarded-For: 203.0.113.9\r\n"
                            "X-Forwarded-Proto: https\r\nConnection: close\r\n",
                        )
                    self.assertEqual(
                        payload["client"], peer[0] if denied else "203.0.113.9"
                    )
                    self.assertEqual(payload["scheme"], "http" if denied else "https")

    def test_default_and_explicit_native_loop_execute(self) -> None:
        for loop in ("auto", "asyncio", "uvloop"):
            with self.subTest(loop=loop), server(loop=loop) as peer:
                with socket.create_connection(peer, timeout=5) as client:
                    payload = request(peer, client, "Connection: close\r\n")
                expected = "asyncio" if loop == "asyncio" else "uvloop"
                self.assertTrue(payload["loop"].startswith(expected), payload)

    def test_actual_portfolio_application_root(self) -> None:
        with server(portfolio=True) as peer:
            with socket.create_connection(peer, timeout=5) as client:
                payload = request(peer, client, "Connection: close\r\n")
            self.assertEqual(
                payload,
                {
                    "message": "Cristobal Portfolio API",
                    "version": "1.0.0",
                    "docs": "/docs",
                },
            )


if __name__ == "__main__":
    if REQUIRE_INSTALLED:
        sys.argv.remove("--require-installed")
    unittest.main()

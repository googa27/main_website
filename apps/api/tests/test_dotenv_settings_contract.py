"""Real settings and contact authorization with synthetic environment files."""

import argparse
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOKEN = "synthetic#literal-admin-token-more-than-thirty-two-characters"
COMMENT = "# synthetic explanation longer than thirty two characters"


class DotenvSettingsContract(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="dotenv-settings-")
        self.addCleanup(self.directory.cleanup)
        self.env_file = Path(self.directory.name) / ".env"
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        for target in (
            "socket.create_connection",
            "socket.getaddrinfo",
            "socket.socket.connect",
        ):
            refusal = patch(
                target, side_effect=AssertionError("External network refused")
            )
            refusal.start()
            self.addCleanup(refusal.stop)

    def settings(self, content, environment=None):
        from app.core.config import Settings

        self.env_file.write_text(content, encoding="utf-8")
        with patch.dict(os.environ, environment or {}, clear=True):
            return Settings(_env_file=self.env_file, _env_file_encoding="utf-8")

    def request_both_routes(self, configured, token, expected, session=None):
        from fastapi.testclient import TestClient

        from app.core.config import settings
        from app.core.database import get_db
        from app.main import app

        calls = []

        def database():
            calls.append(True)
            if session is None:
                raise AssertionError("Unauthorized request reached database")
            return session

        original = app.dependency_overrides.get(get_db)
        app.dependency_overrides[get_db] = database
        try:
            with patch.object(settings, "CONTACT_ADMIN_TOKEN", configured):
                client = TestClient(app)
                try:
                    headers = (
                        {} if token is None else {"Authorization": f"Bearer {token}"}
                    )
                    for method, suffix in [("GET", ""), ("PUT", "/read")]:
                        response = client.request(
                            method, "/api/contact/999999" + suffix, headers=headers
                        )
                        self.assertEqual(response.status_code, expected)
                finally:
                    client.close()
        finally:
            if original is None:
                app.dependency_overrides.pop(get_db, None)
            else:
                app.dependency_overrides[get_db] = original
        self.assertEqual(len(calls), 0 if session is None else 2)

    def test_unconfigured_file_values_disable_both_admin_routes(self):
        for content in [
            "",
            "CONTACT_ADMIN_TOKEN\n",
            "CONTACT_ADMIN_TOKEN=\n",
            f"CONTACT_ADMIN_TOKEN= {COMMENT}\n",
            "CONTACT_ADMIN_TOKEN=short\n",
            "CONTACT_ADMIN_TOKEN='" + " " * 40 + "'\n",
        ]:
            with self.subTest(content=content):
                configured = self.settings(content).CONTACT_ADMIN_TOKEN
                for token in [None, COMMENT]:
                    self.request_both_routes(configured, token, 503)

    def test_quoted_literal_token_authorizes_real_memory_database_requests(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from sqlalchemy.pool import StaticPool

        from app.models.database import Base

        parsed = self.settings(f"CONTACT_ADMIN_TOKEN='{TOKEN}'\n").CONTACT_ADMIN_TOKEN
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.get_secret_value(), TOKEN)
        self.request_both_routes(parsed, None, 401)
        self.request_both_routes(parsed, "synthetic-wrong", 401)
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        try:
            Base.metadata.create_all(engine)
            with Session(engine) as session:
                self.request_both_routes(parsed, TOKEN, 404, session=session)
        finally:
            engine.dispose()

    def test_process_environment_overrides_empty_commented_file(self):
        parsed = self.settings(
            f"CONTACT_ADMIN_TOKEN= {COMMENT}\n", {"CONTACT_ADMIN_TOKEN": TOKEN}
        ).CONTACT_ADMIN_TOKEN
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.get_secret_value(), TOKEN)
        self.request_both_routes(parsed, COMMENT, 401)


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--require-installed", action="store_true")
    args, remaining = parser.parse_known_args()
    previous = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="installed-dotenv-consumer-") as cwd:
        os.chdir(cwd)
        try:
            # Only public synthetic configuration enters the isolated normal probe.
            environment = {
                key: os.environ[key]
                for key in ("PATH", "SYSTEMROOT", "TMPDIR", "LANG")
                if key in os.environ
            }
            environment["DATABASE_URL"] = "sqlite://"
            with patch.dict(os.environ, environment, clear=True):
                if args.require_installed:
                    prefix = Path(sys.prefix).resolve()
                    origins = {}
                    for name in ("app.main", "dotenv", "pydantic_settings"):
                        module = importlib.import_module(name)
                        origin = Path(module.__file__).resolve()
                        if not origin.is_relative_to(prefix):
                            raise AssertionError(
                                f"{name} is outside normal environment"
                            )
                        origins[name] = str(origin)
                    print(json.dumps({"normal_installed_origins": origins}), flush=True)
                result = unittest.main(
                    argv=[sys.argv[0], *remaining], verbosity=2, exit=False
                )
                return 0 if result.result.wasSuccessful() else 1
        finally:
            os.chdir(previous)


if __name__ == "__main__":
    raise SystemExit(main())

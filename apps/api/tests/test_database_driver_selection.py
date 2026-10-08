"""Check configured engine imports with real installed drivers, without connecting."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

DATABASE_PROBE = """
import json
from app.core.database import engine
url = engine.url
print(json.dumps({
    "backend": engine.dialect.name,
    "driver": engine.dialect.driver,
    "dbapi": engine.dialect.loaded_dbapi.__name__,
    "username": url.username,
    "password": url.password,
    "host": url.host,
    "port": url.port,
    "database": url.database,
    "query": dict(url.query),
}))
"""


class DatabaseDriverSelectionTests(unittest.TestCase):
    def invoke(self, url: str) -> subprocess.CompletedProcess[str]:
        # Every URL and emitted component is a public synthetic fixture. The
        # installed application constructs its real engine, but never connects.
        with tempfile.TemporaryDirectory() as cwd:
            return subprocess.run(
                [sys.executable, "-I", "-c", DATABASE_PROBE],
                cwd=cwd,
                env={**os.environ, "DATABASE_URL": url},
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

    def successful(self, url: str) -> dict[str, object]:
        result = self.invoke(url)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_unspecified_postgresql_loads_the_installed_psycopg2(self) -> None:
        result = self.successful("postgresql://localhost/public_driver_fixture")
        self.assertEqual(result["backend"], "postgresql")
        self.assertEqual(result["driver"], "psycopg2")
        self.assertEqual(result["dbapi"], "psycopg2")

    def test_encoded_public_credentials_and_query_survive_selection(self) -> None:
        result = self.successful(
            "postgresql://public_fixture:public%40pass%2Fwith%20spaces"
            "@localhost:5432/publicdb?application_name=public%20contract&sslmode=require"
        )
        self.assertEqual(result["username"], "public_fixture")
        self.assertEqual(result["password"], "public@pass/with spaces")
        self.assertEqual(result["host"], "localhost")
        self.assertEqual(result["port"], 5432)
        self.assertEqual(result["database"], "publicdb")
        self.assertEqual(
            result["query"],
            {"application_name": "public contract", "sslmode": "require"},
        )

    def test_explicit_psycopg2_retains_its_driver_and_query(self) -> None:
        result = self.successful(
            "postgresql+psycopg2://localhost/publicdb?application_name=explicit"
        )
        self.assertEqual(result["driver"], "psycopg2")
        self.assertEqual(result["dbapi"], "psycopg2")
        self.assertEqual(result["query"], {"application_name": "explicit"})

    def test_sqlite_keeps_its_backend_and_query(self) -> None:
        result = self.successful("sqlite:///:memory:?cache=shared")
        self.assertEqual(result["backend"], "sqlite")
        self.assertEqual(result["driver"], "pysqlite")
        self.assertEqual(result["database"], ":memory:")
        self.assertEqual(result["query"], {"cache": "shared"})

    def test_unsupported_explicit_driver_refuses_instead_of_falling_back(self) -> None:
        result = self.invoke(
            "postgresql+unavailable_public_driver://localhost/publicdb"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("NoSuchModuleError", result.stderr)
        self.assertIn("unavailable_public_driver", result.stderr)


if __name__ == "__main__":
    unittest.main()

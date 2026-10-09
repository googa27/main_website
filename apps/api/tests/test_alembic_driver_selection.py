"""Construct real Alembic engines with declared drivers, without connecting."""

import unittest
from pathlib import Path

from alembic.config import Config
from sqlalchemy import Engine, engine_from_config, pool

ROOT = Path(__file__).resolve().parents[1]


class AlembicDriverSelectionTests(unittest.TestCase):
    def engine(self, override: str | None = None) -> Engine:
        config = Config(str(ROOT / "alembic.ini"))
        if override is not None:
            # ConfigParser escapes are distinct from URL percent encoding.
            config.set_main_option("sqlalchemy.url", override.replace("%", "%%"))
        engine = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        self.addCleanup(engine.dispose)
        return engine

    def test_default_config_loads_the_declared_postgresql_driver(self) -> None:
        engine = self.engine()
        self.assertEqual(engine.dialect.name, "postgresql")
        self.assertEqual(engine.dialect.driver, "psycopg2")
        self.assertEqual(engine.dialect.loaded_dbapi.__name__, "psycopg2")

    def test_sqlite_override_retains_backend_and_query(self) -> None:
        engine = self.engine(
            "sqlite:///file:public_driver_fixture?mode=memory&cache=shared&uri=true"
        )
        self.assertEqual(engine.dialect.name, "sqlite")
        self.assertEqual(engine.dialect.driver, "pysqlite")
        self.assertEqual(engine.url.database, "file:public_driver_fixture")
        self.assertEqual(
            dict(engine.url.query), {"mode": "memory", "cache": "shared", "uri": "true"}
        )

    def test_explicit_postgresql_override_preserves_encoded_components(self) -> None:
        engine = self.engine(
            "postgresql+psycopg2://public_fixture:public%40pass%2Fwith%20spaces"
            "@localhost:5432/publicdb?application_name=public%20contract&sslmode=require"
        )
        self.assertEqual(engine.dialect.driver, "psycopg2")
        self.assertEqual(engine.dialect.loaded_dbapi.__name__, "psycopg2")
        self.assertEqual(engine.url.username, "public_fixture")
        self.assertEqual(engine.url.password, "public@pass/with spaces")
        self.assertEqual(engine.url.host, "localhost")
        self.assertEqual(engine.url.port, 5432)
        self.assertEqual(engine.url.database, "publicdb")
        self.assertEqual(
            dict(engine.url.query),
            {"application_name": "public contract", "sslmode": "require"},
        )


if __name__ == "__main__":
    unittest.main()

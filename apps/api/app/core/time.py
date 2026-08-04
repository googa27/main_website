"""Shared timezone-aware timestamp contracts for the optional API."""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator


def as_utc(value: datetime) -> datetime:
    """Interpret a naive legacy value as UTC or convert an aware value to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_utc(value: str | datetime | None) -> datetime | None:
    """Parse a GitHub/ISO timestamp and normalize it to aware UTC."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return as_utc(value)
    return as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))


def utc_now() -> datetime:
    """Return the current time as an aware UTC datetime."""
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """Persist UTC and restore tzinfo lost by SQLite or legacy database rows."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        del dialect
        return as_utc(value) if value is not None else None

    def process_result_value(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        del dialect
        return as_utc(value) if value is not None else None

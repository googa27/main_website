"""Fail-closed authorization for the optional contact inbox API."""

from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

contact_bearer = HTTPBearer(auto_error=False, scheme_name="ContactAdministrator")


async def require_contact_admin(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(contact_bearer)
    ],
) -> None:
    """Require a separately configured secret before any contact database access."""
    configured = settings.CONTACT_ADMIN_TOKEN
    expected = configured.get_secret_value() if configured is not None else ""
    if len(expected) < 32 or not expected.strip():
        raise HTTPException(
            status_code=503, detail="Contact administration unavailable"
        )
    supplied = credentials.credentials if credentials is not None else ""
    if not compare_digest(supplied.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(
            status_code=401,
            detail="Valid administrator credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )

"""API key authentication.

Guards mutating/expensive endpoints (upload, query) with a shared-secret
header. When `API_KEY` is unset (e.g. local development), the check is a
no-op — but production deployments MUST set it, since these endpoints
proxy paid LLM calls and would otherwise be open to abuse by anyone who
finds the URL.
"""

import secrets

from fastapi import Security
from fastapi.security import APIKeyHeader

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError

settings = get_settings()

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    if not settings.api_key:
        return
    # secrets.compare_digest instead of `!=`: a naive comparison returns as
    # soon as it finds the first mismatched character, so response time
    # leaks how many leading characters of a guess were correct — a classic
    # timing side-channel for brute-forcing a shared secret byte by byte.
    if api_key is None or not secrets.compare_digest(api_key, settings.api_key):
        raise UnauthorizedError("Missing or invalid API key")

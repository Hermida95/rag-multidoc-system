"""API key authentication.

Guards mutating/expensive endpoints (upload, query) with a shared-secret
header. When `API_KEY` is unset (e.g. local development), the check is a
no-op — but production deployments MUST set it, since these endpoints
proxy paid LLM calls and would otherwise be open to abuse by anyone who
finds the URL.
"""

from fastapi import Security
from fastapi.security import APIKeyHeader

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError

settings = get_settings()

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    if not settings.api_key:
        return
    if api_key != settings.api_key:
        raise UnauthorizedError("Missing or invalid API key")

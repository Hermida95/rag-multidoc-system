import pytest

from app.api import security
from app.core.exceptions import UnauthorizedError


@pytest.mark.asyncio
async def test_verify_api_key_noop_when_unset(monkeypatch):
    monkeypatch.setattr(security.settings, "api_key", "")

    await security.verify_api_key(api_key=None)
    await security.verify_api_key(api_key="anything")


@pytest.mark.asyncio
async def test_verify_api_key_accepts_matching_key(monkeypatch):
    monkeypatch.setattr(security.settings, "api_key", "correct-key")

    await security.verify_api_key(api_key="correct-key")


@pytest.mark.asyncio
async def test_verify_api_key_rejects_missing_key(monkeypatch):
    monkeypatch.setattr(security.settings, "api_key", "correct-key")

    with pytest.raises(UnauthorizedError):
        await security.verify_api_key(api_key=None)


@pytest.mark.asyncio
async def test_verify_api_key_rejects_wrong_key(monkeypatch):
    monkeypatch.setattr(security.settings, "api_key", "correct-key")

    with pytest.raises(UnauthorizedError):
        await security.verify_api_key(api_key="wrong-key")

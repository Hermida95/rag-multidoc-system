import io

import pytest
from fastapi import UploadFile

from app.api.v1.endpoints.documents import _read_within_limit
from app.core.exceptions import FileTooLargeError


def _upload_file(content: bytes) -> UploadFile:
    return UploadFile(file=io.BytesIO(content), filename="test.pdf")


@pytest.mark.asyncio
async def test_read_within_limit_returns_full_content_when_under_limit():
    content = b"x" * 100
    result = await _read_within_limit(_upload_file(content), max_bytes=1000)
    assert result == content


@pytest.mark.asyncio
async def test_read_within_limit_aborts_without_buffering_everything():
    # Larger than max_bytes: must raise, and must not silently truncate.
    content = b"x" * (5 * 1024 * 1024)
    with pytest.raises(FileTooLargeError):
        await _read_within_limit(_upload_file(content), max_bytes=1024 * 1024)


@pytest.mark.asyncio
async def test_read_within_limit_accepts_content_exactly_at_limit():
    content = b"x" * 2048
    result = await _read_within_limit(_upload_file(content), max_bytes=2048)
    assert result == content

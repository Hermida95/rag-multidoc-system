from __future__ import annotations

import uuid
from typing import Protocol


class FileStorage(Protocol):
    """Port for persisting raw uploaded file bytes and reading them back."""

    def save(self, document_id: uuid.UUID, filename: str, content: bytes) -> str:
        """Persists content, returns a storage path/key."""
        ...

    def read(self, storage_path: str) -> bytes: ...

    def delete(self, storage_path: str) -> None: ...

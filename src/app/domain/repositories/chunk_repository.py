from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.domain.entities.chunk import DocumentChunk


class ChunkRepository(ABC):
    """Abstract persistence contract for DocumentChunk entities."""

    @abstractmethod
    async def bulk_create(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]: ...

    @abstractmethod
    async def list_by_document(self, document_id: uuid.UUID) -> list[DocumentChunk]: ...

    @abstractmethod
    async def delete_by_document(self, document_id: uuid.UUID) -> None: ...

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.domain.entities.document import Document


class DocumentRepository(ABC):
    """Abstract persistence contract for Document aggregates."""

    @abstractmethod
    async def create(self, document: Document) -> Document: ...

    @abstractmethod
    async def get_by_id(self, document_id: uuid.UUID) -> Document | None: ...

    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Document]: ...

    @abstractmethod
    async def update(self, document: Document) -> Document: ...

    @abstractmethod
    async def delete(self, document_id: uuid.UUID) -> None: ...

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.domain.entities.chunk import RetrievedChunk


class VectorStore(ABC):
    """Abstract contract for similarity search over embedded chunks."""

    @abstractmethod
    async def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int,
        min_similarity: float = 0.0,
        document_ids: list[uuid.UUID] | None = None,
    ) -> list[RetrievedChunk]: ...

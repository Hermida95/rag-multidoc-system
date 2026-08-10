from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class DocumentChunk:
    """A semantically-coherent fragment of a document, with its embedding."""

    id: uuid.UUID
    document_id: uuid.UUID
    content: str
    chunk_index: int
    token_count: int
    embedding: list[float] | None = None
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RetrievedChunk:
    """A chunk returned from similarity search, carrying its relevance score."""

    chunk: DocumentChunk
    similarity_score: float
    document_filename: str

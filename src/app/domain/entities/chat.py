from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class SourceCitation:
    document_id: uuid.UUID
    document_filename: str
    chunk_id: uuid.UUID
    chunk_index: int
    similarity_score: float
    excerpt: str


@dataclass
class RagAnswer:
    answer: str
    sources: list[SourceCitation] = field(default_factory=list)
    model: str = ""

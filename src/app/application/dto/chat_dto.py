from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass
class RagQueryRequest:
    question: str
    document_ids: list[uuid.UUID] | None = None
    top_k: int | None = None

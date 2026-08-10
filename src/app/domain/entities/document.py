from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DocumentType(str, Enum):
    PDF = "pdf"
    MARKDOWN = "markdown"


@dataclass
class Document:
    """Core domain entity representing an ingested source document."""

    id: uuid.UUID
    filename: str
    document_type: DocumentType
    storage_path: str
    status: DocumentStatus = DocumentStatus.PENDING
    error_message: str | None = None
    chunk_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def mark_processing(self) -> None:
        self.status = DocumentStatus.PROCESSING
        self.error_message = None

    def mark_ready(self, chunk_count: int) -> None:
        self.status = DocumentStatus.READY
        self.chunk_count = chunk_count
        self.error_message = None

    def mark_failed(self, error_message: str) -> None:
        self.status = DocumentStatus.FAILED
        self.error_message = error_message

    @property
    def is_ready(self) -> bool:
        return self.status == DocumentStatus.READY

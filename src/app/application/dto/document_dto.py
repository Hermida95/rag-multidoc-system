from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.domain.entities.document import DocumentStatus, DocumentType


@dataclass
class DocumentUploadResult:
    document_id: uuid.UUID
    filename: str
    status: DocumentStatus


@dataclass
class DocumentView:
    id: uuid.UUID
    filename: str
    document_type: DocumentType
    status: DocumentStatus
    chunk_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime

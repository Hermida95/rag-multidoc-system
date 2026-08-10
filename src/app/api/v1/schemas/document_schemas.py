import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.entities.document import DocumentStatus, DocumentType


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    filename: str
    status: DocumentStatus
    message: str = "Document received and scheduled for processing."


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    document_type: DocumentType
    status: DocumentStatus
    chunk_count: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    count: int


class ErrorResponse(BaseModel):
    error_code: str = Field(..., examples=["not_found"])
    message: str

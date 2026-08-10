import uuid

from pydantic import BaseModel, Field


class RagQueryRequestSchema(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    document_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Optional filter to restrict retrieval to specific documents.",
    )
    top_k: int | None = Field(default=None, ge=1, le=20)


class SourceCitationSchema(BaseModel):
    document_id: uuid.UUID
    document_filename: str
    chunk_id: uuid.UUID
    chunk_index: int
    similarity_score: float
    excerpt: str


class RagQueryResponseSchema(BaseModel):
    answer: str
    sources: list[SourceCitationSchema]
    model: str

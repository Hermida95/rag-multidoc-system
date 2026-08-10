from app.domain.entities.chunk import DocumentChunk
from app.domain.entities.document import Document, DocumentStatus, DocumentType
from app.infrastructure.db.models import ChunkModel, DocumentModel


def document_to_model(document: Document) -> DocumentModel:
    return DocumentModel(
        id=document.id,
        filename=document.filename,
        document_type=document.document_type.value,
        storage_path=document.storage_path,
        status=document.status.value,
        error_message=document.error_message,
        chunk_count=document.chunk_count,
    )


def document_from_model(model: DocumentModel) -> Document:
    return Document(
        id=model.id,
        filename=model.filename,
        document_type=DocumentType(model.document_type),
        storage_path=model.storage_path,
        status=DocumentStatus(model.status),
        error_message=model.error_message,
        chunk_count=model.chunk_count,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def chunk_to_model(chunk: DocumentChunk) -> ChunkModel:
    return ChunkModel(
        id=chunk.id,
        document_id=chunk.document_id,
        content=chunk.content,
        chunk_index=chunk.chunk_index,
        token_count=chunk.token_count,
        embedding=chunk.embedding,
        chunk_metadata=chunk.metadata,
    )


def chunk_from_model(model: ChunkModel) -> DocumentChunk:
    return DocumentChunk(
        id=model.id,
        document_id=model.document_id,
        content=model.content,
        chunk_index=model.chunk_index,
        token_count=model.token_count,
        embedding=list(model.embedding) if model.embedding is not None else None,
        metadata=model.chunk_metadata or {},
        created_at=model.created_at,
    )

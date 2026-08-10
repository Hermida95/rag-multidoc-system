from __future__ import annotations

import uuid

from app.application.ports.chunker import Chunker
from app.application.ports.embedding_provider import EmbeddingProvider
from app.application.ports.file_storage import FileStorage
from app.application.ports.text_extractor import TextExtractorRegistry
from app.core.exceptions import DocumentProcessingError, NotFoundError
from app.core.logging import get_logger
from app.domain.entities.chunk import DocumentChunk
from app.domain.repositories.chunk_repository import ChunkRepository
from app.domain.repositories.document_repository import DocumentRepository
from app.domain.value_objects.ids import new_id

logger = get_logger(__name__)

# Embedding APIs are called in batches to bound request size / memory.
_EMBEDDING_BATCH_SIZE = 64


class ProcessDocumentUseCase:
    """Runs the full ingestion pipeline for a single document:
    extract raw text -> split into semantic chunks -> embed -> persist.

    Executed asynchronously by a Celery worker, decoupled from the upload
    request/response cycle.
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        chunk_repository: ChunkRepository,
        file_storage: FileStorage,
        extractor_registry: TextExtractorRegistry,
        chunker: Chunker,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._document_repository = document_repository
        self._chunk_repository = chunk_repository
        self._file_storage = file_storage
        self._extractor_registry = extractor_registry
        self._chunker = chunker
        self._embedding_provider = embedding_provider

    async def execute(self, document_id: uuid.UUID) -> None:
        document = await self._document_repository.get_by_id(document_id)
        if document is None:
            raise NotFoundError(f"Document {document_id} not found")

        document.mark_processing()
        await self._document_repository.update(document)

        try:
            raw_bytes = self._file_storage.read(document.storage_path)
            extractor = self._extractor_registry.get_extractor(document.document_type)
            text = extractor.extract(raw_bytes)

            if not text or not text.strip():
                raise DocumentProcessingError(
                    "Extracted text is empty — the file may be corrupted, "
                    "scanned as an image, or unsupported."
                )

            text_chunks = self._chunker.split(text)
            if not text_chunks:
                raise DocumentProcessingError("Chunking produced no content to index")

            await self._chunk_repository.delete_by_document(document.id)

            embeddings = await self._embed_in_batches(
                [c.content for c in text_chunks]
            )

            chunks = [
                DocumentChunk(
                    id=new_id(),
                    document_id=document.id,
                    content=text_chunk.content,
                    chunk_index=text_chunk.index,
                    token_count=text_chunk.token_count,
                    embedding=embedding,
                    metadata={"source_filename": document.filename},
                )
                for text_chunk, embedding in zip(text_chunks, embeddings)
            ]
            await self._chunk_repository.bulk_create(chunks)

            document.mark_ready(chunk_count=len(chunks))
            await self._document_repository.update(document)

            logger.info(
                "document_processed",
                document_id=str(document.id),
                chunk_count=len(chunks),
            )

        except Exception as exc:  # noqa: BLE001 - persist failure state, then re-raise
            logger.error(
                "document_processing_failed",
                document_id=str(document.id),
                error=str(exc),
            )
            document.mark_failed(error_message=str(exc))
            await self._document_repository.update(document)
            raise

    async def _embed_in_batches(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), _EMBEDDING_BATCH_SIZE):
            batch = texts[start : start + _EMBEDDING_BATCH_SIZE]
            embeddings.extend(await self._embedding_provider.embed_texts(batch))
        return embeddings

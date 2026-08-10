"""Composition root: wires abstract ports to concrete infrastructure
implementations and assembles use cases. Keeping this in one place is
what lets the API layer and the Celery worker share identical wiring
without either depending on the other's framework details.
"""

from functools import lru_cache

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.chunker import Chunker
from app.application.ports.embedding_provider import EmbeddingProvider
from app.application.ports.file_storage import FileStorage
from app.application.ports.llm_provider import LLMProvider
from app.application.ports.text_extractor import TextExtractorRegistry
from app.application.use_cases.process_document import ProcessDocumentUseCase
from app.application.use_cases.query_rag import QueryRagUseCase
from app.application.use_cases.upload_document import UploadDocumentUseCase
from app.core.config import get_settings
from app.infrastructure.ai.openai_embedding_provider import OpenAIEmbeddingProvider
from app.infrastructure.ai.openai_llm_provider import OpenAILLMProvider
from app.infrastructure.ai.semantic_chunker import SemanticChunker
from app.infrastructure.ai.text_extractors import (
    MarkdownTextExtractor,
    PdfTextExtractor,
)
from app.infrastructure.db.repositories.pgvector_store import PgVectorStore
from app.infrastructure.db.repositories.sqlalchemy_chunk_repository import (
    SqlAlchemyChunkRepository,
)
from app.infrastructure.db.repositories.sqlalchemy_document_repository import (
    SqlAlchemyDocumentRepository,
)
from app.infrastructure.storage.local_file_storage import LocalFileStorage

settings = get_settings()


@lru_cache
def get_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return OpenAIEmbeddingProvider(
        client=get_openai_client(),
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )


@lru_cache
def get_llm_provider() -> LLMProvider:
    return OpenAILLMProvider(
        client=get_openai_client(),
        model=settings.llm_model,
        temperature=settings.llm_temperature,
    )


@lru_cache
def get_chunker() -> Chunker:
    return SemanticChunker(
        max_tokens=settings.chunk_max_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
    )


@lru_cache
def get_extractor_registry() -> TextExtractorRegistry:
    return TextExtractorRegistry([PdfTextExtractor(), MarkdownTextExtractor()])


@lru_cache
def get_file_storage() -> FileStorage:
    return LocalFileStorage(base_dir=settings.upload_dir)


def build_upload_document_use_case(
    session: AsyncSession, schedule_processing
) -> UploadDocumentUseCase:
    return UploadDocumentUseCase(
        document_repository=SqlAlchemyDocumentRepository(session),
        file_storage=get_file_storage(),
        max_upload_size_bytes=settings.max_upload_size_bytes,
        schedule_processing=schedule_processing,
    )


def build_process_document_use_case(session: AsyncSession) -> ProcessDocumentUseCase:
    return ProcessDocumentUseCase(
        document_repository=SqlAlchemyDocumentRepository(session),
        chunk_repository=SqlAlchemyChunkRepository(session),
        file_storage=get_file_storage(),
        extractor_registry=get_extractor_registry(),
        chunker=get_chunker(),
        embedding_provider=get_embedding_provider(),
    )


def build_query_rag_use_case(session: AsyncSession) -> QueryRagUseCase:
    return QueryRagUseCase(
        embedding_provider=get_embedding_provider(),
        vector_store=PgVectorStore(session),
        llm_provider=get_llm_provider(),
        default_top_k=settings.retrieval_top_k,
        min_similarity=settings.retrieval_min_similarity,
    )

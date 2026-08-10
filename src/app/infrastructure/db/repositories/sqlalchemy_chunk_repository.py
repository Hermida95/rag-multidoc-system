import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.chunk import DocumentChunk
from app.domain.repositories.chunk_repository import ChunkRepository
from app.infrastructure.db.models import ChunkModel
from app.infrastructure.db.repositories.mappers import chunk_from_model, chunk_to_model


class SqlAlchemyChunkRepository(ChunkRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        models = [chunk_to_model(c) for c in chunks]
        self._session.add_all(models)
        await self._session.flush()
        return [chunk_from_model(m) for m in models]

    async def list_by_document(self, document_id: uuid.UUID) -> list[DocumentChunk]:
        stmt = (
            select(ChunkModel)
            .where(ChunkModel.document_id == document_id)
            .order_by(ChunkModel.chunk_index.asc())
        )
        result = await self._session.execute(stmt)
        return [chunk_from_model(m) for m in result.scalars().all()]

    async def delete_by_document(self, document_id: uuid.UUID) -> None:
        stmt = delete(ChunkModel).where(ChunkModel.document_id == document_id)
        await self._session.execute(stmt)
        await self._session.flush()

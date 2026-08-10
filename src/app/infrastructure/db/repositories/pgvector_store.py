import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.chunk import RetrievedChunk
from app.domain.repositories.vector_store import VectorStore
from app.infrastructure.db.models import ChunkModel, DocumentModel
from app.infrastructure.db.repositories.mappers import chunk_from_model


class PgVectorStore(VectorStore):
    """Similarity search backed by pgvector's cosine-distance operator.

    pgvector's `<=>` operator returns cosine *distance* (0 = identical,
    2 = opposite), so similarity is derived as `1 - distance`.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int,
        min_similarity: float = 0.0,
        document_ids: list[uuid.UUID] | None = None,
    ) -> list[RetrievedChunk]:
        distance = ChunkModel.embedding.cosine_distance(query_embedding)
        similarity = (1 - distance).label("similarity")

        stmt = (
            select(ChunkModel, DocumentModel.filename, similarity)
            .join(DocumentModel, ChunkModel.document_id == DocumentModel.id)
            .order_by(distance.asc())
            .limit(top_k)
        )

        if document_ids:
            stmt = stmt.where(ChunkModel.document_id.in_(document_ids))

        result = await self._session.execute(stmt)
        rows = result.all()

        return [
            RetrievedChunk(
                chunk=chunk_from_model(chunk_model),
                similarity_score=float(similarity_score),
                document_filename=filename,
            )
            for chunk_model, filename, similarity_score in rows
            if float(similarity_score) >= min_similarity
        ]

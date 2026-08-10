import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.document import Document
from app.domain.repositories.document_repository import DocumentRepository
from app.infrastructure.db.models import DocumentModel
from app.infrastructure.db.repositories.mappers import (
    document_from_model,
    document_to_model,
)


class SqlAlchemyDocumentRepository(DocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, document: Document) -> Document:
        model = document_to_model(document)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return document_from_model(model)

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        model = await self._session.get(DocumentModel, document_id)
        return document_from_model(model) if model else None

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Document]:
        stmt = (
            select(DocumentModel)
            .order_by(DocumentModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [document_from_model(m) for m in result.scalars().all()]

    async def update(self, document: Document) -> Document:
        model = await self._session.get(DocumentModel, document.id)
        if model is None:
            raise ValueError(f"Document {document.id} not found")
        model.filename = document.filename
        model.status = document.status.value
        model.error_message = document.error_message
        model.chunk_count = document.chunk_count
        await self._session.flush()
        await self._session.refresh(model)
        return document_from_model(model)

    async def delete(self, document_id: uuid.UUID) -> None:
        model = await self._session.get(DocumentModel, document_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.file_storage import FileStorage
from app.application.use_cases.query_rag import QueryRagUseCase
from app.application.use_cases.upload_document import UploadDocumentUseCase
from app.container import (
    build_query_rag_use_case,
    build_upload_document_use_case,
    get_file_storage,
)
from app.domain.repositories.document_repository import DocumentRepository
from app.infrastructure.celery.tasks import process_document_task
from app.infrastructure.db.repositories.sqlalchemy_document_repository import (
    SqlAlchemyDocumentRepository,
)
from app.infrastructure.db.session import get_db_session

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_upload_document_use_case(session: DbSession) -> UploadDocumentUseCase:
    return build_upload_document_use_case(
        session=session,
        schedule_processing=lambda document_id: process_document_task.delay(
            document_id
        ),
    )


def get_query_rag_use_case(session: DbSession) -> QueryRagUseCase:
    return build_query_rag_use_case(session=session)


def get_document_repository(session: DbSession) -> DocumentRepository:
    return SqlAlchemyDocumentRepository(session)


UploadDocumentUseCaseDep = Annotated[
    UploadDocumentUseCase, Depends(get_upload_document_use_case)
]
QueryRagUseCaseDep = Annotated[QueryRagUseCase, Depends(get_query_rag_use_case)]
DocumentRepositoryDep = Annotated[
    DocumentRepository, Depends(get_document_repository)
]
FileStorageDep = Annotated[FileStorage, Depends(get_file_storage)]

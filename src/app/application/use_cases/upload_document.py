from __future__ import annotations

from typing import Callable

from app.application.dto.document_dto import DocumentUploadResult
from app.application.ports.file_storage import FileStorage
from app.core.exceptions import FileTooLargeError, UnsupportedFileTypeError
from app.domain.entities.document import Document, DocumentStatus, DocumentType
from app.domain.repositories.document_repository import DocumentRepository
from app.domain.value_objects.ids import new_id

_EXTENSION_MAP = {
    ".pdf": DocumentType.PDF,
    ".md": DocumentType.MARKDOWN,
    ".markdown": DocumentType.MARKDOWN,
}


class UploadDocumentUseCase:
    """Persists an uploaded file, registers the Document aggregate, and
    schedules background processing (chunking + embedding). Does NOT do
    any AI work itself — that happens asynchronously via Celery.
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        file_storage: FileStorage,
        max_upload_size_bytes: int,
        schedule_processing: Callable[[str], None],
    ) -> None:
        self._document_repository = document_repository
        self._file_storage = file_storage
        self._max_upload_size_bytes = max_upload_size_bytes
        self._schedule_processing = schedule_processing

    async def execute(
        self,
        filename: str,
        content: bytes,
    ) -> DocumentUploadResult:
        document_type = self._resolve_document_type(filename)

        if len(content) > self._max_upload_size_bytes:
            raise FileTooLargeError(
                f"File exceeds maximum allowed size of "
                f"{self._max_upload_size_bytes // (1024 * 1024)}MB"
            )

        document_id = new_id()
        storage_path = self._file_storage.save(document_id, filename, content)

        document = Document(
            id=document_id,
            filename=filename,
            document_type=document_type,
            storage_path=storage_path,
            status=DocumentStatus.PENDING,
        )
        created = await self._document_repository.create(document)

        self._schedule_processing(str(created.id))

        return DocumentUploadResult(
            document_id=created.id,
            filename=created.filename,
            status=created.status,
        )

    @staticmethod
    def _resolve_document_type(filename: str) -> DocumentType:
        suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        document_type = _EXTENSION_MAP.get(suffix)
        if document_type is None:
            raise UnsupportedFileTypeError(
                f"Unsupported file extension '{suffix}'. Allowed: "
                f"{', '.join(sorted(_EXTENSION_MAP))}"
            )
        return document_type

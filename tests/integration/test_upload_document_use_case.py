import pytest

from app.application.use_cases.upload_document import UploadDocumentUseCase
from app.core.exceptions import FileTooLargeError, UnsupportedFileTypeError
from app.domain.entities.document import DocumentStatus


class FakeDocumentRepository:
    def __init__(self):
        self.created = []

    async def create(self, document):
        self.created.append(document)
        return document

    async def get_by_id(self, document_id):
        return next((d for d in self.created if d.id == document_id), None)

    async def list_all(self, limit=100, offset=0):
        return self.created

    async def update(self, document):
        return document

    async def delete(self, document_id):
        self.created = [d for d in self.created if d.id != document_id]


class FakeFileStorage:
    def __init__(self):
        self.saved = {}

    def save(self, document_id, filename, content):
        path = f"/fake/{document_id}/{filename}"
        self.saved[path] = content
        return path

    def read(self, storage_path):
        return self.saved[storage_path]


@pytest.mark.asyncio
async def test_upload_document_schedules_processing_and_persists_pending_document():
    repo = FakeDocumentRepository()
    storage = FakeFileStorage()
    scheduled_ids = []

    use_case = UploadDocumentUseCase(
        document_repository=repo,
        file_storage=storage,
        max_upload_size_bytes=1024 * 1024,
        schedule_processing=lambda document_id: scheduled_ids.append(document_id),
    )

    result = await use_case.execute(filename="report.pdf", content=b"%PDF-fake-content")

    assert result.status == DocumentStatus.PENDING
    assert result.filename == "report.pdf"
    assert len(repo.created) == 1
    assert scheduled_ids == [str(result.document_id)]


@pytest.mark.asyncio
async def test_upload_document_rejects_unsupported_extension():
    use_case = UploadDocumentUseCase(
        document_repository=FakeDocumentRepository(),
        file_storage=FakeFileStorage(),
        max_upload_size_bytes=1024 * 1024,
        schedule_processing=lambda document_id: None,
    )

    with pytest.raises(UnsupportedFileTypeError):
        await use_case.execute(filename="image.png", content=b"binary")


@pytest.mark.asyncio
async def test_upload_document_rejects_oversized_file():
    use_case = UploadDocumentUseCase(
        document_repository=FakeDocumentRepository(),
        file_storage=FakeFileStorage(),
        max_upload_size_bytes=10,
        schedule_processing=lambda document_id: None,
    )

    with pytest.raises(FileTooLargeError):
        await use_case.execute(filename="report.pdf", content=b"x" * 100)

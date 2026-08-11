import uuid

from fastapi import APIRouter, Depends, File, Request, UploadFile, status

from app.api.deps import DocumentRepositoryDep, FileStorageDep, UploadDocumentUseCaseDep
from app.api.security import verify_api_key
from app.api.v1.schemas.document_schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.core.config import get_settings
from app.core.exceptions import FileTooLargeError, NotFoundError
from app.core.logging import get_logger
from app.core.rate_limit import limiter

settings = get_settings()
logger = get_logger(__name__)

# Read in bounded chunks and abort as soon as the limit is exceeded, instead
# of buffering an attacker-controlled amount of data before checking size —
# a client can omit Content-Length (chunked transfer-encoding), so that
# header can't be trusted as the only guard against a disk/memory-exhaustion
# upload.
_READ_CHUNK_BYTES = 1024 * 1024

router = APIRouter(
    prefix="/documents", tags=["documents"], dependencies=[Depends(verify_api_key)]
)


async def _read_within_limit(file: UploadFile, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise FileTooLargeError(
                f"File exceeds maximum allowed size of {max_bytes // (1024 * 1024)}MB"
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a document (PDF/Markdown) for asynchronous RAG ingestion",
)
@limiter.limit(settings.rate_limit_upload)
async def upload_document(
    request: Request,
    use_case: UploadDocumentUseCaseDep,
    file: UploadFile = File(...),
) -> DocumentUploadResponse:
    content = await _read_within_limit(file, settings.max_upload_size_bytes)
    result = await use_case.execute(filename=file.filename or "unnamed", content=content)
    return DocumentUploadResponse(
        document_id=result.document_id,
        filename=result.filename,
        status=result.status,
    )


@router.get("", response_model=DocumentListResponse, summary="List ingested documents")
async def list_documents(
    document_repository: DocumentRepositoryDep,
    limit: int = 50,
    offset: int = 0,
) -> DocumentListResponse:
    documents = await document_repository.list_all(limit=limit, offset=offset)
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d, from_attributes=True) for d in documents],
        count=len(documents),
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get a document's ingestion status",
)
async def get_document(
    document_id: uuid.UUID,
    document_repository: DocumentRepositoryDep,
) -> DocumentResponse:
    document = await document_repository.get_by_id(document_id)
    if document is None:
        raise NotFoundError(f"Document {document_id} not found")
    return DocumentResponse.model_validate(document, from_attributes=True)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document, its chunks, and the stored file",
)
async def delete_document(
    document_id: uuid.UUID,
    document_repository: DocumentRepositoryDep,
    file_storage: FileStorageDep,
) -> None:
    document = await document_repository.get_by_id(document_id)
    if document is None:
        raise NotFoundError(f"Document {document_id} not found")
    await document_repository.delete(document_id)
    try:
        file_storage.delete(document.storage_path)
    except OSError as exc:
        logger.warning(
            "document_file_delete_failed",
            document_id=str(document_id),
            error=str(exc),
        )

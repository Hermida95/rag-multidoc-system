import uuid

from fastapi import APIRouter, Depends, File, Request, UploadFile, status

from app.api.deps import DocumentRepositoryDep, UploadDocumentUseCaseDep
from app.api.security import verify_api_key
from app.api.v1.schemas.document_schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.core.rate_limit import limiter

settings = get_settings()

router = APIRouter(
    prefix="/documents", tags=["documents"], dependencies=[Depends(verify_api_key)]
)


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
    content = await file.read()
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
    summary="Delete a document and its chunks",
)
async def delete_document(
    document_id: uuid.UUID,
    document_repository: DocumentRepositoryDep,
) -> None:
    document = await document_repository.get_by_id(document_id)
    if document is None:
        raise NotFoundError(f"Document {document_id} not found")
    await document_repository.delete(document_id)

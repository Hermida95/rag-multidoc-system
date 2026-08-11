from fastapi import APIRouter, Depends, Request

from app.api.deps import QueryRagUseCaseDep
from app.api.security import verify_api_key
from app.api.v1.schemas.chat_schemas import (
    RagQueryRequestSchema,
    RagQueryResponseSchema,
    SourceCitationSchema,
)
from app.application.dto.chat_dto import RagQueryRequest
from app.core.config import get_settings
from app.core.rate_limit import limiter

settings = get_settings()

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(verify_api_key)])


@router.post(
    "/query",
    response_model=RagQueryResponseSchema,
    summary="Ask a question grounded in the ingested documents",
)
@limiter.limit(settings.rate_limit_query)
async def query_rag(
    request: Request,
    payload: RagQueryRequestSchema,
    use_case: QueryRagUseCaseDep,
) -> RagQueryResponseSchema:
    rag_request = RagQueryRequest(
        question=payload.question,
        document_ids=payload.document_ids,
        top_k=payload.top_k,
    )
    answer = await use_case.execute(rag_request)
    return RagQueryResponseSchema(
        answer=answer.answer,
        sources=[
            SourceCitationSchema(
                document_id=s.document_id,
                document_filename=s.document_filename,
                chunk_id=s.chunk_id,
                chunk_index=s.chunk_index,
                similarity_score=s.similarity_score,
                excerpt=s.excerpt,
            )
            for s in answer.sources
        ],
        model=answer.model,
    )

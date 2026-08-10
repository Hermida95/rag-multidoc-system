from fastapi import APIRouter

from app.api.deps import QueryRagUseCaseDep
from app.api.v1.schemas.chat_schemas import RagQueryRequestSchema, RagQueryResponseSchema
from app.application.dto.chat_dto import RagQueryRequest

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/query",
    response_model=RagQueryResponseSchema,
    summary="Ask a question grounded in the ingested documents",
)
async def query_rag(
    payload: RagQueryRequestSchema,
    use_case: QueryRagUseCaseDep,
) -> RagQueryResponseSchema:
    request = RagQueryRequest(
        question=payload.question,
        document_ids=payload.document_ids,
        top_k=payload.top_k,
    )
    answer = await use_case.execute(request)
    return RagQueryResponseSchema(
        answer=answer.answer,
        sources=[
            {
                "document_id": s.document_id,
                "document_filename": s.document_filename,
                "chunk_id": s.chunk_id,
                "chunk_index": s.chunk_index,
                "similarity_score": s.similarity_score,
                "excerpt": s.excerpt,
            }
            for s in answer.sources
        ],
        model=answer.model,
    )

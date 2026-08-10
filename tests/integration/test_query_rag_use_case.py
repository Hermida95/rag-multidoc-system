import uuid

import pytest

from app.application.dto.chat_dto import RagQueryRequest
from app.application.use_cases.query_rag import QueryRagUseCase
from app.core.exceptions import ValidationAppError
from app.domain.entities.chunk import DocumentChunk, RetrievedChunk


class FakeEmbeddingProvider:
    async def embed_texts(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]

    async def embed_query(self, text):
        return [0.1, 0.2, 0.3]

    @property
    def dimensions(self):
        return 3


class FakeVectorStore:
    def __init__(self, results):
        self._results = results

    async def similarity_search(
        self, query_embedding, top_k, min_similarity=0.0, document_ids=None
    ):
        return self._results[:top_k]


class FakeLLMProvider:
    def __init__(self, response: str = "The answer is 42 [1]."):
        self._response = response
        self.last_user_prompt = None

    async def generate(self, system_prompt, user_prompt):
        self.last_user_prompt = user_prompt
        return self._response

    @property
    def model_name(self):
        return "fake-model"


def _make_retrieved_chunk(content: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=DocumentChunk(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            content=content,
            chunk_index=0,
            token_count=10,
            embedding=[0.1, 0.2, 0.3],
        ),
        similarity_score=score,
        document_filename="doc.pdf",
    )


@pytest.mark.asyncio
async def test_query_rag_returns_grounded_answer_with_sources():
    retrieved = [_make_retrieved_chunk("Relevant content about the answer.", 0.9)]
    llm = FakeLLMProvider()
    use_case = QueryRagUseCase(
        embedding_provider=FakeEmbeddingProvider(),
        vector_store=FakeVectorStore(retrieved),
        llm_provider=llm,
        default_top_k=5,
        min_similarity=0.5,
    )

    result = await use_case.execute(RagQueryRequest(question="What is the answer?"))

    assert result.answer == "The answer is 42 [1]."
    assert len(result.sources) == 1
    assert result.sources[0].document_filename == "doc.pdf"
    assert "[1]" in llm.last_user_prompt


@pytest.mark.asyncio
async def test_query_rag_with_no_matches_skips_llm_call():
    llm = FakeLLMProvider()
    use_case = QueryRagUseCase(
        embedding_provider=FakeEmbeddingProvider(),
        vector_store=FakeVectorStore([]),
        llm_provider=llm,
        default_top_k=5,
        min_similarity=0.5,
    )

    result = await use_case.execute(RagQueryRequest(question="Unanswerable question"))

    assert "couldn't find" in result.answer
    assert result.sources == []
    assert llm.last_user_prompt is None


@pytest.mark.asyncio
async def test_query_rag_rejects_empty_question():
    use_case = QueryRagUseCase(
        embedding_provider=FakeEmbeddingProvider(),
        vector_store=FakeVectorStore([]),
        llm_provider=FakeLLMProvider(),
        default_top_k=5,
        min_similarity=0.5,
    )

    with pytest.raises(ValidationAppError):
        await use_case.execute(RagQueryRequest(question="   "))

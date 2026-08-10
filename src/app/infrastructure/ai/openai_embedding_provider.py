from openai import APIError, AsyncOpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.application.ports.embedding_provider import EmbeddingProvider
from app.core.exceptions import EmbeddingProviderError


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        dimensions: int,
    ) -> None:
        self._client = client
        self._model = model
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = await self._call_embeddings(texts)
        except APIError as exc:
            raise EmbeddingProviderError(f"Embedding request failed: {exc}") from exc
        return [item.embedding for item in response.data]

    async def embed_query(self, text: str) -> list[float]:
        embeddings = await self.embed_texts([text])
        return embeddings[0]

    @retry(
        retry=retry_if_exception_type(APIError),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _call_embeddings(self, texts: list[str]):
        return await self._client.embeddings.create(
            model=self._model,
            input=texts,
            dimensions=self._dimensions,
        )

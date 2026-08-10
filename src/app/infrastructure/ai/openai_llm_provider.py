from openai import APIError, AsyncOpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.application.ports.llm_provider import LLMProvider
from app.core.exceptions import LLMProviderError


class OpenAILLMProvider(LLMProvider):
    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        temperature: float,
    ) -> None:
        self._client = client
        self._model = model
        self._temperature = temperature

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = await self._call_chat_completion(system_prompt, user_prompt)
        except APIError as exc:
            raise LLMProviderError(f"LLM completion request failed: {exc}") from exc

        content = response.choices[0].message.content
        if not content:
            raise LLMProviderError("LLM returned an empty response")
        return content

    @retry(
        retry=retry_if_exception_type(APIError),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _call_chat_completion(self, system_prompt: str, user_prompt: str):
        return await self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

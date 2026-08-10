from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Port for generating grounded chat completions."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

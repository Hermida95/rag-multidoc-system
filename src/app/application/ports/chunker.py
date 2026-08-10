from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TextChunk:
    content: str
    token_count: int
    index: int


class Chunker(ABC):
    """Port for splitting raw text into semantically-coherent chunks."""

    @abstractmethod
    def split(self, text: str) -> list[TextChunk]: ...

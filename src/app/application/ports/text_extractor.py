from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.document import DocumentType


class TextExtractor(ABC):
    """Port for extracting raw text content from a source file."""

    @abstractmethod
    def supports(self, document_type: DocumentType) -> bool: ...

    @abstractmethod
    def extract(self, content: bytes) -> str: ...


class TextExtractorRegistry:
    """Resolves the right extractor for a given document type."""

    def __init__(self, extractors: list[TextExtractor]) -> None:
        self._extractors = extractors

    def get_extractor(self, document_type: DocumentType) -> TextExtractor:
        for extractor in self._extractors:
            if extractor.supports(document_type):
                return extractor
        raise ValueError(f"No extractor registered for document type: {document_type}")

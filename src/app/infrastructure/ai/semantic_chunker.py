import re

import tiktoken

from app.application.ports.chunker import Chunker, TextChunk

# Ordered from "most structurally meaningful" to "most granular". The
# splitter tries each separator in turn and only falls back to a finer
# one when a segment still doesn't fit inside the token budget, so
# paragraphs/sentences are kept intact whenever possible.
_SEPARATORS = [
    r"\n#{1,6}\s",  # markdown headings start a new topic
    r"\n\n+",  # paragraph breaks
    r"\n",  # line breaks
    r"(?<=[.!?])\s+",  # sentence boundaries
    r" ",  # last resort: words
]


class SemanticChunker(Chunker):
    """Structure-aware recursive chunker.

    Splits text along the most meaningful boundary available (headings,
    then paragraphs, then sentences, then words) so that chunks stay
    semantically self-contained, while enforcing a max token budget per
    chunk (measured with the model's real tokenizer) and carrying a
    configurable token overlap between consecutive chunks for retrieval
    continuity.
    """

    def __init__(
        self,
        max_tokens: int,
        overlap_tokens: int,
        encoding_name: str = "cl100k_base",
    ) -> None:
        if overlap_tokens >= max_tokens:
            raise ValueError("overlap_tokens must be smaller than max_tokens")
        self._max_tokens = max_tokens
        self._overlap_tokens = overlap_tokens
        self._encoding = tiktoken.get_encoding(encoding_name)

    def split(self, text: str) -> list[TextChunk]:
        normalized = text.strip()
        if not normalized:
            return []

        segments = self._recursive_split(normalized, separator_level=0)
        merged = self._merge_with_overlap(segments)

        return [
            TextChunk(content=content, token_count=self._count_tokens(content), index=i)
            for i, content in enumerate(merged)
        ]

    def _recursive_split(self, text: str, separator_level: int) -> list[str]:
        if self._count_tokens(text) <= self._max_tokens:
            return [text]

        if separator_level >= len(_SEPARATORS):
            return self._hard_split_by_tokens(text)

        pattern = _SEPARATORS[separator_level]
        pieces = [p for p in re.split(pattern, text) if p and p.strip()]

        if len(pieces) <= 1:
            return self._recursive_split(text, separator_level + 1)

        result: list[str] = []
        for piece in pieces:
            result.extend(self._recursive_split(piece.strip(), separator_level + 1))
        return result

    def _hard_split_by_tokens(self, text: str) -> list[str]:
        tokens = self._encoding.encode(text)
        chunks = []
        for start in range(0, len(tokens), self._max_tokens):
            token_slice = tokens[start : start + self._max_tokens]
            chunks.append(self._encoding.decode(token_slice))
        return chunks

    def _merge_with_overlap(self, segments: list[str]) -> list[str]:
        merged: list[str] = []
        current_parts: list[str] = []
        current_tokens = 0

        for segment in segments:
            segment_tokens = self._count_tokens(segment)

            if current_tokens + segment_tokens > self._max_tokens and current_parts:
                merged.append("\n\n".join(current_parts))
                current_parts, current_tokens = self._start_next_chunk(current_parts)

            current_parts.append(segment)
            current_tokens += segment_tokens

        if current_parts:
            merged.append("\n\n".join(current_parts))

        return merged

    def _start_next_chunk(self, previous_parts: list[str]) -> tuple[list[str], int]:
        """Seeds the next chunk with a tail overlap from the previous one."""
        if self._overlap_tokens <= 0:
            return [], 0

        overlap_parts: list[str] = []
        overlap_tokens = 0
        for part in reversed(previous_parts):
            part_tokens = self._count_tokens(part)
            if overlap_tokens + part_tokens > self._overlap_tokens and overlap_parts:
                break
            overlap_parts.insert(0, part)
            overlap_tokens += part_tokens

        return overlap_parts, overlap_tokens

    def _count_tokens(self, text: str) -> int:
        return len(self._encoding.encode(text))

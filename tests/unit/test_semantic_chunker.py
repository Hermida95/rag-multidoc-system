import pytest

from app.infrastructure.ai.semantic_chunker import SemanticChunker


def test_split_empty_text_returns_no_chunks():
    chunker = SemanticChunker(max_tokens=50, overlap_tokens=10)
    assert chunker.split("   ") == []


def test_short_text_produces_single_chunk():
    chunker = SemanticChunker(max_tokens=100, overlap_tokens=10)
    chunks = chunker.split("This is a short paragraph about RAG systems.")
    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert chunks[0].token_count <= 100


def test_long_text_is_split_into_multiple_chunks_within_budget():
    paragraph = "The quick brown fox jumps over the lazy dog. " * 40
    text = "\n\n".join([paragraph] * 3)

    chunker = SemanticChunker(max_tokens=60, overlap_tokens=15)
    chunks = chunker.split(text)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.token_count <= 60
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_consecutive_chunks_share_overlap_content():
    paragraph = "Alpha beta gamma delta epsilon zeta eta theta iota kappa. " * 10
    chunker = SemanticChunker(max_tokens=40, overlap_tokens=12)
    chunks = chunker.split(paragraph)

    assert len(chunks) > 1
    tail_of_first = chunks[0].content[-20:]
    assert any(
        word in chunks[1].content for word in tail_of_first.split() if len(word) > 3
    )


def test_overlap_must_be_smaller_than_max_tokens():
    with pytest.raises(ValueError):
        SemanticChunker(max_tokens=50, overlap_tokens=50)

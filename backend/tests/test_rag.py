"""Tests for the RAG ingestion and retrieval pipeline."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.rag.ingest import chunk_text, TextChunk


# ── Chunking tests (no DB/API needed) ─────────────────────────────────────────

def test_chunk_text_basic() -> None:
    """Short text should produce a single chunk."""
    text = "This is a short document."
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    assert len(chunks) == 1
    assert chunks[0].content == text
    assert chunks[0].chunk_index == 0


def test_chunk_text_overlap() -> None:
    """Long text should produce multiple overlapping chunks."""
    # Generate a long text (many tokens)
    text = " ".join(["word"] * 1000)
    chunks = chunk_text(text, chunk_size=100, overlap=20)

    assert len(chunks) > 1
    # Check indices are sequential
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i


def test_chunk_text_empty() -> None:
    """Empty text should produce no chunks."""
    chunks = chunk_text("", chunk_size=100, overlap=10)
    assert len(chunks) == 0


def test_chunk_text_preserves_content() -> None:
    """Each chunk should be a decodable string (not corrupted)."""
    text = "The quick brown fox jumps over the lazy dog. " * 50
    chunks = chunk_text(text, chunk_size=50, overlap=5)
    for chunk in chunks:
        assert isinstance(chunk.content, str)
        assert len(chunk.content) > 0


def test_chunk_text_token_count() -> None:
    """Each chunk should respect the chunk_size limit."""
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    text = " ".join(["token"] * 500)
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    for chunk in chunks:
        assert chunk.token_count <= 100


# ── Hybrid search (mocked embeddings + DB) ────────────────────────────────────

async def test_retriever_returns_formatted_context() -> None:
    """format_context should produce readable output from chunks."""
    from app.rag.retriever import RetrievedChunk, format_context

    chunks = [
        RetrievedChunk(
            id="1",
            title="Test Article",
            content="This is the article content.",
            category="billing",
            chunk_index=0,
            vector_score=0.9,
            keyword_score=0.8,
            hybrid_score=0.87,
        )
    ]
    context = format_context(chunks)
    assert "Test Article" in context
    assert "article content" in context
    assert "billing" in context


async def test_retriever_empty_returns_no_articles_message() -> None:
    from app.rag.retriever import format_context

    context = format_context([])
    assert "No relevant" in context


async def test_ingest_document_creates_chunks(db) -> None:
    """Ingestion should create KBDocument rows with embeddings."""
    mock_vector = [0.1] * 1536

    with patch("app.rag.ingest.embed_texts", new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [mock_vector]  # One chunk → one vector

        from app.rag.ingest import ingest_document
        docs = await ingest_document(
            title="Test Doc",
            content="This is a short test document about billing.",
            category="billing",
            db=db,
        )

    assert len(docs) >= 1
    assert docs[0].title == "Test Doc"
    assert docs[0].category == "billing"
    assert docs[0].chunk_index == 0

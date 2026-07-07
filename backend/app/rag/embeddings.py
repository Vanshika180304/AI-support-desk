from __future__ import annotations

from functools import lru_cache

from openai import AsyncOpenAI

from app.core.config import get_settings

settings = get_settings()

_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return a list of 1536-dim embedding vectors for the given texts.

    OpenAI's text-embedding-3-small produces 1536-dim vectors and is
    significantly cheaper than ada-002 while remaining high quality.
    Batches of up to 2048 inputs are supported; we chunk to 512 to stay safe.
    """
    client = get_openai_client()
    results: list[list[float]] = []

    # Batch in chunks of 512 to avoid request size limits
    batch_size = 512
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = await client.embeddings.create(
            model=settings.openai_embedding_model,
            input=batch,
        )
        results.extend([item.embedding for item in response.data])

    return results


async def embed_single(text: str) -> list[float]:
    """Convenience wrapper for embedding a single text."""
    vectors = await embed_texts([text])
    return vectors[0]

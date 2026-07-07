from __future__ import annotations

import uuid
from dataclasses import dataclass

import tiktoken

from app.core.logging import get_logger
from app.models.kb_document import KBDocument
from app.rag.embeddings import embed_texts

log = get_logger(__name__)

CHUNK_TOKENS = 500
OVERLAP_TOKENS = 50
ENCODING_NAME = "cl100k_base"  # used by text-embedding-3-small and gpt-4o


@dataclass
class TextChunk:
    content: str
    chunk_index: int
    token_count: int


def chunk_text(text: str, chunk_size: int = CHUNK_TOKENS, overlap: int = OVERLAP_TOKENS) -> list[TextChunk]:
    """Split `text` into overlapping token-based chunks.

    Uses tiktoken for accurate token counting rather than naive character
    splitting, which is critical for consistent embedding quality.
    """
    enc = tiktoken.get_encoding(ENCODING_NAME)
    tokens = enc.encode(text)
    chunks: list[TextChunk] = []

    start = 0
    idx = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text_str = enc.decode(chunk_tokens)
        chunks.append(TextChunk(
            content=chunk_text_str,
            chunk_index=idx,
            token_count=len(chunk_tokens),
        ))
        idx += 1
        if end == len(tokens):
            break
        start = end - overlap  # slide back by overlap

    log.debug("Chunked text", total_tokens=len(tokens), num_chunks=len(chunks))
    return chunks


async def ingest_document(
    *,
    title: str,
    content: str,
    category: str,
    source_url: str | None = None,
    db,  # AsyncSession
) -> list[KBDocument]:
    """Chunk, embed, and store a document.

    Returns the list of KBDocument rows inserted.
    """
    log.info("Ingesting document", title=title, category=category)

    chunks = chunk_text(content)
    if not chunks:
        log.warning("Empty document — nothing to ingest", title=title)
        return []

    # Embed all chunks in one batched call
    texts = [c.content for c in chunks]
    vectors = await embed_texts(texts)

    docs: list[KBDocument] = []
    for chunk, vector in zip(chunks, vectors):
        doc = KBDocument(
            id=uuid.uuid4(),
            title=title,
            source_url=source_url,
            content=chunk.content,
            category=category,
            embedding=vector,
            chunk_index=chunk.chunk_index,
        )
        db.add(doc)
        docs.append(doc)

    await db.commit()
    log.info(
        "Document ingested",
        title=title,
        chunks=len(docs),
        category=category,
    )
    return docs

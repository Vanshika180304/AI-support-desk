from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Float, Integer, cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.kb_document import KBDocument
from app.rag.embeddings import embed_single

settings = get_settings()
log = get_logger(__name__)

# Weights for hybrid score: vector similarity vs. keyword match
VECTOR_WEIGHT = 0.7
KEYWORD_WEIGHT = 0.3
DEFAULT_TOP_K = 5


@dataclass
class RetrievedChunk:
    id: str
    title: str
    content: str
    category: str
    chunk_index: int
    vector_score: float
    keyword_score: float
    hybrid_score: float


async def hybrid_search(
    query: str,
    *,
    db: AsyncSession,
    category: str | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> list[RetrievedChunk]:
    """Hybrid search combining pgvector cosine similarity + PostgreSQL FTS.

    Algorithm:
    1. Embed the query with the same model used for ingestion.
    2. Run vector ANN search (top_k * 3 candidates) using <=> cosine distance.
    3. Run tsvector full-text search on the same candidate pool.
    4. Merge using: hybrid = VECTOR_WEIGHT * vec_sim + KEYWORD_WEIGHT * kw_sim
    5. Return top_k results sorted by hybrid score.

    The candidate expansion (top_k * 3) gives keyword ranking room to re-order
    results without requiring a separate expensive FTS scan.
    """
    query_vector = await embed_single(query)

    candidates = top_k * 3

    # ── Vector search ─────────────────────────────────────────────────────────
    # 1 - cosine_distance converts distance → similarity
    vector_subq = (
        select(
            KBDocument.id,
            KBDocument.title,
            KBDocument.content,
            KBDocument.category,
            KBDocument.chunk_index,
            (
                1 - KBDocument.embedding.cosine_distance(query_vector)
            ).label("vector_score"),
        )
        .order_by(KBDocument.embedding.cosine_distance(query_vector))
        .limit(candidates)
    )

    if category:
        vector_subq = vector_subq.where(KBDocument.category == category)

    vec_results = await db.execute(vector_subq)
    vec_rows = vec_results.mappings().all()

    if not vec_rows:
        return []

    # ── Keyword search via FTS ────────────────────────────────────────────────
    # ts_rank against a plainto_tsquery gives a normalised keyword relevance score
    candidate_ids = [r["id"] for r in vec_rows]
    fts_query = (
        select(
            KBDocument.id,
            func.ts_rank(
                func.to_tsvector("english", KBDocument.content),
                func.plainto_tsquery("english", query),
            ).label("keyword_score"),
        )
        .where(KBDocument.id.in_(candidate_ids))
    )
    fts_results = await db.execute(fts_query)
    keyword_map: dict = {str(r["id"]): float(r["keyword_score"]) for r in fts_results.mappings()}

    # ── Merge + rerank ─────────────────────────────────────────────────────────
    chunks: list[RetrievedChunk] = []
    for row in vec_rows:
        doc_id = str(row["id"])
        vec_score = float(row["vector_score"])
        kw_score = keyword_map.get(doc_id, 0.0)

        # Normalise keyword score (ts_rank is 0–1 range but can be > 1)
        kw_score_norm = min(kw_score, 1.0)

        hybrid = VECTOR_WEIGHT * vec_score + KEYWORD_WEIGHT * kw_score_norm

        chunks.append(
            RetrievedChunk(
                id=doc_id,
                title=row["title"],
                content=row["content"],
                category=row["category"],
                chunk_index=row["chunk_index"],
                vector_score=vec_score,
                keyword_score=kw_score_norm,
                hybrid_score=hybrid,
            )
        )

    # Sort by hybrid score descending
    chunks.sort(key=lambda c: c.hybrid_score, reverse=True)
    top = chunks[:top_k]

    log.debug(
        "Hybrid search complete",
        query=query[:80],
        category=category,
        top_k=top_k,
        results=len(top),
        top_score=top[0].hybrid_score if top else 0,
    )
    return top


def format_context(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks into a context string for the LLM prompt."""
    if not chunks:
        return "No relevant knowledge base articles found."

    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[{i}] **{chunk.title}** (category: {chunk.category})\n{chunk.content}"
        )
    return "\n\n---\n\n".join(parts)

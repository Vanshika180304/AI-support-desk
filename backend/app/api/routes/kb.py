from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin, get_current_user
from app.models.kb_document import KBDocument
from app.models.user import User
from app.rag.ingest import ingest_document
from app.schemas.ticket import KBDocumentCreateRequest, KBDocumentResponse

router = APIRouter()


@router.post(
    "/documents",
    response_model=list[KBDocumentResponse],
    status_code=201,
    summary="Ingest a new knowledge base document (admin only)",
)
async def ingest_kb_document(
    body: KBDocumentCreateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[KBDocument]:
    """Chunk, embed, and store a document in the knowledge base."""
    docs = await ingest_document(
        title=body.title,
        content=body.content,
        category=body.category,
        source_url=body.source_url,
        db=db,
    )
    return docs


@router.get(
    "/documents",
    response_model=list[KBDocumentResponse],
    summary="List all ingested knowledge base documents (one row per chunk)",
)
async def list_kb_documents(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[KBDocument]:
    query = select(KBDocument).order_by(KBDocument.created_at.desc(), KBDocument.chunk_index)
    if category:
        query = query.where(KBDocument.category == category)
    result = await db.execute(query)
    return list(result.scalars().all())

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.models.base import Base


class KBDocument(Base):
    __tablename__ = "kb_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Category scopes retrieval: billing | technical | general
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # pgvector column — 1536 dims matches text-embedding-3-small
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536), nullable=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        # IVFFlat index for fast approximate nearest-neighbour search
        # Created via Alembic migration after table creation
        Index(
            "ix_kb_documents_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<KBDocument id={self.id} title={self.title!r} "
            f"category={self.category} chunk={self.chunk_index}>"
        )

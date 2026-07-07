from __future__ import annotations

from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.retriever import format_context, hybrid_search


def make_kb_search_tool(db: AsyncSession, category: str | None = None):
    """Factory that returns a LangChain tool scoped to a DB session and category."""

    @tool
    async def kb_search(query: str) -> str:
        """Search the knowledge base for articles relevant to a support query.

        Args:
            query: The user's question or search terms.

        Returns:
            Formatted context string with the most relevant KB articles.
        """
        chunks = await hybrid_search(query, db=db, category=category, top_k=5)
        return format_context(chunks)

    return kb_search

from __future__ import annotations

from typing import Literal

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from app.core.config import get_settings

settings = get_settings()


class RouterOutput(BaseModel):
    """Structured output from the router agent."""
    category: Literal["billing", "technical", "general", "unclear"] = Field(
        description="The ticket category. Use 'unclear' only if the intent is truly ambiguous."
    )
    reasoning: str = Field(
        description="One sentence explaining why this category was chosen."
    )


ROUTER_SYSTEM_PROMPT = """You are a support ticket router for a SaaS company.
Your only job is to classify incoming support tickets into one of four categories:

- **billing**: questions about invoices, charges, refunds, plans, subscriptions, payment methods
- **technical**: questions about bugs, errors, setup, configuration, API issues, integrations
- **general**: account questions, feature requests, how-to questions not fitting billing or technical
- **unclear**: the message is spam, gibberish, or genuinely impossible to classify

Return ONLY the category and a one-sentence reasoning. Do not attempt to answer the ticket."""


async def run_router(subject: str, body: str) -> RouterOutput:
    """Classify a ticket into a routing category using structured LLM output."""
    llm = ChatGroq(
        model=settings.groq_chat_model,
        temperature=0,
        api_key=settings.groq_api_key,
    )
    structured_llm = llm.with_structured_output(RouterOutput)

    result = await structured_llm.ainvoke([
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": f"Subject: {subject}\n\n{body}"},
    ])
    return result

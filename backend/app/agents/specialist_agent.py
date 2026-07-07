from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from app.core.config import get_settings

settings = get_settings()


class SpecialistOutput(BaseModel):
    """Structured output from any specialist agent."""
    answer: str = Field(description="The full answer to the user's support question.")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description=(
            "Confidence score from 0 to 1 reflecting how certain you are this answer "
            "fully resolves the user's issue. Be honest: if you're guessing or the KB "
            "had no relevant articles, score below 0.6."
        ),
    )
    confidence_reasoning: str = Field(
        description="One sentence explaining your confidence level."
    )
    tool_calls_summary: list[str] = Field(
        default_factory=list,
        description="List of tool names called while generating this answer.",
    )


BILLING_SYSTEM_PROMPT = """You are a billing support specialist for a SaaS company.
You help customers with invoices, charges, refunds, subscriptions, and payment methods.

Guidelines:
- Always be empathetic and professional.
- Use the kb_search tool to find relevant billing policy articles before answering.
- Use the billing_lookup tool if the user mentions a specific account, charge, or invoice.
- If you cannot find enough information to answer confidently, say so and set confidence below 0.6.
- Do NOT make up billing policies — rely on the knowledge base.
- Keep answers concise (under 200 words) and actionable."""

TECHNICAL_SYSTEM_PROMPT = """You are a technical support specialist for a SaaS company.
You help customers with bugs, errors, API issues, integrations, and configuration problems.

Guidelines:
- Use the kb_search tool first to find relevant troubleshooting guides.
- Use the order_lookup tool if the customer references an order or subscription change.
- Provide step-by-step instructions where possible.
- If the issue is a known bug with no workaround, acknowledge it and set confidence below 0.6.
- Do NOT invent troubleshooting steps — rely on the knowledge base.
- Keep answers clear and technical (it's OK to use technical terms)."""

GENERAL_SYSTEM_PROMPT = """You are a general support specialist for a SaaS company.
You help customers with account questions, how-to guides, and feature questions.

Guidelines:
- Use kb_search to find relevant help articles.
- Be friendly and encouraging.
- If you don't know something, admit it and set confidence below 0.6.
- Keep answers helpful and under 200 words."""


async def run_specialist(
    *,
    category: str,
    subject: str,
    body: str,
    tools: list,
) -> SpecialistOutput:
    """Run the appropriate specialist agent for a given category."""
    system_prompts = {
        "billing": BILLING_SYSTEM_PROMPT,
        "technical": TECHNICAL_SYSTEM_PROMPT,
        "general": GENERAL_SYSTEM_PROMPT,
    }
    system_prompt = system_prompts.get(category, GENERAL_SYSTEM_PROMPT)

    llm = ChatGroq(
        model=settings.groq_chat_model,
        temperature=0.2,
        api_key=settings.groq_api_key,
    )

    # Bind tools so the LLM can call kb_search, billing_lookup, etc.
    llm_with_tools = llm.bind_tools(tools)
    structured_llm = llm.with_structured_output(SpecialistOutput)

    # First pass: let the model use tools
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Subject: {subject}\n\nMessage: {body}"),
    ]

    tool_calls_made: list[str] = []

    # Agentic tool-use loop (max 3 rounds to prevent runaway calls)
    for _ in range(3):
        response = await llm_with_tools.ainvoke(messages)
        if not response.tool_calls:
            break

        messages.append(response)
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_calls_made.append(tool_name)

            # Find and invoke the matching tool
            matching_tool = next((t for t in tools if t.name == tool_name), None)
            if matching_tool:
                tool_result = await matching_tool.ainvoke(tool_call["args"])
                from langchain_core.messages import ToolMessage
                messages.append(
                    ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"])
                )

    # Final structured output pass
    messages_for_output = messages + [
        HumanMessage(
            content=(
                "Based on the above conversation and tool results, provide your final "
                "structured answer with confidence score."
            )
        )
    ]
    result = await structured_llm.ainvoke(messages_for_output)
    result.tool_calls_summary = tool_calls_made
    return result

"""Tests for routing logic and escalation trigger."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.router_agent import RouterOutput


async def test_router_billing_classification() -> None:
    """Router should classify billing tickets correctly."""
    mock_result = RouterOutput(category="billing", reasoning="Invoice question")

    with patch("app.agents.router_agent.ChatOpenAI") as mock_llm_cls:
        mock_llm = AsyncMock()
        mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
            return_value=mock_result
        )
        mock_llm_cls.return_value = mock_llm

        from app.agents.router_agent import run_router
        result = await run_router(
            subject="I was charged twice",
            body="I see two charges on my credit card for $29 this month.",
        )

    assert result.category == "billing"


async def test_router_technical_classification() -> None:
    mock_result = RouterOutput(category="technical", reasoning="API error")

    with patch("app.agents.router_agent.ChatOpenAI") as mock_llm_cls:
        mock_llm = AsyncMock()
        mock_llm.with_structured_output.return_value.ainvoke = AsyncMock(
            return_value=mock_result
        )
        mock_llm_cls.return_value = mock_llm

        from app.agents.router_agent import run_router
        result = await run_router(
            subject="API returns 401",
            body="Every API request returns 401 Unauthorized.",
        )

    assert result.category == "technical"


async def test_router_unclear_triggers_escalation() -> None:
    """Tickets classified as 'unclear' should be escalated in the graph."""
    from app.agents.graph import route_after_router, AgentState

    state: AgentState = {
        "ticket_id": "test-id",
        "subject": "asdf",
        "body": "asdf asdf",
        "category": "unclear",
        "router_reasoning": "Spam",
        "answer": "",
        "confidence": 0.0,
        "confidence_reasoning": "",
        "tool_calls_summary": [],
        "escalated": False,
        "escalation_reason": "",
        "agent_runs": [],
        "db": None,
    }

    decision = route_after_router(state)
    assert decision == "escalation"


async def test_low_confidence_triggers_escalation() -> None:
    """Confidence below threshold should route to escalation."""
    from app.agents.graph import route_after_specialist, AgentState
    from app.core.config import get_settings

    settings = get_settings()

    state: AgentState = {
        "ticket_id": "test-id",
        "subject": "Complex issue",
        "body": "...",
        "category": "technical",
        "router_reasoning": "Technical",
        "answer": "I'm not sure about this.",
        "confidence": settings.confidence_threshold - 0.01,  # Just below threshold
        "confidence_reasoning": "Not enough info",
        "tool_calls_summary": [],
        "escalated": False,
        "escalation_reason": "",
        "agent_runs": [],
        "db": None,
    }

    decision = route_after_specialist(state)
    assert decision == "escalation"


async def test_high_confidence_returns_answer() -> None:
    """Confidence above threshold should route to END."""
    from app.agents.graph import route_after_specialist, AgentState
    from app.core.config import get_settings

    settings = get_settings()

    state: AgentState = {
        "ticket_id": "test-id",
        "subject": "Simple billing question",
        "body": "How do I update my card?",
        "category": "billing",
        "router_reasoning": "Billing",
        "answer": "Go to Settings > Billing > Payment Methods.",
        "confidence": settings.confidence_threshold + 0.1,  # Above threshold
        "confidence_reasoning": "Clear answer found in KB",
        "tool_calls_summary": ["kb_search"],
        "escalated": False,
        "escalation_reason": "",
        "agent_runs": [],
        "db": None,
    }

    decision = route_after_specialist(state)
    assert decision == "end"

from __future__ import annotations

import time
import uuid
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
log = get_logger(__name__)


# ── Graph State ───────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    """Shared state that flows through every node of the graph."""
    # Input
    ticket_id: str
    subject: str
    body: str

    # Router output
    category: str  # billing | technical | general | unclear
    router_reasoning: str

    # Specialist output
    answer: str
    confidence: float
    confidence_reasoning: str
    tool_calls_summary: list[str]

    # Escalation
    escalated: bool
    escalation_reason: str

    # Audit
    agent_runs: list[dict[str, Any]]  # accumulated run records

    # DB session (injected at runtime, not serialised)
    db: Any


# ── Node implementations ──────────────────────────────────────────────────────

async def router_node(state: AgentState) -> dict:
    """Classify the ticket and update state with category."""
    t0 = time.monotonic()
    from app.agents.router_agent import run_router

    log.info("Router node", ticket_id=state["ticket_id"])
    result = await run_router(subject=state["subject"], body=state["body"])
    latency_ms = int((time.monotonic() - t0) * 1000)

    run_record = {
        "id": str(uuid.uuid4()),
        "ticket_id": state["ticket_id"],
        "agent_name": "router",
        "input": f"{state['subject']}\n{state['body']}",
        "output": f"category={result.category} | {result.reasoning}",
        "confidence": None,
        "tool_calls": [],
        "latency_ms": latency_ms,
    }

    return {
        "category": result.category,
        "router_reasoning": result.reasoning,
        "agent_runs": state.get("agent_runs", []) + [run_record],
    }


async def specialist_node(state: AgentState) -> dict:
    """Run the appropriate specialist agent and return its answer."""
    t0 = time.monotonic()
    from app.agents.specialist_agent import run_specialist
    from app.agents.tools.kb_search import make_kb_search_tool
    from app.agents.tools.billing_lookup import billing_lookup
    from app.agents.tools.order_lookup import order_lookup

    category = state["category"]
    db = state.get("db")

    log.info("Specialist node", category=category, ticket_id=state["ticket_id"])

    # Build tool list scoped to this category
    tools = [make_kb_search_tool(db, category=category)]
    if category == "billing":
        tools.append(billing_lookup)
    elif category == "technical":
        tools.append(order_lookup)

    result = await run_specialist(
        category=category,
        subject=state["subject"],
        body=state["body"],
        tools=tools,
    )
    latency_ms = int((time.monotonic() - t0) * 1000)

    run_record = {
        "id": str(uuid.uuid4()),
        "ticket_id": state["ticket_id"],
        "agent_name": f"{category}_specialist",
        "input": f"{state['subject']}\n{state['body']}",
        "output": result.answer,
        "confidence": result.confidence,
        "tool_calls": result.tool_calls_summary,
        "latency_ms": latency_ms,
    }

    return {
        "answer": result.answer,
        "confidence": result.confidence,
        "confidence_reasoning": result.confidence_reasoning,
        "tool_calls_summary": result.tool_calls_summary,
        "agent_runs": state.get("agent_runs", []) + [run_record],
    }


async def escalation_node(state: AgentState) -> dict:
    """Mark ticket as escalated; record the reason."""
    log.info(
        "Escalation node",
        ticket_id=state["ticket_id"],
        confidence=state.get("confidence"),
        category=state.get("category"),
    )

    if state.get("category") == "unclear":
        reason = f"Router classified ticket as 'unclear': {state.get('router_reasoning', '')}"
    else:
        reason = (
            f"Confidence {state.get('confidence', 0):.2f} below threshold "
            f"{settings.confidence_threshold}. Reason: {state.get('confidence_reasoning', '')}"
        )

    run_record = {
        "id": str(uuid.uuid4()),
        "ticket_id": state["ticket_id"],
        "agent_name": "escalation",
        "input": None,
        "output": reason,
        "confidence": state.get("confidence"),
        "tool_calls": [],
        "latency_ms": 0,
    }

    return {
        "escalated": True,
        "escalation_reason": reason,
        "agent_runs": state.get("agent_runs", []) + [run_record],
    }


# ── Routing edges ─────────────────────────────────────────────────────────────

def route_after_router(state: AgentState) -> Literal["specialist", "escalation"]:
    """Route to specialist or immediately escalate if category is unclear."""
    if state["category"] == "unclear":
        return "escalation"
    return "specialist"


def route_after_specialist(state: AgentState) -> Literal["end", "escalation"]:
    """Escalate if confidence is below threshold, otherwise finish."""
    confidence = state.get("confidence", 0.0)
    if confidence < settings.confidence_threshold:
        return "escalation"
    return "end"


# ── Build the graph ───────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("specialist", specialist_node)
    graph.add_node("escalation", escalation_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", route_after_router)
    graph.add_conditional_edges(
        "specialist",
        route_after_specialist,
        {"end": END, "escalation": "escalation"},
    )
    graph.add_edge("escalation", END)

    return graph.compile()


# Singleton compiled graph
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


async def run_agent_pipeline(
    *,
    ticket_id: str,
    subject: str,
    body: str,
    db,
) -> AgentState:
    """Run the full triage pipeline for a ticket.

    Returns the final AgentState with all outputs and audit records.
    """
    graph = get_graph()

    initial_state: AgentState = {
        "ticket_id": ticket_id,
        "subject": subject,
        "body": body,
        "category": "unclassified",
        "router_reasoning": "",
        "answer": "",
        "confidence": 0.0,
        "confidence_reasoning": "",
        "tool_calls_summary": [],
        "escalated": False,
        "escalation_reason": "",
        "agent_runs": [],
        "db": db,
    }

    final_state = await graph.ainvoke(initial_state)
    return final_state

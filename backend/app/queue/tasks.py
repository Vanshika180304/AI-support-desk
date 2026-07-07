from __future__ import annotations

import asyncio
import uuid

from celery import Celery
from celery.utils.log import get_task_logger

from app.core.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "support_desk",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,          # ack after completion so retries work on crash
    task_reject_on_worker_lost=True,
    task_max_retries=3,
    task_default_retry_delay=60,  # seconds between retries
    worker_prefetch_multiplier=1, # fair dispatch for long-running LLM tasks
    result_expires=86400,         # 1 day
)

logger = get_task_logger(__name__)


@celery_app.task(
    name="process_ticket",
    queue="tickets",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=120,  # 2 min soft limit
    time_limit=150,       # 2.5 min hard limit
)
def process_ticket(self, ticket_id: str) -> dict:
    """Process a support ticket through the LangGraph agent pipeline.

    This task:
    1. Loads the ticket from DB
    2. Runs the full agent graph (router → specialist → [escalation])
    3. Persists all agent_runs to DB
    4. Updates ticket status and answer message
    """
    logger.info(f"Processing ticket {ticket_id}")

    async def _run():
        from sqlalchemy import select

        from app.agents.graph import run_agent_pipeline
        from app.db.session import AsyncSessionLocal
        from app.models.agent_run import AgentRun
        from app.models.message import Message
        from app.models.ticket import Ticket

        async with AsyncSessionLocal() as db:
            # Load ticket
            result = await db.execute(
                select(Ticket).where(Ticket.id == uuid.UUID(ticket_id))
            )
            ticket = result.scalar_one_or_none()
            if not ticket:
                logger.error(f"Ticket {ticket_id} not found — skipping")
                return {"status": "not_found"}

            # Update status to 'routed' immediately
            ticket.status = "routed"
            await db.commit()

            try:
                # Run the agent pipeline
                final_state = await run_agent_pipeline(
                    ticket_id=ticket_id,
                    subject=ticket.subject,
                    body=ticket.body,
                    db=db,
                )

                # Persist all agent run records
                for run_data in final_state.get("agent_runs", []):
                    agent_run = AgentRun(
                        id=uuid.UUID(run_data["id"]),
                        ticket_id=ticket.id,
                        agent_name=run_data["agent_name"],
                        input=run_data.get("input"),
                        output=run_data.get("output"),
                        confidence=run_data.get("confidence"),
                        tool_calls={"calls": run_data.get("tool_calls", [])},
                        latency_ms=run_data.get("latency_ms"),
                    )
                    db.add(agent_run)

                # Update ticket based on outcome
                ticket.category = final_state["category"]
                ticket.confidence_score = final_state.get("confidence")

                if final_state.get("escalated"):
                    ticket.status = "escalated"
                    # Add escalation message
                    reason = final_state.get("escalation_reason", "Escalated to human review.")
                    db.add(Message(
                        ticket_id=ticket.id,
                        sender="agent",
                        content=f"[Escalated] {reason}",
                    ))
                else:
                    ticket.status = "answered"
                    answer = final_state.get("answer", "")
                    db.add(Message(
                        ticket_id=ticket.id,
                        sender="agent",
                        content=answer,
                    ))

                await db.commit()
                logger.info(
                    f"Ticket {ticket_id} processed",
                    extra={
                        "status": ticket.status,
                        "category": ticket.category,
                        "confidence": ticket.confidence_score,
                    },
                )
                return {
                    "status": ticket.status,
                    "category": ticket.category,
                    "confidence": ticket.confidence_score,
                }

            except Exception as exc:
                # On failure, mark as open again so it can be retried
                ticket.status = "open"
                await db.commit()
                raise exc

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.exception(f"Failed to process ticket {ticket_id}: {exc}")
        raise self.retry(exc=exc)

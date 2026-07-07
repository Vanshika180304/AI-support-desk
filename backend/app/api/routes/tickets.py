from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.message import Message
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import (
    PaginatedTickets,
    TicketCreateRequest,
    TicketResponse,
    TicketSummary,
)

router = APIRouter()


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a support ticket (async processing)",
)
async def create_ticket(
    body: TicketCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Ticket:
    # Create ticket record
    ticket = Ticket(
        user_id=current_user.id,
        subject=body.subject,
        body=body.body,
        status="open",
        category="unclassified",
    )
    db.add(ticket)

    # Store the initial user message in thread
    msg = Message(
        ticket_id=ticket.id,
        sender="user",
        content=body.body,
    )
    db.add(msg)

    await db.commit()
    await db.refresh(ticket)

    # Enqueue for async agent processing
    try:
        from app.queue.tasks import process_ticket
        process_ticket.apply_async(
            args=[str(ticket.id)],
            queue="tickets",
            countdown=0,
        )
    except Exception:  # noqa: BLE001
        # Queue unavailable — ticket is still persisted, will be processed later
        pass

    return ticket


@router.get(
    "",
    response_model=PaginatedTickets,
    summary="List tickets (paginated, filterable by status/category)",
)
async def list_tickets(
    status_filter: str | None = Query(None, alias="status"),
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedTickets:
    query = select(Ticket)

    # Non-admins only see their own tickets
    if current_user.role not in ("admin", "agent"):
        query = query.where(Ticket.user_id == current_user.id)

    if status_filter:
        query = query.where(Ticket.status == status_filter)
    if category:
        query = query.where(Ticket.category == category)

    # Total count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    # Paginated results
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Ticket.created_at.desc()).offset(offset).limit(page_size)
    )
    tickets = result.scalars().all()

    return PaginatedTickets(
        items=[TicketSummary.model_validate(t) for t in tickets],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Get ticket details with full message thread and agent run audit",
)
async def get_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Ticket:
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    # Customers can only see their own tickets
    if current_user.role == "customer" and ticket.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return ticket


@router.post(
    "/{ticket_id}/escalate",
    response_model=TicketResponse,
    summary="Manually escalate a ticket to human review",
)
async def escalate_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Ticket:
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    if current_user.role == "customer" and ticket.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if ticket.status in ("closed",):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot escalate ticket with status '{ticket.status}'",
        )

    ticket.status = "escalated"
    escalation_msg = Message(
        ticket_id=ticket.id,
        sender="human",
        content="Ticket manually escalated to human review.",
    )
    db.add(escalation_msg)
    await db.commit()
    await db.refresh(ticket)
    return ticket

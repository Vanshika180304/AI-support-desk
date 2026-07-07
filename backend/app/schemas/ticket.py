from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Request schemas ───────────────────────────────────────────────────────────

class TicketCreateRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=500)
    body: str = Field(min_length=10, max_length=10_000)


class TicketListParams(BaseModel):
    status: str | None = None
    category: str | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


# ── Response schemas ──────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    id: uuid.UUID
    sender: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentRunSummary(BaseModel):
    id: uuid.UUID
    agent_name: str
    confidence: float | None
    latency_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketResponse(BaseModel):
    id: uuid.UUID
    subject: str
    body: str
    status: str
    category: str
    confidence_score: float | None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []
    agent_runs: list[AgentRunSummary] = []

    model_config = {"from_attributes": True}


class TicketSummary(BaseModel):
    id: uuid.UUID
    subject: str
    status: str
    category: str
    confidence_score: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedTickets(BaseModel):
    items: list[TicketSummary]
    total: int
    page: int
    page_size: int
    pages: int


# ── KB document schemas ───────────────────────────────────────────────────────

class KBDocumentCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=500)
    content: str = Field(min_length=10)
    category: str = Field(pattern="^(billing|technical|general)$")
    source_url: str | None = None


class KBDocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    category: str
    source_url: str | None
    chunk_index: int
    created_at: datetime

    model_config = {"from_attributes": True}

"""Import all models here so Alembic's autogenerate can discover them."""

from app.models.base import Base
from app.models.user import User
from app.models.ticket import Ticket
from app.models.message import Message
from app.models.kb_document import KBDocument
from app.models.agent_run import AgentRun

__all__ = ["Base", "User", "Ticket", "Message", "KBDocument", "AgentRun"]

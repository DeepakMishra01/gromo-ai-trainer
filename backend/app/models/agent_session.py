import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.compat import PortableUUID, PortableJSON
from app.database import Base


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    conversation_log: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    product_ids: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(PortableUUID, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

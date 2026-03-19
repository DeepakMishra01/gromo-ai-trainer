import uuid
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.compat import PortableUUID, PortableJSON
from app.database import Base


class Difficulty(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class RoleplaySession(Base):
    __tablename__ = "roleplay_sessions"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(PortableUUID, ForeignKey("products.id"), nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(String(50), nullable=False)
    conversation_log: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    skill_scores: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(PortableUUID, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

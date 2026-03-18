import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.compat import PortableUUID
from app.database import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    video_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(PortableUUID, ForeignKey("video_jobs.id"), nullable=True)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(PortableUUID, ForeignKey("products.id"), nullable=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    # embedding column will be added via pgvector extension when needed
    timestamp_start: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    timestamp_end: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

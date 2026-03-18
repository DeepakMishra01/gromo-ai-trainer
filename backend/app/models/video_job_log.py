import uuid
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.compat import PortableUUID
from app.database import Base


class LogStatus(str, enum.Enum):
    started = "started"
    completed = "completed"
    failed = "failed"


class VideoJobLog(Base):
    __tablename__ = "video_job_logs"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    video_job_id: Mapped[uuid.UUID] = mapped_column(PortableUUID, ForeignKey("video_jobs.id"), nullable=False)
    step: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[LogStatus] = mapped_column(String(50), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    video_job = relationship("VideoJob", back_populates="logs")

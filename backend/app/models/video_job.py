import uuid
import enum
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.compat import PortableUUID, PortableJSON
from app.database import Base


class JobType(str, enum.Enum):
    single_product = "single_product"
    category_overview = "category_overview"
    comparison = "comparison"
    ppt_mode = "ppt_mode"
    gamma_ppt = "gamma_ppt"


class JobStatus(str, enum.Enum):
    queued = "queued"
    generating_ppt = "generating_ppt"
    generating_script = "generating_script"
    generating_audio = "generating_audio"
    generating_avatar = "generating_avatar"
    compositing = "compositing"
    completed = "completed"
    failed = "failed"


class VideoJob(Base):
    __tablename__ = "video_jobs"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    job_type: Mapped[JobType] = mapped_column(String(50), nullable=False)
    product_ids: Mapped[Optional[list]] = mapped_column(PortableJSON, nullable=True)
    avatar_id: Mapped[Optional[uuid.UUID]] = mapped_column(PortableUUID, ForeignKey("avatars.id"), nullable=True)
    voice_id: Mapped[Optional[uuid.UUID]] = mapped_column(PortableUUID, ForeignKey("voices.id"), nullable=True)
    language: Mapped[str] = mapped_column(String(50), default="hinglish")
    target_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[JobStatus] = mapped_column(String(50), default=JobStatus.queued)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    script_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    video_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ppt_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    gamma_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    avatar = relationship("Avatar", lazy="joined")
    voice = relationship("Voice", lazy="joined")
    logs = relationship("VideoJobLog", back_populates="video_job", cascade="all, delete-orphan")

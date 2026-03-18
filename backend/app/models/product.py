import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.compat import PortableUUID, PortableJSON
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(PortableUUID, primary_key=True, default=uuid.uuid4)
    category_id: Mapped[uuid.UUID] = mapped_column(PortableUUID, ForeignKey("categories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    gromo_product_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)

    # Real GroMo API fields
    payout: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sub_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    benefits_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    how_works_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    terms_conditions_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Cleaned plain-text versions (for AI grounding)
    benefits_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    how_works_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    terms_conditions_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Legacy fields (kept for backward compatibility)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    features: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    eligibility: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    fees: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    benefits: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    faqs: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)
    raw_data: Mapped[Optional[dict]] = mapped_column(PortableJSON, nullable=True)

    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    category = relationship("Category", back_populates="products")

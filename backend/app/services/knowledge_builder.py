"""
Knowledge Base Builder Service.
Builds structured knowledge text documents from REAL GroMo product data.
This knowledge text is used as grounding context for AI (training, doubt resolution,
video scripts, roleplay) to prevent hallucination.
"""
import logging
import uuid
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)


def build_knowledge_base(product_id: str, db: Session) -> str:
    """
    Fetch product from DB with all details and build a structured knowledge text document.
    Uses ONLY real data from the GroMo API — no fabricated content.
    """
    product = db.query(Product).filter(Product.id == uuid.UUID(str(product_id))).first()
    if not product:
        raise ValueError(f"Product not found: {product_id}")

    knowledge_text = _build_knowledge_text(product)

    # Store in knowledge_bases table
    kb_entry = KnowledgeBase(
        product_id=product.id,
        chunk_text=knowledge_text,
    )
    db.add(kb_entry)
    db.commit()

    logger.info(f"Built knowledge base for product: {product.name} ({product_id})")
    return knowledge_text


def get_knowledge_for_product(product_id: str, db: Session) -> Optional[str]:
    """
    Retrieve existing knowledge base text for a product.
    If not exists, builds it automatically from real product data.
    """
    pid = uuid.UUID(str(product_id))

    # Check for existing knowledge base entry
    existing = (
        db.query(KnowledgeBase)
        .filter(KnowledgeBase.product_id == pid)
        .order_by(KnowledgeBase.created_at.desc())
        .first()
    )

    if existing:
        return existing.chunk_text

    # Build automatically if not exists
    try:
        return build_knowledge_base(product_id, db)
    except ValueError:
        return None


def _build_knowledge_text(product: Product) -> str:
    """
    Build a structured knowledge text document from a Product model instance.
    Uses real GroMo API fields: benefits, howWorks, tc (terms & conditions).
    IMPORTANT: Only uses data that exists in the DB — never fabricates information.
    """
    sections = []

    # Header
    sections.append(f"=== PRODUCT: {product.name} ===")
    sections.append(f"Category: {product.sub_type or 'Financial Product'}")
    if product.payout:
        sections.append(f"Partner Payout: {product.payout}")
    sections.append("")

    # Benefits (from real GroMo data)
    sections.append("## Product Benefits & Features")
    if product.benefits_text:
        sections.append(product.benefits_text)
    else:
        sections.append("No benefits information available from GroMo.")
    sections.append("")

    # How It Works (from real GroMo data)
    sections.append("## How It Works (Sales Process)")
    if product.how_works_text:
        sections.append(product.how_works_text)
    else:
        sections.append("No process information available from GroMo.")
    sections.append("")

    # Terms & Conditions (from real GroMo data)
    sections.append("## Terms & Conditions (Payout Rules)")
    if product.terms_conditions_text:
        sections.append(product.terms_conditions_text)
    else:
        sections.append("No terms & conditions available from GroMo.")
    sections.append("")

    # Grounding instruction for AI
    sections.append("## IMPORTANT GROUNDING RULES")
    sections.append(
        "ONLY use the information provided above when answering questions. "
        "Do NOT fabricate, assume, or hallucinate any details about this product. "
        "If information is not available above, say 'This information is not available "
        "in our current product data. Please check the GroMo app for the latest details.'"
    )

    return "\n".join(sections)

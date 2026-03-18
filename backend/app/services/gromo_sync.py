"""
GroMo API sync service.
Connects to real GroMo API, fetches products, categorizes by subType, and syncs to DB.
"""
import re
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.category import Category
from app.models.product import Product

logger = logging.getLogger(__name__)

# Insurance-related keywords for exclusion
INSURANCE_KEYWORDS = [
    "insurance", "bima", "life cover", "health cover", "term plan",
    "life insurance", "health insurance", "motor insurance", "travel insurance",
    "accident cover", "critical illness", "endowment", "ulip",
]


def is_insurance_category(name: str) -> bool:
    """Check if a category name matches insurance-related keywords."""
    name_lower = name.lower().strip()
    excluded = settings.excluded_categories_list
    for keyword in INSURANCE_KEYWORDS + excluded:
        if keyword in name_lower:
            return True
    return False


def strip_html(html: str) -> str:
    """Convert HTML to clean plain text for AI consumption."""
    if not html:
        return ""
    # Replace <br>, <br/>, <br /> with newlines
    text = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    # Remove all remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode common HTML entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&nbsp;', ' ').replace('&#39;', "'").replace('&quot;', '"')
    # Clean up extra whitespace
    lines = [line.strip() for line in text.split('\n')]
    lines = [line for line in lines if line]
    return '\n'.join(lines)


async def fetch_from_gromo_api() -> List[Dict]:
    """Fetch products from GroMo API using POST with clientid/secretkey."""
    if not settings.gromo_api_client_id or not settings.gromo_api_secret_key:
        raise ValueError("GroMo API credentials not configured (GROMO_API_CLIENT_ID and GROMO_API_SECRET_KEY)")

    headers = {
        "clientid": settings.gromo_api_client_id,
        "secretkey": settings.gromo_api_secret_key,
        "Content-Type": "application/json",
    }

    payload = {"gpuid": settings.gromo_api_gpuid}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.gromo_api_base_url}/api/v5/productsForGp",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    products = data.get("products", [])
    logger.info(f"Fetched {len(products)} products from GroMo API")
    return products


def sync_to_database(
    db: Session,
    products_data: List[Dict],
) -> Dict[str, int]:
    """Sync fetched products to database, grouping by subType as categories."""
    now = datetime.utcnow()
    stats = {
        "categories_synced": 0,
        "categories_excluded": 0,
        "products_synced": 0,
        "products_excluded": 0,
    }

    # Group products by subType to create categories
    category_map: Dict[str, Category] = {}

    # First pass: create/update categories from subTypes
    sub_types = set(p.get("subType", "Other") for p in products_data)

    for sub_type in sub_types:
        excluded = is_insurance_category(sub_type)

        if excluded:
            stats["categories_excluded"] += 1

        # Upsert category by gromo_category_id = subType
        existing = db.query(Category).filter(Category.gromo_category_id == sub_type).first()
        if existing:
            existing.name = sub_type
            existing.is_excluded = excluded
            existing.synced_at = now
            category_map[sub_type] = existing
        else:
            new_cat = Category(
                name=sub_type,
                gromo_category_id=sub_type,
                is_excluded=excluded,
                synced_at=now,
            )
            db.add(new_cat)
            db.flush()
            category_map[sub_type] = new_cat

        if not excluded:
            stats["categories_synced"] += 1

    # Second pass: sync products
    for prod_data in products_data:
        prod_name = prod_data.get("name", "Unknown Product")
        sub_type = prod_data.get("subType", "Other")
        cat = category_map.get(sub_type)

        if not cat or cat.is_excluded:
            stats["products_excluded"] += 1
            continue

        # Extract and clean HTML fields
        benefits_html = prod_data.get("benefits", "")
        how_works_html = prod_data.get("howWorks", "")
        tc_html = prod_data.get("tc", "")
        payout = prod_data.get("payout", "")

        benefits_text = strip_html(benefits_html)
        how_works_text = strip_html(how_works_html)
        tc_text = strip_html(tc_html)

        # Use product name as unique ID (no separate ID from API)
        gromo_pid = prod_name.strip()

        # Upsert product
        existing = db.query(Product).filter(Product.gromo_product_id == gromo_pid).first()

        if existing:
            existing.name = prod_name
            existing.category_id = cat.id
            existing.payout = payout
            existing.sub_type = sub_type
            existing.benefits_html = benefits_html
            existing.how_works_html = how_works_html
            existing.terms_conditions_html = tc_html
            existing.benefits_text = benefits_text
            existing.how_works_text = how_works_text
            existing.terms_conditions_text = tc_text
            existing.description = benefits_text[:500] if benefits_text else None
            existing.raw_data = prod_data
            existing.synced_at = now
        else:
            new_prod = Product(
                name=prod_name,
                category_id=cat.id,
                gromo_product_id=gromo_pid,
                payout=payout,
                sub_type=sub_type,
                benefits_html=benefits_html,
                how_works_html=how_works_html,
                terms_conditions_html=tc_html,
                benefits_text=benefits_text,
                how_works_text=how_works_text,
                terms_conditions_text=tc_text,
                description=benefits_text[:500] if benefits_text else None,
                raw_data=prod_data,
                synced_at=now,
            )
            db.add(new_prod)

        stats["products_synced"] += 1

    db.commit()
    return stats


async def run_sync(db: Session, use_demo: bool = False) -> Dict[str, Any]:
    """Run the full sync pipeline."""
    try:
        if use_demo or (not settings.gromo_api_client_id and not settings.gromo_api_secret_key):
            logger.info("Using demo data (no API credentials configured)")
            products_data = _get_demo_data()
            source = "demo"
        else:
            logger.info("Fetching from GroMo API (live)")
            products_data = await fetch_from_gromo_api()
            source = "api"

        stats = sync_to_database(db, products_data)

        return {
            "status": "completed",
            "source": source,
            **stats,
            "message": (
                f"Synced {stats['products_synced']} products across "
                f"{stats['categories_synced']} categories. "
                f"Excluded {stats['categories_excluded']} insurance categories "
                f"and {stats['products_excluded']} insurance products."
            ),
        }
    except httpx.HTTPStatusError as e:
        logger.error(f"GroMo API error: {e}")
        return {"status": "failed", "message": f"API error: {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Sync error: {e}")
        return {"status": "failed", "message": str(e)}


def _get_demo_data() -> List[Dict]:
    """Fallback demo data in the same format as the real API."""
    return [
        {
            "name": "HDFC Regalia Credit Card",
            "payout": "Rs 1200",
            "subType": "Credit Card",
            "benefits": "Premium credit card with airport lounge access.<br>4 complimentary lounge visits per quarter.<br>2X reward points on travel & dining.",
            "howWorks": "1. Share the link with customers.<br>2. Customer applies online.<br>3. You earn payout on approval.",
            "tc": "Annual fee Rs 2,500 (waived on Rs 3L+ spend).<br>Min income Rs 12 lakh/year.<br>CIBIL 750+.",
        },
        {
            "name": "Bajaj Finserv Personal Loan",
            "payout": "Rs 800",
            "subType": "Personal Loan",
            "benefits": "Instant loan up to Rs 40 lakh.<br>Quick disbursal within 24 hours.<br>No collateral required.",
            "howWorks": "1. Customer fills basic details.<br>2. E-KYC verification.<br>3. Loan disbursed to account.",
            "tc": "Interest from 11% p.a.<br>Processing fee up to 3.54%.<br>Min salary Rs 25,000/month.",
        },
    ]

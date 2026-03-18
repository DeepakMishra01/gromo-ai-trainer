import asyncio
import logging
from app.tasks.video_tasks import celery_app
from app.database import SessionLocal
from app.services.gromo_sync import run_sync

logger = logging.getLogger(__name__)


@celery_app.task(name="sync_gromo_products")
def sync_gromo_products():
    """Scheduled task to sync products from GroMo API.
    Falls back to demo data when API key is not configured.
    """
    db = SessionLocal()
    try:
        result = asyncio.get_event_loop().run_until_complete(run_sync(db))
        logger.info(
            f"Sync completed: {result.get('products_synced', 0)} products, "
            f"{result.get('categories_synced', 0)} categories"
        )
        return result
    except Exception as e:
        logger.error(f"Sync task failed: {e}")
        raise
    finally:
        db.close()

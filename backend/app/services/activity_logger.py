"""Simple activity logging for analytics."""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog

logger = logging.getLogger(__name__)


def log_activity(db: Session, user_id, action: str, metadata: Optional[dict] = None):
    """Log a user activity. Fire-and-forget — never raises."""
    try:
        entry = ActivityLog(user_id=user_id, action=action, metadata_json=metadata)
        db.add(entry)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log activity: {e}")
        try:
            db.rollback()
        except Exception:
            pass

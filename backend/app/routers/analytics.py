"""Analytics router — admin-only usage stats."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_admin
from app.models.user import User
from app.models.activity_log import ActivityLog
from app.models.roleplay_session import RoleplaySession
from app.models.agent_session import AgentSession
from app.models.video_job import VideoJob

router = APIRouter(
    prefix="/api/analytics",
    tags=["analytics"],
    dependencies=[Depends(require_admin)],
)


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    """High-level stats."""
    total_users = db.query(User).count()

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    active_7d = db.query(func.count(func.distinct(ActivityLog.user_id))).filter(
        ActivityLog.created_at >= seven_days_ago
    ).scalar() or 0

    total_roleplay = db.query(RoleplaySession).count()
    total_sahayak = db.query(AgentSession).count()
    total_videos = db.query(VideoJob).count()

    return {
        "total_users": total_users,
        "active_users_7d": active_7d,
        "total_roleplay_sessions": total_roleplay,
        "total_sahayak_chats": total_sahayak,
        "total_videos_created": total_videos,
    }


@router.get("/feature-usage")
def feature_usage(db: Session = Depends(get_db)):
    """Usage counts per feature."""
    results = (
        db.query(
            ActivityLog.action,
            func.count(ActivityLog.id).label("count"),
            func.count(func.distinct(ActivityLog.user_id)).label("unique_users"),
        )
        .group_by(ActivityLog.action)
        .order_by(func.count(ActivityLog.id).desc())
        .all()
    )
    return [
        {"feature": r.action, "count": r.count, "unique_users": r.unique_users}
        for r in results
    ]


@router.get("/users")
def user_list(db: Session = Depends(get_db)):
    """List all users with usage stats."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    result = []
    for u in users:
        activity_count = db.query(ActivityLog).filter(ActivityLog.user_id == u.id).count()
        roleplay_count = db.query(RoleplaySession).filter(
            RoleplaySession.user_id == u.id
        ).count() if hasattr(RoleplaySession, 'user_id') else 0
        sahayak_count = db.query(AgentSession).filter(
            AgentSession.user_id == u.id
        ).count() if hasattr(AgentSession, 'user_id') else 0

        result.append({
            "id": str(u.id),
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "activity_count": activity_count,
            "roleplay_count": roleplay_count,
            "sahayak_count": sahayak_count,
        })
    return result


@router.get("/activity")
def daily_activity(days: int = 30, db: Session = Depends(get_db)):
    """Daily activity counts for charting."""
    since = datetime.utcnow() - timedelta(days=days)
    results = (
        db.query(
            func.date(ActivityLog.created_at).label("date"),
            func.count(ActivityLog.id).label("count"),
            func.count(func.distinct(ActivityLog.user_id)).label("unique_users"),
        )
        .filter(ActivityLog.created_at >= since)
        .group_by(func.date(ActivityLog.created_at))
        .order_by(func.date(ActivityLog.created_at))
        .all()
    )
    return [
        {"date": str(r.date), "count": r.count, "unique_users": r.unique_users}
        for r in results
    ]

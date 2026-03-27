import logging
import os

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, init_db, SessionLocal, engine
from app.models import *  # noqa: F401,F403 - ensure all models loaded for init_db
from app.auth import require_admin, hash_password
from app.services.seed_data import seed_avatars_and_voices
from app.routers import (
    categories,
    products,
    sync,
    avatars,
    voices,
    video_jobs,
    training_agent,
    roleplay,
    settings as settings_router,
    agent,
    auth,
    analytics,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="GroMo AI Trainer",
    description="AI-powered training platform for GroMo fintech partners",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://frontend:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static storage for serving generated files
storage_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
os.makedirs(storage_path, exist_ok=True)
app.mount("/storage", StaticFiles(directory=storage_path), name="storage")

# Register routers — auth is public, others are protected
app.include_router(auth.router)  # Public: register, login, me
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(sync.router)
app.include_router(avatars.router)
app.include_router(voices.router)
app.include_router(video_jobs.router)
app.include_router(training_agent.router)
app.include_router(roleplay.router)
app.include_router(settings_router.router)
app.include_router(agent.router)
app.include_router(analytics.router)


def _run_migrations():
    """Add user_id columns to existing tables if missing (SQLite dev mode)."""
    try:
        inspector = inspect(engine)
        for table_name in ["roleplay_sessions", "agent_sessions", "video_jobs"]:
            try:
                columns = [c["name"] for c in inspector.get_columns(table_name)]
                if "user_id" not in columns:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN user_id VARCHAR(36)"))
                    logger.info(f"Added user_id column to {table_name}")
            except Exception as e:
                logger.warning(f"Migration for {table_name}: {e}")

        # Add phone column to users table if missing
        try:
            user_columns = [c["name"] for c in inspector.get_columns("users")]
            if "phone" not in user_columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(20)"))
                logger.info("Added phone column to users")
            # Make email nullable if needed
        except Exception as e:
            logger.warning(f"Users migration: {e}")
    except Exception as e:
        logger.warning(f"Migration check failed: {e}")


def _seed_admin():
    """Create admin user from env vars if none exists."""
    from app.models.user import User, UserRole

    db = SessionLocal()
    try:
        admin_exists = db.query(User).filter(User.role == UserRole.admin.value).first()
        if admin_exists:
            return

        admin_email = (settings.admin_email or "").strip().lower()
        if not admin_email:
            return

        existing = db.query(User).filter(User.email == admin_email).first()
        if existing:
            existing.role = UserRole.admin.value
            db.commit()
            logger.info(f"Promoted existing user {admin_email} to admin")
            return

        admin = User(
            email=admin_email,
            hashed_password=hash_password(settings.admin_password),
            name="Admin",
            role=UserRole.admin.value,
        )
        db.add(admin)
        db.commit()
        logger.info(f"Created admin user: {admin_email}")
    except Exception as e:
        logger.warning(f"Admin seed failed: {e}")
        db.rollback()
    finally:
        db.close()


@app.on_event("startup")
def startup():
    init_db()
    _run_migrations()

    db = SessionLocal()
    try:
        seed_avatars_and_voices(db)
    finally:
        db.close()

    _seed_admin()


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "gromo-ai-trainer"}


@app.get("/api/dashboard/stats")
def dashboard_stats(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    from app.models.product import Product
    from app.models.category import Category
    from app.models.video_job import VideoJob, JobStatus
    from app.models.roleplay_session import RoleplaySession
    from sqlalchemy import func

    total_products = db.query(Product).join(Category).filter(Category.is_excluded == False).count()  # noqa: E712
    total_categories = db.query(Category).filter(Category.is_excluded == False).count()  # noqa: E712
    total_videos = db.query(VideoJob).filter(VideoJob.status == JobStatus.completed).count()
    videos_in_queue = db.query(VideoJob).filter(VideoJob.status.notin_([JobStatus.completed, JobStatus.failed])).count()
    roleplay_sessions = db.query(RoleplaySession).count()
    avg_score = db.query(func.avg(RoleplaySession.overall_score)).filter(RoleplaySession.overall_score.isnot(None)).scalar()

    return {
        "total_products": total_products,
        "total_videos": total_videos,
        "videos_in_queue": videos_in_queue,
        "total_categories": total_categories,
        "roleplay_sessions": roleplay_sessions,
        "avg_roleplay_score": round(float(avg_score), 1) if avg_score else 0,
    }

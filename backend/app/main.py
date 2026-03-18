from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import os

from app.database import get_db, init_db, SessionLocal
from app.models import *  # noqa: F401,F403 - ensure all models loaded for init_db
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
    settings,
    agent,
)

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

# Register routers
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(sync.router)
app.include_router(avatars.router)
app.include_router(voices.router)
app.include_router(video_jobs.router)
app.include_router(training_agent.router)
app.include_router(roleplay.router)
app.include_router(settings.router)
app.include_router(agent.router)


@app.on_event("startup")
def startup():
    init_db()
    # Seed default avatars and voices
    db = SessionLocal()
    try:
        seed_avatars_and_voices(db)
    finally:
        db.close()


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "gromo-ai-trainer"}


@app.get("/api/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)):
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

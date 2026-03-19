import os
import uuid
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.video_job import VideoJob, JobType, JobStatus
from app.models.video_job_log import VideoJobLog
from app.models.product import Product
from app.auth import require_admin

# Base storage path for PPT uploads
STORAGE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/video-jobs", tags=["video-jobs"], dependencies=[Depends(require_admin)])


class VideoJobCreate(BaseModel):
    title: str
    job_type: JobType
    product_ids: Optional[List[uuid.UUID]] = None
    avatar_id: Optional[uuid.UUID] = None
    voice_id: Optional[uuid.UUID] = None
    language: str = "hinglish"
    script_text: Optional[str] = None
    target_duration: Optional[float] = None  # in seconds (30-300)


class VideoJobOut(BaseModel):
    id: uuid.UUID
    title: str
    job_type: JobType
    product_ids: Optional[list]
    avatar_id: Optional[uuid.UUID]
    voice_id: Optional[uuid.UUID]
    language: str
    target_duration: Optional[float]
    status: JobStatus
    progress: int
    script_text: Optional[str]
    audio_path: Optional[str]
    video_path: Optional[str]
    ppt_file_path: Optional[str]
    gamma_url: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class VideoJobLogOut(BaseModel):
    id: uuid.UUID
    step: str
    status: str
    message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[VideoJobOut])
def list_video_jobs(status: Optional[JobStatus] = None, db: Session = Depends(get_db)):
    query = db.query(VideoJob)
    if status:
        query = query.filter(VideoJob.status == status)
    return query.order_by(VideoJob.created_at.desc()).all()


@router.post("", response_model=VideoJobOut)
def create_video_job(data: VideoJobCreate, db: Session = Depends(get_db)):
    # Validate product_ids if provided
    if data.product_ids:
        for pid in data.product_ids:
            product = db.query(Product).filter(Product.id == pid).first()
            if not product:
                raise HTTPException(
                    status_code=400,
                    detail=f"Product {pid} not found",
                )

    # Validate target_duration if provided (30s to 300s)
    target_duration = data.target_duration
    if target_duration is not None:
        if target_duration < 30 or target_duration > 300:
            raise HTTPException(
                status_code=400,
                detail="Target duration must be between 30 and 300 seconds",
            )

    job = VideoJob(
        title=data.title,
        job_type=data.job_type,
        product_ids=[str(pid) for pid in data.product_ids] if data.product_ids else None,
        avatar_id=data.avatar_id,
        voice_id=data.voice_id,
        language=data.language,
        target_duration=target_duration,
        script_text=data.script_text,
        status=JobStatus.queued,
        progress=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Dispatch appropriate task based on job type
    # Note: gamma_ppt uses the standard pipeline which already handles Gamma AI
    # internally (with LLM narration for better quality) when gamma_api_key is set
    try:
        if data.job_type == JobType.ppt_mode:
            from app.tasks.video_tasks import generate_video_from_ppt
            generate_video_from_ppt(str(job.id))
            logger.info(f"Dispatched PPT video generation for job {job.id}")
        else:
            from app.tasks.video_tasks import generate_video
            generate_video(str(job.id))
            logger.info(f"Dispatched video generation task for job {job.id}")
    except Exception as e:
        logger.error(f"Failed to dispatch video task for job {job.id}: {e}")
        job.error_message = f"Task dispatch failed: {e}. Retry manually."
        db.commit()
        db.refresh(job)

    return job


@router.post("/ppt-upload", response_model=VideoJobOut)
def upload_ppt_and_create_job(
    file: UploadFile = File(...),
    language: str = Form("hinglish"),
    avatar_id: Optional[str] = Form(None),
    voice_id: Optional[str] = Form(None),
    target_duration: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Upload a .pptx file and create a PPT-mode video job."""
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pptx"):
        raise HTTPException(status_code=400, detail="Only .pptx files are accepted")

    # Save the uploaded PPT file
    ppts_dir = os.path.join(STORAGE_PATH, "ppts")
    os.makedirs(ppts_dir, exist_ok=True)

    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}.pptx"
    ppt_file_path = os.path.join(ppts_dir, safe_filename)

    try:
        contents = file.file.read()
        with open(ppt_file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save PPT file: {e}")
    finally:
        file.file.close()

    # Parse PPT content and generate script
    try:
        from app.services.ppt_parser import parse_ppt, generate_script_from_ppt

        ppt_data = parse_ppt(ppt_file_path)
        script_text = generate_script_from_ppt(ppt_data, language)
    except Exception as e:
        logger.error(f"Failed to parse PPT: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse PPT file: {e}")

    # Generate title from first slide or filename
    first_slide_title = ""
    if ppt_data.get("slides"):
        first_slide_title = ppt_data["slides"][0].get("title", "")
    title = first_slide_title if first_slide_title else (file.filename.rsplit(".", 1)[0] if file.filename else "PPT Video")
    title = f"{title} - PPT Training Video"

    # Parse optional UUIDs and duration
    parsed_avatar_id = uuid.UUID(avatar_id) if avatar_id else None
    parsed_voice_id = uuid.UUID(voice_id) if voice_id else None
    parsed_duration = float(target_duration) if target_duration else None
    if parsed_duration is not None and (parsed_duration < 30 or parsed_duration > 300):
        parsed_duration = None

    # Create the VideoJob
    job = VideoJob(
        title=title,
        job_type=JobType.ppt_mode,
        avatar_id=parsed_avatar_id,
        voice_id=parsed_voice_id,
        language=language,
        target_duration=parsed_duration,
        script_text=script_text,
        ppt_file_path=ppt_file_path,
        status=JobStatus.queued,
        progress=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Dispatch PPT video generation in background thread
    try:
        from app.tasks.video_tasks import generate_video_from_ppt
        generate_video_from_ppt(str(job.id))
        logger.info(f"Dispatched PPT video generation task for job {job.id}")
    except Exception as e:
        logger.error(f"Failed to dispatch PPT video task for job {job.id}: {e}")
        job.error_message = f"Task dispatch failed: {e}. Retry manually."
        db.commit()
        db.refresh(job)

    return job


@router.get("/{job_id}", response_model=VideoJobOut)
def get_video_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = db.query(VideoJob).filter(VideoJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Video job not found")
    return job


@router.get("/{job_id}/logs", response_model=List[VideoJobLogOut])
def get_video_job_logs(job_id: uuid.UUID, db: Session = Depends(get_db)):
    logs = (
        db.query(VideoJobLog)
        .filter(VideoJobLog.video_job_id == job_id)
        .order_by(VideoJobLog.created_at)
        .all()
    )
    return logs


@router.delete("/{job_id}")
def delete_video_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a video job and its associated files."""
    import shutil

    job = db.query(VideoJob).filter(VideoJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Video job not found")

    # Don't allow deleting jobs that are currently processing
    if job.status in ("generating_script", "generating_audio", "generating_avatar", "compositing"):
        raise HTTPException(status_code=400, detail="Cannot delete a job that is currently processing")

    # Delete associated files from disk
    job_dir = os.path.join(STORAGE_PATH, "videos", str(job_id))
    if os.path.exists(job_dir):
        try:
            shutil.rmtree(job_dir)
            logger.info(f"Deleted video files for job {job_id}: {job_dir}")
        except Exception as e:
            logger.warning(f"Failed to delete files for job {job_id}: {e}")

    # Delete PPT file if it exists outside the job dir
    if job.ppt_file_path and os.path.exists(job.ppt_file_path):
        try:
            os.remove(job.ppt_file_path)
        except Exception:
            pass

    # Delete logs first (even though cascade should handle it)
    db.query(VideoJobLog).filter(VideoJobLog.video_job_id == job_id).delete()

    # Delete the job record
    db.delete(job)
    db.commit()
    logger.info(f"Deleted video job {job_id}: {job.title}")

    return {"detail": "Video job deleted successfully"}


@router.delete("")
def delete_all_video_jobs(db: Session = Depends(get_db)):
    """Delete all video jobs and their associated files."""
    import shutil

    jobs = db.query(VideoJob).all()
    deleted_count = 0

    for job in jobs:
        # Skip jobs currently processing
        if job.status in ("generating_script", "generating_audio", "generating_avatar", "compositing"):
            continue

        # Delete files
        job_dir = os.path.join(STORAGE_PATH, "videos", str(job.id))
        if os.path.exists(job_dir):
            try:
                shutil.rmtree(job_dir)
            except Exception:
                pass

        if job.ppt_file_path and os.path.exists(job.ppt_file_path):
            try:
                os.remove(job.ppt_file_path)
            except Exception:
                pass

        # Delete logs and job
        db.query(VideoJobLog).filter(VideoJobLog.video_job_id == job.id).delete()
        db.delete(job)
        deleted_count += 1

    db.commit()
    logger.info(f"Deleted {deleted_count} video jobs")
    return {"detail": f"Deleted {deleted_count} video jobs"}


@router.post("/{job_id}/retry", response_model=VideoJobOut)
def retry_video_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = db.query(VideoJob).filter(VideoJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Video job not found")
    if job.status != JobStatus.failed:
        raise HTTPException(status_code=400, detail="Only failed jobs can be retried")

    job.status = JobStatus.queued
    job.progress = 0
    job.error_message = None
    db.commit()
    db.refresh(job)

    # Dispatch retry based on job type
    try:
        if job.job_type == JobType.ppt_mode.value:
            from app.tasks.video_tasks import generate_video_from_ppt
            generate_video_from_ppt(str(job.id))
        else:
            from app.tasks.video_tasks import generate_video
            generate_video(str(job.id))
        logger.info(f"Dispatched retry video generation task for job {job.id}")
    except Exception as e:
        logger.error(f"Failed to dispatch retry task for job {job.id}: {e}")
        job.error_message = f"Retry task dispatch failed: {e}. Retry manually."
        db.commit()
        db.refresh(job)

    return job

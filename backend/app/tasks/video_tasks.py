"""
Video generation tasks.
Implements the full video generation pipeline: script -> audio -> avatar -> composite.
Runs in background threads (no Celery/Redis required).
"""
import os
import uuid
import logging
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger(__name__)

# Base storage path for generated files
STORAGE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage")


def _get_db_session() -> Session:
    """Create a new DB session for use inside background tasks."""
    from app.database import SessionLocal
    return SessionLocal()


def log_step(
    db: Session,
    job_id: str,
    step: str,
    status: str,
    message: Optional[str] = None,
) -> None:
    """Write a log entry to VideoJobLog."""
    from app.models.video_job_log import VideoJobLog
    log_entry = VideoJobLog(
        video_job_id=uuid.UUID(job_id),
        step=step,
        status=status,
        message=message,
    )
    db.add(log_entry)
    db.commit()


def _update_job_status(
    db: Session,
    job_id: str,
    status: str,
    progress: int,
    error_message: Optional[str] = None,
    video_path: Optional[str] = None,
    script_text: Optional[str] = None,
    audio_path: Optional[str] = None,
    completed_at: Optional[datetime] = None,
) -> None:
    """Update a VideoJob record's status and progress."""
    from app.models.video_job import VideoJob
    job = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(job_id)).first()
    if not job:
        return
    job.status = status
    job.progress = progress
    if error_message is not None:
        job.error_message = error_message
    if video_path is not None:
        job.video_path = video_path
    if script_text is not None:
        job.script_text = script_text
    if audio_path is not None:
        job.audio_path = audio_path
    if completed_at is not None:
        job.completed_at = completed_at
    db.commit()


def _fetch_product_data(db: Session, product_ids: List[str]) -> List[Dict[str, Any]]:
    """Fetch product data from DB for the given product IDs."""
    from app.models.product import Product
    from app.models.category import Category

    products = []
    for pid in product_ids:
        try:
            product = db.query(Product).filter(Product.id == uuid.UUID(pid)).first()
            if product:
                category = db.query(Category).filter(Category.id == product.category_id).first()
                products.append({
                    "name": product.name,
                    "payout": product.payout or "",
                    "sub_type": product.sub_type or "",
                    "benefits_text": product.benefits_text or "",
                    "how_works_text": product.how_works_text or "",
                    "terms_conditions_text": product.terms_conditions_text or "",
                    "description": product.description or "",
                    "category_name": category.name if category else "",
                    # Legacy fields for backward compatibility
                    "features": product.features,
                    "eligibility": product.eligibility,
                    "fees": product.fees,
                    "benefits": product.benefits,
                    "faqs": product.faqs,
                })
        except Exception as e:
            logger.warning(f"Could not fetch product {pid}: {e}")

    return products


def _run_generate_video(job_id: str):
    """
    Production video pipeline (runs in background thread).
    Uses Gamma AI PPT slides when available for visually appealing presentations,
    with per-slide Edge-TTS audio for perfect narration sync.
    Falls back to DALL-E slide images if Gamma is not available.
    """
    db = _get_db_session()

    try:
        from app.models.video_job import VideoJob

        job = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(job_id)).first()
        if not job:
            logger.error(f"Video job {job_id} not found")
            return

        logger.info(f"Starting production video for job {job_id}: {job.title}")

        job_dir = os.path.join(STORAGE_PATH, "videos", job_id)
        os.makedirs(job_dir, exist_ok=True)

        # ---- Step 1: Generate Script ----
        _update_job_status(db, job_id, "generating_script", 0)
        log_step(db, job_id, "generating_script", "started", "Starting script generation")

        try:
            from app.services.script_generator import generate_script

            product_ids = job.product_ids or []
            product_data_list = _fetch_product_data(db, product_ids)

            if not product_data_list:
                product_data_list = [{"name": job.title, "description": f"Training video for {job.title}"}]

            target_dur = getattr(job, 'target_duration', None)
            if job.job_type in ("category_overview", "comparison"):
                script_text = generate_script(product_data_list, job.job_type, job.language, target_dur)
            else:
                script_text = generate_script(product_data_list[0], job.job_type, job.language, target_dur)

            if job.script_text:
                script_text = job.script_text

            _update_job_status(db, job_id, "generating_script", 10, script_text=script_text)
            log_step(db, job_id, "generating_script", "completed", "Script generated successfully")

        except Exception as e:
            log_step(db, job_id, "generating_script", "failed", str(e))
            raise

        # ---- Step 2: Try Gamma AI for visually appealing slides ----
        gamma_slide_images = None
        gamma_slide_texts = None

        if settings.gamma_api_key:
            _update_job_status(db, job_id, "generating_ppt", 10)
            log_step(db, job_id, "generating_ppt", "started", "Generating Gamma AI presentation")

            try:
                from app.services.gamma_service import generate_presentation, download_pptx
                from app.services.pptx_to_images import pptx_to_images

                # For category_overview/comparison, pass all products; otherwise just the first
                effective_job_type = job.job_type if job.job_type != "gamma_ppt" else "single_product"
                if effective_job_type in ("category_overview", "comparison"):
                    gamma_product_data = product_data_list
                else:
                    gamma_product_data = product_data_list[0] if product_data_list else {"name": job.title}

                gamma_result = generate_presentation(
                    product_data=gamma_product_data,
                    job_type=effective_job_type,
                    language=job.language,
                    target_duration=target_dur,
                )

                gamma_url = gamma_result.get("gamma_url")
                pptx_url = gamma_result.get("pptx_url")

                if gamma_url:
                    jobj = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(job_id)).first()
                    if jobj:
                        jobj.gamma_url = gamma_url
                        db.commit()

                if pptx_url:
                    ppt_path = os.path.join(job_dir, "gamma_presentation.pptx")
                    download_pptx(pptx_url, ppt_path)

                    jobj = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(job_id)).first()
                    if jobj:
                        jobj.ppt_file_path = ppt_path
                        db.commit()

                    slides_dir = os.path.join(job_dir, "slides")
                    gamma_slide_images = pptx_to_images(ppt_path, slides_dir)
                    logger.info(f"Gamma: {len(gamma_slide_images)} slides converted to images")

                    # Extract per-slide text for narration sync
                    from app.services.pptx_to_images import extract_slide_texts
                    gamma_slide_texts = extract_slide_texts(ppt_path)
                    logger.info(f"Extracted text from {len(gamma_slide_texts)} slides for sync")

                _update_job_status(db, job_id, "generating_ppt", 25)
                log_step(db, job_id, "generating_ppt", "completed",
                         f"Gamma slides: {len(gamma_slide_images) if gamma_slide_images else 0} images")

            except Exception as e:
                logger.warning(f"Gamma pipeline failed, falling back to DALL-E: {e}")
                log_step(db, job_id, "generating_ppt", "warning", f"Gamma fallback: {e}")

        # ---- Step 3: Production Video Pipeline ----
        _update_job_status(db, job_id, "generating_audio", 25)
        log_step(db, job_id, "generating_audio", "started", "Starting production video pipeline")

        try:
            from app.services.video_pipeline import generate_production_video

            primary_product = product_data_list[0] if product_data_list else {"name": job.title}

            def on_progress(pct, msg):
                job_pct = 25 + int(pct * 0.70)
                status = "generating_audio" if pct < 40 else ("generating_avatar" if pct < 70 else "compositing")
                _update_job_status(db, job_id, status, job_pct)

            result = generate_production_video(
                product_data=primary_product,
                script_text=script_text,
                output_dir=job_dir,
                language=job.language,
                on_progress=on_progress,
                gamma_slide_images=gamma_slide_images,
                gamma_slide_texts=gamma_slide_texts,
            )

            video_path = result["video_path"]
            audio_path = result.get("audio_path", "")

            relative_video_path = os.path.relpath(video_path, STORAGE_PATH)
            storage_url = f"/storage/{relative_video_path}"

            _update_job_status(
                db, job_id, "completed", 100,
                video_path=storage_url,
                audio_path=audio_path,
                completed_at=datetime.utcnow(),
            )
            log_step(db, job_id, "compositing", "completed",
                     f"Production video: {storage_url} ({result.get('num_slides', 0)} slides, {result.get('duration', 0):.0f}s)")
            logger.info(f"Production video completed for job {job_id}")

        except Exception as e:
            log_step(db, job_id, "pipeline", "failed", str(e))
            raise

    except Exception as e:
        logger.error(f"Video generation failed for job {job_id}: {e}")
        _update_job_status(
            db, job_id, "failed", 0,
            error_message=str(e),
        )
        log_step(db, job_id, "pipeline", "failed", f"Pipeline error: {e}")
    finally:
        db.close()


def _run_generate_video_from_ppt(job_id: str):
    """
    PPT-based video generation pipeline (runs in background thread).
    Steps: parse PPT -> script -> audio -> avatar -> composite (slide-based).
    """
    db = _get_db_session()

    try:
        from app.models.video_job import VideoJob

        # Step 0: Fetch the job
        job = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(job_id)).first()
        if not job:
            logger.error(f"PPT video job {job_id} not found")
            return

        logger.info(f"Starting PPT video generation for job {job_id}: {job.title}")

        # Create job-specific output directory
        job_dir = os.path.join(STORAGE_PATH, "videos", job_id)
        os.makedirs(job_dir, exist_ok=True)

        # ---- Step 1: Parse PPT & Generate Script ----
        _update_job_status(db, job_id, "generating_script", 0)
        log_step(db, job_id, "generating_script", "started", "Parsing PPT and generating script")

        try:
            script_text = job.script_text
            ppt_data = None

            if not script_text:
                from app.services.ppt_parser import parse_ppt, generate_script_from_ppt

                ppt_file_path = job.ppt_file_path
                if not ppt_file_path or not os.path.exists(ppt_file_path):
                    raise FileNotFoundError(f"PPT file not found: {ppt_file_path}")

                ppt_data = parse_ppt(ppt_file_path)
                script_text = generate_script_from_ppt(ppt_data, job.language)
            else:
                if job.ppt_file_path and os.path.exists(job.ppt_file_path):
                    from app.services.ppt_parser import parse_ppt
                    ppt_data = parse_ppt(job.ppt_file_path)

            _update_job_status(db, job_id, "generating_script", 20, script_text=script_text)
            log_step(db, job_id, "generating_script", "completed", "Script generated from PPT")

        except Exception as e:
            log_step(db, job_id, "generating_script", "failed", str(e))
            raise

        # ---- Step 2: Generate Audio (TTS) ----
        _update_job_status(db, job_id, "generating_audio", 20)
        log_step(db, job_id, "generating_audio", "started", "Starting audio generation")

        try:
            from app.services.tts_service import generate_audio
            from app.models.voice import Voice

            voice_name = "Aditi (Hinglish Female)"
            if job.voice_id:
                voice = db.query(Voice).filter(Voice.id == job.voice_id).first()
                if voice:
                    voice_name = voice.name

            ppt_target_dur = getattr(job, 'target_duration', None)
            audio_output = os.path.join(job_dir, "audio.mp3")
            audio_path = generate_audio(
                script_text, voice_name, audio_output, job.language,
                target_duration=ppt_target_dur,
            )

            _update_job_status(db, job_id, "generating_audio", 40, audio_path=audio_path)
            log_step(db, job_id, "generating_audio", "completed", f"Audio saved to {audio_path}")

        except Exception as e:
            log_step(db, job_id, "generating_audio", "failed", str(e))
            raise

        # ---- Step 3: Generate Avatar Video ----
        _update_job_status(db, job_id, "generating_avatar", 40)
        log_step(db, job_id, "generating_avatar", "started", "Starting avatar video generation")

        try:
            from app.services.avatar_service import generate_avatar_video
            from app.models.avatar import Avatar

            avatar_image_path = None
            if job.avatar_id:
                avatar = db.query(Avatar).filter(Avatar.id == job.avatar_id).first()
                if avatar and avatar.image_path:
                    avatar_image_path = avatar.image_path

            avatar_output = os.path.join(job_dir, "avatar.mp4")

            ppt_product = _build_product_data_from_ppt(ppt_data, job.title) if ppt_data else {"name": job.title}
            avatar_video_path = generate_avatar_video(
                audio_path,
                avatar_image_path,
                avatar_output,
                product_data=ppt_product,
                script_text=script_text,
            )

            _update_job_status(db, job_id, "generating_avatar", 60)
            log_step(db, job_id, "generating_avatar", "completed", f"Avatar video saved to {avatar_video_path}")

        except Exception as e:
            log_step(db, job_id, "generating_avatar", "failed", str(e))
            raise

        # ---- Step 4: Render PPT Slides & Composite Video ----
        _update_job_status(db, job_id, "compositing", 60)
        log_step(db, job_id, "compositing", "started", "Rendering PPT slides and compositing video")

        try:
            from app.services.video_compositor import compose_video

            ppt_product_data = _build_product_data_from_ppt(ppt_data, job.title)

            # Render PPT slide data as professional images
            slide_image_paths = None
            if ppt_data and ppt_data.get("slides"):
                from app.services.slide_renderer import render_slides_from_ppt_data
                slides_dir = os.path.join(job_dir, "slides")
                slide_image_paths = render_slides_from_ppt_data(
                    ppt_data, ppt_product_data, slides_dir
                )

            final_output = os.path.join(job_dir, "final.mp4")
            video_path = compose_video(
                audio_path=audio_path,
                avatar_video_path=avatar_video_path,
                product_data=ppt_product_data,
                script_text=script_text,
                output_path=final_output,
                slide_image_paths=slide_image_paths,
            )

            relative_video_path = os.path.relpath(video_path, STORAGE_PATH)
            storage_url = f"/storage/{relative_video_path}"

            _update_job_status(
                db, job_id, "completed", 100,
                video_path=storage_url,
                completed_at=datetime.utcnow(),
            )
            log_step(db, job_id, "compositing", "completed", f"Final video saved to {storage_url}")
            logger.info(f"PPT video generation completed for job {job_id}")

        except Exception as e:
            log_step(db, job_id, "compositing", "failed", str(e))
            raise

    except Exception as e:
        logger.error(f"PPT video generation failed for job {job_id}: {e}")
        _update_job_status(
            db, job_id, "failed", 0,
            error_message=str(e),
        )
        log_step(db, job_id, "pipeline", "failed", f"Pipeline error: {e}")
    finally:
        db.close()


def generate_video(job_id: str):
    """Dispatch video generation in a background thread."""
    thread = threading.Thread(
        target=_run_generate_video,
        args=(job_id,),
        daemon=True,
        name=f"video-gen-{job_id[:8]}",
    )
    thread.start()
    logger.info(f"Dispatched video generation thread for job {job_id}")


def generate_video_from_ppt(job_id: str):
    """Dispatch PPT video generation in a background thread."""
    thread = threading.Thread(
        target=_run_generate_video_from_ppt,
        args=(job_id,),
        daemon=True,
        name=f"ppt-video-gen-{job_id[:8]}",
    )
    thread.start()
    logger.info(f"Dispatched PPT video generation thread for job {job_id}")


def generate_video_from_gamma(job_id: str):
    """Dispatch Gamma PPT video generation in a background thread."""
    thread = threading.Thread(
        target=_run_generate_video_from_gamma,
        args=(job_id,),
        daemon=True,
        name=f"gamma-video-gen-{job_id[:8]}",
    )
    thread.start()
    logger.info(f"Dispatched Gamma video generation thread for job {job_id}")


def _run_generate_video_from_gamma(job_id: str):
    """
    Gamma AI video pipeline (runs in background thread).
    Steps:
      1. Generate Gamma presentation (visually appealing PPT)
      2. Download PPTX → convert actual Gamma slides to images
      3. Parse PPT + generate narration script
      4. Generate per-slide Edge-TTS audio (synced to each slide)
      5. Compose video: Gamma slide images + synced narration audio
    """
    db = _get_db_session()

    try:
        from app.models.video_job import VideoJob

        job = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(job_id)).first()
        if not job:
            logger.error(f"Gamma video job {job_id} not found")
            return

        logger.info(f"Starting Gamma PPT video generation for job {job_id}: {job.title}")

        job_dir = os.path.join(STORAGE_PATH, "videos", job_id)
        os.makedirs(job_dir, exist_ok=True)

        # ---- Step 1: Generate Gamma Presentation ----
        _update_job_status(db, job_id, "generating_ppt", 0)
        log_step(db, job_id, "generating_ppt", "started", "Generating presentation via Gamma AI")

        try:
            from app.services.gamma_service import generate_presentation, download_pptx

            product_ids = job.product_ids or []
            product_data_list = _fetch_product_data(db, product_ids)

            if not product_data_list:
                product_data_list = [{"name": job.title, "description": f"Training video for {job.title}"}]

            target_dur = getattr(job, 'target_duration', None)

            if job.job_type in ("category_overview", "comparison"):
                gamma_input = product_data_list
            else:
                gamma_input = product_data_list[0]

            result = generate_presentation(
                product_data=gamma_input,
                job_type=job.job_type if job.job_type != "gamma_ppt" else "single_product",
                language=job.language,
                target_duration=target_dur,
            )

            gamma_url = result.get("gamma_url")
            pptx_url = result.get("pptx_url")

            if gamma_url:
                jobj = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(job_id)).first()
                if jobj:
                    jobj.gamma_url = gamma_url
                    db.commit()

            ppt_file_path = None
            if pptx_url:
                ppt_file_path = os.path.join(job_dir, "gamma_presentation.pptx")
                download_pptx(pptx_url, ppt_file_path)

                jobj = db.query(VideoJob).filter(VideoJob.id == uuid.UUID(job_id)).first()
                if jobj:
                    jobj.ppt_file_path = ppt_file_path
                    db.commit()

            _update_job_status(db, job_id, "generating_ppt", 10)
            log_step(db, job_id, "generating_ppt", "completed",
                     f"Gamma presentation ready: {gamma_url}")

        except Exception as e:
            log_step(db, job_id, "generating_ppt", "failed", str(e))
            raise

        # ---- Step 2: Convert Gamma PPTX slides to images ----
        _update_job_status(db, job_id, "generating_ppt", 10)
        log_step(db, job_id, "generating_ppt", "started", "Converting Gamma slides to images")

        slide_image_paths = None
        try:
            if ppt_file_path and os.path.exists(ppt_file_path):
                from app.services.pptx_to_images import pptx_to_images
                slides_dir = os.path.join(job_dir, "slides")
                slide_image_paths = pptx_to_images(ppt_file_path, slides_dir)
                logger.info(f"Converted {len(slide_image_paths)} Gamma slides to images")
            else:
                logger.warning("No PPTX file available, will use generated slides")

            _update_job_status(db, job_id, "generating_ppt", 20)
            log_step(db, job_id, "generating_ppt", "completed",
                     f"Converted {len(slide_image_paths) if slide_image_paths else 0} slides to images")

        except Exception as e:
            logger.warning(f"PPTX-to-images conversion failed: {e}, will fall back to rendered slides")
            log_step(db, job_id, "generating_ppt", "warning", f"Slide conversion fallback: {e}")

        # ---- Step 3: Parse PPT & Generate Script ----
        _update_job_status(db, job_id, "generating_script", 20)
        log_step(db, job_id, "generating_script", "started", "Generating narration script from Gamma PPT")

        try:
            ppt_data = None
            script_text = job.script_text

            if not script_text and ppt_file_path and os.path.exists(ppt_file_path):
                from app.services.ppt_parser import parse_ppt, generate_script_from_ppt
                ppt_data = parse_ppt(ppt_file_path)
                script_text = generate_script_from_ppt(ppt_data, job.language)
            elif not script_text:
                from app.services.script_generator import generate_script
                if job.job_type in ("category_overview", "comparison"):
                    script_text = generate_script(product_data_list, job.job_type, job.language, target_dur)
                else:
                    script_text = generate_script(product_data_list[0], "single_product", job.language, target_dur)

            if ppt_file_path and os.path.exists(ppt_file_path) and ppt_data is None:
                from app.services.ppt_parser import parse_ppt
                ppt_data = parse_ppt(ppt_file_path)

            _update_job_status(db, job_id, "generating_script", 30, script_text=script_text)
            log_step(db, job_id, "generating_script", "completed", "Narration script generated")

        except Exception as e:
            log_step(db, job_id, "generating_script", "failed", str(e))
            raise

        # ---- Step 4: Generate per-slide audio (synced narration) ----
        _update_job_status(db, job_id, "generating_audio", 30)
        log_step(db, job_id, "generating_audio", "started", "Generating per-slide synced audio")

        try:
            from app.services.video_pipeline import (
                _clean_narration, _generate_slide_audio,
                _generate_slide_audio_sarvam,
            )

            # Split script into sections matching slides
            num_slides = len(slide_image_paths) if slide_image_paths else (
                len(ppt_data.get("slides", [])) if ppt_data else 6
            )
            narration_sections = _split_script_for_slides(script_text, num_slides, ppt_data)

            audio_dir = os.path.join(job_dir, "audio_chunks")
            os.makedirs(audio_dir, exist_ok=True)

            # Use Sarvam for Hinglish/Hindi, Edge-TTS for English
            use_sarvam = (
                job.language in ("hinglish", "hindi")
                and settings.sarvam_api_key
            )

            slide_audios = []
            for i, narration in enumerate(narration_sections):
                clean_text = _clean_narration(narration)
                if not clean_text or len(clean_text) < 5:
                    clean_text = "Aaiye agle section ko dekhte hain."

                audio_path = os.path.join(audio_dir, f"slide_{i+1:03d}.mp3")
                try:
                    if use_sarvam:
                        _generate_slide_audio_sarvam(
                            clean_text, audio_path,
                            language=job.language, pace=1.15,
                            speaker="anushka",
                        )
                    else:
                        _generate_slide_audio(
                            clean_text, audio_path,
                            voice="en-IN-NeerjaExpressiveNeural",
                            rate="+8%",
                        )
                    slide_audios.append(audio_path)
                    logger.info(f"Audio for slide {i+1}: {len(clean_text)} chars")
                except Exception as ae:
                    logger.error(f"Audio gen failed for slide {i+1}: {ae}")
                    slide_audios.append(None)

                pct = 30 + int(25 * (i + 1) / len(narration_sections))
                _update_job_status(db, job_id, "generating_audio", pct)

            _update_job_status(db, job_id, "generating_audio", 55)
            log_step(db, job_id, "generating_audio", "completed",
                     f"Generated {len([a for a in slide_audios if a])} audio chunks")

        except Exception as e:
            log_step(db, job_id, "generating_audio", "failed", str(e))
            raise

        # ---- Step 5: If no Gamma slide images, fall back to rendered slides ----
        if not slide_image_paths:
            _update_job_status(db, job_id, "compositing", 55)
            log_step(db, job_id, "compositing", "started", "Rendering fallback slides")

            try:
                primary_product = product_data_list[0] if product_data_list else {"name": job.title}
                from app.services.video_pipeline import (
                    _parse_script_to_slides, _build_dalle_prompts,
                    _generate_slide_image, _render_slide,
                )

                slides_data = _parse_script_to_slides(script_text, primary_product)
                slides_dir = os.path.join(job_dir, "slides")
                os.makedirs(slides_dir, exist_ok=True)

                slide_image_paths = []
                for i, sd in enumerate(slides_data):
                    prompt = _build_dalle_prompts([sd])[0]
                    dalle_img = _generate_slide_image(prompt)
                    img = _render_slide(sd, dalle_img, i + 1, len(slides_data),
                                        primary_product.get("name", "Product"))
                    path = os.path.join(slides_dir, f"slide_{i+1:03d}.png")
                    img.save(path, "PNG", quality=95)
                    slide_image_paths.append(path)

                # Re-generate audios to match new slide count
                slide_audios = slide_audios[:len(slide_image_paths)]
                while len(slide_audios) < len(slide_image_paths):
                    slide_audios.append(None)

            except Exception as e:
                logger.error(f"Fallback slide rendering failed: {e}")

        # ---- Step 6: Compose final video (Gamma slides + synced audio) ----
        _update_job_status(db, job_id, "compositing", 65)
        log_step(db, job_id, "compositing", "started", "Composing video with Gamma slides + synced audio")

        try:
            from app.services.video_pipeline import _compose_synced_video, _concat_audio_files

            final_output = os.path.join(job_dir, "final.mp4")
            result = _compose_synced_video(slide_image_paths, slide_audios, final_output)

            # Also create combined audio file
            combined_audio = os.path.join(job_dir, "audio.mp3")
            valid_audios = [a for a in slide_audios if a and os.path.exists(a)]
            _concat_audio_files(valid_audios, combined_audio)

            relative_video_path = os.path.relpath(final_output, STORAGE_PATH)
            storage_url = f"/storage/{relative_video_path}"

            _update_job_status(
                db, job_id, "completed", 100,
                video_path=storage_url,
                audio_path=combined_audio,
                completed_at=datetime.utcnow(),
            )
            log_step(db, job_id, "compositing", "completed",
                     f"Gamma video: {storage_url} ({len(slide_image_paths)} slides, {result.get('duration', 0):.0f}s)")
            logger.info(f"Gamma video generation completed for job {job_id}")

        except Exception as e:
            log_step(db, job_id, "compositing", "failed", str(e))
            raise

    except Exception as e:
        logger.error(f"Gamma video generation failed for job {job_id}: {e}")
        _update_job_status(
            db, job_id, "failed", 0,
            error_message=str(e),
        )
        log_step(db, job_id, "pipeline", "failed", f"Pipeline error: {e}")
    finally:
        db.close()


def _split_script_for_slides(
    script_text: str,
    num_slides: int,
    ppt_data: Optional[Dict] = None,
) -> List[str]:
    """
    Split a narration script into sections matching the number of slides.
    Uses PPT slide content as a guide when available.
    """
    import re

    # If PPT data has slide-specific content, use that as narration base
    if ppt_data and ppt_data.get("slides"):
        ppt_slides = ppt_data["slides"]
        sections = []
        for slide in ppt_slides:
            title = slide.get("title", "")
            content = slide.get("content", "")
            # Build narration from slide content
            narration = f"{title}. {content}" if title else content
            sections.append(narration.strip() or "Let's move to the next section.")

        # Ensure we match num_slides
        while len(sections) < num_slides:
            sections.append("Let's continue.")
        return sections[:num_slides]

    # Fallback: split script into sections by double newlines or markers
    sections = re.split(r'\[(?:SLIDE|INTRO|Screen|CTA).*?\]', script_text)
    sections = [s.strip() for s in sections if s.strip()]

    if len(sections) <= 1:
        sections = [s.strip() for s in script_text.split("\n\n") if s.strip()]

    # Distribute to match num_slides
    if len(sections) == 0:
        return ["Welcome to this training video."] * num_slides

    if len(sections) >= num_slides:
        # Merge excess into last section
        result = sections[:num_slides - 1]
        result.append("\n".join(sections[num_slides - 1:]))
        return result
    else:
        # Split longer sections to fill
        while len(sections) < num_slides:
            # Find longest section and split it
            longest_idx = max(range(len(sections)), key=lambda i: len(sections[i]))
            text = sections[longest_idx]
            mid = len(text) // 2
            # Find nearest sentence boundary
            for offset in range(min(100, mid)):
                if mid + offset < len(text) and text[mid + offset] in '.!?।':
                    mid = mid + offset + 1
                    break
                if mid - offset >= 0 and text[mid - offset] in '.!?।':
                    mid = mid - offset + 1
                    break
            part1 = text[:mid].strip()
            part2 = text[mid:].strip()
            sections[longest_idx] = part1
            sections.insert(longest_idx + 1, part2 or "Let's continue.")

        return sections[:num_slides]


def _build_product_data_from_ppt(
    ppt_data: Optional[Dict[str, Any]],
    job_title: str,
) -> Dict[str, Any]:
    """
    Build a product_data dict from parsed PPT data for use by the video compositor.
    """
    if not ppt_data or not ppt_data.get("slides"):
        return {"name": job_title, "description": f"Training video: {job_title}"}

    slides = ppt_data["slides"]
    first_title = slides[0].get("title", "") or job_title

    features = []
    for slide in slides[1:]:
        title = slide.get("title", "")
        content = slide.get("content", "")
        if title and content:
            features.append(f"{title}: {content[:100]}")
        elif title:
            features.append(title)
        elif content:
            features.append(content[:120])

    return {
        "name": first_title,
        "description": slides[0].get("content", "") or f"PPT Training: {first_title}",
        "features": features[:6],
    }

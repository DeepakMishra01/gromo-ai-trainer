"""
Video compositor service.
Combines slide images with audio narration into a professional training video.
Each slide image gets equal time, synced with the TTS audio.
Compatible with moviepy 2.x API.
"""
import os
import re
import logging
from typing import Optional, List, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)

SLIDE_W, SLIDE_H = 1280, 720


def compose_video(
    audio_path: str,
    avatar_video_path: Optional[str],
    product_data: dict,
    script_text: str,
    output_path: str,
    slide_image_paths: Optional[List[str]] = None,
) -> str:
    """
    Compose a final training video with slide images and audio narration.

    If slide_image_paths are provided, uses those as video backgrounds.
    Otherwise falls back to generating slide images from product data.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        return _compose_slide_video(
            audio_path, product_data, script_text, output_path, slide_image_paths
        )
    except Exception as e:
        logger.error(f"Slide video composition failed: {e}")
        # Fallback to basic text-based video
        try:
            return _compose_basic_video(audio_path, product_data, script_text, output_path)
        except Exception as e2:
            logger.error(f"Basic video composition also failed: {e2}")
            raise


def _compose_slide_video(
    audio_path: str,
    product_data: dict,
    script_text: str,
    output_path: str,
    slide_image_paths: Optional[List[str]] = None,
) -> str:
    """Create a professional training video with rendered slide images."""
    from moviepy import (
        ImageClip,
        AudioFileClip,
        concatenate_videoclips,
    )
    import numpy as np

    # Get audio duration
    audio_clip = None
    try:
        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration
    except Exception:
        total_duration = 60.0
        audio_clip = None

    logger.info(f"Composing slide video: {total_duration:.1f}s total")

    # If no slide images provided, render from product data
    if not slide_image_paths or not any(os.path.exists(p) for p in slide_image_paths):
        logger.info("No slide images found, rendering from product data...")
        from app.services.slide_renderer import render_slides_from_product_data

        slides_dir = os.path.join(os.path.dirname(output_path), "slides")
        slide_image_paths = render_slides_from_product_data(
            product_data, slides_dir, script_text
        )

    # Filter to existing files
    slide_image_paths = [p for p in slide_image_paths if os.path.exists(p)]

    if not slide_image_paths:
        raise ValueError("No slide images available for video composition")

    num_slides = len(slide_image_paths)

    # Calculate duration per slide based on script sections
    slide_durations = _calculate_slide_durations(script_text, total_duration, num_slides)

    logger.info(f"Using {num_slides} slides, durations: {[f'{d:.1f}s' for d in slide_durations]}")

    # Build video clips from slide images
    slide_clips = []
    for i, (img_path, duration) in enumerate(zip(slide_image_paths, slide_durations)):
        try:
            from PIL import Image
            img = Image.open(img_path).convert("RGB")
            img = img.resize((SLIDE_W, SLIDE_H), Image.LANCZOS)
            img_array = np.array(img)

            clip = ImageClip(img_array, duration=duration)
            slide_clips.append(clip)
            logger.debug(f"Slide {i+1}: {duration:.1f}s from {img_path}")
        except Exception as e:
            logger.warning(f"Failed to load slide image {img_path}: {e}")
            # Fallback: dark background
            from moviepy import ColorClip
            clip = ColorClip(size=(SLIDE_W, SLIDE_H), color=(15, 23, 42), duration=duration)
            slide_clips.append(clip)

    # Concatenate all slides
    if slide_clips:
        final_video = concatenate_videoclips(slide_clips, method="compose")
    else:
        from moviepy import ColorClip
        final_video = ColorClip(size=(SLIDE_W, SLIDE_H), color=(15, 23, 42), duration=total_duration)

    # Attach audio
    if audio_clip:
        # Trim or pad video to match audio duration
        if final_video.duration > total_duration + 1:
            final_video = final_video.subclipped(0, total_duration)
        final_video = final_video.with_audio(audio_clip)

    # Ensure .mp4 extension
    if not output_path.endswith(".mp4"):
        output_path = output_path.rsplit(".", 1)[0] + ".mp4" if "." in output_path else output_path + ".mp4"

    final_video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        logger=None,
    )

    # Clean up
    final_video.close()
    for clip in slide_clips:
        clip.close()
    if audio_clip:
        audio_clip.close()

    logger.info(f"Slide video composed: {output_path} ({total_duration:.1f}s, {num_slides} slides)")
    return output_path


def _calculate_slide_durations(
    script_text: str,
    total_duration: float,
    num_slides: int,
) -> List[float]:
    """
    Calculate how long each slide should be shown based on script section lengths.
    Longer script sections get proportionally more time.
    """
    # Split script into sections (by [SLIDE...] markers or double newlines)
    sections = re.split(r'\[(?:SLIDE|INTRO|Screen|CTA).*?\]', script_text)
    sections = [s.strip() for s in sections if s.strip()]

    # If we don't have section markers, split by paragraphs
    if len(sections) <= 1:
        sections = [s.strip() for s in script_text.split("\n\n") if s.strip()]

    # Ensure we have at least num_slides sections
    while len(sections) < num_slides:
        sections.append("")

    # Trim to num_slides (merge excess into last)
    if len(sections) > num_slides:
        merged = "\n".join(sections[num_slides - 1:])
        sections = sections[:num_slides - 1] + [merged]

    # Calculate word counts per section
    word_counts = [len(s.split()) for s in sections]
    total_words = sum(word_counts) or 1

    # Distribute time proportionally (minimum 3s per slide)
    min_duration = 3.0
    available_time = total_duration - (min_duration * num_slides)

    if available_time < 0:
        # Not enough time, equal distribution
        return [total_duration / num_slides] * num_slides

    durations = []
    for wc in word_counts:
        proportion = wc / total_words
        dur = min_duration + (available_time * proportion)
        durations.append(round(dur, 2))

    # Adjust last slide to fill remaining time
    used = sum(durations[:-1])
    durations[-1] = max(min_duration, total_duration - used)

    return durations


def _compose_basic_video(
    audio_path: str,
    product_data: dict,
    script_text: str,
    output_path: str,
) -> str:
    """Fallback: basic text-on-color video (moviepy 2.x)."""
    from moviepy import (
        ColorClip,
        TextClip,
        CompositeVideoClip,
        AudioFileClip,
    )

    audio_clip = None
    try:
        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration
    except Exception:
        total_duration = 30.0
        audio_clip = None

    product_name = product_data.get("name", "GroMo Training")

    bg = ColorClip(size=(SLIDE_W, SLIDE_H), color=(15, 23, 42), duration=total_duration)
    clips = [bg]

    try:
        title = TextClip(
            text=product_name, font_size=48, color="white",
            duration=total_duration,
        ).with_position(("center", 300))
        clips.append(title)
    except Exception:
        pass

    video = CompositeVideoClip(clips, size=(SLIDE_W, SLIDE_H))
    if audio_clip:
        video = video.with_audio(audio_clip)

    if not output_path.endswith(".mp4"):
        output_path = output_path.rsplit(".", 1)[0] + ".mp4"

    video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
    video.close()
    if audio_clip:
        audio_clip.close()

    return output_path

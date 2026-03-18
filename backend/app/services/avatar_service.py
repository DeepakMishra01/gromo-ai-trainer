"""
Avatar / Visual generation service.
Generates visual content for training videos using OpenAI DALL-E or placeholder.
Compatible with moviepy 2.x API.
"""
import os
import logging
import base64
from typing import Optional
from io import BytesIO

from app.config import settings

logger = logging.getLogger(__name__)


def generate_avatar_video(
    audio_path: str,
    avatar_image_path: Optional[str],
    output_path: str,
    product_data: Optional[dict] = None,
    script_text: Optional[str] = None,
) -> str:
    """
    Generate a visual video with product-relevant images and audio.
    """
    provider = settings.avatar_provider
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        if provider == "openai_dalle":
            return _generate_dalle_video(
                audio_path, output_path, product_data, script_text
            )
        else:
            return _generate_demo_video(audio_path, avatar_image_path, output_path)
    except Exception as e:
        logger.error(f"Avatar/visual generation failed with '{provider}': {e}")
        logger.info("Falling back to demo video generator")
        return _generate_demo_video(audio_path, avatar_image_path, output_path)


def generate_product_image(product_name: str, category: str) -> Optional[bytes]:
    """
    Generate a single product-relevant image using DALL-E.
    Returns image bytes or None.
    """
    if not settings.openai_api_key:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)

        prompt = (
            f"Professional, clean financial product banner for '{product_name}' "
            f"({category}). Modern gradient background (blue/purple tones), "
            f"minimalist fintech design style, no text in image, "
            f"abstract finance icons and shapes, suitable for a training video slide. "
            f"Corporate, trustworthy, premium look."
        )

        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1792x1024",
            quality="standard",
            n=1,
            response_format="b64_json",
        )

        image_b64 = response.data[0].b64_json
        return base64.b64decode(image_b64)

    except Exception as e:
        logger.error(f"DALL-E image generation failed: {e}")
        return None


def _generate_dalle_video(
    audio_path: str,
    output_path: str,
    product_data: Optional[dict],
    script_text: Optional[str],
) -> str:
    """
    Generate a video with DALL-E background image and TTS audio overlay.
    """
    from moviepy import (
        ImageClip,
        ColorClip,
        TextClip,
        CompositeVideoClip,
        AudioFileClip,
    )
    import numpy as np

    # Get audio duration
    audio_clip = None
    try:
        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration
    except Exception:
        total_duration = 30.0
        audio_clip = None

    product_name = "GroMo Training"
    category = "Financial Product"
    if product_data:
        product_name = product_data.get("name", product_name)
        category = product_data.get("category_name", product_data.get("sub_type", category))

    # Generate DALL-E background image
    logger.info(f"Generating DALL-E image for: {product_name}")
    image_bytes = generate_product_image(product_name, category)

    if image_bytes:
        try:
            from PIL import Image
            img = Image.open(BytesIO(image_bytes)).convert("RGB")
            img = img.resize((1280, 720), Image.LANCZOS)
            img_array = np.array(img)
            bg_clip = ImageClip(img_array, duration=total_duration)
            logger.info("DALL-E image generated successfully")
        except Exception as e:
            logger.error(f"Failed to process DALL-E image: {e}")
            bg_clip = ColorClip(size=(1280, 720), color=(20, 50, 100), duration=total_duration)
    else:
        logger.info("Using gradient background (DALL-E unavailable)")
        bg_clip = ColorClip(size=(1280, 720), color=(20, 50, 100), duration=total_duration)

    # Semi-transparent overlay for text readability
    overlay = ColorClip(
        size=(1280, 720), color=(0, 0, 0), duration=total_duration,
    ).with_opacity(0.4)

    clips = [bg_clip, overlay]

    # Title
    try:
        title = TextClip(
            text=product_name, font_size=48, color="white",
            duration=total_duration,
        ).with_position(("center", 280))
        clips.append(title)
    except Exception:
        pass

    # Category badge
    try:
        cat_text = TextClip(
            text=category, font_size=28, color="lightgray",
            duration=total_duration,
        ).with_position(("center", 350))
        clips.append(cat_text)
    except Exception:
        pass

    # Footer
    try:
        footer = TextClip(
            text="GroMo AI Trainer", font_size=20, color="gray",
            duration=total_duration,
        ).with_position(("center", 680))
        clips.append(footer)
    except Exception:
        pass

    video = CompositeVideoClip(clips, size=(1280, 720))
    if audio_clip:
        video = video.with_audio(audio_clip)

    if not output_path.endswith(".mp4"):
        output_path = output_path.rsplit(".", 1)[0] + ".mp4" if "." in output_path else output_path + ".mp4"

    video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
    video.close()
    if audio_clip:
        audio_clip.close()

    logger.info(f"DALL-E video saved to {output_path}")
    return output_path


def _generate_demo_video(
    audio_path: str,
    avatar_image_path: Optional[str],
    output_path: str,
) -> str:
    """Create a placeholder avatar video using moviepy 2.x."""
    from moviepy import ColorClip, TextClip, CompositeVideoClip, AudioFileClip

    audio_clip = None
    try:
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
    except Exception:
        duration = 30.0
        audio_clip = None

    bg_clip = ColorClip(size=(1280, 720), color=(30, 60, 120), duration=duration)
    clips = [bg_clip]

    try:
        avatar_text = TextClip(
            text="AVATAR", font_size=60, color="white",
            duration=duration,
        ).with_position("center")
        clips.append(avatar_text)
    except Exception:
        pass

    try:
        subtitle_text = TextClip(
            text="GroMo AI Trainer - Avatar Video Placeholder",
            font_size=28, color="lightgray",
            duration=duration,
        ).with_position(("center", 600))
        clips.append(subtitle_text)
    except Exception:
        pass

    video = CompositeVideoClip(clips, size=(1280, 720))
    if audio_clip:
        video = video.with_audio(audio_clip)

    if not output_path.endswith(".mp4"):
        output_path = output_path.rsplit(".", 1)[0] + ".mp4" if "." in output_path else output_path + ".mp4"

    video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
    video.close()
    if audio_clip:
        audio_clip.close()

    logger.info(f"Demo avatar video saved to {output_path}")
    return output_path

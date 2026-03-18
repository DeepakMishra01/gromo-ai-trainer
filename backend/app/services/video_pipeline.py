"""
Production video pipeline.
Generates professional training videos with:
- Per-slide DALL-E background images for visual richness
- Per-slide audio generation for perfect voice-slide sync
- Professional text overlays with proper typography
- Smooth transitions between slides
"""
import os
import re
import logging
import base64
import asyncio
from io import BytesIO
from typing import Optional, List, Dict, Any, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from app.config import settings

logger = logging.getLogger(__name__)

SLIDE_W, SLIDE_H = 1280, 720


# ── Font Helpers ──

_font_cache = {}

def _font(size: int, bold: bool = False):
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    paths = [
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                idx = 1 if bold and p.endswith(".ttc") else 0
                f = ImageFont.truetype(p, size, index=idx)
                _font_cache[key] = f
                return f
            except Exception:
                try:
                    f = ImageFont.truetype(p, size)
                    _font_cache[key] = f
                    return f
                except Exception:
                    continue
    f = ImageFont.load_default()
    _font_cache[key] = f
    return f


def _wrap(text: str, font, max_w: int) -> List[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = f"{cur} {w}".strip() if cur else w
        if font.getbbox(test)[2] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _draw_text(draw, text, x, y, font, color, max_w=1100, spacing=8, max_lines=15):
    """Draw wrapped text, return final Y."""
    for line in _wrap(text, font, max_w)[:max_lines]:
        draw.text((x, y), line, fill=color, font=font)
        y += font.getbbox(line)[3] + spacing
    return y


# ── DALL-E Image Generation ──

def _generate_slide_image(prompt: str) -> Optional[Image.Image]:
    """Generate a single slide background image via DALL-E 3."""
    if not settings.openai_api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1792x1024",
            quality="standard",
            n=1,
            response_format="b64_json",
        )
        img_bytes = base64.b64decode(resp.data[0].b64_json)
        img = Image.open(BytesIO(img_bytes)).convert("RGB")
        return img.resize((SLIDE_W, SLIDE_H), Image.LANCZOS)
    except Exception as e:
        logger.warning(f"DALL-E slide image failed: {e}")
        return None


def _build_dalle_prompts(slides_data: List[Dict]) -> List[str]:
    """Build unique DALL-E prompts for each slide based on content."""
    prompts = []
    for i, slide in enumerate(slides_data):
        stype = slide.get("type", "info")
        title = slide.get("title", "")

        base = (
            "Professional, modern presentation slide background. "
            "Clean minimalist design, NO text in image, subtle abstract elements. "
            "16:9 aspect ratio, suitable as a presentation background. "
        )

        type_styles = {
            "title": "Grand, impressive fintech hero image. Deep blue and purple gradient with gold accents. Abstract financial symbols floating. Premium corporate feel.",
            "benefits": "Bright, positive imagery. Green and blue tones. Abstract growth arrows, checkmarks, upward trends. Optimistic, rewarding atmosphere.",
            "how_works": "Step-by-step process visualization. Blue tones with connecting dots/lines. Abstract flowchart or pipeline imagery. Clean, organized feel.",
            "terms": "Professional, trustworthy imagery. Navy blue and silver tones. Abstract document/shield icons. Secure, reliable atmosphere.",
            "payout": "Wealth and earnings imagery. Gold and green tones. Abstract coin/money flow visualization. Prosperous, motivating feel.",
            "overview": "Informative, educational imagery. Blue and white tones. Abstract knowledge/information flow. Clear, enlightening atmosphere.",
            "cta": "Action-oriented, exciting imagery. Vibrant gradient of blue to green. Abstract rocket/arrow imagery. Energetic, motivating call-to-action feel.",
        }

        style = type_styles.get(stype, type_styles["overview"])
        prompts.append(f"{base}{style}")

    return prompts


# ── Slide Rendering with DALL-E backgrounds ──

def _gradient_bg(top=(15, 23, 42), bottom=(30, 58, 138)) -> Image.Image:
    """Create a gradient background image."""
    img = Image.new("RGB", (SLIDE_W, SLIDE_H))
    draw = ImageDraw.Draw(img)
    for y in range(SLIDE_H):
        r = int(top[0] + (bottom[0] - top[0]) * y / SLIDE_H)
        g = int(top[1] + (bottom[1] - top[1]) * y / SLIDE_H)
        b = int(top[2] + (bottom[2] - top[2]) * y / SLIDE_H)
        draw.line([(0, y), (SLIDE_W, y)], fill=(r, g, b))
    return img


THEME_GRADIENTS = [
    ((15, 23, 42), (30, 58, 138)),   # Deep blue
    ((15, 23, 42), (21, 94, 117)),   # Teal
    ((15, 23, 42), (88, 28, 135)),   # Purple
    ((15, 23, 42), (22, 78, 99)),    # Cyan
    ((15, 23, 42), (55, 48, 163)),   # Indigo
    ((15, 23, 42), (30, 70, 50)),    # Green
]

ACCENT_COLORS = [
    (59, 130, 246),   # Blue
    (34, 211, 238),   # Cyan
    (168, 85, 247),   # Purple
    (45, 212, 191),   # Teal
    (129, 140, 248),  # Indigo
    (34, 197, 94),    # Green
]


def _render_slide(
    slide_data: Dict,
    dalle_img: Optional[Image.Image],
    slide_num: int,
    total: int,
    product_name: str,
) -> Image.Image:
    """Render a single slide with DALL-E background or gradient fallback."""
    stype = slide_data.get("type", "info")
    title = slide_data.get("title", "")
    content = slide_data.get("content", "")
    payout = slide_data.get("payout", "")
    category = slide_data.get("category", "")

    theme_idx = (slide_num - 1) % len(THEME_GRADIENTS)
    accent = ACCENT_COLORS[theme_idx]

    # Background: DALL-E image or gradient
    if dalle_img:
        img = dalle_img.copy()
        # Add dark overlay for text readability
        overlay = Image.new("RGBA", (SLIDE_W, SLIDE_H), (0, 0, 0, 140))
        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay).convert("RGB")
    else:
        top, bottom = THEME_GRADIENTS[theme_idx]
        img = _gradient_bg(top, bottom)

    draw = ImageDraw.Draw(img)

    # Top accent bar
    draw.rectangle([0, 0, SLIDE_W, 4], fill=accent)

    if stype == "title":
        return _draw_title_slide(img, draw, product_name, category, payout, accent, slide_num, total)
    elif stype == "cta":
        return _draw_cta_slide(img, draw, product_name, payout, accent, slide_num, total)
    else:
        return _draw_content_slide(img, draw, title, content, stype, accent, product_name, slide_num, total)


def _draw_title_slide(img, draw, name, category, payout, accent, num, total):
    # Header
    draw.text((50, 30), "GroMo AI Trainer", fill=accent, font=_font(18, True))
    draw.text((SLIDE_W - 70, 30), f"{num}/{total}", fill=(148, 163, 184), font=_font(16))

    # Category badge
    if category:
        cat = category.upper()
        cw = _font(18, True).getbbox(cat)[2] + 30
        cx = (SLIDE_W - cw) // 2
        draw.rounded_rectangle([cx, 240, cx + cw, 270], radius=12, fill=accent)
        draw.text((cx + 15, 244), cat, fill=(255, 255, 255), font=_font(18, True))

    # Product name
    tf = _font(54, True)
    for i, line in enumerate(_wrap(name, tf, 1000)[:2]):
        lw = tf.getbbox(line)[2]
        draw.text(((SLIDE_W - lw) // 2, 300 + i * 68), line, fill=(255, 255, 255), font=tf)

    # Payout note (no specific amount — changes frequently)
    pt = "Check GroMo App for Latest Payout"
    pf = _font(24, True)
    pw = pf.getbbox(pt)[2] + 50
    px = (SLIDE_W - pw) // 2
    draw.rounded_rectangle([px, 470, px + pw, 520], radius=20, fill=(21, 128, 61))
    draw.text((px + 25, 480), pt, fill=(255, 255, 255), font=pf)

    # Footer
    ft = "Partner Training Video | Powered by GroMo AI"
    fw = _font(16).getbbox(ft)[2]
    draw.text(((SLIDE_W - fw) // 2, SLIDE_H - 45), ft, fill=(100, 116, 139), font=_font(16))

    return img


def _draw_cta_slide(img, draw, name, payout, accent, num, total):
    draw.text((SLIDE_W - 70, 30), f"{num}/{total}", fill=(148, 163, 184), font=_font(16))

    tf = _font(50, True)
    t = f"Sell {name}"
    for i, line in enumerate(_wrap(t, tf, 1000)[:2]):
        lw = tf.getbbox(line)[2]
        draw.text(((SLIDE_W - lw) // 2, 220 + i * 62), line, fill=(255, 255, 255), font=tf)

    sf = _font(38)
    st = "on GroMo App!"
    sw = sf.getbbox(st)[2]
    draw.text(((SLIDE_W - sw) // 2, 360), st, fill=accent, font=sf)

    pt = "Check GroMo App for Latest Payout!"
    pf = _font(24, True)
    pw = pf.getbbox(pt)[2] + 50
    px = (SLIDE_W - pw) // 2
    draw.rounded_rectangle([px, 430, px + pw, 480], radius=20, fill=(21, 128, 61))
    draw.text((px + 25, 440), pt, fill=(255, 255, 255), font=pf)

    hf = _font(30, True)
    ht = "Happy Selling!"
    hw = hf.getbbox(ht)[2]
    draw.text(((SLIDE_W - hw) // 2, SLIDE_H - 130), ht, fill=(34, 197, 94), font=hf)

    draw.text((SLIDE_W // 2 - 100, SLIDE_H - 45), "Powered by GroMo AI Trainer", fill=(100, 116, 139), font=_font(16))
    return img


def _draw_content_slide(img, draw, title, content, stype, accent, product_name, num, total):
    # Header bar
    draw.rectangle([0, 4, SLIDE_W, 65], fill=(5, 10, 20))
    draw.text((30, 22), product_name or "GroMo Training", fill=(148, 163, 184), font=_font(16))
    draw.text((SLIDE_W - 70, 22), f"{num}/{total}", fill=(148, 163, 184), font=_font(16))

    # Section title with accent bar
    draw.rectangle([50, 90, 55, 130], fill=accent)
    draw.text((70, 88), title or stype.replace("_", " ").title(), fill=(255, 255, 255), font=_font(34, True))

    # Content card
    card_y, card_b = 150, SLIDE_H - 55
    draw.rounded_rectangle([40, card_y, SLIDE_W - 40, card_b], radius=16, fill=(15, 25, 45, 200))

    # Parse content into bullet points
    lines = [l.strip() for l in content.split("\n") if l.strip()]
    y = card_y + 20
    content_x = 70
    max_w = SLIDE_W - 140

    for line in lines:
        if y > card_b - 40:
            draw.text((content_x, y), "...", fill=(148, 163, 184), font=_font(22))
            break

        # Check if bullet
        is_bullet = bool(re.match(r'^[-•→*]|\d+[\.\)]', line))
        clean = re.sub(r'^[-•→*]\s*', '', line)
        clean = re.sub(r'^\d+[\.\)]\s*', '', clean)

        if is_bullet:
            # Bullet dot
            draw.ellipse([content_x, y + 9, content_x + 10, y + 19], fill=accent)
            y = _draw_text(draw, clean, content_x + 22, y, _font(22), (203, 213, 225), max_w - 22, 6, 3)
            y += 4
        else:
            y = _draw_text(draw, clean, content_x, y, _font(22), (203, 213, 225), max_w, 6, 4)
            y += 8

    # Footer
    draw.text((SLIDE_W // 2 - 50, SLIDE_H - 35), "GroMo AI Trainer", fill=(70, 80, 100), font=_font(14))
    return img


# ── Per-Slide Audio Generation ──

def _generate_slide_audio(
    text: str,
    output_path: str,
    voice: str = "en-IN-NeerjaExpressiveNeural",
    rate: str = "-5%",
) -> str:
    """Generate audio for a single slide narration using Edge-TTS."""
    import edge_tts

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    async def _run():
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(output_path)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                pool.submit(lambda: asyncio.run(_run())).result(timeout=60)
        else:
            loop.run_until_complete(_run())
    except RuntimeError:
        asyncio.run(_run())

    return output_path


def _generate_slide_audio_sarvam(
    text: str,
    output_path: str,
    language: str = "hinglish",
    pace: float = 1.15,
    speaker: str = "anushka",
) -> str:
    """Generate audio for a single slide using Sarvam AI (handles Hinglish natively)."""
    import httpx

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    lang_code = {"hindi": "hi-IN", "hinglish": "hi-IN", "english": "en-IN"}.get(language, "hi-IN")

    # Sarvam v2 has a 500-char limit per input
    chunks = _split_text_for_sarvam(text, max_chars=480)
    chunk_audio_files = []

    for ci, chunk in enumerate(chunks):
        response = httpx.post(
            "https://api.sarvam.ai/text-to-speech",
            headers={
                "api-subscription-key": settings.sarvam_api_key,
                "Content-Type": "application/json",
            },
            json={
                "inputs": [chunk],
                "target_language_code": lang_code,
                "speaker": speaker,
                "model": "bulbul:v2",
                "pace": round(pace, 2),
                "enable_preprocessing": True,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        audios = data.get("audios", [])

        if audios:
            audio_bytes = base64.b64decode(audios[0])
            chunk_path = output_path.replace(".mp3", f"_chunk{ci}.wav")
            with open(chunk_path, "wb") as f:
                f.write(audio_bytes)
            chunk_audio_files.append(chunk_path)

    if not chunk_audio_files:
        return output_path

    if len(chunk_audio_files) == 1:
        # Single chunk — just rename/copy to output
        import shutil
        shutil.move(chunk_audio_files[0], output_path)
    else:
        # Multiple chunks — use ffmpeg to properly concatenate (avoids WAV header duplication)
        _ffmpeg_concat_audio(chunk_audio_files, output_path)
        # Cleanup temp chunk files
        for cf in chunk_audio_files:
            try:
                os.remove(cf)
            except OSError:
                pass

    return output_path


def _ffmpeg_concat_audio(input_files: List[str], output_path: str):
    """Properly concatenate audio files using moviepy (handles WAV headers correctly)."""
    from moviepy import AudioFileClip, concatenate_audioclips

    clips = []
    try:
        for fp in input_files:
            try:
                clip = AudioFileClip(fp)
                clips.append(clip)
            except Exception as e:
                logger.warning(f"Failed to load audio chunk {fp}: {e}")

        if not clips:
            logger.error("No audio chunks loaded for concatenation")
            import shutil
            shutil.copy2(input_files[0], output_path)
            return

        combined = concatenate_audioclips(clips)
        combined.write_audiofile(output_path, logger=None)
        combined.close()
    finally:
        for c in clips:
            try:
                c.close()
            except Exception:
                pass


def _split_text_for_sarvam(text: str, max_chars: int = 480) -> List[str]:
    """Split text into chunks for Sarvam API v2 (max 500 chars per request)."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    sentences = re.split(r'(?<=[.!?।])\s+', text)
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}".strip() if current else sentence
        else:
            if current:
                chunks.append(current)
            current = sentence[:max_chars]  # Truncate if single sentence too long

    if current:
        chunks.append(current)

    return chunks or [text[:max_chars]]


# ── Script-to-Slides Parser ──

def _parse_script_to_slides(
    script_text: str,
    product_data: Dict,
) -> List[Dict]:
    """
    Parse AI-generated script into slide sections.
    Returns list of dicts with: type, title, content, narration
    """
    product_name = product_data.get("name", "Financial Product")
    category = product_data.get("category_name", product_data.get("sub_type", ""))
    payout = product_data.get("payout", "")

    slides = []

    # Title slide
    slides.append({
        "type": "title",
        "title": product_name,
        "content": "",
        "category": category,
        "payout": payout,
        "narration": "",  # Will be filled from script
    })

    # Split script into sections
    sections = re.split(r'\n\n+', script_text.strip())

    # Classify each section
    for section in sections:
        section = section.strip()
        if not section or len(section) < 20:
            continue

        # Detect section type
        lower = section.lower()
        if any(w in lower for w in ["namaste", "hello", "welcome", "aaj hum"]):
            slides[0]["narration"] = section  # Attach to title
            continue

        stype = "overview"
        stitle = "Product Overview"

        if any(w in lower for w in ["benefit", "fayda", "advantage", "key point"]):
            stype = "benefits"
            stitle = "Key Benefits"
        elif any(w in lower for w in ["how to", "kaise", "process", "step", "tarika", "how it works"]):
            stype = "how_works"
            stitle = "How It Works"
        elif any(w in lower for w in ["terms", "condition", "eligib", "sharten", "requirement"]):
            stype = "terms"
            stitle = "Terms & Conditions"
        elif any(w in lower for w in ["payout", "earn", "commission", "kamai", "income"]):
            stype = "payout"
            stitle = "Partner Earnings"
        elif any(w in lower for w in ["happy selling", "download", "start selling", "call to action"]):
            continue  # CTA - handled by the closing slide
        elif any(w in lower for w in ["product overview", "overview", "about"]):
            stype = "overview"
            stitle = "Product Overview"

        # Extract display content (short bullet points for slides)
        display = _extract_display_content(section, product_data, stype)

        slides.append({
            "type": stype,
            "title": stitle,
            "content": display,
            "narration": section,
            "payout": payout,
        })

    # CTA slide
    slides.append({
        "type": "cta",
        "title": "Start Selling!",
        "content": "",
        "payout": payout,
        "narration": f"Toh partners, aaj hi GroMo App pe {product_name} ki selling shuru karein! Latest payout ke liye GroMo App check karein. Happy Selling!",
    })

    # If title has no narration, create one
    if not slides[0]["narration"]:
        slides[0]["narration"] = f"Namaste GroMo partners! Aaj hum baat karenge {product_name} ke baare mein."

    return slides


def _extract_display_content(narration: str, product_data: Dict, stype: str) -> str:
    """Extract concise bullet points for slide display from narration text."""
    # For benefits/how_works/terms, prefer real product data over narration
    if stype == "benefits":
        raw = product_data.get("benefits_text", "")
        if raw:
            lines = [l.strip() for l in raw.split("\n") if l.strip()]
            return "\n".join(f"• {l}" for l in lines[:8])

    if stype == "how_works":
        raw = product_data.get("how_works_text", "")
        if raw:
            lines = [l.strip() for l in raw.split("\n") if l.strip()]
            return "\n".join(f"• {l}" for l in lines[:10])

    if stype == "terms":
        raw = product_data.get("terms_conditions_text", "")
        if raw:
            lines = [l.strip() for l in raw.split("\n") if l.strip()]
            return "\n".join(f"• {l}" for l in lines[:8])

    # Fallback: extract key sentences from narration
    sentences = re.split(r'[.!?।]+', narration)
    bullets = []
    for s in sentences:
        s = s.strip()
        if len(s) > 15 and len(s) < 150:
            # Remove script markers
            s = re.sub(r'\[.*?\]', '', s).strip()
            if s:
                bullets.append(f"• {s}")
        if len(bullets) >= 6:
            break

    return "\n".join(bullets) if bullets else narration[:400]


# ── Pre-process narration for TTS ──

def _clean_narration(text: str) -> str:
    """Clean narration text for TTS — remove markers, fix pronunciation.

    Ensures output is pure Roman script suitable for Sarvam TTS:
    no emojis, no Devanagari, no special Unicode characters.
    """
    # Step 1: Remove all emojis and special Unicode symbols
    # Covers emoticons, dingbats, symbols, pictographs, flags, etc.
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed chars
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols extended-A
        "\U00002600-\U000026FF"  # misc symbols
        "\U0000FE00-\U0000FE0F"  # variation selectors
        "\U0000200D"             # zero width joiner
        "\U00002B50-\U00002B55"  # stars
        "\U0000200B-\U0000200F"  # zero-width chars
        "\U0000231A-\U0000231B"  # watch/hourglass
        "\U000023E9-\U000023F3"  # media controls
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub(' ', text)

    # Step 2: Convert Devanagari text to remove it (TTS can't pronounce it properly)
    # Remove Devanagari Unicode block (0900-097F) and extensions
    text = re.sub(r'[\u0900-\u097F\u0980-\u09FF\uA8E0-\uA8FF]+', ' ', text)

    # Step 3: Remove script markers and formatting
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'[#*_]{1,3}', '', text)
    text = re.sub(r'^[-•→✅❌►▸▹◆◇★☆]\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\(.*?\)', '', text)  # Remove parenthetical notes
    text = re.sub(r'\|', ', ', text)  # Pipe separators to commas

    # Step 4: Fix currency and symbols
    text = text.replace('₹', 'rupees ')
    text = text.replace('Rs.', 'rupees ')
    text = text.replace('Rs ', 'rupees ')
    text = re.sub(r'rupees\s*(\d)', r'rupees \1', text)
    text = text.replace('%', ' percent')
    text = text.replace('&', ' and ')
    text = re.sub(r'/\s*month', ' per month', text)
    text = re.sub(r'/\s*year', ' per year', text)
    text = re.sub(r'/\s*day', ' per day', text)
    text = text.replace('/', ' or ')
    text = text.replace('~', 'approximately ')
    text = text.replace('+', ' plus ')
    text = text.replace('=', ' equals ')
    text = text.replace('>', ' se zyada ')
    text = text.replace('<', ' se kam ')

    # Step 5: Expand number formatting: 3,00,000 → 3 lakh, 50,00,000 → 50 lakh
    text = re.sub(r'(\d+),00,00,000', lambda m: f"{m.group(1)} crore", text)
    text = re.sub(r'(\d+),00,000', lambda m: f"{m.group(1)} lakh", text)
    text = re.sub(r'(\d+),000', lambda m: f"{m.group(1)} hazaar", text)
    # Remove remaining commas inside numbers: 7,500 → 7500
    text = re.sub(r'(\d),(\d)', r'\1\2', text)

    # Step 6: Expand abbreviations for clear pronunciation
    # Use hyphenated letters for Sarvam TTS (reads "Kay-Why-See" better than "K Y C")
    # Use spaced phonetics (NOT hyphens — Sarvam TTS loops on hyphens)
    abbrevs = {
        'KYC': 'ke wai see',
        'eKYC': 'ee ke wai see',
        'OTP': 'oh tee pee',
        'EMI': 'ee em ai',
        'SIP': 'sip',
        'UPI': 'you pee ai',
        'FnO': 'ef and oh',
        'F&O': 'ef and oh',
        'IPO': 'ai pee oh',
        'NRI': 'en aar ai',
        'DOB': 'date of birth',
        'PAN card': 'paan card',
        'PAN Card': 'paan card',
        'PAN': 'paan',
        'ATM': 'ay tee em',
        'SFB': 'es ef bee',
        'AU SFB': 'ay you es ef bee',
        'CIBIL': 'sibil',
        'NBFC': 'en bee ef see',
        'GST': 'jee es tee',
        'ITR': 'ai tee aar',
        'PF': 'pee ef',
        'EPF': 'ee pee ef',
        'FD': 'ef dee',
        'RD': 'aar dee',
        'MF': 'mutual fund',
        'p.a.': 'per annum',
        'yrs': 'years',
        'yr': 'year',
        'mins': 'minutes',
        'min': 'minimum',
        'max': 'maximum',
        'amt': 'amount',
        'txn': 'transaction',
        'govt': 'government',
        'approx': 'approximately',
        'info': 'information',
        'ref': 'reference',
        'req': 'required',
        'pvt': 'private',
        'ltd': 'limited',
        'cr': 'crore',
        'lacs': 'lakhs',
    }
    for a, e in abbrevs.items():
        text = re.sub(r'\b' + re.escape(a) + r'\b', e, text)

    # Step 7a: Replace Hindi words that Sarvam preprocessing mangles
    # These Hindi words get mispronounced badly (e.g., "kamaai" → "kheti")
    # Replace with English equivalents that Sarvam handles correctly
    hindi_to_english = {
        'kamaai': 'earning',
        'kamaayi': 'earning',
        'kamai': 'earning',
        'kamao': 'earn karo',
        'kamayein': 'earn karein',
        'kamaana': 'earn karna',
        'kamana': 'earn karna',
        'bechna': 'sell karna',
        'becho': 'sell karo',
        'bechein': 'sell karein',
        'bechne': 'sell karne',
        'khareedna': 'buy karna',
        'khareedein': 'buy karein',
        'khareedo': 'buy karo',
        'khareedne': 'buy karne',
        'kheti': 'selling',
        'padhiye': 'read kariye',
        'samjhiye': 'samajh lijiye',
    }
    for hindi, eng in hindi_to_english.items():
        text = re.sub(r'\b' + re.escape(hindi) + r'\b', eng, text, flags=re.IGNORECASE)

    # Step 7b: Fix English words that Sarvam truly mispronounces
    english_pronunciation = {
        'demat': 'dee mat',
        'Demat': 'dee mat',
        'profile': 'pro file',
        'surcharge': 'sur charge',
        'lifetime': 'life time',
        'cashback': 'cash back',
        'waiver': 'weyver',
        'features': 'feechers',
        'feature': 'feecher',
    }
    for eng, phonetic in english_pronunciation.items():
        text = re.sub(r'\b' + re.escape(eng) + r'\b', phonetic, text, flags=re.IGNORECASE)

    # Step 8: Fix brand/product name pronunciation
    brand_fixes = {
        'GroMo': 'Gromo',
        'GROMO': 'Gromo',
        '5paisa': 'paanch paisa',
        '5Paisa': 'paanch paisa',
        'Zerodha': 'Zerodha',
        'Groww': 'Gro',
        'Paytm': 'Pay Tee Em',
        'PhonePe': 'Phone Pay',
        'mPokket': 'Em Pokket',
        'Fi Money': 'Fai Money',
        'BajajFinserv': 'Bajaaj Finserv',
        'Bajaj Finserv': 'Bajaaj Finserv',
        'HDFC': 'aich dee ef see',
        'ICICI': 'ai see ai see ai',
        'SBI': 'es bee ai',
        'IndusInd': 'Indus Ind',
        'Kotak': 'Kotak',
        'Aadhaar': 'Aadhaar',
        'Aadhar': 'Aadhaar',
        'AU Small Finance Bank': 'ay you Small Finance Bank',
        'AU SFB': 'ay you es ef bee',
        'AU Bank': 'ay you Bank',
    }
    for brand, fix in brand_fixes.items():
        text = text.replace(brand, fix)

    # Step 9: Fix common doubling/pronunciation issues
    text = re.sub(r'paan card\s+card', 'paan card', text, flags=re.IGNORECASE)
    # Fix standalone "AU" that wasn't caught by brand_fixes (e.g. "AU credit card")
    text = re.sub(r'\bAU\b', 'ay you', text)

    # Step 9b: Remove any specific payout amounts that slipped through
    # Payouts change frequently — replace with "check GroMo App" message
    text = re.sub(
        r'(?:Partner\s+)?[Pp]ayout[:\s]+(?:rupees\s*)?[\d,]+(?:\s*(?:per\s+\w+)?)?',
        'check Gromo app for latest payout',
        text,
    )
    text = re.sub(
        r'(?:earn|kamayein|kamao|milega|milte hain|milenge)\s+(?:rupees\s*)?[\d,]+(?:\s*(?:rupees|per\s+\w+|commission|tak))?',
        'check Gromo app for latest payout',
        text, flags=re.IGNORECASE,
    )
    text = re.sub(
        r'rupees\s*[\d,]+\s*(?:ki\s+)?(?:kamai|kamaai|earning|earnings|commission|payout|milte|milega|mil\b)',
        'check Gromo app for latest payout',
        text, flags=re.IGNORECASE,
    )
    # Catch patterns like "aapko rupees 750" or "aapki rupees 7500"
    text = re.sub(
        r'(?:aapko|aapki|apni)\s+rupees\s*[\d,]+',
        'aapki achhi kamaai',
        text, flags=re.IGNORECASE,
    )
    # Catch "rupees X kama/earn" patterns
    text = re.sub(
        r'rupees\s*[\d,]+\s*(?:kama|earn|tak)',
        'achhi income kama',
        text, flags=re.IGNORECASE,
    )

    # Step 10: Remove any remaining non-ASCII characters (safety net)
    # Keep only printable ASCII + basic punctuation
    text = re.sub(r'[^\x20-\x7E]', ' ', text)

    # Step 11: Clean up whitespace and punctuation
    text = re.sub(r'\n+', '. ', text)
    text = re.sub(r'\.\s*\.', '.', text)
    text = re.sub(r',\s*,', ',', text)
    # Remove hyphens — Sarvam TTS loops/glitches on hyphenated words
    text = text.replace('-', ' ')
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\s+([.,!?])', r'\1', text)
    text = re.sub(r'([.,!?])\1+', r'\1', text)  # Remove repeated punctuation

    return text.strip()


# ── Main Pipeline ──

def generate_production_video(
    product_data: Dict,
    script_text: str,
    output_dir: str,
    language: str = "hinglish",
    voice_name: str = "en-IN-NeerjaExpressiveNeural",
    on_progress=None,
    gamma_slide_images: Optional[List[str]] = None,
    gamma_slide_texts: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Generate a production-quality training video.

    If gamma_slide_images are provided (from Gamma AI PPTX), uses those
    as the visual slides — they are already beautifully designed.
    Otherwise, generates DALL-E background images + text overlay slides.

    Returns:
        Dict with: video_path, audio_path, slide_paths, duration, num_slides
    """
    os.makedirs(output_dir, exist_ok=True)

    product_name = product_data.get("name", "Product")
    using_gamma = bool(gamma_slide_images and len(gamma_slide_images) > 0)

    slides_dir = os.path.join(output_dir, "slides")
    audio_dir = os.path.join(output_dir, "audio_chunks")
    os.makedirs(slides_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    # Decide TTS engine: Sarvam for Hinglish/Hindi (native support), Edge-TTS for English
    use_sarvam = (
        language.lower() in ("hinglish", "hindi")
        and settings.sarvam_api_key
    )
    tts_engine = "sarvam" if use_sarvam else "edge-tts"
    logger.info(f"TTS engine: {tts_engine} (language={language})")

    def _gen_audio_for_slide(text: str, out_path: str):
        """Generate audio using the best TTS for the language."""
        if use_sarvam:
            return _generate_slide_audio_sarvam(
                text, out_path, language=language, pace=1.0, speaker="anushka",
            )
        else:
            return _generate_slide_audio(
                text, out_path, voice=voice_name, rate="+8%",
            )

    if using_gamma:
        # ── Gamma Slide Path ──
        logger.info(f"Using {len(gamma_slide_images)} Gamma AI slides for: {product_name}")
        slide_images = gamma_slide_images
        num_slides = len(slide_images)

        if on_progress:
            on_progress(10, f"Using {num_slides} Gamma slides")

        # Parse script into sections matching the number of Gamma slides
        # Use actual slide content for perfect sync when available
        narration_sections = _split_script_for_gamma_slides(
            script_text, num_slides, slide_texts=gamma_slide_texts,
        )

        if on_progress:
            on_progress(15, "Matched narration to slides")

        # Generate per-slide audio
        logger.info(f"Generating per-slide audio ({tts_engine}) for {num_slides} Gamma slides...")
        slide_audios = []
        for i, narration in enumerate(narration_sections):
            clean_text = _clean_narration(narration)
            if not clean_text or len(clean_text) < 5:
                clean_text = f"Aaiye is section ko dekhte hain {product_name} ke baare mein."

            audio_path = os.path.join(audio_dir, f"slide_{i+1:03d}.mp3")
            try:
                _gen_audio_for_slide(clean_text, audio_path)
                slide_audios.append(audio_path)
                logger.info(f"Audio for Gamma slide {i+1}: {len(clean_text)} chars")
            except Exception as e:
                logger.error(f"Audio gen failed for Gamma slide {i+1}: {e}")
                # Fallback to Edge-TTS if Sarvam fails
                try:
                    _generate_slide_audio(clean_text, audio_path, voice=voice_name, rate="+8%")
                    slide_audios.append(audio_path)
                except Exception:
                    slide_audios.append(None)

            if on_progress:
                pct = 15 + int(50 * (i + 1) / num_slides)
                on_progress(pct, f"Generated audio {i+1}/{num_slides}")

    else:
        # ── DALL-E Slide Path (original pipeline) ──
        logger.info(f"Parsing script into slides for: {product_name}")
        slides = _parse_script_to_slides(script_text, product_data)
        num_slides = len(slides)
        logger.info(f"Created {num_slides} slides")

        if on_progress:
            on_progress(10, "Parsed script into slides")

        # Generate DALL-E background images
        logger.info("Generating DALL-E background images...")
        dalle_prompts = _build_dalle_prompts(slides)
        dalle_images = []

        for i, prompt in enumerate(dalle_prompts):
            logger.info(f"Generating DALL-E image {i+1}/{len(dalle_prompts)}...")
            img = _generate_slide_image(prompt)
            dalle_images.append(img)
            if on_progress:
                pct = 10 + int(30 * (i + 1) / len(dalle_prompts))
                on_progress(pct, f"Generated image {i+1}/{len(dalle_prompts)}")

        # Generate per-slide audio
        logger.info(f"Generating per-slide audio ({tts_engine})...")
        slide_audios = []
        for i, slide in enumerate(slides):
            narration = _clean_narration(slide.get("narration", ""))
            if not narration or len(narration) < 5:
                narration = f"Aaiye is section ko dekhte hain {slide.get('title', 'is topic')} ke baare mein."

            audio_path = os.path.join(audio_dir, f"slide_{i+1:03d}.mp3")
            try:
                _gen_audio_for_slide(narration, audio_path)
                slide_audios.append(audio_path)
                logger.info(f"Audio for slide {i+1}: {len(narration)} chars")
            except Exception as e:
                logger.error(f"Audio gen failed for slide {i+1}: {e}")
                slide_audios.append(None)

            if on_progress:
                pct = 40 + int(25 * (i + 1) / len(slides))
                on_progress(pct, f"Generated audio {i+1}/{len(slides)}")

        # Render slide images with DALL-E backgrounds
        logger.info("Rendering slide images...")
        slide_images = []
        for i, (slide, dalle_img) in enumerate(zip(slides, dalle_images)):
            img = _render_slide(slide, dalle_img, i + 1, len(slides), product_name)
            path = os.path.join(slides_dir, f"slide_{i+1:03d}.png")
            img.save(path, "PNG", quality=95)
            slide_images.append(path)

    if on_progress:
        on_progress(70, "All slides and audio ready")

    # Compose final video with synced audio
    logger.info("Composing final video with synced audio...")
    final_path = os.path.join(output_dir, "final.mp4")
    result = _compose_synced_video(slide_images, slide_audios, final_path)

    if on_progress:
        on_progress(95, "Video composition complete")

    # Concatenate all audio into one file
    combined_audio = os.path.join(output_dir, "audio.mp3")
    _concat_audio_files([a for a in slide_audios if a and os.path.exists(a)], combined_audio)

    source = "Gamma AI" if using_gamma else "DALL-E"
    logger.info(f"Production video complete ({source}): {final_path}")

    return {
        "video_path": final_path,
        "audio_path": combined_audio,
        "slide_paths": slide_images,
        "duration": result.get("duration", 0),
        "num_slides": num_slides,
        "source": source,
    }


def _split_script_for_gamma_slides(
    script_text: str,
    num_slides: int,
    slide_texts: Optional[List[Dict]] = None,
) -> List[str]:
    """
    Generate per-slide narration matched to actual slide content.

    Uses OpenAI GPT to generate natural, conversational Hinglish narration
    that sounds like a real human trainer — NOT a bullet-point reader.
    """
    # If we have actual slide content, use LLM to generate natural narration
    if slide_texts and len(slide_texts) == num_slides:
        return _generate_llm_narration(slide_texts)

    # Fallback: split script text to match slides
    sections = re.split(r'\[(?:SLIDE|INTRO|Screen|CTA).*?\]', script_text)
    sections = [s.strip() for s in sections if s.strip()]

    if len(sections) <= 1:
        sections = [s.strip() for s in script_text.split("\n\n") if s.strip()]

    if not sections:
        return [f"Aaiye is training ko shuru karte hain."] * num_slides

    # Match to num_slides
    if len(sections) >= num_slides:
        result = sections[:num_slides - 1]
        result.append(" ".join(sections[num_slides - 1:]))
        return result

    # Need more sections — split the longest ones
    while len(sections) < num_slides:
        longest_idx = max(range(len(sections)), key=lambda i: len(sections[i]))
        text = sections[longest_idx]
        mid = len(text) // 2
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
        sections.insert(longest_idx + 1, part2 or "Aaiye agle point ko dekhte hain.")

    return sections[:num_slides]


def _generate_llm_narration(slide_texts: List[Dict]) -> List[str]:
    """
    Use OpenAI GPT to generate natural, conversational Hinglish narration
    for each slide. The narration should sound like a real trainer explaining
    the product — NOT reading bullet points.
    """
    if not settings.openai_api_key:
        logger.warning("No OpenAI key for LLM narration, using basic fallback")
        return _basic_narration_fallback(slide_texts)

    # Build slide content summary for the LLM
    slides_summary = []
    for i, st in enumerate(slide_texts):
        title = st.get("title", "").strip()
        content = st.get("content", "").strip()
        slides_summary.append(f"Slide {i+1}: Title: {title}\nContent: {content}")

    slides_block = "\n\n".join(slides_summary)

    prompt = f"""You are a professional GroMo training video narrator. Generate natural, conversational Hinglish narration for each slide of a training presentation.

RULES:
1. Write in Romanized Hinglish (Hindi words in English script mixed with English). Example: "Namaste partners! Aaj hum baat karenge ek bahut hi achi product ke baare mein."
2. DO NOT just read the bullet points. Instead, EXPLAIN the content naturally like a real trainer would.
3. Add natural transitions between points — "Sabse pehle...", "Iske alawa...", "Ab baat karte hain...", "Aur suniye..."
4. Keep each slide narration 4-7 sentences long (50-100 words). Explain the key points thoroughly — cover ALL important details shown on the slide. Do not rush or skip information.
5. First slide should be a warm welcome/intro. Last slide should be a motivating CTA ending with "Toh aaj hi GroMo App pe selling shuru karein! Happy Selling!"
6. NEVER mention any specific payout amount (like Rs 750, Rs 500, etc.) because payouts change frequently. Instead say "latest payout ke liye GroMo App check karein" or "updated payout GroMo App pe dekh sakte hain".
7. DO NOT use any emojis, special characters, Devanagari script, or markdown formatting.
8. DO NOT use symbols like |, *, #, →, •, ✅, 💳, etc.
9. Write ONLY in simple Roman English alphabet. Numbers are okay for non-payout data (like age, income limits).
10. Sound enthusiastic and motivating — you're training sales partners to sell financial products.
11. IMPORTANT — Use ENGLISH words for actions instead of Hindi equivalents. This is critical for correct pronunciation:
    - Use "selling" or "sell" instead of "bechna/becho"
    - Use "earning" or "earn" instead of "kamaai/kamao/kamana"
    - Use "buying" or "buy" instead of "khareedna/khareedo"
    - Use "start" or "shuru" for beginning something
    - Mix simple Hindi connector words (aaj, aur, bahut, achi, ke liye, etc.) with English nouns and verbs.
    - Example good CTA: "Toh aaj hi GroMo App pe selling shuru karein! Happy Selling!"
    - Example bad CTA: "Toh aaj hi bechna shuru karo aur kamaai karo!" (DO NOT write like this)

SLIDES:
{slides_block}

Generate exactly {len(slide_texts)} narrations, one per slide. Output format — each narration on its own line, separated by "---":

Narration for slide 1
---
Narration for slide 2
---
...and so on"""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a GroMo training video narrator. Write natural Hinglish narration in Roman script only. No emojis, no Devanagari, no special characters."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=3000,
        )

        raw = response.choices[0].message.content.strip()
        logger.info(f"LLM narration generated: {len(raw)} chars")

        # Parse the "---" separated narrations
        parts = [p.strip() for p in raw.split("---") if p.strip()]

        # Remove any leading "Narration for slide N:" prefix
        cleaned = []
        for p in parts:
            p = re.sub(r'^(?:Narration\s+for\s+)?[Ss]lide\s*\d+\s*[:\.]\s*', '', p).strip()
            if p:
                cleaned.append(p)

        if len(cleaned) >= len(slide_texts):
            return cleaned[:len(slide_texts)]
        elif len(cleaned) > 0:
            # Pad with basic fallback if LLM returned fewer sections
            while len(cleaned) < len(slide_texts):
                idx = len(cleaned)
                title = slide_texts[idx].get("title", "")
                cleaned.append(f"Ab baat karte hain {title} ke baare mein.")
            return cleaned
        else:
            logger.warning("LLM returned unparseable narration, using fallback")
            return _basic_narration_fallback(slide_texts)

    except Exception as e:
        logger.error(f"LLM narration generation failed: {e}")
        return _basic_narration_fallback(slide_texts)


def _basic_narration_fallback(slide_texts: List[Dict]) -> List[str]:
    """Basic narration fallback when LLM is unavailable."""
    narrations = []
    num = len(slide_texts)
    for i, st in enumerate(slide_texts):
        title = st.get("title", "")
        content = st.get("content", "")

        if i == 0:
            narration = f"Namaste GroMo partners! Aaj hum baat karenge {title} ke baare mein."
        elif i == num - 1:
            narration = f"{title}. Toh aaj hi GroMo app pe is product ko bechna shuru karein! Latest payout ke liye GroMo App check karein."
        else:
            narration = f"Ab baat karte hain {title} ki."
            if content:
                points = [p.strip() for p in content.split("|") if p.strip()]
                # Take only first 3 points and frame them naturally
                for j, pt in enumerate(points[:3]):
                    clean_pt = re.sub(r'[^\w\s.,!?₹%&\'-]', '', pt).strip()
                    if clean_pt:
                        if j == 0:
                            narration += f" Sabse pehle, {clean_pt}."
                        elif j == 1:
                            narration += f" Iske alawa, {clean_pt}."
                        else:
                            narration += f" Aur {clean_pt}."

        narrations.append(narration or f"Aaiye slide {i+1} ko dekhte hain.")
    return narrations


def _compose_synced_video(
    slide_images: List[str],
    slide_audios: List[Optional[str]],
    output_path: str,
) -> Dict:
    """Compose video with each slide shown for its audio duration."""
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips

    clips = []
    total_duration = 0

    for i, (img_path, audio_path) in enumerate(zip(slide_images, slide_audios)):
        # Get audio duration
        audio_clip = None
        duration = 5.0  # fallback

        if audio_path and os.path.exists(audio_path):
            try:
                audio_clip = AudioFileClip(audio_path)
                duration = audio_clip.duration + 0.5  # Add 0.5s pause between slides
                # Only cap truly extreme durations (corrupted/looping audio)
                if duration > 60:
                    logger.warning(f"Slide {i+1} audio suspiciously long ({duration:.1f}s), likely corrupted — capping at 45s")
                    audio_clip = audio_clip.subclipped(0, 45)
                    duration = 45.5
                else:
                    logger.info(f"Slide {i+1} audio duration: {duration:.1f}s")
            except Exception:
                duration = 5.0
                audio_clip = None

        # Create image clip
        try:
            pil_img = Image.open(img_path).convert("RGB").resize((SLIDE_W, SLIDE_H), Image.LANCZOS)
            img_array = np.array(pil_img)
            clip = ImageClip(img_array, duration=duration)

            if audio_clip:
                # Pad audio with silence at end for the pause
                clip = clip.with_audio(audio_clip)

            clips.append(clip)
            total_duration += duration
        except Exception as e:
            logger.error(f"Failed to create clip for slide {i+1}: {e}")

    if not clips:
        raise ValueError("No video clips created")

    # Concatenate
    final = concatenate_videoclips(clips, method="compose")

    if not output_path.endswith(".mp4"):
        output_path += ".mp4"

    final.write_videofile(
        output_path, fps=24, codec="libx264", audio_codec="aac",
        logger=None,
    )

    # Cleanup
    final.close()
    for c in clips:
        c.close()

    logger.info(f"Synced video: {output_path} ({total_duration:.1f}s, {len(clips)} slides)")
    return {"duration": total_duration, "path": output_path}


def _concat_audio_files(audio_paths: List[str], output_path: str):
    """Concatenate MP3 files by appending bytes."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as out:
        for path in audio_paths:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    out.write(f.read())
    logger.info(f"Combined audio: {output_path} ({len(audio_paths)} chunks)")

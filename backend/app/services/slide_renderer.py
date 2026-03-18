"""
Slide renderer service.
Converts PPTX slide data into professional PNG images using PIL.
Each slide image is used as a video frame in the final training video.
"""
import os
import re
import logging
import textwrap
from typing import Optional, List, Dict, Any, Tuple

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# ── Dimensions ──
SLIDE_W, SLIDE_H = 1280, 720

# ── Color Palette (GroMo branded) ──
COLORS = {
    "bg_dark": (15, 23, 42),       # slate-900
    "bg_medium": (30, 41, 59),     # slate-800
    "bg_card": (51, 65, 85),       # slate-700
    "accent": (59, 130, 246),      # blue-500
    "accent_light": (96, 165, 250),# blue-400
    "accent_dark": (29, 78, 216),  # blue-700
    "green": (34, 197, 94),        # green-500
    "orange": (249, 115, 22),      # orange-500
    "purple": (168, 85, 247),      # purple-500
    "white": (255, 255, 255),
    "light_gray": (203, 213, 225), # slate-300
    "mid_gray": (148, 163, 184),   # slate-400
    "dark_gray": (100, 116, 139),  # slate-500
}

# Slide type colors for visual variety
SLIDE_THEMES = [
    {"gradient_top": (15, 23, 42), "gradient_bottom": (30, 58, 138), "accent": (59, 130, 246)},    # Blue
    {"gradient_top": (15, 23, 42), "gradient_bottom": (21, 94, 117), "accent": (34, 211, 238)},    # Cyan
    {"gradient_top": (15, 23, 42), "gradient_bottom": (88, 28, 135), "accent": (168, 85, 247)},    # Purple
    {"gradient_top": (15, 23, 42), "gradient_bottom": (22, 78, 99), "accent": (45, 212, 191)},     # Teal
    {"gradient_top": (15, 23, 42), "gradient_bottom": (30, 58, 138), "accent": (96, 165, 250)},    # Light Blue
    {"gradient_top": (15, 23, 42), "gradient_bottom": (55, 48, 163), "accent": (129, 140, 248)},   # Indigo
]

# ── Font loading ──
_font_cache: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}

def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load font, caching for reuse."""
    key = (f"{'bold' if bold else 'regular'}", size)
    if key in _font_cache:
        return _font_cache[key]

    font_paths = [
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/ArialHB.ttc",
        "/System/Library/Fonts/Avenir Next.ttc",
    ]

    font = None
    for path in font_paths:
        if os.path.exists(path):
            try:
                # For .ttc files, index 0 = regular, index 1 = bold (varies)
                idx = 1 if bold and path.endswith(".ttc") else 0
                font = ImageFont.truetype(path, size, index=idx)
                break
            except Exception:
                try:
                    font = ImageFont.truetype(path, size)
                    break
                except Exception:
                    continue

    if font is None:
        font = ImageFont.load_default()

    _font_cache[key] = font
    return font


def _draw_gradient(img: Image.Image, top_color: Tuple, bottom_color: Tuple):
    """Draw a vertical gradient on the image."""
    draw = ImageDraw.Draw(img)
    for y in range(SLIDE_H):
        ratio = y / SLIDE_H
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        draw.line([(0, y), (SLIDE_W, y)], fill=(r, g, b))


def _draw_rounded_rect(draw: ImageDraw.Draw, xy: Tuple, radius: int, fill: Tuple, outline: Optional[Tuple] = None):
    """Draw a rounded rectangle."""
    x1, y1, x2, y2 = xy
    # Draw the main rectangle
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill, outline=None)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill, outline=None)
    # Draw corners
    draw.pieslice([x1, y1, x1 + 2*radius, y1 + 2*radius], 180, 270, fill=fill)
    draw.pieslice([x2 - 2*radius, y1, x2, y1 + 2*radius], 270, 360, fill=fill)
    draw.pieslice([x1, y2 - 2*radius, x1 + 2*radius, y2], 90, 180, fill=fill)
    draw.pieslice([x2 - 2*radius, y2 - 2*radius, x2, y2], 0, 90, fill=fill)
    if outline:
        draw.rounded_rectangle(xy, radius=radius, outline=outline, width=1)


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """Wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip() if current_line else word
        bbox = font.getbbox(test_line)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines if lines else [""]


def _draw_text_block(
    draw: ImageDraw.Draw,
    text: str,
    x: int, y: int,
    font: ImageFont.FreeTypeFont,
    color: Tuple,
    max_width: int = 1100,
    line_spacing: int = 8,
    max_lines: int = 20,
) -> int:
    """Draw wrapped text block. Returns the Y position after the text."""
    lines = _wrap_text(text, font, max_width)
    for i, line in enumerate(lines[:max_lines]):
        draw.text((x, y), line, fill=color, font=font)
        bbox = font.getbbox(line)
        y += (bbox[3] - bbox[1]) + line_spacing
    return y


# ── Slide Renderers ──

def render_title_slide(
    product_name: str,
    category: str,
    payout: str = "",
    slide_num: int = 1,
    total_slides: int = 1,
) -> Image.Image:
    """Render a professional title slide."""
    img = Image.new("RGB", (SLIDE_W, SLIDE_H))
    _draw_gradient(img, (15, 23, 42), (30, 58, 138))
    draw = ImageDraw.Draw(img)

    # Decorative accent bar at top
    draw.rectangle([0, 0, SLIDE_W, 5], fill=COLORS["accent"])

    # GroMo logo area (top-left)
    logo_font = _get_font(18, bold=True)
    draw.text((50, 30), "GroMo AI Trainer", fill=COLORS["accent_light"], font=logo_font)

    # Slide counter (top-right)
    counter_font = _get_font(16)
    draw.text((SLIDE_W - 80, 30), f"{slide_num}/{total_slides}", fill=COLORS["mid_gray"], font=counter_font)

    # Category badge
    cat_font = _get_font(20, bold=True)
    cat_text = category.upper() if category else "FINANCIAL PRODUCT"
    cat_bbox = cat_font.getbbox(cat_text)
    cat_w = cat_bbox[2] - cat_bbox[0] + 30
    cat_x = (SLIDE_W - cat_w) // 2
    _draw_rounded_rect(draw, (cat_x, 220, cat_x + cat_w, 255), radius=12, fill=COLORS["accent"])
    draw.text((cat_x + 15, 224), cat_text, fill=COLORS["white"], font=cat_font)

    # Product name (main title)
    title_font = _get_font(52, bold=True)
    title_lines = _wrap_text(product_name, title_font, 1000)
    title_y = 290
    for line in title_lines[:3]:
        bbox = title_font.getbbox(line)
        line_w = bbox[2] - bbox[0]
        draw.text(((SLIDE_W - line_w) // 2, title_y), line, fill=COLORS["white"], font=title_font)
        title_y += (bbox[3] - bbox[1]) + 12

    # Payout note (no specific amount — changes frequently)
    payout_font = _get_font(22, bold=True)
    payout_text = "Check GroMo App for Latest Payout"
    payout_bbox = payout_font.getbbox(payout_text)
    pw = payout_bbox[2] - payout_bbox[0] + 40
    px = (SLIDE_W - pw) // 2
    py = title_y + 30
    _draw_rounded_rect(draw, (px, py, px + pw, py + 50), radius=15, fill=(21, 128, 61))
    draw.text((px + 20, py + 12), payout_text, fill=COLORS["white"], font=payout_font)

    # Bottom tagline
    tag_font = _get_font(18)
    tag_text = "Partner Training Video | Powered by GroMo AI"
    tag_bbox = tag_font.getbbox(tag_text)
    draw.text(((SLIDE_W - (tag_bbox[2] - tag_bbox[0])) // 2, SLIDE_H - 50),
              tag_text, fill=COLORS["dark_gray"], font=tag_font)

    return img


def render_content_slide(
    title: str,
    content: str,
    slide_num: int = 1,
    total_slides: int = 1,
    slide_type: str = "info",
    product_name: str = "",
) -> Image.Image:
    """Render a content slide with proper layout."""
    theme_idx = (slide_num - 1) % len(SLIDE_THEMES)
    theme = SLIDE_THEMES[theme_idx]

    img = Image.new("RGB", (SLIDE_W, SLIDE_H))
    _draw_gradient(img, theme["gradient_top"], theme["gradient_bottom"])
    draw = ImageDraw.Draw(img)

    # Top accent bar
    draw.rectangle([0, 0, SLIDE_W, 4], fill=theme["accent"])

    # Header bar
    draw.rectangle([0, 0, SLIDE_W, 70], fill=(0, 0, 0, 80))
    header_alpha = Image.new("RGBA", (SLIDE_W, 70), (0, 0, 0, 100))
    # Simple dark header
    draw.rectangle([0, 4, SLIDE_W, 70], fill=(10, 15, 30))

    # Product name (top-left)
    prod_font = _get_font(16)
    draw.text((30, 25), product_name or "GroMo Training", fill=COLORS["mid_gray"], font=prod_font)

    # Slide counter (top-right)
    counter_font = _get_font(16)
    draw.text((SLIDE_W - 80, 25), f"{slide_num}/{total_slides}", fill=COLORS["mid_gray"], font=counter_font)

    # Slide type icon/badge
    icon_map = {
        "benefits": ("✨", "Key Benefits", COLORS["green"]),
        "how_works": ("⚙️", "How It Works", COLORS["accent"]),
        "terms": ("📋", "Terms & Conditions", COLORS["orange"]),
        "payout": ("💰", "Partner Payout", COLORS["green"]),
        "features": ("🎯", "Key Features", COLORS["purple"]),
        "info": ("📌", "Information", theme["accent"]),
        "cta": ("🚀", "Start Selling!", COLORS["green"]),
    }
    icon, type_label, type_color = icon_map.get(slide_type, icon_map["info"])

    # Section title with accent
    title_font = _get_font(36, bold=True)
    clean_title = title.strip()
    if not clean_title:
        clean_title = type_label

    # Accent line before title
    draw.rectangle([50, 100, 54, 145], fill=type_color)
    draw.text((70, 98), clean_title, fill=COLORS["white"], font=title_font)

    # Content area - card style
    card_y = 160
    card_margin = 50
    _draw_rounded_rect(
        draw,
        (card_margin, card_y, SLIDE_W - card_margin, SLIDE_H - 60),
        radius=16,
        fill=(30, 41, 59),
    )

    # Parse and render content
    content_font = _get_font(24)
    bullet_font = _get_font(22)
    content_y = card_y + 25
    content_x = card_margin + 30
    max_content_w = SLIDE_W - 2 * card_margin - 60

    # Split content into lines/bullets
    lines = content.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            content_y += 10
            continue

        if content_y > SLIDE_H - 100:
            draw.text((content_x, content_y), "...", fill=COLORS["mid_gray"], font=content_font)
            break

        # Check if it's a bullet point
        is_bullet = line.startswith(("-", "•", "→", "*")) or re.match(r'^\d+[\.\)]\s', line)

        if is_bullet:
            # Clean the bullet prefix
            clean_line = re.sub(r'^[-•→*]\s*', '', line)
            clean_line = re.sub(r'^\d+[\.\)]\s*', '', clean_line)

            # Draw bullet dot
            draw.ellipse(
                [content_x + 5, content_y + 10, content_x + 13, content_y + 18],
                fill=type_color,
            )

            # Draw bullet text
            content_y = _draw_text_block(
                draw, clean_line,
                content_x + 25, content_y,
                bullet_font, COLORS["light_gray"],
                max_width=max_content_w - 25,
                line_spacing=6,
                max_lines=3,
            )
            content_y += 6
        else:
            # Regular paragraph
            content_y = _draw_text_block(
                draw, line,
                content_x, content_y,
                content_font, COLORS["light_gray"],
                max_width=max_content_w,
                line_spacing=6,
                max_lines=4,
            )
            content_y += 10

    # Footer
    footer_font = _get_font(14)
    draw.text((SLIDE_W // 2 - 60, SLIDE_H - 35), "GroMo AI Trainer", fill=COLORS["dark_gray"], font=footer_font)

    return img


def render_cta_slide(
    product_name: str,
    payout: str = "",
    slide_num: int = 1,
    total_slides: int = 1,
) -> Image.Image:
    """Render a call-to-action closing slide."""
    img = Image.new("RGB", (SLIDE_W, SLIDE_H))
    _draw_gradient(img, (15, 23, 42), (21, 94, 117))
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, SLIDE_W, 5], fill=COLORS["green"])

    # Counter
    counter_font = _get_font(16)
    draw.text((SLIDE_W - 80, 30), f"{slide_num}/{total_slides}", fill=COLORS["mid_gray"], font=counter_font)

    # Big CTA
    cta_font = _get_font(48, bold=True)
    cta_text = f"Sell {product_name}"
    cta_lines = _wrap_text(cta_text, cta_font, 1000)
    cta_y = 200
    for line in cta_lines:
        bbox = cta_font.getbbox(line)
        lw = bbox[2] - bbox[0]
        draw.text(((SLIDE_W - lw) // 2, cta_y), line, fill=COLORS["white"], font=cta_font)
        cta_y += (bbox[3] - bbox[1]) + 10

    # "on GroMo App!"
    sub_font = _get_font(36)
    sub_text = "on GroMo App!"
    sub_bbox = sub_font.getbbox(sub_text)
    draw.text(((SLIDE_W - (sub_bbox[2] - sub_bbox[0])) // 2, cta_y + 15),
              sub_text, fill=COLORS["accent_light"], font=sub_font)

    # Payout note (no specific amount)
    payout_font = _get_font(26, bold=True)
    payout_text = "Check GroMo App for Latest Payout!"
    payout_bbox = payout_font.getbbox(payout_text)
    pw = payout_bbox[2] - payout_bbox[0] + 50
    px = (SLIDE_W - pw) // 2
    py = cta_y + 100
    _draw_rounded_rect(draw, (px, py, px + pw, py + 55), radius=20, fill=(21, 128, 61))
    draw.text((px + 25, py + 14), payout_text, fill=COLORS["white"], font=payout_font)

    # Happy Selling
    happy_font = _get_font(28, bold=True)
    happy_text = "Happy Selling! 🎉"
    happy_bbox = happy_font.getbbox(happy_text)
    draw.text(((SLIDE_W - (happy_bbox[2] - happy_bbox[0])) // 2, SLIDE_H - 120),
              happy_text, fill=COLORS["green"], font=happy_font)

    # Footer
    footer_font = _get_font(16)
    draw.text((SLIDE_W // 2 - 80, SLIDE_H - 45), "Powered by GroMo AI Trainer", fill=COLORS["dark_gray"], font=footer_font)

    return img


# ── Main API ──

def render_slides_from_ppt_data(
    ppt_data: Dict[str, Any],
    product_data: Dict[str, Any],
    output_dir: str,
) -> List[str]:
    """
    Render PPTX slide data into PNG images.

    Args:
        ppt_data: Parsed PPT data from ppt_parser.parse_ppt()
        product_data: Product info dict with name, category, payout, etc.
        output_dir: Directory to save slide images

    Returns:
        List of paths to rendered slide PNG images
    """
    os.makedirs(output_dir, exist_ok=True)
    slides = ppt_data.get("slides", [])
    total = len(slides) + 1  # +1 for CTA slide

    product_name = product_data.get("name", "Financial Product")
    category = product_data.get("category_name", product_data.get("sub_type", ""))
    payout = product_data.get("payout", "")

    image_paths = []

    for i, slide in enumerate(slides):
        title = slide.get("title", "").strip()
        content = slide.get("content", "").strip()
        notes = slide.get("notes", "").strip()

        slide_num = i + 1

        if i == 0:
            # First slide = title slide
            img = render_title_slide(
                product_name=title or product_name,
                category=category,
                payout=payout,
                slide_num=slide_num,
                total_slides=total,
            )
        else:
            # Detect slide type from title/content
            slide_type = _detect_slide_type(title, content)
            display_content = content or notes or title
            img = render_content_slide(
                title=title,
                content=display_content,
                slide_num=slide_num,
                total_slides=total,
                slide_type=slide_type,
                product_name=product_name,
            )

        path = os.path.join(output_dir, f"slide_{slide_num:03d}.png")
        img.save(path, "PNG", quality=95)
        image_paths.append(path)
        logger.debug(f"Rendered slide {slide_num}: {path}")

    # CTA slide
    cta_img = render_cta_slide(
        product_name=product_name,
        payout=payout,
        slide_num=total,
        total_slides=total,
    )
    cta_path = os.path.join(output_dir, f"slide_{total:03d}.png")
    cta_img.save(cta_path, "PNG", quality=95)
    image_paths.append(cta_path)

    logger.info(f"Rendered {len(image_paths)} slide images to {output_dir}")
    return image_paths


def render_slides_from_product_data(
    product_data: Dict[str, Any],
    output_dir: str,
    script_text: Optional[str] = None,
) -> List[str]:
    """
    Render professional slides directly from GroMo product data (no PPTX needed).

    This is the fallback when Gamma doesn't provide a downloadable PPTX.
    """
    os.makedirs(output_dir, exist_ok=True)

    product_name = product_data.get("name", "Financial Product")
    category = product_data.get("category_name", product_data.get("sub_type", ""))
    payout = product_data.get("payout", "")
    benefits = product_data.get("benefits_text", "")
    how_works = product_data.get("how_works_text", "")
    terms = product_data.get("terms_conditions_text", "")
    description = product_data.get("description", "")

    slides_content = []

    # 1. Title slide
    slides_content.append(("title", product_name, category))

    # 2. Overview
    if description:
        slides_content.append(("info", "Product Overview", description[:600]))

    # 3. Benefits
    if benefits:
        slides_content.append(("benefits", "Key Benefits", benefits[:700]))

    # 4. How it works
    if how_works:
        # Split into parts if too long
        if len(how_works) > 700:
            slides_content.append(("how_works", "How It Works (Part 1)", how_works[:700]))
            slides_content.append(("how_works", "How It Works (Part 2)", how_works[700:1400]))
        else:
            slides_content.append(("how_works", "How It Works", how_works))

    # 5. Terms
    if terms:
        slides_content.append(("terms", "Terms & Conditions", terms[:700]))

    # 6. Payout note
    slides_content.append(("payout", "Partner Earnings", "Sell this product through GroMo app and start earning today!\n\nCheck GroMo App for the latest partner payout."))

    # If we only have title, add a generic slide
    if len(slides_content) <= 1:
        slides_content.append(("info", "About This Product", f"{product_name} is available on GroMo app for partners to sell."))

    total = len(slides_content) + 1  # +1 for CTA

    image_paths = []

    for i, (stype, title, content) in enumerate(slides_content):
        slide_num = i + 1
        if stype == "title":
            img = render_title_slide(product_name, category, "", slide_num, total)
        else:
            img = render_content_slide(title, content, slide_num, total, stype, product_name)

        path = os.path.join(output_dir, f"slide_{slide_num:03d}.png")
        img.save(path, "PNG", quality=95)
        image_paths.append(path)

    # CTA slide
    cta_img = render_cta_slide(product_name, "", total, total)
    cta_path = os.path.join(output_dir, f"slide_{total:03d}.png")
    cta_img.save(cta_path, "PNG", quality=95)
    image_paths.append(cta_path)

    logger.info(f"Rendered {len(image_paths)} product slides to {output_dir}")
    return image_paths


def _detect_slide_type(title: str, content: str) -> str:
    """Detect the slide type from title/content keywords."""
    combined = (title + " " + content).lower()

    if any(w in combined for w in ["benefit", "advantage", "fayda", "labh"]):
        return "benefits"
    if any(w in combined for w in ["how it works", "process", "steps", "kaise", "tarika"]):
        return "how_works"
    if any(w in combined for w in ["terms", "condition", "eligib", "requirement", "sharten"]):
        return "terms"
    if any(w in combined for w in ["payout", "earn", "commission", "kamai"]):
        return "payout"
    if any(w in combined for w in ["feature", "key point", "highlight"]):
        return "features"
    if any(w in combined for w in ["sell", "action", "start", "download", "happy selling"]):
        return "cta"

    return "info"

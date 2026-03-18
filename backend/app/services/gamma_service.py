"""
Gamma AI service.
Generates professional presentations using Gamma's Generate API,
then downloads the PPTX for use in the video pipeline.
"""
import os
import time
import logging
from typing import Optional, Dict, Any, List

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

GAMMA_API_BASE = "https://public-api.gamma.app/v1.0"


def generate_presentation(
    product_data: Dict[str, Any],
    job_type: str = "single_product",
    language: str = "hinglish",
    num_slides: int = 8,
    target_duration: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Generate a presentation via Gamma AI using real product data.

    Args:
        product_data: Product info dict (or list for category/comparison).
        job_type: single_product, category_overview, or comparison.
        language: Language for the presentation.
        num_slides: Number of slides (cards) to generate.
        target_duration: Optional target video duration in seconds.

    Returns:
        Dict with keys: gamma_url, pptx_url (if exported), generation_id
    """
    if not settings.gamma_api_key:
        raise ValueError("Gamma API key not configured")

    # Build input text from real product data
    input_text = _build_input_text(product_data, job_type, language, target_duration)

    # Build additional instructions for Gamma
    lang_instruction = {
        "hinglish": (
            "Write in Hinglish — use ENGLISH SCRIPT (Roman alphabet) ONLY. "
            "Mix Hindi words written in Roman script with English. "
            "Example: 'Aaj hi apply karein' NOT 'आज ही अप्लाई करें'. "
            "NEVER use Devanagari (Hindi) script anywhere in the presentation. "
            "All text must be in Roman/English letters only."
        ),
        "hindi": "Write in Hindi (Devanagari script). Keep it simple and clear.",
        "english": "Write in clear, professional English.",
    }.get(language, "Write in Hinglish using ENGLISH SCRIPT only — no Devanagari.")

    additional = (
        f"{lang_instruction} "
        "This is a PROFESSIONAL training presentation for GroMo — India's leading financial product selling app. "
        "GroMo partners earn commission by selling financial products through the GroMo mobile app. "
        "CRITICAL LANGUAGE RULE: For Hinglish, write ALL text in Roman/English alphabet. "
        "Do NOT use any Devanagari or Hindi script characters anywhere. "
        "DESIGN RULES: "
        "1. Use mobile app UI mockups and smartphone screenshots showing a fintech app interface — NOT random stock photos. "
        "2. Show images of Indian professionals using smartphones, people earning money, mobile banking screens. "
        "3. Use infographics, numbered step cards with icons, comparison tables, icon grids. "
        "4. Keep text MINIMAL — max 4-5 bullet points per slide, short phrases only. "
        "5. Use GroMo brand colors: green (#22C55E) as primary accent, with modern dark/white layouts. "
        "6. Include: product intro, key benefits with icons, step-by-step selling process (app-based), "
        "eligibility & terms, and a strong CTA. "
        "7. Use ONLY the product information provided. Do NOT make up any details. "
        "8. NEVER mention any specific payout amount, commission amount, or earning amount "
        "(like Rs 750, Rs 500, ₹750, etc). Payouts change frequently. "
        "Do NOT include any slide about 'Payout Eligibility' or 'Commission Details'. "
        "In the CTA slide, write 'Check GroMo App for latest payout'. "
        "9. Style: Premium corporate training deck — clean, modern, mobile-first visuals."
    )

    # Adjust slide count based on duration
    if target_duration:
        # ~10 seconds per slide for comfortable viewing with narration
        num_slides = max(4, min(20, int(target_duration / 10)))

    payload = {
        "inputText": input_text,
        "textMode": "generate",
        "format": "presentation",
        "numCards": num_slides,
        "exportAs": "pptx",
        "additionalInstructions": additional[:2000],
        "textOptions": {
            "amount": "brief",
            "tone": "professional, motivating, training-focused",
            "audience": "GroMo partner sales agents in India",
            "language": _gamma_language_code(language),
        },
        "imageOptions": {
            "source": "aiGenerated",
            "style": "fintech mobile app UI, smartphone mockups, Indian professionals, green accent, modern corporate",
        },
        "cardOptions": {
            "dimensions": "16x9",
        },
    }

    logger.info(f"Gamma: Creating presentation ({num_slides} slides, {language})")

    # Step 1: Submit generation request
    response = httpx.post(
        f"{GAMMA_API_BASE}/generations",
        headers={
            "X-API-KEY": settings.gamma_api_key,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    generation_id = data.get("generationId")

    if not generation_id:
        raise ValueError(f"Gamma API returned no generationId: {data}")

    logger.info(f"Gamma: Generation submitted, ID={generation_id}")

    # Step 2: Poll for completion
    result = _poll_generation(generation_id)

    logger.info(
        f"Gamma: Presentation ready — URL={result.get('gamma_url')}, "
        f"PPTX={bool(result.get('pptx_url'))}"
    )
    return result


def _poll_generation(
    generation_id: str,
    max_wait: int = 300,
    poll_interval: int = 5,
) -> Dict[str, Any]:
    """Poll Gamma API until generation completes or fails."""
    start = time.time()

    while time.time() - start < max_wait:
        response = httpx.get(
            f"{GAMMA_API_BASE}/generations/{generation_id}",
            headers={"X-API-KEY": settings.gamma_api_key},
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()

        status = data.get("status", "unknown")
        logger.debug(f"Gamma poll: status={status}")

        if status == "completed":
            # The PPTX download URL can appear as pptxUrl, exportUrl, or need separate export
            pptx_url = (
                data.get("pptxUrl")
                or data.get("exportUrl")
                or data.get("export_url")
            )

            result = {
                "generation_id": generation_id,
                "gamma_url": data.get("gammaUrl"),
                "pptx_url": pptx_url,
                "pdf_url": data.get("pdfUrl"),
                "credits": data.get("credits"),
            }

            logger.info(f"Gamma completed: gammaUrl={result['gamma_url']}, pptxUrl={bool(pptx_url)}")

            # If still no PPTX URL, try separate export endpoint
            if not result["pptx_url"]:
                try:
                    export_url = _export_pptx(generation_id)
                    if export_url:
                        result["pptx_url"] = export_url
                except Exception as ex:
                    logger.warning(f"Gamma PPTX export failed: {ex}")
            return result
        elif status == "failed":
            error = data.get("error", {})
            raise RuntimeError(
                f"Gamma generation failed: {error.get('message', 'Unknown error')}"
            )

        time.sleep(poll_interval)

    raise TimeoutError(f"Gamma generation {generation_id} timed out after {max_wait}s")


def _export_pptx(generation_id: str) -> Optional[str]:
    """Try to export PPTX from a completed Gamma generation."""
    try:
        response = httpx.post(
            f"{GAMMA_API_BASE}/generations/{generation_id}/export",
            headers={
                "X-API-KEY": settings.gamma_api_key,
                "Content-Type": "application/json",
            },
            json={"format": "pptx"},
            timeout=30.0,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("pptxUrl") or data.get("url")
    except Exception as e:
        logger.debug(f"Export endpoint not available: {e}")
    return None


def download_pptx(pptx_url: str, output_path: str) -> str:
    """Download the generated PPTX file from Gamma's temporary URL."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    response = httpx.get(pptx_url, timeout=60.0, follow_redirects=True)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)

    logger.info(f"Gamma PPTX downloaded to {output_path} ({len(response.content)} bytes)")
    return output_path


def list_themes() -> List[Dict[str, Any]]:
    """List available Gamma themes."""
    if not settings.gamma_api_key:
        return []

    response = httpx.get(
        f"{GAMMA_API_BASE}/themes",
        headers={"X-API-KEY": settings.gamma_api_key},
        params={"limit": 50},
        timeout=15.0,
    )
    response.raise_for_status()
    return response.json()


def _gamma_language_code(language: str) -> str:
    """Map our language codes to Gamma-supported ISO codes.

    Hinglish maps to 'en' so Gamma generates Roman script text,
    not Devanagari. The Hinglish mixing is handled by additionalInstructions.
    """
    return {
        "hindi": "hi",
        "hinglish": "en",
        "english": "en",
    }.get(language.lower(), "en")


def _strip_payout_amounts(text: str) -> str:
    """Remove any specific payout/commission amounts from text before sending to Gamma."""
    import re
    # Rs/₹/INR followed by numbers
    text = re.sub(r'(?:Rs\.?|₹|INR)\s*[\d,]+(?:\s*(?:per|/)\s*\w+)?', 'Check GroMo App for latest payout', text, flags=re.IGNORECASE)
    # "earn X commission" patterns
    text = re.sub(r'earn\s+(?:Rs\.?|₹|INR)?\s*[\d,]+\s*(?:commission|per\s+sale)?', 'earn commission (Check GroMo App for latest payout)', text, flags=re.IGNORECASE)
    # "payout: Rs X" or "payout of Rs X"
    text = re.sub(r'payout\s*(?::|of)\s*(?:Rs\.?|₹|INR)?\s*[\d,]+', 'Payout: Check GroMo App', text, flags=re.IGNORECASE)
    return text


def _build_input_text(
    product_data: Any,
    job_type: str,
    language: str,
    target_duration: Optional[float] = None,
) -> str:
    """Build rich input text for Gamma from real GroMo product data."""

    if job_type == "category_overview":
        products = product_data if isinstance(product_data, list) else [product_data]
        category = products[0].get("category_name", "Financial Products") if products else "Financial Products"

        text = f"# GroMo Partner Training: {category}\n\n"
        text += f"Category: {category}\n"
        text += f"Number of products: {len(products)}\n\n"

        for i, p in enumerate(products[:5], 1):
            text += f"## Product {i}: {p.get('name', 'Product')}\n"
            if p.get("benefits_text"):
                text += f"Benefits:\n{_strip_payout_amounts(p['benefits_text'][:500])}\n"
            if p.get("how_works_text"):
                text += f"How It Works:\n{_strip_payout_amounts(p['how_works_text'][:300])}\n"
            text += "\n---\n"

        text += "\nKey message: Help partners understand which product to recommend to which customer type. Do NOT mention any specific payout amounts — payouts change frequently. Instead say 'Check GroMo App for latest payout'."
        return text

    elif job_type == "comparison":
        products = product_data if isinstance(product_data, list) else [product_data]

        text = "# GroMo Partner Training: Product Comparison\n\n"
        for i, p in enumerate(products[:3], 1):
            text += f"## Product {i}: {p.get('name', 'Product')}\n"
            if p.get("benefits_text"):
                text += f"Benefits:\n{_strip_payout_amounts(p['benefits_text'][:500])}\n"
            if p.get("how_works_text"):
                text += f"How It Works:\n{_strip_payout_amounts(p['how_works_text'][:400])}\n"
            if p.get("terms_conditions_text"):
                text += f"Terms:\n{_strip_payout_amounts(p['terms_conditions_text'][:300])}\n"
            text += "\n---\n"

        text += "\nCompare features, process, and customer suitability. Do NOT mention specific payout amounts — say 'Check GroMo App for latest payout'."
        return text

    else:
        # single_product
        name = product_data.get("name", "Financial Product")
        category = product_data.get("category_name", product_data.get("sub_type", "Financial Product"))
        benefits = _strip_payout_amounts(product_data.get("benefits_text", ""))
        how_works = _strip_payout_amounts(product_data.get("how_works_text", ""))
        terms = _strip_payout_amounts(product_data.get("terms_conditions_text", ""))

        text = f"# GroMo Partner Training: {name}\n\n"
        text += f"Product: {name}\n"
        text += f"Category: {category}\n\n"

        if benefits:
            text += f"## Benefits & Features\n{benefits[:800]}\n\n"
        if how_works:
            text += f"## How It Works (Sales Process)\n{how_works[:800]}\n\n"
        if terms:
            text += f"## Terms & Conditions\n{terms[:600]}\n\n"

        text += (
            "## Call to Action\n"
            f"Sell {name} on GroMo app today! Check GroMo App for the latest partner payout.\n"
        )
        return text

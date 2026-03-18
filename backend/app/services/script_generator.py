"""
Script generator service.
Generates training video scripts using real GroMo product data as grounding context.
All scripts use only verified product information to prevent hallucination.
"""
import logging
from typing import Optional, List, Dict, Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def generate_script(
    product_data: dict,
    job_type: str,
    language: str = "hinglish",
    target_duration: Optional[float] = None,
) -> str:
    """
    Generate a training video script for GroMo partners.
    Uses real product data as grounding context.

    Args:
        product_data: Product information dict or list of dicts.
        job_type: Type of video (single_product, category_overview, comparison).
        language: Script language (hinglish, hindi, english).
        target_duration: Optional target video duration in seconds (30-300).
    """
    provider = settings.llm_provider

    # Build the prompt with real data and duration hint
    prompt = _build_prompt(product_data, job_type, language, target_duration)

    try:
        if provider == "openai":
            return _generate_openai(prompt, target_duration)
        elif provider == "ollama":
            return _generate_ollama(prompt)
        else:
            return _generate_demo(product_data, job_type, language, target_duration)
    except Exception as e:
        logger.error(f"Script generation failed with provider '{provider}': {e}")
        logger.info("Falling back to demo script generator")
        return _generate_demo(product_data, job_type, language, target_duration)


def _duration_instruction(target_duration: Optional[float]) -> str:
    """Build a duration instruction string with word count guidance for the prompt.

    Targets ~2.5 spoken words/second for clear, understandable Hinglish speech.
    This is slower than typical speech to ensure training content is easy to follow.
    """
    if target_duration is None:
        return "60-90 second (approximately 150-220 words, keep it concise)"
    secs = int(target_duration)
    # Target ~2.5 words/sec for clear, slow training speech
    target_words = int(secs * 2.5)
    if secs <= 60:
        return f"{secs} second (MAXIMUM {target_words} words, short and concise)"
    elif secs <= 120:
        return f"{secs} second (~{secs // 60} minute, approximately {target_words} words)"
    else:
        mins = secs / 60
        return f"{secs} second (~{mins:.1f} minute, approximately {target_words} words, detailed)"


def _build_prompt(product_data: Any, job_type: str, language: str, target_duration: Optional[float] = None) -> str:
    """Build the LLM prompt with real product data as grounding context."""
    dur = _duration_instruction(target_duration)

    if job_type == "category_overview":
        products = product_data if isinstance(product_data, list) else [product_data]
        product_names = ", ".join(p.get("name", "Unknown") for p in products)
        category_name = products[0].get("category_name", "Financial Products") if products else "Financial Products"

        product_details = ""
        for p in products[:5]:
            product_details += f"\n--- {p.get('name', 'Product')} ---\n"
            product_details += f"Benefits: {p.get('benefits_text', 'N/A')}\n"

        return (
            f"Create a {dur} training video script for GroMo partners about "
            f"the {category_name} category. Products: {product_names}.\n"
            f"Language: {language}.\n\n"
            f"REAL PRODUCT DATA (use ONLY this data, do NOT make up any details):\n"
            f"{product_details}\n"
            f"Include: category overview, brief summary of each product, "
            f"key differentiators, and a call-to-action for GroMo partners.\n"
            f"IMPORTANT: Do NOT mention any specific payout amounts — payouts change frequently. "
            f"Instead say 'Check GroMo App for the latest payout'."
        )
    elif job_type == "comparison":
        products = product_data if isinstance(product_data, list) else [product_data]
        product_details = ""
        for p in products[:3]:
            product_details += f"\n--- {p.get('name', 'Product')} ---\n"
            product_details += f"Benefits: {p.get('benefits_text', 'N/A')}\n"
            product_details += f"How It Works: {p.get('how_works_text', 'N/A')}\n"
            product_details += f"Terms: {p.get('terms_conditions_text', 'N/A')}\n"

        return (
            f"Create a {dur} comparison video script for GroMo partners.\n"
            f"Language: {language}.\n\n"
            f"REAL PRODUCT DATA (use ONLY this data, do NOT make up any details):\n"
            f"{product_details}\n"
            f"Compare features, process, and terms. Help partner understand which "
            f"product suits which customer type.\n"
            f"IMPORTANT: Do NOT mention any specific payout amounts — payouts change frequently. "
            f"Instead say 'Check GroMo App for the latest payout'."
        )
    else:
        # single_product
        name = product_data.get("name", "Financial Product")
        benefits = product_data.get("benefits_text", "")
        how_works = product_data.get("how_works_text", "")
        terms = product_data.get("terms_conditions_text", "")

        return (
            f"Create a {dur} training video script for GroMo partners about "
            f"{name}. Language: {language}.\n\n"
            f"REAL PRODUCT DATA (use ONLY this data, do NOT fabricate any details):\n\n"
            f"Product: {name}\n\n"
            f"Benefits & Features:\n{benefits}\n\n"
            f"How It Works (Sales Process):\n{how_works}\n\n"
            f"Terms & Conditions:\n{terms}\n\n"
            f"Include: product overview, key benefits, how to sell it, "
            f"terms the partner should know, and a call-to-action.\n"
            f"IMPORTANT: Do NOT mention any specific payout amounts — payouts change frequently. "
            f"Instead say 'Check GroMo App for the latest payout'."
        )


def _get_system_prompt() -> str:
    return (
        "You are a script writer for GroMo, India's largest fintech distribution platform. "
        "Write training scripts for GroMo partners (sales agents) who sell financial products. "
        "CRITICAL: Use ONLY the product data provided. Do NOT make up or assume any details "
        "about fees, features, eligibility, or benefits that are not in the data. "
        "Scripts should be in Hinglish (mix of Hindi and English) unless specified otherwise. "
        "Keep the tone friendly, professional, and easy to understand. "
        "IMPORTANT: Write scripts that are SHORT and CONCISE. The script will be read aloud "
        "at a slow, clear pace (~2.5 words per second) for training purposes. "
        "Strictly respect the word count limit given in the prompt. Use simple sentences. "
        "Avoid long paragraphs. Use line breaks between sections."
    )


def _generate_openai(prompt: str, target_duration: Optional[float] = None) -> str:
    """Generate script using OpenAI API."""
    from openai import OpenAI

    if not settings.openai_api_key:
        raise ValueError("OpenAI API key not configured")

    # Scale max_tokens based on target duration
    # ~2.5 words/second spoken, ~1.5 tokens/word → ~3.75 tokens/second
    if target_duration:
        max_tokens = min(2000, max(300, int(target_duration * 3.75)))
    else:
        max_tokens = 800

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": _get_system_prompt()},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def _generate_ollama(prompt: str) -> str:
    """Generate script using local Ollama API."""
    response = httpx.post(
        f"{settings.ollama_base_url}/api/generate",
        json={
            "model": settings.ollama_model,
            "system": _get_system_prompt(),
            "prompt": prompt,
            "stream": False,
        },
        timeout=120.0,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")


def _generate_demo(
    product_data: Any,
    job_type: str,
    language: str,
    target_duration: Optional[float] = None,
) -> str:
    """Generate a template-based script using REAL product data. No fabrication."""
    if job_type == "category_overview":
        return _demo_category_script(product_data, language)
    elif job_type == "comparison":
        return _demo_comparison_script(product_data, language)
    else:
        return _demo_single_product_script(product_data, language)


def _demo_single_product_script(product_data: dict, language: str) -> str:
    """Generate a demo script for a single product using real GroMo data."""
    name = product_data.get("name", "Financial Product")
    benefits = product_data.get("benefits_text", "")
    how_works = product_data.get("how_works_text", "")
    terms = product_data.get("terms_conditions_text", "")
    category = product_data.get("category_name", product_data.get("sub_type", "Financial Product"))

    # Format benefits as bullet points
    benefits_lines = benefits.split('\n') if benefits else []
    benefits_formatted = ""
    for i, line in enumerate(benefits_lines[:6], 1):
        if line.strip():
            benefits_formatted += f"  {i}. {line.strip()}\n"

    # Format how it works
    how_works_lines = how_works.split('\n') if how_works else []
    how_works_formatted = ""
    for line in how_works_lines[:6]:
        if line.strip():
            how_works_formatted += f"  {line.strip()}\n"

    # Format terms
    terms_lines = terms.split('\n') if terms else []
    terms_formatted = ""
    for line in terms_lines[:5]:
        if line.strip():
            terms_formatted += f"  {line.strip()}\n"

    script = f"""[INTRO - 10 seconds]
Namaste GroMo Partners! Aaj hum baat karenge {name} ke baare mein.
Yeh ek {category} product hai jo aapke customers ke liye designed hai.

[PRODUCT BENEFITS - 20 seconds]
Ab dekhte hain iske key benefits:
{benefits_formatted if benefits_formatted else "  Product ki detailed benefits GroMo app pe available hain."}

[HOW IT WORKS - 20 seconds]
Ab samjhte hain ki yeh kaise kaam karta hai:
{how_works_formatted if how_works_formatted else "  Process ki full details GroMo app pe check karein."}

[TERMS & CONDITIONS - 15 seconds]
Kuch important baatein dhyan mein rakhein:
{terms_formatted if terms_formatted else "  Terms & conditions GroMo app pe available hain."}

[CALL TO ACTION - 10 seconds]
Toh partners, {name} ek excellent product hai aapke customers ke liye.
Latest payout ke liye GroMo App check karein.
Abhi GroMo app pe jaake is product ko share karein aur apni earnings badhayein!
GroMo ke saath aage badhein - Happy Selling!
"""
    return script.strip()


def _demo_category_script(product_data: Any, language: str) -> str:
    """Generate a demo category overview script with real product data."""
    products = product_data if isinstance(product_data, list) else [product_data]
    category_name = products[0].get("category_name", products[0].get("sub_type", "Financial Products")) if products else "Financial Products"

    product_sections = ""
    for i, p in enumerate(products[:5], 1):
        name = p.get("name", "Product")
        benefits_text = p.get("benefits_text", "")
        # Get first benefit line as summary
        first_benefit = ""
        if benefits_text:
            lines = [l.strip() for l in benefits_text.split('\n') if l.strip()]
            first_benefit = lines[0] if lines else ""

        product_sections += f"""
[PRODUCT {i}: {name} - 10 seconds]
{name}
{first_benefit}
"""

    script = f"""[INTRO - 10 seconds]
Namaste GroMo Partners! Aaj hum cover karenge {category_name} category ke products.
Is category mein humne {len(products)} products hain jo aapke customers ke liye available hain.
{product_sections}
[SELLING TIP - 10 seconds]
Har customer ki need alag hoti hai. Unki requirement samajhke
sahi product recommend karein - isse aapki conversion rate badhegi!

[CALL TO ACTION - 10 seconds]
Toh partners, {category_name} products sell karke achhi earnings kamayein.
Latest payouts ke liye GroMo App check karein. Happy Selling!
"""
    return script.strip()


def _demo_comparison_script(product_data: Any, language: str) -> str:
    """Generate a comparison script with real product data."""
    products = product_data if isinstance(product_data, list) else [product_data]

    if len(products) < 2:
        return _demo_single_product_script(products[0] if products else {}, language)

    p1, p2 = products[0], products[1]
    name1, name2 = p1.get("name", "Product A"), p2.get("name", "Product B")

    # Get first 2 benefits for each
    def first_benefits(p):
        text = p.get("benefits_text", "")
        lines = [l.strip() for l in text.split('\n') if l.strip()][:2]
        return '\n  '.join(lines) if lines else "Details available on GroMo app."

    script = f"""[INTRO - 10 seconds]
Namaste GroMo Partners! Aaj hum compare karenge {name1} aur {name2}.
Dono achhe products hain, lekin kaun kiske liye best hai? Aayiye jaante hain.

[{name1} - 15 seconds]
Pehle baat karte hain {name1} ki.
Key Benefits:
  {first_benefits(p1)}

[{name2} - 15 seconds]
Ab dekhte hain {name2}.
Key Benefits:
  {first_benefits(p2)}

[COMPARISON TIP - 15 seconds]
Customer ki need ke hisaab se sahi product recommend karein.
Dono ki terms & conditions GroMo app pe check kar sakte hain.

[CALL TO ACTION - 10 seconds]
Dono products GroMo app pe available hain.
Customer se baat karein, unki need samjhein, aur best product suggest karein.
Happy Selling!
"""
    return script.strip()

"""
Doubt Resolver Service.
Resolves GroMo partner doubts using REAL product data as grounding context.
All answers are based on actual GroMo product information — no hallucination.
"""
import logging
from typing import Optional, List, Dict, Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Keyword categories for template matching against real product sections
KEYWORD_MAP = {
    "benefits": [
        "benefit", "fayda", "feature", "kya milta", "kya hai", "special",
        "offer", "reward", "cashback", "points", "achha kya", "advantage",
        "usp", "why", "kyun", "best", "value", "recommend", "lena chahiye",
    ],
    "process": [
        "how", "kaise", "process", "apply", "step", "kya karna",
        "activate", "start", "register", "sign up", "link", "share",
        "customer", "form", "document", "kyc",
    ],
    "terms": [
        "terms", "condition", "rule", "payout", "earn", "commission",
        "fee", "charge", "cost", "price", "kitna lagta", "kitna milta",
        "eligib", "qualify", "age", "income", "salary", "required",
        "time", "kitna time", "kab", "status",
    ],
}


def resolve_doubt(
    question: str,
    product_knowledge: str,
    language: str = "hinglish",
) -> str:
    """
    Resolve a partner's doubt using LLM or template-based approach.
    product_knowledge contains REAL data from GroMo API.
    """
    provider = settings.llm_provider

    try:
        if provider == "openai":
            return _resolve_openai(question, product_knowledge, language)
        elif provider == "ollama":
            return _resolve_ollama(question, product_knowledge, language)
        else:
            return _resolve_demo(question, product_knowledge, language)
    except Exception as e:
        logger.error(f"Doubt resolution failed with provider '{provider}': {e}")
        logger.info("Falling back to demo doubt resolver")
        return _resolve_demo(question, product_knowledge, language)


def _build_system_prompt(language: str) -> str:
    return (
        "You are a helpful training assistant for GroMo, India's largest fintech distribution platform. "
        "You help GroMo partners (sales agents) understand financial products so they can sell better. "
        f"Respond in {language} style (mix of Hindi and English if Hinglish). "
        "CRITICAL RULES:\n"
        "1. ONLY use information from the Product Knowledge Base provided below.\n"
        "2. Do NOT fabricate, assume, or hallucinate ANY product details.\n"
        "3. If the answer is NOT in the knowledge base, say: 'Yeh information hamare current data mein "
        "available nahi hai. GroMo app pe latest details check karein.'\n"
        "4. Be professional, clear, and specific.\n"
        "5. Include exact details from the knowledge base when answering."
    )


def _build_user_prompt(question: str, product_knowledge: str) -> str:
    return (
        f"Product Knowledge Base (REAL GroMo data — ONLY use this):\n"
        f"---\n{product_knowledge}\n---\n\n"
        f"Partner's Question: {question}\n\n"
        "Answer the partner's question using ONLY the product data above. "
        "If the information is not in the knowledge base, say so clearly."
    )


def _resolve_openai(question: str, product_knowledge: str, language: str) -> str:
    from openai import OpenAI

    if not settings.openai_api_key:
        raise ValueError("OpenAI API key not configured")

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": _build_system_prompt(language)},
            {"role": "user", "content": _build_user_prompt(question, product_knowledge)},
        ],
        temperature=0.3,  # Lower temperature for factual answers
        max_tokens=500,
    )
    return response.choices[0].message.content


def _resolve_ollama(question: str, product_knowledge: str, language: str) -> str:
    response = httpx.post(
        f"{settings.ollama_base_url}/api/generate",
        json={
            "model": settings.ollama_model,
            "system": _build_system_prompt(language),
            "prompt": _build_user_prompt(question, product_knowledge),
            "stream": False,
        },
        timeout=120.0,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")


def _resolve_demo(question: str, product_knowledge: str, language: str) -> str:
    """
    Template-based answer using keyword matching against REAL product data.
    Extracts relevant sections from the knowledge base.
    """
    question_lower = question.lower()

    # Match question to a knowledge section
    matched_section = _match_question_section(question_lower)

    if matched_section:
        section_text = _extract_section(product_knowledge, matched_section)
        if section_text:
            return _format_answer(matched_section, section_text, question)

    # Fallback: search for any relevant lines in the knowledge base
    return _search_knowledge(question, product_knowledge)


def _match_question_section(question_lower: str) -> Optional[str]:
    """Match question to a knowledge base section."""
    best_match = None
    best_score = 0

    for section, keywords in KEYWORD_MAP.items():
        score = sum(1 for kw in keywords if kw in question_lower)
        if score > best_score:
            best_score = score
            best_match = section

    return best_match


def _extract_section(knowledge_text: str, section: str) -> Optional[str]:
    """Extract a section from the knowledge base text."""
    section_headers = {
        "benefits": "## Product Benefits & Features",
        "process": "## How It Works (Sales Process)",
        "terms": "## Terms & Conditions (Payout Rules)",
    }

    header = section_headers.get(section)
    if not header:
        return None

    start_idx = knowledge_text.find(header)
    if start_idx == -1:
        return None

    content_start = start_idx + len(header)
    next_section = knowledge_text.find("\n## ", content_start)
    if next_section == -1:
        section_text = knowledge_text[content_start:].strip()
    else:
        section_text = knowledge_text[content_start:next_section].strip()

    return section_text if section_text else None


def _format_answer(section: str, section_text: str, question: str) -> str:
    """Format answer in Hinglish using real product data."""
    intros = {
        "benefits": "Achha sawaal! Is product ke benefits yeh hain (GroMo verified data):\n\n",
        "process": "Zaroor! Is product ka process yeh hai (GroMo verified data):\n\n",
        "terms": "Important! Terms & conditions yeh hain (GroMo verified data):\n\n",
    }

    intro = intros.get(section, "Yeh rahi aapke sawaal ki information:\n\n")
    outro = (
        "\n\nYeh information GroMo ke official data se hai. "
        "Latest updates ke liye GroMo app check karein. "
        "Aur koi doubt hai toh puchiye!"
    )

    return f"{intro}{section_text}{outro}"


def _search_knowledge(question: str, product_knowledge: str) -> str:
    """Search the entire knowledge base for relevant information."""
    # Extract product name
    product_name = "is product"
    lines = product_knowledge.split("\n")
    for line in lines:
        if line.startswith("=== PRODUCT:"):
            product_name = line.replace("=== PRODUCT:", "").replace("===", "").strip()
            break

    # Find relevant lines
    question_words = set(question.lower().split())
    relevant_lines = []

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("##") or line_stripped.startswith("==="):
            continue
        if line_stripped.startswith("ONLY use") or line_stripped.startswith("Do NOT"):
            continue
        line_words = set(line_stripped.lower().split())
        overlap = len(question_words.intersection(line_words))
        if overlap >= 2:
            relevant_lines.append(line_stripped)

    if relevant_lines:
        info = "\n".join(relevant_lines[:5])
        return (
            f"Achha sawaal! {product_name} ke baare mein yeh information hai "
            f"(GroMo verified data):\n\n{info}\n\n"
            "Latest updates ke liye GroMo app check karein. "
            "Aur koi doubt hai toh puchiye!"
        )

    return (
        f"{product_name} ke baare mein yeh specific information hamare current data mein "
        f"available nahi hai. Kripya GroMo app pe latest details check karein.\n\n"
        "Aap yeh pooch sakte hain:\n"
        "- Product benefits kya hain?\n"
        "- Sales process kaise kaam karta hai?\n"
        "- Terms & conditions kya hain?\n"
        "- Partner payout kitna hai?"
    )

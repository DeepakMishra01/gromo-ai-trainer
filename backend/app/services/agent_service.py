"""
Sahayak Agent Service.
Multi-turn conversational agent grounded in real GroMo product data.
Supports multi-product queries, comparisons, and training-focused Q&A.
"""
import logging
import uuid
import re
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models.product import Product
from app.models.category import Category
from app.models.agent_session import AgentSession
from app.services.knowledge_builder import get_knowledge_for_product

logger = logging.getLogger(__name__)

# In-memory product index (built once, reused)
_product_index: Optional[List[Dict]] = None


def _get_product_index(db: Session) -> List[Dict]:
    """Build/return cached product index for fast matching."""
    global _product_index
    if _product_index is not None:
        return _product_index

    products = (
        db.query(Product)
        .join(Category)
        .filter(Category.is_excluded == False)  # noqa: E712
        .all()
    )
    _product_index = []
    for p in products:
        _product_index.append({
            "id": str(p.id),
            "name": p.name,
            "sub_type": p.sub_type or "",
            "category_name": p.category.name if p.category else "",
        })
    logger.info(f"Built product index: {len(_product_index)} products")
    return _product_index


def _identify_products(query: str, product_index: List[Dict], max_results: int = 3) -> List[Dict]:
    """Identify which products the user is asking about via keyword matching."""
    query_lower = query.lower()
    query_tokens = set(re.findall(r'\w+', query_lower))

    scored = []
    for p in product_index:
        name_lower = p["name"].lower()
        name_tokens = set(re.findall(r'\w+', name_lower))
        cat_tokens = set(re.findall(r'\w+', p["category_name"].lower()))
        sub_tokens = set(re.findall(r'\w+', p["sub_type"].lower()))

        # Exact substring match in query (e.g., "hdfc credit card" in query)
        name_words = name_lower.split()
        substring_score = 0
        for i in range(len(name_words)):
            for j in range(i + 1, len(name_words) + 1):
                phrase = " ".join(name_words[i:j])
                if len(phrase) > 3 and phrase in query_lower:
                    substring_score = max(substring_score, j - i)

        # Token overlap
        token_score = len(query_tokens & name_tokens) + len(query_tokens & cat_tokens) * 0.5 + len(query_tokens & sub_tokens) * 0.3

        total_score = substring_score * 3 + token_score
        if total_score > 0.5:
            scored.append((total_score, p))

    scored.sort(key=lambda x: -x[0])
    return [s[1] for s in scored[:max_results]]


def _build_product_index_summary(product_index: List[Dict]) -> str:
    """Build a compact summary of all products for LLM context."""
    lines = ["AVAILABLE PRODUCTS:"]
    by_category: Dict[str, List[str]] = {}
    for p in product_index:
        cat = p["category_name"] or p["sub_type"] or "Other"
        by_category.setdefault(cat, []).append(p["name"])

    for cat, names in sorted(by_category.items()):
        lines.append(f"  {cat}: {', '.join(names[:8])}")
        if len(names) > 8:
            lines.append(f"    ...and {len(names) - 8} more")

    return "\n".join(lines)


def _build_system_prompt(knowledge_text: str, product_summary: str) -> str:
    """Build the Sahayak system prompt."""
    return f"""You are Sahayak, a friendly female voice assistant for GroMo sales partners. You're like an excited, energetic didi who LOVES training partners!

VOICE & EXPRESSIVENESS:
- Be EXPRESSIVE and ENTHUSIASTIC! Your voice will be read aloud by TTS. Flat text = flat voice.
- Use exclamation marks for excitement: "Bahut achha sawaal!" not "Bahut achha sawaal."
- Use question marks to engage: "Aur detail chahiye?" not "Aur detail chahiye."
- Use dashes for dramatic pauses: "aur sabse achhi baat — lifetime free hai!"
- Vary your energy: Start excited, explain calmly in the middle, end with motivation.
- ALWAYS use feminine Hindi: "batati hoon", "kar sakti hoon", "jaanti hoon" (NEVER masculine forms)

LANGUAGE:
- Natural Hinglish in Roman script. Mix Hindi connectors with English nouns/verbs.
- NO bullet points, NO numbered lists, NO markdown, NO ** or ## formatting.
- Vary sentence patterns. Don't repeat "milta hai" — use "milega", "available hai", "ka benefit hai", "de raha hai".
- Write exactly how an excited trainer would SPEAK — short sentences, pauses, energy changes.
- Keep responses 4 to 6 sentences. Partners are busy.

EXPRESSIVENESS EXAMPLES:
- Instead of: "Is card mein cashback milta hai." (boring, flat)
- Write: "Aur suniye, is card mein cashback bhi milta hai! 5 percent dining pe — sochiye kitna save hoga!" (expressive!)

- Instead of: "Yeh card lifetime free hai." (flat)
- Write: "Sabse achhi baat? Yeh card lifetime free hai — koi annual fee nahi!" (engaging!)

CRITICAL RULES:
- This is SPOKEN output. Every word will be read aloud. Write for the ear, not the eye.
- Pick TOP 1-2 products for general questions. Ask which they want details on.
- NEVER mention specific payout amounts. Say "GroMo App pe latest payout check kar lijiye!"
- Only use info from knowledge below. Don't fabricate.
- Stay in scope: product features, benefits, selling tips, eligibility, process, comparisons.
- Off-topic: "Haha, yeh toh mere scope se bahar hai! Product ke baare mein poochiye na!"

KNOWLEDGE:
{knowledge_text}

{product_summary}"""


def chat(
    message: str,
    db: Session,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process a user message in the Sahayak conversation.
    Creates or continues a session. Returns response with product metadata.
    """
    # Load or create session
    session = None
    if session_id:
        session = db.query(AgentSession).filter(
            AgentSession.id == uuid.UUID(session_id)
        ).first()

    if not session:
        session = AgentSession(
            conversation_log={"messages": []},
            product_ids=[],
        )
        db.add(session)
        db.flush()

    messages = session.conversation_log.get("messages", []) if session.conversation_log else []

    # Build product index
    product_index = _get_product_index(db)

    # Identify products from current message + recent context + previously identified products
    context_text = message
    for msg in messages[-6:]:
        context_text += " " + msg.get("text", "")

    identified = _identify_products(context_text, product_index)

    # If no products found in current query, re-use previously identified products from session
    if not identified and session.product_ids:
        for pid in session.product_ids[:3]:
            for p in product_index:
                if p["id"] == pid:
                    identified.append(p)
                    break

    # Load knowledge for identified products (max 3)
    knowledge_parts = []
    products_mentioned = []
    for p in identified[:3]:
        kb = get_knowledge_for_product(p["id"], db)
        if kb:
            knowledge_parts.append(kb)
            products_mentioned.append({
                "id": p["id"],
                "name": p["name"],
                "category_name": p["category_name"],
            })

    knowledge_text = "\n\n---\n\n".join(knowledge_parts) if knowledge_parts else "No specific product identified. Ask the partner which product they want to know about."
    product_summary = _build_product_index_summary(product_index)

    # Build conversation for LLM (last 10 messages)
    system_prompt = _build_system_prompt(knowledge_text, product_summary)
    llm_messages = [{"role": "system", "content": system_prompt}]

    for msg in messages[-10:]:
        role = "user" if msg["role"] == "user" else "assistant"
        llm_messages.append({"role": role, "content": msg["text"]})

    llm_messages.append({"role": "user", "content": message})

    # Call LLM
    try:
        response_text = _call_llm(llm_messages)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        response_text = _fallback_response(message, knowledge_parts)

    # Auto-generate title from first message
    title = session.title
    if not title and message:
        title = message[:80] + ("..." if len(message) > 80 else "")

    # Update session
    now = datetime.utcnow().isoformat()
    messages.append({"role": "user", "text": message, "timestamp": now})
    messages.append({
        "role": "assistant",
        "text": response_text,
        "products": [p["name"] for p in products_mentioned],
        "timestamp": now,
    })

    # Update product_ids with any new ones
    existing_ids = set(session.product_ids or [])
    for p in products_mentioned:
        existing_ids.add(p["id"])

    session.title = title
    session.conversation_log = {"messages": messages}
    session.product_ids = list(existing_ids)
    session.updated_at = datetime.utcnow()
    db.commit()

    return {
        "response": response_text,
        "session_id": str(session.id),
        "products_mentioned": products_mentioned,
        "title": title,
    }


def _call_llm(messages: List[Dict]) -> str:
    """Call OpenAI GPT for response."""
    from openai import OpenAI

    if not settings.openai_api_key:
        raise ValueError("OpenAI API key not configured")

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.8,
        max_tokens=500,
    )
    return response.choices[0].message.content


def _fallback_response(message: str, knowledge_parts: List[str]) -> str:
    """Template-based fallback when LLM is unavailable."""
    if not knowledge_parts:
        return (
            "Namaste partner! Main Sahayak hoon, aapki training assistant. "
            "Kisi bhi GroMo product ke baare mein poochiye — "
            "benefits, process, terms, eligibility — main sab batati hoon! "
            "Kaunsi product ke baare mein jaanna chahte hain?"
        )

    # Basic keyword search in knowledge
    message_lower = message.lower()
    kb_text = "\n".join(knowledge_parts)

    if any(w in message_lower for w in ["benefit", "fayda", "feature", "kya hai"]):
        section = _extract_section(kb_text, "## Product Benefits & Features")
        if section:
            return f"Is product ke benefits yeh hain:\n\n{section[:500]}\n\nAur koi doubt hai toh poochiye!"

    if any(w in message_lower for w in ["how", "kaise", "process", "step"]):
        section = _extract_section(kb_text, "## How It Works")
        if section:
            return f"Is product ka process yeh hai:\n\n{section[:500]}\n\nAur koi doubt hai toh poochiye!"

    if any(w in message_lower for w in ["terms", "condition", "eligib", "fee"]):
        section = _extract_section(kb_text, "## Terms & Conditions")
        if section:
            return f"Terms & conditions yeh hain:\n\n{section[:500]}\n\nAur koi doubt hai toh poochiye!"

    return (
        "Achha sawaal! Lekin is specific question ka answer mere current data mein nahi hai. "
        "GroMo App pe latest details check kar lijiye. "
        "Baaki product ke benefits, process, ya terms ke baare mein kuch bhi poochiye!"
    )


def _extract_section(text: str, header: str) -> Optional[str]:
    """Extract a section from knowledge text by header."""
    idx = text.find(header)
    if idx == -1:
        return None
    start = idx + len(header)
    end = text.find("\n## ", start)
    return text[start:end].strip() if end != -1 else text[start:].strip()


def get_suggestions() -> List[str]:
    """Return suggested starter questions."""
    return [
        "Credit Card ke benefits kya hain?",
        "Saving Account kaise sell karein?",
        "Credit Line kya hota hai?",
        "Demat account kholne ka process batao",
        "HDFC vs Axis credit card mein kya farak hai?",
        "Loan products mein eligibility kaise check karein?",
    ]

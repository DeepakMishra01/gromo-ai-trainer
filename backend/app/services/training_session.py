"""
Training Session Service.
Creates structured training sessions using REAL GroMo product data.
All content is grounded in actual product information — no hallucination.
"""
import logging
import uuid
import random
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.category import Category

logger = logging.getLogger(__name__)


def create_training_session(product_id: str, db: Session) -> dict:
    """
    Create a structured training session for a product using real GroMo data.
    """
    product = (
        db.query(Product)
        .filter(Product.id == uuid.UUID(str(product_id)))
        .first()
    )
    if not product:
        raise ValueError(f"Product not found: {product_id}")

    category = db.query(Category).filter(Category.id == product.category_id).first()
    category_name = category.name if category else product.sub_type or "Financial Product"

    product_data = {
        "id": str(product.id),
        "name": product.name,
        "category_name": category_name,
        "payout": product.payout or "",
        "benefits_text": product.benefits_text or "",
        "how_works_text": product.how_works_text or "",
        "terms_conditions_text": product.terms_conditions_text or "",
    }

    # Build sections
    sections = _build_sections(product_data)

    # Generate quiz questions from real data
    quiz = generate_quiz_questions(product_data)

    session = {
        "session_id": str(uuid.uuid4()),
        "product_id": str(product.id),
        "product_name": product.name,
        "category_name": category_name,
        "payout": product.payout or "",
        "total_sections": len(sections),
        "sections": sections,
        "quiz": quiz,
    }

    logger.info(f"Created training session for product: {product.name}")
    return session


def generate_quiz_questions(product_data: dict) -> List[dict]:
    """
    Generate 5 quiz questions from REAL product data.
    Questions test actual product knowledge, not fabricated info.
    """
    questions = []
    product_name = product_data.get("name", "this product")

    # Q1: Category question
    questions.append(_build_category_question(product_data))

    # Q2: Benefits question (from real benefits_text)
    questions.append(_build_benefits_question(product_data))

    # Q3: Process question (from real how_works_text)
    questions.append(_build_process_question(product_data))

    # Q4: Terms question (from real terms_conditions_text)
    questions.append(_build_terms_question(product_data))

    # Q5: Payout question
    questions.append(_build_payout_question(product_data))

    return questions


def _build_sections(product_data: dict) -> List[dict]:
    """Build training session sections using real product data."""
    product_name = product_data["name"]
    category = product_data.get("category_name", "Financial Product")
    payout = product_data.get("payout", "")
    benefits_text = product_data.get("benefits_text", "")
    how_works_text = product_data.get("how_works_text", "")
    terms_text = product_data.get("terms_conditions_text", "")

    sections = []

    # Section 1: Product Introduction
    sections.append({
        "index": 0,
        "title": "Product Introduction",
        "icon": "info",
        "content": {
            "type": "intro",
            "product_name": product_name,
            "category": category,
            "payout": payout,
            "description": (
                f"{product_name} ek {category} product hai. "
                f"{'Aap is product ko sell karke ' + payout + ' tak kama sakte hain.' if payout else ''}"
            ),
            "summary": (
                f"Is training mein hum {product_name} ke benefits, process, aur terms & conditions cover karenge. "
                f"Sab information GroMo se verified hai."
            ),
        },
        "talking_points": [
            f"{product_name} ek {category} product hai",
            f"Partner payout: {payout}" if payout else "Payout details GroMo app pe check karein",
            "Customer ko product ke baare mein clearly samjhana zaroori hai",
        ],
    })

    # Section 2: Benefits & Features
    benefits_items = _text_to_items(benefits_text, "Product Benefits")
    sections.append({
        "index": 1,
        "title": "Benefits & Features",
        "icon": "star",
        "content": {
            "type": "benefits",
            "items": benefits_items,
            "tip": (
                "Customer ko benefits batate time unki specific needs se connect karein. "
                "Real data use karein, kuch bhi assume mat karein."
            ),
        },
        "talking_points": [
            "Benefits customer ko attract karte hain",
            "Har benefit ka practical use case batayein",
            "ONLY GroMo data use karein, kuch fabricate mat karein",
        ],
    })

    # Section 3: How It Works (Sales Process)
    process_items = _text_to_items(how_works_text, "Sales Process")
    sections.append({
        "index": 2,
        "title": "How It Works",
        "icon": "clipboard",
        "content": {
            "type": "process",
            "items": process_items,
            "tip": (
                "Customer ko step-by-step process samjhayein. "
                "Clear instructions se customer ka confidence badhta hai."
            ),
        },
        "talking_points": [
            "Step-by-step process clear hona chahiye",
            "Customer ko pehle se documents ki list de dein",
            "Process simple aur fast batane se conversion badhti hai",
        ],
    })

    # Section 4: Terms & Conditions
    terms_items = _text_to_items(terms_text, "Terms & Conditions")
    sections.append({
        "index": 3,
        "title": "Terms & Conditions",
        "icon": "currency",
        "content": {
            "type": "terms",
            "items": terms_items,
            "tip": (
                "Terms ke baare mein transparent rahein. "
                "Customer ko hidden conditions ka pata chalne se trust toot-ta hai."
            ),
        },
        "talking_points": [
            "Transparency zaroori hai - saari conditions pehle batayein",
            "Payout rules samajhna important hai",
            "Agar koi condition unclear hai toh GroMo app pe verify karein",
        ],
    })

    # Section 5: Selling Tips
    sections.append({
        "index": 4,
        "title": "Selling Tips",
        "icon": "trophy",
        "content": {
            "type": "tips",
            "items": [
                {"label": "Know Your Product", "value": "Training complete karke hi sell karein. Confident answers dena trust build karta hai."},
                {"label": "Match Customer Needs", "value": "Pehle customer ki need samjhein, phir product recommend karein."},
                {"label": "Be Transparent", "value": "Terms & conditions clearly batayein. Hidden info se trust toot-ta hai."},
                {"label": "Use GroMo App", "value": "GroMo app se share link bhejein, isse tracking easy hoti hai."},
                {"label": "Follow Up", "value": "Customer se 2-3 din baad follow up zaroor karein."},
            ],
            "tip": "In tips ko follow karke aap apni conversion rate significantly improve kar sakte hain.",
        },
        "talking_points": [
            "Product knowledge + customer empathy = best results",
            "Real data use karein, kuch bhi assume mat karein",
            "GroMo app se share links use karein for proper tracking",
        ],
    })

    # Section 6: Quick Quiz
    sections.append({
        "index": 5,
        "title": "Quick Quiz",
        "icon": "quiz",
        "content": {
            "type": "quiz",
            "description": (
                f"Ab test karte hain ki aapne {product_name} ke baare mein kitna seekha! "
                "5 questions hain - try karein aur apna score dekhein."
            ),
        },
        "talking_points": [
            "Quiz se apna knowledge check karein",
            "Galat answers se bhi seekhne milta hai",
            "80%+ score aaye toh aap sell karne ke liye ready hain!",
        ],
    })

    return sections


def _text_to_items(text: str, fallback_label: str) -> List[dict]:
    """Convert plain text (from GroMo API) to display items."""
    if not text:
        return [{"label": "", "value": f"No {fallback_label.lower()} information available from GroMo."}]

    items = []
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    for line in lines:
        # Try to split on colon for label:value pairs
        if ':' in line and not line.startswith('http'):
            parts = line.split(':', 1)
            items.append({"label": parts[0].strip(), "value": parts[1].strip()})
        else:
            items.append({"label": "", "value": line})

    return items if items else [{"label": "", "value": f"No {fallback_label.lower()} information available."}]


# ---- Quiz Question Builders (using real data) ----

def _extract_real_facts(text: str) -> List[str]:
    """Extract distinct fact lines from product text."""
    if not text:
        return []
    lines = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 10]
    return lines


def _build_category_question(product_data: dict) -> dict:
    """Build a question about the product category."""
    product_name = product_data.get("name", "This product")
    category = product_data.get("category_name", "Financial Product")

    wrong_categories = [
        "Real Estate", "Automobile", "Travel", "Gaming",
        "Healthcare", "Education Loan", "Insurance",
        "Mutual Fund", "Credit Card", "Personal Loan",
        "Business Loan", "Demat Account", "Saving Account",
    ]
    wrong_categories = [c for c in wrong_categories if c.lower() != category.lower()]
    random.shuffle(wrong_categories)

    options = [category] + wrong_categories[:3]
    random.shuffle(options)
    correct_index = options.index(category)

    return {
        "question": f"{product_name} kis category mein aata hai?",
        "options": options,
        "correct_answer": correct_index,
        "explanation": f"{product_name} {category} category mein aata hai.",
    }


def _build_benefits_question(product_data: dict) -> dict:
    """Build a question about product benefits using real data."""
    product_name = product_data.get("name", "This product")
    benefits_text = product_data.get("benefits_text", "")
    facts = _extract_real_facts(benefits_text)

    if facts:
        real_fact = facts[0][:100]  # Use first real benefit
    else:
        real_fact = "GroMo app pe listed benefits available hain"

    fake_options = [
        "Free international flights har saal",
        "Guaranteed 50% annual returns",
        "Free luxury car with every purchase",
        "Zero tax on all transactions",
        "Free gold coins har mahine",
        "Lifetime free gym membership",
    ]
    random.shuffle(fake_options)

    options = [real_fact] + fake_options[:3]
    random.shuffle(options)
    correct_index = options.index(real_fact)

    return {
        "question": f"{product_name} ka kaunsa benefit correct hai?",
        "options": options,
        "correct_answer": correct_index,
        "explanation": f"Correct answer: {real_fact}",
    }


def _build_process_question(product_data: dict) -> dict:
    """Build a question about how the product works using real data."""
    product_name = product_data.get("name", "This product")
    how_works = product_data.get("how_works_text", "")
    facts = _extract_real_facts(how_works)

    if facts:
        real_fact = facts[0][:100]
    else:
        real_fact = "GroMo app se link share karke sell kar sakte hain"

    fake_options = [
        "Customer ko office mein bulana padta hai",
        "Sirf cash payment se hota hai",
        "Customer ka physical signature zaroori hai branch pe",
        "Minimum 10 customers chahiye ek saath",
        "Sirf weekdays pe 9-5 apply kar sakte hain",
        "Agent ko customer ke ghar jaana padta hai",
    ]
    random.shuffle(fake_options)

    options = [real_fact] + fake_options[:3]
    random.shuffle(options)
    correct_index = options.index(real_fact)

    return {
        "question": f"{product_name} ka process kya hai?",
        "options": options,
        "correct_answer": correct_index,
        "explanation": f"Correct answer: {real_fact}",
    }


def _build_terms_question(product_data: dict) -> dict:
    """Build a question about terms using real data."""
    product_name = product_data.get("name", "This product")
    terms = product_data.get("terms_conditions_text", "")
    facts = _extract_real_facts(terms)

    if facts:
        real_fact = facts[0][:100]
    else:
        real_fact = "Terms & conditions GroMo app pe available hain"

    fake_options = [
        "Koi terms & conditions nahi hain",
        "Sirf 18 saal se kam ke liye hai",
        "Sirf NRI customers ke liye available hai",
        "Annual fee Rs 50,000 hai",
        "Processing fee 25% hai",
        "Sirf government employees ke liye hai",
    ]
    random.shuffle(fake_options)

    options = [real_fact] + fake_options[:3]
    random.shuffle(options)
    correct_index = options.index(real_fact)

    return {
        "question": f"{product_name} ke terms ke baare mein kaunsi baat sahi hai?",
        "options": options,
        "correct_answer": correct_index,
        "explanation": f"Correct answer: {real_fact}",
    }


def _build_payout_question(product_data: dict) -> dict:
    """Build a question about partner payout."""
    product_name = product_data.get("name", "This product")
    payout = product_data.get("payout", "")

    if payout:
        real_answer = f"Partner payout: {payout}"
    else:
        real_answer = "Payout details GroMo app pe available hain"

    fake_options = [
        "Partner payout: Rs 50,000 per sale",
        "Koi payout nahi milta",
        "Payout sirf Rs 10 hai",
        "Partner payout: Rs 1 lakh guaranteed",
        "Payout 6 mahine baad milta hai",
        "Sirf top 10 partners ko payout milta hai",
    ]
    random.shuffle(fake_options)

    options = [real_answer] + fake_options[:3]
    random.shuffle(options)
    correct_index = options.index(real_answer)

    return {
        "question": f"{product_name} sell karne pe GroMo partner ko kitna milta hai?",
        "options": options,
        "correct_answer": correct_index,
        "explanation": f"Correct answer: {real_answer}",
    }

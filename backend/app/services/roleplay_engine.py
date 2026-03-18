"""
Roleplay engine service.
Simulates customer interactions for GroMo partner sales practice.
Uses OpenAI GPT-4 for dynamic responses (primary) or template-based fallback.
"""
import random
import logging
from typing import Optional, List, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Predefined customer personas by difficulty
# ---------------------------------------------------------------------------

EASY_PERSONAS = [
    {
        "name": "Priya Sharma",
        "age": 28,
        "occupation": "School Teacher",
        "personality": "Friendly and curious, interested in saving money",
        "buying_intent": 0.7,
        "objections": ["Kya yeh safe hai?"],
        "concerns": ["Minimum investment kitna hai?"],
    },
    {
        "name": "Rahul Verma",
        "age": 32,
        "occupation": "Small Business Owner",
        "personality": "Practical, wants quick solutions for financial needs",
        "buying_intent": 0.65,
        "objections": ["Processing time kitna hai?"],
        "concerns": ["Kya online apply kar sakte hain?"],
    },
    {
        "name": "Anita Desai",
        "age": 45,
        "occupation": "Homemaker",
        "personality": "Warm and trusting, looking for family financial products",
        "buying_intent": 0.75,
        "objections": ["Mere husband se baat karni padegi"],
        "concerns": ["Kya yeh mere bachcho ke liye bhi hai?"],
    },
]

MEDIUM_PERSONAS = [
    {
        "name": "Vikram Singh",
        "age": 35,
        "occupation": "IT Professional",
        "personality": "Analytical, compares multiple options before deciding",
        "buying_intent": 0.4,
        "objections": [
            "Doosre products se yeh kaise alag hai?",
            "Returns guaranteed hain kya?",
        ],
        "concerns": [
            "Tax benefits kya hain?",
            "Lock-in period kitna hai?",
        ],
    },
    {
        "name": "Meena Patel",
        "age": 40,
        "occupation": "Bank Clerk",
        "personality": "Cautious, already knows some financial products, needs convincing",
        "buying_intent": 0.35,
        "objections": [
            "Meri bank mein bhi similar product hai",
            "Hidden charges toh nahi hain?",
        ],
        "concerns": [
            "Customer support kaisa hai?",
            "Claim process easy hai?",
        ],
    },
    {
        "name": "Suresh Kumar",
        "age": 50,
        "occupation": "Retired Government Employee",
        "personality": "Experienced, values trust and long-term safety",
        "buying_intent": 0.4,
        "objections": [
            "Mujhe koi risk nahi chahiye",
            "Pehle bhi logon ne galat product becha hai",
        ],
        "concerns": [
            "Company kitni purani hai?",
            "Kya guaranteed return milega?",
        ],
    },
]

HARD_PERSONAS = [
    {
        "name": "Rajesh Agarwal",
        "age": 42,
        "occupation": "CA / Chartered Accountant",
        "personality": "Skeptical, questions everything, very price-sensitive",
        "buying_intent": 0.15,
        "objections": [
            "Yeh product toh overpriced hai",
            "Market mein better options hain",
            "Commission ke liye bech rahe ho kya?",
            "SEBI registered hai kya?",
        ],
        "concerns": [
            "Exact fees breakdown do",
            "Past performance data dikhao",
            "Regulatory compliance kya hai?",
        ],
    },
    {
        "name": "Neha Gupta",
        "age": 30,
        "occupation": "Startup Founder",
        "personality": "Busy and dismissive, very little time, hard to impress",
        "buying_intent": 0.1,
        "objections": [
            "Mujhe interest nahi hai",
            "Time waste mat karo mera",
            "Sab products same hote hain",
        ],
        "concerns": [
            "2 minute mein batao kya special hai",
            "ROI kya milega exactly?",
            "Koi proof hai claims ka?",
        ],
    },
    {
        "name": "Deepak Tiwari",
        "age": 55,
        "occupation": "Retired Army Officer",
        "personality": "Tough, direct, does not trust easily, demands proof",
        "buying_intent": 0.2,
        "objections": [
            "Pehle bhi fraud hua hai mere saath",
            "Tumhari company ka track record kya hai?",
            "Guarantee do ki paisa doobega nahi",
            "Written mein do sab kuch",
        ],
        "concerns": [
            "Government backed hai kya?",
            "Complaint kahan karein agar problem ho?",
        ],
    },
]

# ---------------------------------------------------------------------------
# Persona creation
# ---------------------------------------------------------------------------


def create_customer_persona(difficulty: str = "medium") -> Dict[str, Any]:
    """
    Generate a customer persona based on difficulty level.

    Args:
        difficulty: One of "easy", "medium", "hard".

    Returns:
        Dict with name, age, occupation, personality, buying_intent,
        objections, and concerns.
    """
    if difficulty == "easy":
        persona = random.choice(EASY_PERSONAS)
    elif difficulty == "hard":
        persona = random.choice(HARD_PERSONAS)
    else:
        persona = random.choice(MEDIUM_PERSONAS)

    # Return a copy so the original templates are not mutated
    return {
        "name": persona["name"],
        "age": persona["age"],
        "occupation": persona["occupation"],
        "personality": persona["personality"],
        "buying_intent": persona["buying_intent"],
        "objections": list(persona["objections"]),
        "concerns": list(persona["concerns"]),
    }


# ---------------------------------------------------------------------------
# Greeting templates
# ---------------------------------------------------------------------------

GREETING_TEMPLATES = {
    "easy": [
        "Namaste! Maine {product} ke baare mein suna hai. Kya aap mujhe iske baare mein bata sakte hain?",
        "Hello! Mujhe {product} mein interest hai. Thoda detail mein batayenge?",
        "Ji namaste, mujhe ek achha financial product chahiye. {product} kaisa hai?",
    ],
    "medium": [
        "Haan, bataiye {product} ke baare mein. Lekin pehle yeh bataiye ki yeh doosron se kaise alag hai?",
        "Namaste. Mujhe {product} ke baare mein kuch pata hai, lekin convince karo ki yeh sahi hai mere liye.",
        "Ok, suniye, {product} ke baare mein baat karte hain. But main compare karunga doosre options se.",
    ],
    "hard": [
        "Dekhiye, mujhe koi product nahi chahiye. Aapko kya lagta hai {product} special hai?",
        "Hmm, {product}? Sab log yahi kehte hain ki unka product best hai. Proof dikhao.",
        "Theek hai, 2 minute deta hoon. Batao {product} mein aisa kya hai jo mujhe paise lagane chahiye?",
    ],
}

# ---------------------------------------------------------------------------
# Template-based response generation
# ---------------------------------------------------------------------------

# Keywords that the partner might mention and corresponding customer response patterns
KEYWORD_RESPONSES = {
    "features": {
        "easy": [
            "Achha, yeh features toh achhe hain! Lekin price kya hai iska?",
            "Wow, yeh toh kaafi useful lag raha hai. Kitna paisa lagana padega?",
        ],
        "medium": [
            "Features toh theek hain, lekin pricing kya hai? Koi hidden charges toh nahi?",
            "Hmm interesting. Par doosre products mein bhi yahi features milte hain. Price batao.",
        ],
        "hard": [
            "Features toh sab batate hain. Exact pricing batao, sab charges ke saath.",
            "Yeh features marketing ke liye hain. Real data dikhao aur price breakdown do.",
        ],
    },
    "price": {
        "easy": [
            "Ok, price reasonable hai. Kaun apply kar sakta hai? Meri eligibility kya hai?",
            "Theek hai, yeh toh affordable hai. Kya main eligible hoon?",
        ],
        "medium": [
            "Hmm, price thoda zyada hai. Eligibility kya hai? Aur koi discount milega?",
            "Itna toh competitors se zyada hai. Eligibility criteria batao, aur koi offer ho toh batao.",
        ],
        "hard": [
            "Yeh toh bahut zyada hai. Competitors se compare karo. Eligibility bhi exact batao.",
            "Price justify karo. Market mein isse sasta mil raha hai. Eligibility conditions kya hain?",
        ],
    },
    "eligibility": {
        "easy": [
            "Achha, main eligible hoon! Toh apply kaise karu? Process kya hai?",
            "Great, meri eligibility match karti hai. Apply karne mein kitna time lagega?",
        ],
        "medium": [
            "Ok eligibility samajh aayi. But documentation kya chahiye? Process complicated toh nahi?",
            "Theek hai, eligible hoon. Par process mein kitna time lagega? Aur koi issue aaye toh?",
        ],
        "hard": [
            "Eligibility toh ek side hai. Rejection rate kya hai? Aur agar reject ho gaya toh?",
            "Fine, eligible hoon. Par approval guaranteed nahi hai na? Success rate batao.",
        ],
    },
    "benefit": {
        "easy": [
            "Yeh benefits toh bahut achhe hain! Mujhe lagta hai yeh mere liye sahi hai.",
            "Waah, itne saare benefits! Main interested hoon, aage kya karna hai?",
        ],
        "medium": [
            "Benefits achhe hain, lekin yeh guaranteed hain? Koi fine print toh nahi hai?",
            "Hmm, benefits attractive hain. Par pehle terms & conditions bata do.",
        ],
        "hard": [
            "Benefits pe mat jao. Real returns batao with proof. Claims ki guarantee kya hai?",
            "Har product mein benefits likhte hain. Data dikhao ki actually kitna fayda hua logon ko.",
        ],
    },
    "objection": {
        "easy": [
            "Achha, aapne meri concern address kar di. Theek hai, mujhe aur batao.",
            "Ok, samajh aaya. Meri doubt clear ho gayi. Aage kya step hai?",
        ],
        "medium": [
            "Hmm, thoda convince hua hoon. Lekin ek aur doubt hai - kya guarantee hai?",
            "Achha point hai. Par phir bhi main puri tarah convinced nahi hoon. Aur evidence do.",
        ],
        "hard": [
            "Yeh toh standard answer hai. Specific data do, general baatein mat karo.",
            "Theek hai, partially samajh aaya. Par written guarantee milegi kya?",
        ],
    },
    "close": {
        "easy": [
            "Haan, mujhe lagta hai yeh achha product hai. Main lena chahta/chahti hoon!",
            "Ok, convinced hoon! Apply kaise karein? Abhi kar sakte hain kya?",
        ],
        "medium": [
            "Hmm, sochta/sochti hoon. Ek din ka time do. Kal baat karte hain.",
            "Interesting hai. Main ek baar ghar pe discuss karke batata/batati hoon.",
        ],
        "hard": [
            "Abhi nahi. Documentation bhejo email pe, review karke bataunga/bataungi.",
            "Jaldi mat karo. Pehle mujhe sab written mein do. Phir decide karunga/karungi.",
        ],
    },
}

# Fallback responses when no keyword matches
FALLBACK_RESPONSES = {
    "easy": [
        "Achha, aur batao iske baare mein. Mujhe aur details chahiye.",
        "Ok ok, interesting hai. Kuch aur features hain iske?",
        "Theek hai, samajh aa raha hai. Aur kya kya milta hai?",
    ],
    "medium": [
        "Hmm, yeh toh suna hai pehle. Kuch naya batao.",
        "Theek hai, par yeh information toh website pe bhi hai. Kuch alag batao.",
        "Ok, but specifically mere liye kya fayda hai?",
    ],
    "hard": [
        "Yeh sab marketing hai. Real facts do mujhe.",
        "Time waste ho raha hai mera. Sidhe point pe aao.",
        "Generic baatein mat karo. Specific numbers aur data do.",
    ],
}

# Positive closing responses when buying signal is high
BUYING_RESPONSES = {
    "easy": [
        "Haan, main convinced hoon! Mujhe yeh product lena hai. Process start karte hain!",
        "Bahut achha explain kiya aapne. Main ready hoon apply karne ke liye!",
    ],
    "medium": [
        "Achha, kaafi achhe se samjhaya aapne. Main interested hoon. Aage process batao.",
        "Ok, convinced hoon kaafi had tak. Application start karte hain.",
    ],
    "hard": [
        "Hmm, aapne achhe points diye. Thodi si interest ban rahi hai. Documentation share karo.",
        "Ok fine, aapne mehnat ki hai. Main consider karunga. Details email karo.",
    ],
}


def _detect_keywords(message: str) -> str:
    """Detect which keyword category a partner message falls into."""
    msg_lower = message.lower()

    # Close / purchase intent detection
    close_keywords = [
        "apply", "sign up", "register", "buy", "kharido", "le lo",
        "start", "process", "shuru", "ready", "proceed", "lena chahiye",
        "best option", "recommend", "suggest", "le lijiye",
    ]
    if any(kw in msg_lower for kw in close_keywords):
        return "close"

    # Feature detection
    feature_keywords = [
        "feature", "benefit", "advantage", "fayda", "achha", "special",
        "kya milta", "kya hai", "functionality", "capability", "offer",
    ]
    if any(kw in msg_lower for kw in feature_keywords):
        return "features"

    # Price detection
    price_keywords = [
        "price", "cost", "fee", "charge", "kitna", "paisa", "rupee",
        "rs", "amount", "premium", "emi", "installment", "rate",
        "kharcha", "daam", "free", "discount", "offer",
    ]
    if any(kw in msg_lower for kw in price_keywords):
        return "price"

    # Eligibility detection
    elig_keywords = [
        "eligib", "qualify", "kaun", "apply", "age", "income",
        "document", "requirement", "criteria", "yogya", "paatr",
        "kon kar sakta", "kaise apply",
    ]
    if any(kw in msg_lower for kw in elig_keywords):
        return "eligibility"

    # Benefit detection
    benefit_keywords = [
        "benefit", "fayda", "advantage", "return", "profit", "labh",
        "kamai", "earn", "milega", "kya milta",
    ]
    if any(kw in msg_lower for kw in benefit_keywords):
        return "benefit"

    # Objection handling detection
    objection_keywords = [
        "safe", "risk", "guarantee", "trust", "bharosa", "sure",
        "pakka", "certain", "worry", "tension", "problem", "issue",
        "complaint", "fraud", "scam",
    ]
    if any(kw in msg_lower for kw in objection_keywords):
        return "objection"

    return "fallback"


def _calculate_response_quality(message: str) -> float:
    """
    Heuristic score (0-1) for how good a partner message is.
    Longer, more detailed messages score higher.
    """
    score = 0.0
    msg_lower = message.lower()
    word_count = len(message.split())

    # Length bonus
    if word_count >= 20:
        score += 0.3
    elif word_count >= 10:
        score += 0.2
    elif word_count >= 5:
        score += 0.1

    # Contains product details
    detail_keywords = [
        "feature", "benefit", "eligib", "fee", "charge", "return",
        "safe", "guarantee", "process", "document", "apply",
        "fayda", "suvidha", "aasan",
    ]
    matches = sum(1 for kw in detail_keywords if kw in msg_lower)
    score += min(matches * 0.1, 0.3)

    # Empathy / politeness signals
    empathy_keywords = [
        "samajh", "zaroor", "bilkul", "achha", "sahi",
        "aapke liye", "aapki", "help", "madad", "sure",
        "don't worry", "no tension", "tension mat",
    ]
    if any(kw in msg_lower for kw in empathy_keywords):
        score += 0.2

    # Hinglish usage bonus
    hinglish_keywords = [
        "namaste", "ji", "haan", "nahi", "aap", "yeh",
        "hai", "kar", "ke", "se",
    ]
    if sum(1 for kw in hinglish_keywords if kw in msg_lower) >= 2:
        score += 0.1

    return min(score, 1.0)


def _generate_openai_response(
    persona: Dict[str, Any],
    product_data: Dict[str, Any],
    conversation: List[Dict[str, Any]],
    partner_message: str,
    difficulty: str,
) -> Optional[Dict[str, Any]]:
    """
    Generate customer response using OpenAI GPT-4.
    Returns None if OpenAI is unavailable, triggering template fallback.
    """
    if settings.llm_provider != "openai" or not settings.openai_api_key:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)

        # Build product context from real GroMo data
        product_context = f"""Product: {product_data.get('name', 'Unknown')}
Category: {product_data.get('category', product_data.get('category_name', ''))}
Payout: {product_data.get('payout', 'N/A')}
Benefits: {(product_data.get('benefits_text') or '')[:500]}
How It Works: {(product_data.get('how_works_text') or '')[:500]}
Terms: {(product_data.get('terms_conditions_text') or '')[:300]}"""

        # Build conversation history
        conv_history = ""
        for msg in conversation[-10:]:  # Last 10 messages
            role_label = "GroMo Partner" if msg.get("role") == "partner" else "Customer"
            conv_history += f"{role_label}: {msg.get('text', '')}\n"

        difficulty_instructions = {
            "easy": "You are friendly, curious, and relatively easy to convince. You ask simple questions and are open to buying.",
            "medium": "You are moderately skeptical. You compare options, ask about fees and fine print, and need proper convincing before buying.",
            "hard": "You are very skeptical and hard to convince. You challenge every claim, demand proof and data, are price-sensitive, and resist buying pressure.",
        }

        turn_count = len([m for m in conversation if m.get("role") == "partner"])

        system_prompt = f"""You are a realistic Indian customer in a roleplay training session for GroMo financial product sales.

CHARACTER:
- Name: {persona.get('name', 'Customer')}
- Age: {persona.get('age', 35)}
- Occupation: {persona.get('occupation', 'Professional')}
- Personality: {persona.get('personality', 'Average customer')}

DIFFICULTY: {difficulty}
{difficulty_instructions.get(difficulty, difficulty_instructions['medium'])}

PRODUCT BEING SOLD:
{product_context}

RULES:
1. Respond in Hinglish (mix of Hindi and English) naturally, as a real Indian customer would speak
2. Stay in character - never break the roleplay
3. Base your responses ONLY on the product information provided above
4. Ask relevant questions about the product features, pricing, process, eligibility
5. If the partner gives wrong information about the product, politely challenge them
6. Keep responses concise (1-3 sentences typically)
7. After {5 if difficulty == 'easy' else 7 if difficulty == 'medium' else 10}+ good exchanges, gradually become more interested
8. This is turn {turn_count + 1} of the conversation

CONVERSATION SO FAR:
{conv_history}

Respond as the customer to the partner's latest message. Output ONLY the customer's dialogue."""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"GroMo Partner says: {partner_message}"},
            ],
            temperature=0.8,
            max_tokens=200,
        )

        ai_response = response.choices[0].message.content.strip()

        # Calculate buying signal based on turn count and quality
        quality = _calculate_response_quality(partner_message)
        base_signal = persona.get("buying_intent", 0.3)
        quality_bonus = quality * 0.1 * turn_count
        signal = min(base_signal + quality_bonus, 1.0)

        if turn_count >= 5 and quality >= 0.3:
            signal = min(signal + 0.2, 1.0)

        if signal >= 0.7:
            sentiment = "positive"
        elif signal >= 0.4:
            sentiment = "neutral"
        else:
            sentiment = "negative"

        logger.info(f"OpenAI roleplay response generated (turn {turn_count + 1})")
        return {
            "response": ai_response,
            "sentiment": sentiment,
            "buying_signal": round(signal, 2),
        }

    except Exception as e:
        logger.error(f"OpenAI roleplay response failed: {e}")
        return None


def generate_customer_response(
    persona: Dict[str, Any],
    product_data: Dict[str, Any],
    conversation: List[Dict[str, Any]],
    partner_message: str,
    difficulty: str,
) -> Dict[str, Any]:
    """
    Generate the AI customer's response.
    Uses OpenAI GPT-4 (primary) or template matching (fallback).

    Args:
        persona: The customer persona dict.
        product_data: Product information.
        conversation: List of conversation messages so far.
        partner_message: The partner's latest message.
        difficulty: "easy", "medium", or "hard".

    Returns:
        Dict with response, sentiment, buying_signal.
    """
    # Try OpenAI first for dynamic, realistic responses
    openai_result = _generate_openai_response(
        persona, product_data, conversation, partner_message, difficulty
    )
    if openai_result:
        return openai_result

    # Fallback to template-based responses
    logger.info("Using template-based roleplay (OpenAI unavailable)")
    turn_count = len([m for m in conversation if m.get("role") == "partner"])
    quality = _calculate_response_quality(partner_message)
    keyword_category = _detect_keywords(partner_message)

    # Base buying signal from persona
    base_signal = persona.get("buying_intent", 0.3)

    # Adjust signal based on conversation quality
    quality_bonus = quality * 0.1 * turn_count
    signal = min(base_signal + quality_bonus, 1.0)

    # After 5+ good exchanges with decent quality, move towards buying
    if turn_count >= 5 and quality >= 0.3:
        signal = min(signal + 0.2, 1.0)

    # Determine sentiment
    if signal >= 0.7:
        sentiment = "positive"
    elif signal >= 0.4:
        sentiment = "neutral"
    else:
        sentiment = "negative"

    # If buying signal is high enough after several turns, respond positively
    if signal >= 0.75 and turn_count >= 4:
        responses = BUYING_RESPONSES.get(difficulty, BUYING_RESPONSES["medium"])
        response = random.choice(responses)
    elif keyword_category == "fallback":
        responses = FALLBACK_RESPONSES.get(difficulty, FALLBACK_RESPONSES["medium"])
        response = random.choice(responses)
    else:
        category_responses = KEYWORD_RESPONSES.get(keyword_category, {})
        responses = category_responses.get(difficulty, category_responses.get("medium", []))
        if responses:
            response = random.choice(responses)
        else:
            responses = FALLBACK_RESPONSES.get(difficulty, FALLBACK_RESPONSES["medium"])
            response = random.choice(responses)

    # Occasionally inject a persona-specific objection or concern
    if turn_count >= 2 and turn_count <= 4 and random.random() < 0.3:
        objections = persona.get("objections", [])
        concerns = persona.get("concerns", [])
        extras = objections + concerns
        if extras:
            extra = random.choice(extras)
            response = response + " Aur haan, " + extra

    return {
        "response": response,
        "sentiment": sentiment,
        "buying_signal": round(signal, 2),
    }


# ---------------------------------------------------------------------------
# Session evaluation
# ---------------------------------------------------------------------------


def _evaluate_with_openai(
    conversation: List[Dict[str, Any]],
    product_data: Dict[str, Any],
    difficulty: str,
) -> Optional[Dict[str, Any]]:
    """Evaluate session using OpenAI GPT-4 for richer feedback."""
    if settings.llm_provider != "openai" or not settings.openai_api_key:
        return None

    try:
        from openai import OpenAI
        import json

        client = OpenAI(api_key=settings.openai_api_key)

        conv_text = ""
        for msg in conversation:
            role = "Partner" if msg.get("role") == "partner" else "Customer"
            conv_text += f"{role}: {msg.get('text', '')}\n"

        product_context = f"""Product: {product_data.get('name', 'Unknown')}
Benefits: {(product_data.get('benefits_text') or '')[:400]}
Process: {(product_data.get('how_works_text') or '')[:400]}
Payout: {product_data.get('payout', 'N/A')}"""

        system_prompt = f"""You are an expert sales trainer evaluating a GroMo partner's roleplay practice session.
Difficulty level: {difficulty}

PRODUCT INFO:
{product_context}

CONVERSATION:
{conv_text}

Evaluate the partner's performance and respond in this EXACT JSON format:
{{
    "overall_score": <float 0-10>,
    "skill_scores": {{
        "product_knowledge": <float 0-10>,
        "communication": <float 0-10>,
        "objection_handling": <float 0-10>,
        "closing_skills": <float 0-10>,
        "empathy": <float 0-10>
    }},
    "feedback": "<2-3 sentence overall feedback in English>",
    "strengths": ["<strength 1>", "<strength 2>"],
    "improvements": ["<improvement 1>", "<improvement 2>"]
}}

Score strictly based on:
- Did the partner accurately describe the product using REAL product data?
- Did they handle customer objections well?
- Did they communicate clearly in Hinglish?
- Did they attempt to close the sale?
- Did they show empathy and customer-centric approach?
- For {difficulty} difficulty, adjust expectations accordingly."""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Evaluate this roleplay session."},
            ],
            temperature=0.3,
            max_tokens=500,
        )

        result_text = response.choices[0].message.content.strip()

        # Parse JSON from response
        # Handle markdown code blocks
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        evaluation = json.loads(result_text)
        logger.info("OpenAI session evaluation completed")
        return evaluation

    except Exception as e:
        logger.error(f"OpenAI session evaluation failed: {e}")
        return None


def evaluate_session(
    conversation: List[Dict[str, Any]],
    product_data: Dict[str, Any],
    difficulty: str,
) -> Dict[str, Any]:
    """
    Evaluate partner performance across multiple skills.
    Uses OpenAI GPT-4 (primary) or heuristic scoring (fallback).

    Args:
        conversation: Full conversation log.
        product_data: Product information dict.
        difficulty: Session difficulty level.

    Returns:
        Dict with overall_score, skill_scores, feedback, strengths,
        improvements.
    """
    # Try OpenAI evaluation first
    openai_eval = _evaluate_with_openai(conversation, product_data, difficulty)
    if openai_eval:
        return openai_eval

    logger.info("Using heuristic evaluation (OpenAI unavailable)")
    partner_messages = [
        m.get("text", "") for m in conversation if m.get("role") == "partner"
    ]
    all_partner_text = " ".join(partner_messages).lower()
    num_partner_turns = len(partner_messages)

    # 1. Product Knowledge (0-10)
    product_knowledge = _score_product_knowledge(all_partner_text, product_data)

    # 2. Communication Skills (0-10)
    communication = _score_communication(partner_messages)

    # 3. Objection Handling (0-10)
    objection_handling = _score_objection_handling(all_partner_text, conversation)

    # 4. Closing Skills (0-10)
    closing = _score_closing(partner_messages, conversation)

    # 5. Empathy (0-10)
    empathy = _score_empathy(all_partner_text, partner_messages)

    # Weighted average
    weights = {
        "product_knowledge": 0.25,
        "communication": 0.20,
        "objection_handling": 0.20,
        "closing_skills": 0.20,
        "empathy": 0.15,
    }

    skill_scores = {
        "product_knowledge": round(product_knowledge, 1),
        "communication": round(communication, 1),
        "objection_handling": round(objection_handling, 1),
        "closing_skills": round(closing, 1),
        "empathy": round(empathy, 1),
    }

    overall = (
        product_knowledge * weights["product_knowledge"]
        + communication * weights["communication"]
        + objection_handling * weights["objection_handling"]
        + closing * weights["closing_skills"]
        + empathy * weights["empathy"]
    )
    overall = round(overall, 1)

    # Difficulty bonus
    if difficulty == "hard" and overall >= 5:
        overall = min(overall + 0.5, 10.0)
    elif difficulty == "easy" and overall >= 7:
        overall = max(overall - 0.3, 0.0)

    # Generate feedback
    feedback, strengths, improvements = _generate_feedback(
        skill_scores, num_partner_turns, difficulty
    )

    return {
        "overall_score": round(overall, 1),
        "skill_scores": skill_scores,
        "feedback": feedback,
        "strengths": strengths,
        "improvements": improvements,
    }


def _score_product_knowledge(text: str, product_data: Dict[str, Any]) -> float:
    """Score how well partner mentioned product details using real GroMo data."""
    score = 2.0  # Base score for participating

    product_name = (product_data.get("name") or "").lower()
    if product_name and product_name in text:
        score += 1.5

    # Check if they mentioned real product benefits (from benefits_text)
    benefits_text = (product_data.get("benefits_text") or "").lower()
    if benefits_text:
        benefit_words = [w for w in benefits_text.split() if len(w) > 4][:20]
        benefit_mentions = sum(1 for w in benefit_words if w in text)
        score += min(benefit_mentions * 0.3, 2.0)

    # Check if they mentioned process details (from how_works_text)
    how_works = (product_data.get("how_works_text") or "").lower()
    if how_works:
        process_words = [w for w in how_works.split() if len(w) > 4][:15]
        process_mentions = sum(1 for w in process_words if w in text)
        score += min(process_mentions * 0.3, 1.5)

    # Check if they mentioned payout
    payout = (product_data.get("payout") or "").lower()
    if payout and any(part in text for part in payout.split() if len(part) > 2):
        score += 1.0

    # Check benefit-related keywords
    benefit_keywords = ["benefit", "fayda", "advantage", "return", "labh", "feature"]
    if any(kw in text for kw in benefit_keywords):
        score += 0.5

    # Check process-related keywords
    process_keywords = ["process", "apply", "step", "document", "kaise", "tarika"]
    if any(kw in text for kw in process_keywords):
        score += 0.5

    # Check terms/fee mentions
    terms_keywords = ["terms", "condition", "fee", "charge", "cost", "price", "free", "emi", "kharcha"]
    if any(kw in text for kw in terms_keywords):
        score += 1.0

    return min(score, 10.0)


def _score_communication(messages: List[str]) -> float:
    """Score communication quality based on message characteristics."""
    if not messages:
        return 0.0

    score = 2.0  # Base
    avg_length = sum(len(m.split()) for m in messages) / len(messages)

    # Ideal message length: 10-30 words
    if 10 <= avg_length <= 30:
        score += 3.0
    elif 5 <= avg_length < 10:
        score += 1.5
    elif avg_length > 30:
        score += 2.0
    else:
        score += 0.5

    # Variety in message lengths (not all the same length)
    lengths = [len(m.split()) for m in messages]
    if len(set(lengths)) > 1:
        score += 1.0

    # Hinglish usage
    hinglish_words = ["namaste", "ji", "aap", "haan", "bilkul", "zaroor", "achha", "sahi"]
    all_text = " ".join(messages).lower()
    hinglish_count = sum(1 for w in hinglish_words if w in all_text)
    score += min(hinglish_count * 0.5, 2.0)

    # Number of turns (more engagement = better)
    if len(messages) >= 5:
        score += 1.5
    elif len(messages) >= 3:
        score += 0.5

    return min(score, 10.0)


def _score_objection_handling(text: str, conversation: List[Dict[str, Any]]) -> float:
    """Score how well partner handled customer objections."""
    score = 3.0  # Base

    # Find customer objections/concerns in conversation
    customer_messages = [
        m.get("text", "") for m in conversation if m.get("role") == "customer"
    ]
    objection_keywords = [
        "risk", "expensive", "zyada", "trust", "bharosa", "fraud",
        "hidden", "guarantee", "problem", "issue", "compare", "better",
        "nahi", "skeptic",
    ]

    objections_found = 0
    for msg in customer_messages:
        msg_lower = msg.lower()
        if any(kw in msg_lower for kw in objection_keywords):
            objections_found += 1

    if objections_found == 0:
        return 7.0  # No objections to handle

    # Check partner response quality after objections
    reassurance_keywords = [
        "safe", "secure", "guarantee", "bharosa", "trust", "sure",
        "pakka", "don't worry", "tension mat", "certified", "registered",
        "rbi", "sebi", "irda", "government", "regulated", "proof",
    ]
    reassurance_count = sum(1 for kw in reassurance_keywords if kw in text)
    score += min(reassurance_count * 1.0, 4.0)

    # Comparison handling
    comparison_keywords = ["compare", "better", "advantage", "alag", "special", "unique"]
    if any(kw in text for kw in comparison_keywords):
        score += 1.5

    return min(score, 10.0)


def _score_closing(
    partner_messages: List[str],
    conversation: List[Dict[str, Any]],
) -> float:
    """Score closing attempt quality."""
    if not partner_messages:
        return 0.0

    score = 2.0
    all_text = " ".join(partner_messages).lower()

    # Check for closing attempts
    close_keywords = [
        "apply", "sign up", "register", "start", "process",
        "shuru", "karna chahenge", "le lijiye", "try", "abhi",
        "download", "install", "open", "app pe",
    ]
    close_count = sum(1 for kw in close_keywords if kw in all_text)
    score += min(close_count * 1.0, 3.0)

    # Check if close was in the later part of conversation (not too early, not too late)
    if len(partner_messages) >= 3:
        last_messages = " ".join(partner_messages[-3:]).lower()
        if any(kw in last_messages for kw in close_keywords):
            score += 2.0

    # Call to action
    cta_keywords = ["gromo", "app", "link", "share", "send"]
    if any(kw in all_text for kw in cta_keywords):
        score += 1.5

    # Urgency or offer
    urgency_keywords = ["limited", "offer", "aaj", "abhi", "jaldi", "special"]
    if any(kw in all_text for kw in urgency_keywords):
        score += 1.0

    return min(score, 10.0)


def _score_empathy(text: str, messages: List[str]) -> float:
    """Score empathy and customer-centric approach."""
    score = 2.0

    empathy_keywords = [
        "samajh", "zaroor", "bilkul", "aapke liye", "aapki",
        "help", "madad", "tension mat", "don't worry", "achha",
        "sahi", "theek", "problem", "concern", "pareshaan",
        "dekhiye", "suniye",
    ]
    empathy_count = sum(1 for kw in empathy_keywords if kw in text)
    score += min(empathy_count * 0.8, 4.0)

    # Question asking (showing interest in customer needs)
    questions = sum(1 for m in messages if "?" in m)
    score += min(questions * 0.7, 2.0)

    # Acknowledging customer statements
    ack_keywords = ["haan", "ji", "sahi kaha", "achha point", "bilkul sahi"]
    if any(kw in text for kw in ack_keywords):
        score += 1.5

    return min(score, 10.0)


def _generate_feedback(
    skill_scores: Dict[str, float],
    num_turns: int,
    difficulty: str,
) -> tuple:
    """Generate textual feedback, strengths, and improvements."""
    strengths = []  # type: List[str]
    improvements = []  # type: List[str]

    # Product Knowledge
    pk = skill_scores["product_knowledge"]
    if pk >= 7:
        strengths.append("Strong product knowledge - you explained features and details well")
    elif pk >= 4:
        improvements.append("Try to mention more specific product features, eligibility criteria, and fees")
    else:
        improvements.append("Focus on learning product details - features, eligibility, and pricing are essential")

    # Communication
    comm = skill_scores["communication"]
    if comm >= 7:
        strengths.append("Excellent communication - clear, well-structured responses")
    elif comm >= 4:
        improvements.append("Keep your responses concise but informative - aim for 10-30 word messages")
    else:
        improvements.append("Work on message clarity and length - avoid very short or very long responses")

    # Objection Handling
    oh = skill_scores["objection_handling"]
    if oh >= 7:
        strengths.append("Good objection handling - you addressed customer concerns effectively")
    elif oh >= 4:
        improvements.append("When customer raises concerns, provide specific data and reassurance")
    else:
        improvements.append("Practice handling objections - acknowledge concerns and provide evidence-based responses")

    # Closing
    cs = skill_scores["closing_skills"]
    if cs >= 7:
        strengths.append("Strong closing skills - you guided the customer towards a decision")
    elif cs >= 4:
        improvements.append("Try to include a clear call-to-action towards the end of the conversation")
    else:
        improvements.append("Work on closing - always guide the customer to take the next step (apply, download app)")

    # Empathy
    emp = skill_scores["empathy"]
    if emp >= 7:
        strengths.append("Great empathy - you showed genuine interest in customer needs")
    elif emp >= 4:
        improvements.append("Show more empathy by asking questions about customer needs and acknowledging their concerns")
    else:
        improvements.append("Focus on customer-centric approach - ask about their needs, use polite language")

    # Overall feedback
    avg = sum(skill_scores.values()) / len(skill_scores)
    if avg >= 7:
        feedback = (
            f"Excellent performance! You handled this {difficulty} session very well "
            f"with strong skills across the board. Keep up the great work!"
        )
    elif avg >= 5:
        feedback = (
            f"Good effort in this {difficulty} session! You showed solid fundamentals "
            f"but there is room for improvement in some areas. Review the suggestions below."
        )
    elif avg >= 3:
        feedback = (
            f"Decent attempt at this {difficulty} session. Focus on the improvement areas "
            f"listed below and practice more to build confidence."
        )
    else:
        feedback = (
            f"This {difficulty} session needs improvement. Don't worry - practice makes perfect! "
            f"Focus on learning product details and building conversational skills."
        )

    if num_turns < 3:
        feedback += " Note: The session was quite short. Longer conversations help build better rapport."

    return feedback, strengths, improvements


# ---------------------------------------------------------------------------
# Sahayak Coaching Review
# ---------------------------------------------------------------------------


def generate_coaching_review(
    conversation: List[Dict],
    product_data: Dict,
    overall_score: Optional[float] = None,
    skill_scores: Optional[Dict] = None,
    feedback: Optional[str] = None,
) -> str:
    """Generate detailed coaching feedback using GPT-4o-mini.
    Analyzes the roleplay conversation and provides actionable tips in Hinglish."""

    if not settings.openai_api_key:
        return _fallback_coaching(overall_score, skill_scores, feedback)

    # Build conversation transcript
    transcript_lines = []
    for msg in conversation:
        role = "Partner" if msg["role"] == "partner" else "Customer"
        transcript_lines.append(f"{role}: {msg['text']}")
    transcript = "\n".join(transcript_lines)

    product_name = product_data.get("name", "the product")

    scores_text = ""
    if skill_scores:
        scores_text = "SCORES:\n"
        for skill, score in skill_scores.items():
            scores_text += f"- {skill}: {score}/10\n"
    if overall_score is not None:
        scores_text += f"- Overall: {overall_score}/10\n"

    prompt = f"""You are Sahayak, a coaching assistant for GroMo sales partners. Analyze this roleplay practice session and give coaching feedback.

RULES:
- Speak in natural Hinglish (Roman script) — like a supportive coach talking to a colleague
- Be specific — quote what the partner actually said (or didn't say) and suggest exact phrases they could use
- Keep it conversational, 5-8 sentences. No bullet points or lists.
- Focus on 2-3 actionable improvements, not everything at once
- Be encouraging — start with what they did well, then suggest improvements
- ALWAYS use FEMININE Hindi verb forms: "batati hoon", "kar sakti hoon" (you are female)
- End with a motivating line

PRODUCT: {product_name}
{scores_text}

CONVERSATION TRANSCRIPT:
{transcript}

Generate your coaching response as natural spoken Hinglish. No formatting, no markdown."""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are Sahayak, a female coaching assistant. Give coaching feedback in natural spoken Hinglish. No formatting, no lists."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Coaching review generation failed: {e}")
        return _fallback_coaching(overall_score, skill_scores, feedback)


def _fallback_coaching(
    overall_score: Optional[float],
    skill_scores: Optional[Dict],
    feedback: Optional[str],
) -> str:
    """Template coaching when LLM is unavailable."""
    score = overall_score or 5
    if score >= 7:
        return (
            "Bahut achha practice session raha! Aapne product ke benefits achhe se explain kiye. "
            "Ek tip deti hoon — customer ke objections ko aur naturally handle karne ki practice karein. "
            "Jaise customer bole 'yeh expensive hai' toh bolein 'Haan, lekin iske benefits dekhiye — long term mein aapko save hoga'. "
            "Keep it up, aap toh expert ban rahe hain!"
        )
    elif score >= 4:
        return (
            "Achha effort tha! Kuch cheezein achhi thi lekin improvement ki zaroorat hai. "
            "Product ke features toh aapne bataye, lekin customer ki concerns ko address karna important hai. "
            "Jab customer doubt kare, toh pehle uski baat sunein, phir reassure karein. "
            "Ek aur session practice karein — har baar better hoga!"
        )
    else:
        return (
            "Don't worry, practice se sab aata hai! Is session mein product details thode kam the. "
            "Pehle product ki 3-4 key benefits yaad kar lijiye — jaise cashback, free card, eligibility. "
            "Phir customer se naturally baat karein, jaise aap kisi friend ko explain kar rahe hain. "
            "Ek aur try karein — main yahin hoon help ke liye!"
        )

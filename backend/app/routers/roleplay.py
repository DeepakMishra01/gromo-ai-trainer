import uuid
import random
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.roleplay_session import RoleplaySession, Difficulty
from app.models.product import Product
from app.services.roleplay_engine import (
    create_customer_persona,
    generate_customer_response,
    evaluate_session,
)

router = APIRouter(prefix="/api/roleplay", tags=["roleplay"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class StartSessionRequest(BaseModel):
    product_id: str
    difficulty: str = "medium"


class StartSessionResponse(BaseModel):
    session_id: str
    persona: Dict[str, Any]
    first_message: str


class SendMessageRequest(BaseModel):
    session_id: str
    message: str


class SendMessageResponse(BaseModel):
    response: str
    sentiment: str
    buying_signal: float
    turn_number: int


class EndSessionRequest(BaseModel):
    session_id: str


class EndSessionResponse(BaseModel):
    overall_score: float
    skill_scores: Dict[str, float]
    feedback: str
    strengths: List[str]
    improvements: List[str]


class SessionHistoryItem(BaseModel):
    id: str
    product_id: str
    product_name: str
    difficulty: str
    overall_score: Optional[float]
    skill_scores: Optional[Dict[str, Any]]
    feedback: Optional[str]
    duration_seconds: Optional[int]
    created_at: str

    class Config:
        from_attributes = True


class RoleplaySessionOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    difficulty: Difficulty
    conversation_log: Optional[dict]
    overall_score: Optional[float]
    skill_scores: Optional[dict]
    feedback: Optional[str]
    duration_seconds: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/start", response_model=StartSessionResponse)
def start_session(data: StartSessionRequest, db: Session = Depends(get_db)):
    """Start a new roleplay session with a customer persona."""
    # Validate product
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Validate difficulty
    difficulty = data.difficulty.lower()
    if difficulty not in ("easy", "medium", "hard"):
        difficulty = "medium"

    # Create persona
    persona = create_customer_persona(difficulty)

    # Build product data dict using real GroMo fields
    product_data = {
        "name": product.name,
        "category": product.sub_type or "",
        "payout": product.payout or "",
        "benefits_text": product.benefits_text or "",
        "how_works_text": product.how_works_text or "",
        "terms_conditions_text": product.terms_conditions_text or "",
        # Legacy fields for backward compat
        "description": product.description,
        "features": product.features,
        "benefits": product.benefits,
    }

    # Generate first message (greeting from customer)
    from app.services.roleplay_engine import GREETING_TEMPLATES

    greetings = GREETING_TEMPLATES.get(difficulty, GREETING_TEMPLATES["medium"])
    first_message = random.choice(greetings).format(product=product.name)

    # Build initial conversation log
    conversation_log = {
        "persona": persona,
        "product_data": product_data,
        "messages": [
            {"role": "customer", "text": first_message},
        ],
    }

    # Create DB session
    session = RoleplaySession(
        product_id=product.id,
        difficulty=difficulty,
        conversation_log=conversation_log,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return StartSessionResponse(
        session_id=str(session.id),
        persona={
            "name": persona["name"],
            "personality": persona["personality"],
            "scenario_intro": f"{persona['name']}, {persona['age']} saal, {persona['occupation']}. {persona['personality']}.",
        },
        first_message=first_message,
    )


@router.post("/message", response_model=SendMessageResponse)
def send_message(data: SendMessageRequest, db: Session = Depends(get_db)):
    """Send a message in an active roleplay session."""
    session = (
        db.query(RoleplaySession)
        .filter(RoleplaySession.id == data.session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    conversation_log = session.conversation_log or {}
    messages = conversation_log.get("messages", [])
    persona = conversation_log.get("persona", {})
    product_data = conversation_log.get("product_data", {})
    difficulty = session.difficulty

    # Add partner message
    messages.append({"role": "partner", "text": data.message})

    # Generate customer response
    result = generate_customer_response(
        persona=persona,
        product_data=product_data,
        conversation=messages,
        partner_message=data.message,
        difficulty=difficulty,
    )

    # Add customer response to messages
    messages.append({"role": "customer", "text": result["response"]})

    # Update conversation log
    conversation_log["messages"] = messages
    session.conversation_log = conversation_log

    # Force SQLAlchemy to detect the change on JSON column
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(session, "conversation_log")

    db.commit()

    # Count partner turns
    turn_number = len([m for m in messages if m["role"] == "partner"])

    return SendMessageResponse(
        response=result["response"],
        sentiment=result["sentiment"],
        buying_signal=result["buying_signal"],
        turn_number=turn_number,
    )


@router.post("/end", response_model=EndSessionResponse)
def end_session(data: EndSessionRequest, db: Session = Depends(get_db)):
    """End a roleplay session and get evaluation."""
    session = (
        db.query(RoleplaySession)
        .filter(RoleplaySession.id == data.session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    conversation_log = session.conversation_log or {}
    messages = conversation_log.get("messages", [])
    product_data = conversation_log.get("product_data", {})
    difficulty = session.difficulty

    # Evaluate the session
    evaluation = evaluate_session(
        conversation=messages,
        product_data=product_data,
        difficulty=difficulty,
    )

    # Calculate duration
    duration = int((datetime.utcnow() - session.created_at).total_seconds())

    # Update session record
    session.overall_score = evaluation["overall_score"]
    session.skill_scores = evaluation["skill_scores"]
    session.feedback = evaluation["feedback"]
    session.duration_seconds = duration

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(session, "skill_scores")

    db.commit()

    return EndSessionResponse(
        overall_score=evaluation["overall_score"],
        skill_scores=evaluation["skill_scores"],
        feedback=evaluation["feedback"],
        strengths=evaluation["strengths"],
        improvements=evaluation["improvements"],
    )


@router.get("/history", response_model=List[SessionHistoryItem])
def get_history(db: Session = Depends(get_db)):
    """Get past roleplay sessions with scores and product names."""
    sessions = (
        db.query(RoleplaySession)
        .order_by(RoleplaySession.created_at.desc())
        .limit(20)
        .all()
    )

    result = []
    for s in sessions:
        # Look up product name
        product = db.query(Product).filter(Product.id == s.product_id).first()
        product_name = product.name if product else "Unknown Product"

        result.append(
            SessionHistoryItem(
                id=str(s.id),
                product_id=str(s.product_id),
                product_name=product_name,
                difficulty=s.difficulty,
                overall_score=s.overall_score,
                skill_scores=s.skill_scores,
                feedback=s.feedback,
                duration_seconds=s.duration_seconds,
                created_at=s.created_at.isoformat() if s.created_at else "",
            )
        )

    return result


# ---------------------------------------------------------------------------
# Keep legacy CRUD endpoints for backwards compatibility
# ---------------------------------------------------------------------------


@router.get("", response_model=List[RoleplaySessionOut])
def list_sessions(db: Session = Depends(get_db)):
    return (
        db.query(RoleplaySession)
        .order_by(RoleplaySession.created_at.desc())
        .limit(50)
        .all()
    )


@router.get("/{session_id}", response_model=RoleplaySessionOut)
def get_session(session_id: uuid.UUID, db: Session = Depends(get_db)):
    session = db.query(RoleplaySession).filter(RoleplaySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}")
def delete_session(session_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a single roleplay session."""
    session = db.query(RoleplaySession).filter(RoleplaySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"detail": "Roleplay session deleted successfully"}


# ---------------------------------------------------------------------------
# Sahayak Integration Endpoints
# ---------------------------------------------------------------------------


class SahayakHelpRequest(BaseModel):
    product_id: str
    question: str
    session_id: Optional[str] = None


class CoachingRequest(BaseModel):
    session_id: str


@router.post("/sahayak-help")
def sahayak_help(data: SahayakHelpRequest, db: Session = Depends(get_db)):
    """Get quick product help from Sahayak during roleplay (doesn't affect roleplay conversation)."""
    from app.services import agent_service

    result = agent_service.chat(
        message=data.question,
        db=db,
        session_id=data.session_id,
    )

    return {
        "response": result["response"],
        "session_id": result["session_id"],
        "products_mentioned": result["products_mentioned"],
    }


@router.post("/coaching")
def get_coaching(data: CoachingRequest, db: Session = Depends(get_db)):
    """Get Sahayak coaching feedback after a completed roleplay session."""
    session = (
        db.query(RoleplaySession)
        .filter(RoleplaySession.id == data.session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    from app.services.roleplay_engine import generate_coaching_review

    conversation_log = session.conversation_log or {}
    messages = conversation_log.get("messages", [])
    product_data = conversation_log.get("product_data", {})

    coaching = generate_coaching_review(
        conversation=messages,
        product_data=product_data,
        overall_score=session.overall_score,
        skill_scores=session.skill_scores,
        feedback=session.feedback,
    )

    return {"coaching": coaching}


@router.delete("")
def delete_all_sessions(db: Session = Depends(get_db)):
    """Delete all roleplay sessions."""
    count = db.query(RoleplaySession).delete()
    db.commit()
    return {"detail": f"Deleted {count} roleplay sessions"}

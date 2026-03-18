import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
import json

from app.database import get_db
from app.models.product import Product
from app.models.category import Category
from app.services.knowledge_builder import get_knowledge_for_product
from app.services.doubt_resolver import resolve_doubt
from app.services.training_session import create_training_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/training", tags=["training"])


# ---- Pydantic Models ----

class TrainingProductOut(BaseModel):
    id: uuid.UUID
    name: str
    category_name: str = ""
    sub_type: Optional[str] = None
    payout: Optional[str] = None
    description: Optional[str] = None
    has_benefits: bool = False
    has_process: bool = False
    has_terms: bool = False

    class Config:
        from_attributes = True


class SessionCreateRequest(BaseModel):
    product_id: str


class AskDoubtRequest(BaseModel):
    product_id: str
    question: str


class AskDoubtResponse(BaseModel):
    answer: str
    source: str


class QuizCheckRequest(BaseModel):
    question_index: int
    selected_answer: int
    correct_answer: int


class QuizCheckResponse(BaseModel):
    correct: bool
    explanation: str


# ---- WebSocket (kept for future real-time use) ----

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_json(self, websocket: WebSocket, data: dict):
        await websocket.send_json(data)


manager = ConnectionManager()


@router.websocket("/ws")
async def training_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await manager.send_json(websocket, {
                "type": "ack",
                "message": "WebSocket connected. Use REST endpoints for training sessions.",
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ---- REST Endpoints ----

@router.get("/products", response_model=List[TrainingProductOut])
def list_training_products(db: Session = Depends(get_db)):
    """List products available for training, formatted with training-relevant metadata."""
    products = (
        db.query(Product)
        .join(Category)
        .filter(Category.is_excluded == False)  # noqa: E712
        .options(joinedload(Product.category))
        .order_by(Product.name)
        .all()
    )

    result = []
    for p in products:
        out = TrainingProductOut(
            id=p.id,
            name=p.name,
            category_name=p.category.name if p.category else "",
            sub_type=p.sub_type,
            payout=p.payout,
            description=p.description,
            has_benefits=bool(p.benefits_text),
            has_process=bool(p.how_works_text),
            has_terms=bool(p.terms_conditions_text),
        )
        result.append(out)

    return result


@router.post("/session")
def create_session(request: SessionCreateRequest, db: Session = Depends(get_db)):
    """Create a new training session for a product with sections, content, and quiz."""
    try:
        session_data = create_training_session(request.product_id, db)
        return session_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create training session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create training session")


@router.post("/ask", response_model=AskDoubtResponse)
def ask_doubt(request: AskDoubtRequest, db: Session = Depends(get_db)):
    """Ask a doubt during training. Uses knowledge base and doubt resolver to answer."""
    # Get knowledge base for the product
    knowledge = get_knowledge_for_product(request.product_id, db)
    if not knowledge:
        raise HTTPException(status_code=404, detail="Product not found or knowledge base unavailable")

    try:
        answer = resolve_doubt(
            question=request.question,
            product_knowledge=knowledge,
            language="hinglish",
        )
        return AskDoubtResponse(answer=answer, source="knowledge_base")
    except Exception as e:
        logger.error(f"Doubt resolution failed: {e}")
        return AskDoubtResponse(
            answer=(
                "Maaf kijiye, is waqt aapke sawaal ka jawab dene mein problem aa rahi hai. "
                "Kripya thodi der baad dobara try karein."
            ),
            source="fallback",
        )


@router.post("/quiz/check", response_model=QuizCheckResponse)
def check_quiz_answer(request: QuizCheckRequest):
    """Check a quiz answer and return whether it's correct with explanation."""
    is_correct = request.selected_answer == request.correct_answer

    if is_correct:
        explanation = "Bahut badhiya! Aapka jawab bilkul sahi hai. Keep it up!"
    else:
        explanation = (
            "Yeh jawab sahi nahi hai. Koi baat nahi, galtiyon se seekhte hain! "
            "Training section dobara padh kar try karein."
        )

    return QuizCheckResponse(correct=is_correct, explanation=explanation)

"""
Sahayak Agent Router.
Endpoints for the Sahayak virtual training agent — chat, TTS, sessions.
"""
import uuid
import base64
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.agent_session import AgentSession
from app.services import agent_service
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])


# ── Schemas ──

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class ProductMention(BaseModel):
    id: str
    name: str
    category_name: str


class ChatResponse(BaseModel):
    response: str
    session_id: str
    products_mentioned: List[ProductMention]
    title: str


class TTSRequest(BaseModel):
    text: str


class SessionListItem(BaseModel):
    id: str
    title: Optional[str]
    created_at: str
    updated_at: str
    message_count: int


class SessionDetail(BaseModel):
    id: str
    title: Optional[str]
    conversation_log: dict
    product_ids: list
    created_at: str
    updated_at: str


# ── Chat ──

@router.post("/chat", response_model=ChatResponse)
def agent_chat(req: ChatRequest, db: Session = Depends(get_db)):
    """Send a message to Sahayak and get a response."""
    if not req.message.strip():
        raise HTTPException(400, "Message cannot be empty")

    result = agent_service.chat(
        message=req.message.strip(),
        db=db,
        session_id=req.session_id,
    )

    return ChatResponse(
        response=result["response"],
        session_id=result["session_id"],
        products_mentioned=[
            ProductMention(**p) for p in result["products_mentioned"]
        ],
        title=result["title"] or "",
    )


# ── TTS (Text-to-Speech for voice output) ──

@router.post("/tts")
def agent_tts(req: TTSRequest):
    """Convert Sahayak's response text to speech audio via Sarvam TTS.
    Handles full-length responses by chunking and concatenating audio."""
    import httpx
    import re
    import os
    import tempfile

    if not settings.sarvam_api_key:
        raise HTTPException(503, "Sarvam TTS not configured")

    text = req.text.strip()
    if not text:
        raise HTTPException(400, "Text cannot be empty")

    # Light cleaning for conversational TTS — no aggressive phonetic swaps
    cleaned = _clean_for_agent_tts(text)
    if not cleaned:
        raise HTTPException(400, "Text empty after cleaning")

    # Split into chunks (Sarvam v2 max 480 chars per request)
    chunks = _split_for_tts(cleaned, max_chars=480)

    try:
        all_audio_parts = []
        for chunk in chunks:
            response = httpx.post(
                "https://api.sarvam.ai/text-to-speech",
                headers={
                    "api-subscription-key": settings.sarvam_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "inputs": [chunk],
                    "target_language_code": "hi-IN",
                    "speaker": "manisha",
                    "model": "bulbul:v2",
                    "pace": 1.05,
                    "enable_preprocessing": True,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            audios = data.get("audios", [])
            if audios:
                all_audio_parts.append(base64.b64decode(audios[0]))

        if not all_audio_parts:
            raise HTTPException(500, "No audio returned from TTS")

        # Single chunk — return directly
        if len(all_audio_parts) == 1:
            return Response(content=all_audio_parts[0], media_type="audio/wav")

        # Multiple chunks — properly concatenate using moviepy
        from moviepy import AudioFileClip, concatenate_audioclips

        tmp_files = []
        clips = []
        try:
            for i, audio_bytes in enumerate(all_audio_parts):
                tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                tmp.write(audio_bytes)
                tmp.close()
                tmp_files.append(tmp.name)
                clips.append(AudioFileClip(tmp.name))

            combined = concatenate_audioclips(clips)
            out_path = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
            combined.write_audiofile(out_path, logger=None)
            combined.close()

            with open(out_path, "rb") as f:
                result_bytes = f.read()
            os.unlink(out_path)

            return Response(content=result_bytes, media_type="audio/mpeg")
        finally:
            for c in clips:
                try:
                    c.close()
                except Exception:
                    pass
            for f in tmp_files:
                try:
                    os.unlink(f)
                except Exception:
                    pass

    except httpx.HTTPStatusError as e:
        logger.error(f"Sarvam TTS error: {e.response.status_code} - {e.response.text[:200]}")
        raise HTTPException(503, "TTS service error")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        raise HTTPException(500, "TTS generation failed")


def _clean_for_agent_tts(text: str) -> str:
    """Light cleaning for conversational TTS — preserves natural pronunciation.
    Sarvam handles common English/Hinglish words correctly with preprocessing enabled.
    Only fix things that truly break TTS."""
    import re

    # Remove markdown formatting
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'[#*_]{1,3}', '', text)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\(.*?\)', '', text)  # Remove parenthetical notes

    # Remove emojis and non-ASCII (except Devanagari which Sarvam handles)
    text = re.sub(
        r'['
        r'\U0001F600-\U0001F64F'
        r'\U0001F300-\U0001F5FF'
        r'\U0001F680-\U0001F6FF'
        r'\U0001F1E0-\U0001F1FF'
        r'\U00002702-\U000027B0'
        r'\U0001F900-\U0001F9FF'
        r'\U00002600-\U000026FF'
        r']+', ' ', text)

    # Remove bullet point markers
    text = re.sub(r'^[-•→►▸]\s*', '', text, flags=re.MULTILINE)

    # Fix numbered lists for speech
    text = re.sub(r'(\d+)\.\s+', r'\1, ', text)

    # Currency and symbols
    text = text.replace('₹', 'rupees ')
    text = text.replace('Rs.', 'rupees ')
    text = text.replace('Rs ', 'rupees ')
    text = text.replace('%', ' percent')
    text = text.replace('&', ' and ')
    text = text.replace('/', ' or ')
    text = text.replace('+', ' plus ')

    # Number formatting
    text = re.sub(r'(\d+),00,00,000', lambda m: f"{m.group(1)} crore", text)
    text = re.sub(r'(\d+),00,000', lambda m: f"{m.group(1)} lakh", text)
    text = re.sub(r'(\d+),000', lambda m: f"{m.group(1)} hazaar", text)
    text = re.sub(r'(\d),(\d)', r'\1\2', text)

    # Only expand abbreviations that Sarvam truly can't handle
    abbrevs = {
        'KYC': 'ke wai see',
        'eKYC': 'ee ke wai see',
        'OTP': 'oh tee pee',
        'EMI': 'ee em ai',
        'UPI': 'you pee ai',
        'PAN': 'paan',
        'CIBIL': 'sibil',
        'HDFC': 'aich dee ef see',
        'ICICI': 'ai see ai see ai',
        'SBI': 'es bee ai',
        'ATM': 'ay tee em',
        'NRI': 'en aar ai',
        'FD': 'ef dee',
        'NBFC': 'en bee ef see',
        'GST': 'jee es tee',
    }
    for a, e in abbrevs.items():
        text = re.sub(r'\b' + re.escape(a) + r'\b', e, text)

    # Brand names
    text = text.replace('GroMo', 'Gromo')
    text = text.replace('GROMO', 'Gromo')
    text = re.sub(r'\bAU\b', 'ay you', text)

    # Remove hyphens (Sarvam loops on them)
    text = text.replace('-', ' ')

    # Remove exclamation mark clusters (cause weird TTS emphasis)
    text = re.sub(r'!{2,}', '!', text)
    text = re.sub(r'\?{2,}', '?', text)

    # Clean whitespace
    text = re.sub(r'\n+', '. ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\s+([.,!?])', r'\1', text)
    text = re.sub(r'([.,!?])\1+', r'\1', text)

    return text.strip()


def _split_for_tts(text: str, max_chars: int = 480) -> list:
    """Split text into chunks at sentence boundaries for Sarvam API."""
    import re

    if len(text) <= max_chars:
        return [text]

    chunks = []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}".strip() if current else sentence
        else:
            if current:
                chunks.append(current)
            current = sentence[:max_chars]

    if current:
        chunks.append(current)

    return chunks or [text[:max_chars]]


# ── Sessions ──

@router.get("/sessions")
def list_sessions(limit: int = 20, db: Session = Depends(get_db)):
    """List past agent sessions."""
    sessions = (
        db.query(AgentSession)
        .order_by(AgentSession.updated_at.desc())
        .limit(limit)
        .all()
    )

    result = []
    for s in sessions:
        messages = s.conversation_log.get("messages", []) if s.conversation_log else []
        result.append(SessionListItem(
            id=str(s.id),
            title=s.title,
            created_at=s.created_at.isoformat() if s.created_at else "",
            updated_at=s.updated_at.isoformat() if s.updated_at else "",
            message_count=len(messages),
        ))
    return result


@router.get("/sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    """Get full session with conversation history."""
    session = db.query(AgentSession).filter(
        AgentSession.id == uuid.UUID(session_id)
    ).first()
    if not session:
        raise HTTPException(404, "Session not found")

    return SessionDetail(
        id=str(session.id),
        title=session.title,
        conversation_log=session.conversation_log or {"messages": []},
        product_ids=session.product_ids or [],
        created_at=session.created_at.isoformat() if session.created_at else "",
        updated_at=session.updated_at.isoformat() if session.updated_at else "",
    )


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete a single agent session."""
    session = db.query(AgentSession).filter(
        AgentSession.id == uuid.UUID(session_id)
    ).first()
    if not session:
        raise HTTPException(404, "Session not found")

    db.delete(session)
    db.commit()
    return {"detail": "deleted"}


@router.delete("/sessions")
def delete_all_sessions(db: Session = Depends(get_db)):
    """Delete all agent sessions."""
    count = db.query(AgentSession).delete()
    db.commit()
    return {"detail": f"Deleted {count} sessions"}


# ── Suggestions ──

@router.get("/suggestions")
def get_suggestions():
    """Get suggested starter questions for Sahayak."""
    return {"suggestions": agent_service.get_suggestions()}

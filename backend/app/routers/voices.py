import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models.voice import Voice

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voices", tags=["voices"])


class VoiceOut(BaseModel):
    id: uuid.UUID
    name: str
    sample_path: Optional[str]
    language: str
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


class VoiceCreate(BaseModel):
    name: str
    language: str = "hinglish"


@router.get("", response_model=List[VoiceOut])
def list_voices(db: Session = Depends(get_db)):
    return db.query(Voice).order_by(Voice.is_default.desc(), Voice.name).all()


@router.get("/{voice_id}", response_model=VoiceOut)
def get_voice(voice_id: uuid.UUID, db: Session = Depends(get_db)):
    voice = db.query(Voice).filter(Voice.id == voice_id).first()
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    return voice


@router.post("", response_model=VoiceOut)
def create_voice(data: VoiceCreate, db: Session = Depends(get_db)):
    """Create a new voice with name and language."""
    voice = Voice(
        name=data.name,
        language=data.language,
        is_default=False,
    )
    db.add(voice)
    db.commit()
    db.refresh(voice)
    logger.info(f"Created voice: {voice.name} (id={voice.id}, language={voice.language})")
    return voice


@router.post("/{voice_id}/set-default")
def set_default_voice(voice_id: uuid.UUID, db: Session = Depends(get_db)):
    voice = db.query(Voice).filter(Voice.id == voice_id).first()
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    db.query(Voice).update({Voice.is_default: False})
    voice.is_default = True
    db.commit()
    return {"status": "ok"}


@router.delete("/{voice_id}")
def delete_voice(voice_id: uuid.UUID, db: Session = Depends(get_db)):
    voice = db.query(Voice).filter(Voice.id == voice_id).first()
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")
    if voice.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete default voice")
    db.delete(voice)
    db.commit()
    return {"status": "deleted"}

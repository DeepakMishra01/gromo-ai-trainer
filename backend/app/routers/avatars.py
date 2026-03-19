import uuid
import os
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.avatar import Avatar
from app.auth import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/avatars", tags=["avatars"], dependencies=[Depends(require_admin)])

# Storage path for avatar images
AVATAR_STORAGE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "storage", "avatars",
)


class AvatarOut(BaseModel):
    id: uuid.UUID
    name: str
    image_path: Optional[str]
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AvatarCreate(BaseModel):
    name: str


@router.get("", response_model=List[AvatarOut])
def list_avatars(db: Session = Depends(get_db)):
    return db.query(Avatar).order_by(Avatar.is_default.desc(), Avatar.name).all()


@router.get("/{avatar_id}", response_model=AvatarOut)
def get_avatar(avatar_id: uuid.UUID, db: Session = Depends(get_db)):
    avatar = db.query(Avatar).filter(Avatar.id == avatar_id).first()
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return avatar


@router.post("", response_model=AvatarOut)
def create_avatar(data: AvatarCreate, db: Session = Depends(get_db)):
    """Create a new avatar with just a name."""
    avatar = Avatar(
        name=data.name,
        is_default=False,
    )
    db.add(avatar)
    db.commit()
    db.refresh(avatar)
    logger.info(f"Created avatar: {avatar.name} (id={avatar.id})")
    return avatar


@router.post("/upload", response_model=AvatarOut)
async def upload_avatar_image(
    name: str = "Custom Avatar",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Create a new avatar with an uploaded image."""
    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed: {', '.join(allowed_types)}",
        )

    # Ensure storage directory exists
    os.makedirs(AVATAR_STORAGE, exist_ok=True)

    # Generate unique filename
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "png"
    file_id = uuid.uuid4()
    filename = f"{file_id}.{ext}"
    file_path = os.path.join(AVATAR_STORAGE, filename)

    # Save file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Store relative path for serving via /storage/
    relative_path = f"/storage/avatars/{filename}"

    avatar = Avatar(
        name=name,
        image_path=relative_path,
        is_default=False,
    )
    db.add(avatar)
    db.commit()
    db.refresh(avatar)

    logger.info(f"Created avatar with image: {avatar.name} (id={avatar.id})")
    return avatar


@router.post("/{avatar_id}/set-default")
def set_default_avatar(avatar_id: uuid.UUID, db: Session = Depends(get_db)):
    avatar = db.query(Avatar).filter(Avatar.id == avatar_id).first()
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    db.query(Avatar).update({Avatar.is_default: False})
    avatar.is_default = True
    db.commit()
    return {"status": "ok"}


@router.delete("/{avatar_id}")
def delete_avatar(avatar_id: uuid.UUID, db: Session = Depends(get_db)):
    avatar = db.query(Avatar).filter(Avatar.id == avatar_id).first()
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
    if avatar.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete default avatar")
    db.delete(avatar)
    db.commit()
    return {"status": "deleted"}

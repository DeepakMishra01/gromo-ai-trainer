"""
Seed data service.
Creates default avatars and voices if tables are empty.
"""
import logging

from sqlalchemy.orm import Session

from app.models.avatar import Avatar
from app.models.voice import Voice

logger = logging.getLogger(__name__)


def seed_avatars_and_voices(db: Session) -> None:
    """Create default avatars and voices if tables are empty."""
    _seed_avatars(db)
    _seed_voices(db)


def _seed_avatars(db: Session) -> None:
    """Seed default avatars if none exist."""
    count = db.query(Avatar).count()
    if count > 0:
        logger.info(f"Avatars table already has {count} entries, skipping seed")
        return

    default_avatars = [
        {"name": "Priya", "is_default": True},
        {"name": "Rahul", "is_default": False},
        {"name": "Ananya", "is_default": False},
        {"name": "Vikram", "is_default": False},
    ]

    for avatar_data in default_avatars:
        avatar = Avatar(
            name=avatar_data["name"],
            is_default=avatar_data["is_default"],
        )
        db.add(avatar)

    db.commit()
    logger.info(f"Seeded {len(default_avatars)} default avatars")


def _seed_voices(db: Session) -> None:
    """Seed default voices if none exist."""
    count = db.query(Voice).count()
    if count > 0:
        logger.info(f"Voices table already has {count} entries, skipping seed")
        return

    default_voices = [
        {"name": "Neerja (Hindi Female)", "language": "hindi", "is_default": True},
        {"name": "Ravi (Hindi Male)", "language": "hindi", "is_default": False},
        {"name": "Aditi (Hinglish Female)", "language": "hinglish", "is_default": False},
        {"name": "Kabir (Hinglish Male)", "language": "hinglish", "is_default": False},
    ]

    for voice_data in default_voices:
        voice = Voice(
            name=voice_data["name"],
            language=voice_data["language"],
            is_default=voice_data["is_default"],
        )
        db.add(voice)

    db.commit()
    logger.info(f"Seeded {len(default_voices)} default voices")

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class AppSettings(BaseModel):
    gromo_api_base_url: str
    gromo_api_client_id_set: bool
    gromo_api_secret_key_set: bool
    gromo_api_gpuid: str
    excluded_categories: str
    llm_provider: str
    ollama_base_url: str
    ollama_model: str
    openai_api_key_set: bool
    tts_provider: str
    sarvam_api_key_set: bool
    elevenlabs_api_key_set: bool
    avatar_provider: str
    heygen_api_key_set: bool
    gamma_api_key_set: bool
    default_language: str
    default_resolution: str
    default_video_speed: float
    storage_backend: str


@router.get("", response_model=AppSettings)
def get_settings():
    return AppSettings(
        gromo_api_base_url=settings.gromo_api_base_url,
        gromo_api_client_id_set=bool(settings.gromo_api_client_id),
        gromo_api_secret_key_set=bool(settings.gromo_api_secret_key),
        gromo_api_gpuid=settings.gromo_api_gpuid,
        excluded_categories=settings.excluded_categories,
        llm_provider=settings.llm_provider,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
        openai_api_key_set=bool(settings.openai_api_key),
        tts_provider=settings.tts_provider,
        sarvam_api_key_set=bool(settings.sarvam_api_key),
        elevenlabs_api_key_set=bool(settings.elevenlabs_api_key),
        avatar_provider=settings.avatar_provider,
        heygen_api_key_set=bool(settings.heygen_api_key),
        gamma_api_key_set=bool(settings.gamma_api_key),
        default_language=settings.default_language,
        default_resolution=settings.default_resolution,
        default_video_speed=settings.default_video_speed,
        storage_backend=settings.storage_backend,
    )

import os
from pydantic_settings import BaseSettings
from typing import Optional, List

# Resolve .env path relative to the backend directory (where config.py lives)
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_FILE = os.path.join(_BACKEND_DIR, ".env")


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://gromo:gromo@db:5432/gromo_ai_trainer"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # GroMo API
    gromo_api_base_url: str = "https://api.gromo.in"
    gromo_api_client_id: str = ""
    gromo_api_secret_key: str = ""
    gromo_api_gpuid: str = "ULTI9999"

    # Excluded Categories
    excluded_categories: str = "insurance,bima"

    # AI Models
    llm_provider: str = "openai"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3"
    openai_api_key: Optional[str] = None

    tts_provider: str = "sarvam"
    sarvam_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None

    avatar_provider: str = "openai_dalle"
    heygen_api_key: Optional[str] = None

    # Gamma AI (presentation generation)
    gamma_api_key: Optional[str] = None

    # Auth / JWT
    jwt_secret: str = "change-me-in-production-use-a-random-64-char-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours
    admin_email: Optional[str] = None
    admin_password: str = "admin123"
    google_client_id: str = ""
    firebase_project_id: str = ""
    firebase_api_key: str = ""

    # Defaults
    default_language: str = "hinglish"
    default_resolution: str = "1080p"
    default_video_speed: float = 1.0

    # Storage
    storage_backend: str = "local"
    s3_endpoint: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None

    @property
    def excluded_categories_list(self) -> List[str]:
        return [c.strip().lower() for c in self.excluded_categories.split(",") if c.strip()]

    class Config:
        env_file = _ENV_FILE
        env_file_encoding = "utf-8"


settings = Settings()

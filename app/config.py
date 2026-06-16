from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "SpareTrack API"
    APP_ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/sparetrack_db"

    SECRET_KEY: str = "change-this-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    UPLOAD_DIR: str = "uploads"
    ORIGINAL_FILE_DIR: str = "uploads/original"
    PROCESSED_FILE_DIR: str = "uploads/processed"
    MAX_UPLOAD_SIZE_MB: int = 25

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    LOOKUP_PROVIDER: str = "web_claude"
    DEFAULT_CURRENCY: str = "USD"

    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-haiku-4-5-20251001"
    ANTHROPIC_MAX_TOKENS: int = 4000

    TAVILY_API_KEY: str | None = None
    TAVILY_SEARCH_DEPTH: str = "basic"
    TAVILY_MAX_RESULTS: int = 5

    SERPAPI_API_KEY: str | None = None
    USE_SERPAPI_FALLBACK: bool = False

    LOOKUP_TIMEOUT_SECONDS: int = 45
    LOOKUP_MIN_CONFIDENCE: float = 0.50
    LOOKUP_BATCH_SIZE: int = 3

    LOOKUP_MAX_SEARCH_QUERIES_PER_PART: int = 1

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    def create_upload_directories(self) -> None:
        Path(self.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.ORIGINAL_FILE_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.PROCESSED_FILE_DIR).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.create_upload_directories()
    return settings


settings = get_settings()
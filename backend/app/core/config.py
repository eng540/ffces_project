# ============================================
# FFCES - إعدادات النظام (System Configuration)
# ============================================
import json
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    إعدادات النظام الرئيسية
    Loaded from environment variables and .env file
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    # ---- Database ----
    DATABASE_URL: str = "postgresql+asyncpg://ffces_user:ffces_pass@localhost:5432/ffces_db"

    # ---- Redis ----
    REDIS_URL: str = "redis://localhost:6379/0"

    # ---- JWT ----
    SECRET_KEY: str = "development-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---- CORS ----
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:5173"]'

    @property
    def cors_origins_list(self) -> List[str]:
        try:
            return json.loads(self.CORS_ORIGINS)
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:3000"]

    # ---- MinIO ----
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "ffces-documents"
    MINIO_SECURE: bool = False

    # ---- Application ----
    DEBUG: bool = True

    # ---- Approval Thresholds (SAR) ----
    APPROVAL_LEVEL1_THRESHOLD: float = 10000.0
    APPROVAL_LEVEL2_THRESHOLD: float = 50000.0
    APPROVAL_LEVEL3_THRESHOLD: float = 100000.0


# Singleton instance
settings = Settings()

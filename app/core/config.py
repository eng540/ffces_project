# ============================================================
# Configuration Settings
# ============================================================

from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/ffces"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # File Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "ffces-attachments"

    # Application
    APP_NAME: str = "FFCES"
    DEBUG: bool = True

    # Approval Thresholds
    EXPENSE_APPROVAL_THRESHOLD: float = 1000.0
    CUSTODY_APPROVAL_THRESHOLD: float = 2000.0
    PAYMENT_APPROVAL_THRESHOLD: float = 1000.0

    class Config:
        env_file = ".env"

settings = Settings()

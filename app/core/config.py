from pydantic_settings import BaseSettings
from typing import List, Optional
import secrets


class Settings(BaseSettings):
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "Collaborative Event Management System"
    CORS_ORIGINS: List[str] = ["*"]
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    DATABASE_URL: str = "sqlite:///./app.db"
    REDIS_URL: Optional[str] = None
    RATE_LIMIT_PER_MINUTE: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

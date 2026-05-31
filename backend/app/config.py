from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:Tzj5Eep2Too9@192.168.0.11:5432/wealth"
    SECRET_KEY: str = "wealth-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
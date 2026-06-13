from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./mebtty.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "mebtty-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    STATIC_DIR: str = ""  # Empty = auto-detect
    REGISTRATION_ENABLED: bool = True

    class Config:
        env_prefix = "MEBTTY_"


settings = Settings()

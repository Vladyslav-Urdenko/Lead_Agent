import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Lead Master"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: str = "6379"

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Database
    # Using explicit valid default to avoid crash on import if .env missing,
    # but it will fail connection if not set to real DB.
    # Better to allow it to be empty string and let Pydantic/SQLAlchemy validation handle it?
    # No, SQLAlchemy 'create_engine' crashed on empty string.
    # Let's trust .env loading.
    DATABASE_URL: str

    # Serper API (Google Maps)
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra="ignore")

    @property
    def CELERY_BROKER_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

settings = Settings()

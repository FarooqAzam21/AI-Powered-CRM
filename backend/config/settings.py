import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    app_name = os.getenv("APP_NAME", "AI Email Automation CRM")
    environment = os.getenv("ENVIRONMENT", "development")
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    cors_origins = [item.strip() for item in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]

    database_url = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    celery_broker_url = os.getenv("CELERY_BROKER_URL", redis_url)
    celery_result_backend = os.getenv("CELERY_RESULT_BACKEND", redis_url)

    jwt_secret_key = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", "dev-only-change-me"))
    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    token_encryption_key = os.getenv("TOKEN_ENCRYPTION_KEY", "")

    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/google/callback")

    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "tinyllama")
    ollama_context = int(os.getenv("OLLAMA_CONTEXT", "1024"))
    ollama_idle_unload_seconds = int(os.getenv("OLLAMA_IDLE_UNLOAD_SECONDS", "180"))
    ai_cache_ttl_seconds = int(os.getenv("AI_CACHE_TTL_SECONDS", "86400"))

    gmail_page_size = int(os.getenv("GMAIL_PAGE_SIZE", "10"))
    gmail_sync_window_days = int(os.getenv("GMAIL_SYNC_WINDOW_DAYS", "14"))
    campaign_send_rate_per_minute = int(os.getenv("CAMPAIGN_SEND_RATE_PER_MINUTE", "2"))

    log_level = os.getenv("LOG_LEVEL", "INFO")

    def validate_for_production(self):
        if self.environment == "production":
            missing = []
            if self.jwt_secret_key == "dev-only-change-me":
                missing.append("JWT_SECRET_KEY")
            if not self.token_encryption_key:
                missing.append("TOKEN_ENCRYPTION_KEY")
            if missing:
                raise RuntimeError(f"Missing production configuration: {', '.join(missing)}")


@lru_cache
def get_settings():
    Path("data").mkdir(exist_ok=True)
    settings = Settings()
    settings.validate_for_production()
    return settings

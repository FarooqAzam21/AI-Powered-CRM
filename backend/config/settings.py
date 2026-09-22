import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    app_name: str = os.getenv("APP_NAME", "AI Email Automation CRM")
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes") if os.getenv("ENVIRONMENT") == "production" else os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")
    
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    cors_origins: list = [item.strip() for item in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if item.strip()]
    allowed_hosts: list = [item.strip() for item in os.getenv("ALLOWED_HOSTS", "*").split(",") if item.strip()]

    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")
    db_pool_size: int = int(os.getenv("DB_POOL_SIZE", "10"))
    db_max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    db_pool_timeout: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    db_pool_recycle: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    slow_query_threshold_ms: int = int(os.getenv("SLOW_QUERY_THRESHOLD_MS", "500"))

    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", redis_url)
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", redis_url)

    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", "dev-only-change-me"))
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    token_encryption_key: str = os.getenv("TOKEN_ENCRYPTION_KEY", "")
    jwt_access_token_expire_minutes: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    jwt_refresh_token_expire_days: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "true" if os.getenv("ENVIRONMENT") == "production" else "false").lower() in ("true", "1", "yes")
    cookie_samesite: str = os.getenv("COOKIE_SAMESITE", "lax")

    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/google/callback")

    ai_provider: str = os.getenv("AI_PROVIDER", "ollama")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
    ollama_context: int = int(os.getenv("OLLAMA_CONTEXT", "1024"))
    ollama_idle_unload_seconds: int = int(os.getenv("OLLAMA_IDLE_UNLOAD_SECONDS", "180"))
    ai_cache_ttl_seconds: int = int(os.getenv("AI_CACHE_TTL_SECONDS", "86400"))

    gmail_page_size: int = int(os.getenv("GMAIL_PAGE_SIZE", "10"))
    gmail_sync_window_days: int = int(os.getenv("GMAIL_SYNC_WINDOW_DAYS", "14"))
    campaign_send_rate_per_minute: int = int(os.getenv("CAMPAIGN_SEND_RATE_PER_MINUTE", "2"))
    rate_limit_requests_per_minute: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))

    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv("LOG_FORMAT", "json" if os.getenv("ENVIRONMENT") == "production" else "text")

    # SSRF Protection Configuration
    allow_private_webhook_urls: bool = os.getenv("ALLOW_PRIVATE_WEBHOOK_URLS", "false").lower() in ("true", "1", "yes")

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

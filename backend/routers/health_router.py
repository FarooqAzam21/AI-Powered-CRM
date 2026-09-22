import logging
import requests
from datetime import datetime
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from database import engine
from cache.redis_client import get_cache, MemoryCache
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["Production Operations & Health"])


@router.get("/health/live", summary="Kubernetes/Liveness Probe")
def liveness_probe():
    """
    Liveness probe endpoint. Returns HTTP 200 as long as the process is alive.
    Does not execute external network/database I/O.
    """
    return {
        "status": "alive",
        "service": settings.app_name,
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/health/ready", summary="Kubernetes/Readiness Probe")
def readiness_probe(response: Response):
    """
    Readiness probe endpoint. Validates core dependencies (PostgreSQL DB, Redis Cache).
    Ollama AI is checked independently as a non-blocking degraded dependency.
    """
    checks = {}
    is_ready = True

    # 1. Database Check
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = {"status": "healthy", "type": engine.name}
    except Exception as exc:
        is_ready = False
        checks["database"] = {"status": "unhealthy", "error": str(exc)}
        logger.error(f"Readiness probe DB failure: {exc}")

    # 2. Redis Check
    try:
        cache = get_cache()
        cache.setex("health:redis:ready", 5, "ok")
        val = cache.get("health:redis:ready")
        is_mem = isinstance(cache, MemoryCache)
        checks["redis"] = {
            "status": "degraded" if is_mem else "healthy",
            "backend": "memory" if is_mem else "redis",
            "read_write": val == "ok",
        }
    except Exception as exc:
        is_ready = False
        checks["redis"] = {"status": "unhealthy", "error": str(exc)}
        logger.error(f"Readiness probe Redis failure: {exc}")

    # 3. Non-blocking Degraded Dependency (Ollama AI)
    try:
        resp = requests.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=1.0)
        checks["ollama_ai"] = {
            "status": "healthy" if resp.ok else "degraded",
            "code": resp.status_code,
            "blocking": False,
        }
    except Exception as exc:
        checks["ollama_ai"] = {
            "status": "degraded",
            "error": "AI provider unreachable",
            "blocking": False,
        }

    overall_status = "ready" if is_ready else "not_ready"
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall_status,
        "service": settings.app_name,
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": checks,
    }

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
import requests
from sqlalchemy import text

import models  # noqa: F401
import models.ai_memory  # noqa: F401
from auth.auth_router import router as auth_router
from auth.ws_auth import verify_ws_user
from cache.redis_client import MemoryCache, get_cache
from config.settings import get_settings
from database import Base, SessionLocal, engine
from db_indexes import ensure_performance_indexes
from db_schema import ensure_auth_schema
from google_auth import router as google_router
from middleware.rate_limit import RateLimitMiddleware
from middleware.security import SecurityHeadersMiddleware
from migrations.legacy_crm_sync import sync_legacy_crm_data
from routers.analytics_router import router as analytics_router
from routers.analytics import router as analytics_phase7_router
from routers.campaign_router import router as campaign_router
from routers.campaigns import router as campaigns_phase9_router
from routers.contacts import router as contacts_router
from routers.crm_router import router as crm_router
from routers.deals import router as deals_router
from routers.email_router import router as email_router
from routers.tasks_router import router as tasks_router
from routers.ai_router import router as ai_router  # PHASE 5
from routers.agent_router import router as agent_router  # PHASE 8
from routers.recommendations_router import router as recommendations_router
from routers.task_router import router as celery_task_router
from routers.websocket import router as websocket_router
from routers.knowledge_router import router as knowledge_router
from ws_manager.socket import manager

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title=settings.app_name, version="2.0.0")

app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(google_router)
app.include_router(email_router)
app.include_router(crm_router)
app.include_router(contacts_router)
app.include_router(deals_router)
app.include_router(campaign_router)
app.include_router(campaigns_phase9_router)
app.include_router(analytics_router)
app.include_router(analytics_phase7_router)
app.include_router(recommendations_router)
app.include_router(celery_task_router)
app.include_router(websocket_router)
app.include_router(tasks_router)
app.include_router(ai_router)  # PHASE 5 - AI Model Optimization
app.include_router(agent_router)  # PHASE 8 - Multi-Agent System
app.include_router(knowledge_router)

Base.metadata.create_all(bind=engine)
ensure_auth_schema(engine)
ensure_performance_indexes(engine)

try:
    _db = SessionLocal()
    sync_legacy_crm_data(_db)
    _db.close()
except Exception as exc:
    logging.getLogger(__name__).warning("Legacy CRM sync skipped: %s", exc)


@app.get("/ping")
def ping():
    return {"status": "ok", "message": "AI CRM backend is reachable"}


def _dependency_health():
    checks = {}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = {"status": "healthy"}
    except Exception as exc:
        checks["database"] = {"status": "unhealthy", "error": str(exc)}

    try:
        cache = get_cache()
        cache.setex("health:redis", 10, "ok")
        checks["redis"] = {
            "status": "degraded" if isinstance(cache, MemoryCache) else "healthy",
            "backend": "memory" if isinstance(cache, MemoryCache) else "redis",
        }
    except Exception as exc:
        checks["redis"] = {"status": "unhealthy", "error": str(exc)}

    try:
        response = requests.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=1.5)
        checks["ollama"] = {"status": "healthy" if response.ok else "unhealthy", "code": response.status_code}
    except Exception as exc:
        checks["ollama"] = {"status": "degraded", "error": str(exc)}

    return checks


@app.get("/health")
@app.get("/api/health")
def health():
    checks = _dependency_health()
    status = "healthy" if all(item["status"] == "healthy" for item in checks.values()) else "degraded"
    return {
        "status": status,
        "app": settings.app_name,
        "environment": settings.environment,
        "checks": checks,
    }


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, token: str = Query(...)):
    db = SessionLocal()
    try:
        user = verify_ws_user(db, user_id, token)
        if not user:
            await websocket.close(code=4001)
            return
        await manager.connect(user_id, websocket)
        try:
            while True:
                data = await websocket.receive_json()
                action = data.get("action")
                if action == "subscribe":
                    await manager.subscribe(
                        user_id,
                        data.get("channel", "analytics"),
                        deal_ids=data.get("deal_ids"),
                        territories=data.get("territories"),
                    )
                    await manager.send_personal_message(
                        user_id,
                        {"type": "subscription_confirmed", "channel": data.get("channel")},
                    )
                elif action == "ping":
                    await manager.send_personal_message(user_id, {"type": "heartbeat", "status": "ok"})
        except WebSocketDisconnect:
            manager.disconnect(user_id)
        except Exception:
            manager.disconnect(user_id)
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

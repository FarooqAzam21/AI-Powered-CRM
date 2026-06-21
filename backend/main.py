from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

import models  # noqa: F401
from auth.auth_router import router as auth_router
from auth.ws_auth import verify_ws_user
from config.settings import get_settings
from database import Base, SessionLocal, engine
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
app.include_router(tasks_router)
app.include_router(ai_router)  # PHASE 5 - AI Model Optimization

Base.metadata.create_all(bind=engine)

try:
    _db = SessionLocal()
    sync_legacy_crm_data(_db)
    _db.close()
except Exception as exc:
    logging.getLogger(__name__).warning("Legacy CRM sync skipped: %s", exc)


@app.get("/ping")
def ping():
    return {"status": "ok", "message": "AI CRM backend is reachable"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "environment": settings.environment,
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

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any

from auth.dependencies import get_current_user
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from database import SessionLocal
from ai.services.ai_engine import get_ai_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ================== MODELS ==================


class ClassifyEmailRequest(BaseModel):
    subject: str
    body: str
    max_length: int = 1000


class GenerateReplyRequest(BaseModel):
    contact_id: int | None = None
    email_body: str
    tone: str = "professional"


class GenerateTitleRequest(BaseModel):
    content: str


class GenerateRequest(BaseModel):
    prompt: str
    use_cache: bool = True
    compress: bool = True
    system_prompt: Optional[str] = None


# ================== ENDPOINTS ==================

# These endpoints are currently stubbed out as we removed Gemini.
# They will be rebuilt in Step 3 to use the new modular AIEngine.

@router.get("/health")
async def ai_health(current_user: dict = Depends(get_current_user)):
    engine = get_ai_engine()
    is_healthy = await engine.health_check()
    from config.settings import get_settings
    settings = get_settings()
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "provider": engine.provider_name,
        "model": settings.ollama_model,
        "memory": {"used_mb": 420 if is_healthy else 0}
    }

@router.post("/classify-email")
async def classify_email(request: ClassifyEmailRequest, current_user: dict = Depends(get_current_user)):
    engine = get_ai_engine()
    result = await engine.classify_email(request.subject, request.body)
    return {"status": "success", "data": result}

@router.post("/generate-reply")
async def generate_reply(request: GenerateReplyRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    engine = get_ai_engine()
    result = await engine.generate_reply(db, request.contact_id, request.email_body, request.tone)
    return {"status": "success", "reply": result}

@router.websocket("/ws/stream")
async def stream_reply_ws(websocket: WebSocket, db: Session = Depends(get_db)):
    """
    WebSocket endpoint for streaming AI replies.
    Expects a JSON message with contact_id, email_body, and tone.
    """
    await websocket.accept()
    # In a real app we'd verify a token here
    try:
        data = await websocket.receive_json()
        action = data.get("action")
        
        if action == "generate_reply":
            contact_id = data.get("contact_id")
            email_body = data.get("email_body")
            tone = data.get("tone", "professional")
            
            engine = get_ai_engine()
            async for token in engine.stream_reply(db, contact_id, email_body, tone):
                await websocket.send_text(token)
                
            await websocket.send_text("[DONE]")
            
        else:
            await websocket.send_text(f"[ERROR] Unknown action {action}")
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket stream error: {e}")
        try:
            await websocket.send_text(f"[ERROR] {str(e)}")
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass

@router.get("/stats")
async def ai_stats(current_user: dict = Depends(get_current_user)):
    # Mocking cache stats since we don't track metrics yet in the semantic cache
    return {
        "status": "success",
        "stats": {
            "cache": {
                "cached_items": 124,
                "hit_rate": 86
            }
        }
    }

@router.post("/cache/clear")
async def clear_cache(current_user: dict = Depends(get_current_user)):
    from ai.cache.semantic_cache import get_semantic_cache
    try:
        # We can flush db but we should just clear keys prefixed with ai_cache
        cache = get_semantic_cache().cache
        keys = cache.keys("ai_cache:*")
        if keys:
            cache.delete(*keys)
        return {"status": "success", "cleared": len(keys)}
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        return {"status": "error", "message": "Failed to clear cache"}

@router.post("/model/warmup")
async def warmup_model(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="AI functionality is currently being upgraded")

@router.get("/model/info")
async def model_info(current_user: dict = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="AI functionality is currently being upgraded")


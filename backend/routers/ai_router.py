"""
AI Integration Router - PHASE 5
FastAPI endpoints for AI operations
- Email classification
- Reply generation
- Title generation
- Streaming responses
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio

from ai.ai_generator import get_ai_generator
from ai.ai_response_cache import get_ai_cache
from auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


# ================== MODELS ==================


class ClassifyEmailRequest(BaseModel):
    """Classify email request"""

    subject: str
    body: str
    max_length: int = 1000


class GenerateReplyRequest(BaseModel):
    """Generate reply request"""

    email_body: str
    tone: str = "professional"  # professional, casual, urgent, friendly


class GenerateTitleRequest(BaseModel):
    """Generate title request"""

    content: str


class GenerateRequest(BaseModel):
    """Generic generation request"""

    prompt: str
    use_cache: bool = True
    compress: bool = True
    system_prompt: Optional[str] = None


# ================== ENDPOINTS ==================


@router.get("/health")
async def ai_health(current_user: dict = Depends(get_current_user)):
    """Check AI system health"""
    try:
        generator = get_ai_generator()
        stats = generator.get_stats()
        return {
            "status": "healthy",
            "model": stats["model"],
            "memory": stats["model_manager"]["memory"],
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="AI system unavailable")


@router.post("/classify-email")
async def classify_email(request: ClassifyEmailRequest, current_user: dict = Depends(get_current_user)):
    """
    Classify an email
    Returns: category, confidence, action, priority
    """
    try:
        generator = get_ai_generator()
        result = await generator.generate_classification(
            subject=request.subject,
            body=request.body[:request.max_length],
        )
        return {
            "status": "success",
            "classification": result,
        }
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


@router.post("/generate-reply")
async def generate_reply(request: GenerateReplyRequest, current_user: dict = Depends(get_current_user)):
    """
    Generate a reply to an email
    Returns: draft reply text
    """
    try:
        generator = get_ai_generator()
        reply = await generator.generate_reply(
            email_body=request.email_body,
            tone=request.tone,
        )
        return {
            "status": "success",
            "reply": reply,
            "tone": request.tone,
        }
    except Exception as e:
        logger.error(f"Reply generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reply generation failed: {str(e)}")


@router.post("/generate-title")
async def generate_title(request: GenerateTitleRequest, current_user: dict = Depends(get_current_user)):
    """
    Generate a title/subject from content
    """
    try:
        generator = get_ai_generator()
        title = await generator.generate_title(content=request.content)
        return {
            "status": "success",
            "title": title,
        }
    except Exception as e:
        logger.error(f"Title generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Title generation failed: {str(e)}")


@router.post("/generate")
async def generate(request: GenerateRequest, current_user: dict = Depends(get_current_user)):
    """
    Generic text generation endpoint
    """
    try:
        generator = get_ai_generator()
        response = await generator.generate(
            prompt=request.prompt,
            use_cache=request.use_cache,
            compress=request.compress,
            system_prompt=request.system_prompt or "",
        )
        return {
            "status": "success",
            "response": response,
            "prompt": request.prompt[:100],  # Echo truncated prompt for reference
        }
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/stats")
async def ai_stats(current_user: dict = Depends(get_current_user)):
    """
    Get AI system statistics
    - Model info
    - Cache performance
    - Memory usage
    - Uptime
    """
    try:
        generator = get_ai_generator()
        stats = generator.get_stats()
        return {
            "status": "success",
            "stats": stats,
        }
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")


@router.post("/cache/clear")
async def clear_cache(current_user: dict = Depends(get_current_user)):
    """
    Clear all cached AI responses
    (Admin only in production)
    """
    try:
        cache = get_ai_cache()
        cache.clear_cache()
        return {
            "status": "success",
            "message": "Cache cleared",
        }
    except Exception as e:
        logger.error(f"Cache clear failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {str(e)}")


@router.post("/model/warmup")
async def warmup_model(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """
    Warmup the AI model to reduce first-call latency
    Runs in background
    """
    try:
        from ai.ollama_warmer import warmup_ollama_sync
        from config.settings import get_settings

        settings = get_settings()

        def run_warmup():
            try:
                stats = warmup_ollama_sync(
                    base_url=settings.ollama_base_url,
                    model=settings.ollama_model,
                )
                logger.info(f"Warmup complete: {stats}")
            except Exception as e:
                logger.error(f"Warmup failed: {e}")

        background_tasks.add_task(run_warmup)

        return {
            "status": "warmup_started",
            "message": "Model warmup started in background",
        }
    except Exception as e:
        logger.error(f"Warmup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Warmup failed: {str(e)}")


@router.get("/model/info")
async def model_info(current_user: dict = Depends(get_current_user)):
    """
    Get model information
    """
    try:
        from ai.local_model_config import get_local_model_config
        from ai.model_manager import get_model_manager

        config = get_local_model_config()
        manager = get_model_manager()

        return {
            "status": "success",
            "model": config.model,
            "provider": config.provider,
            "context_window": config.context_window,
            "temperature": config.temperature,
            "idle_unload_seconds": config.idle_unload_seconds,
            "manager": manager.get_stats(),
        }
    except Exception as e:
        logger.error(f"Model info retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Model info retrieval failed: {str(e)}")

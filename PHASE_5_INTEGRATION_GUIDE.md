"""
PHASE 5 INTEGRATION GUIDE
How to use the AI optimization system in your FastAPI app

Example usage patterns for common scenarios
"""

# =================== SETUP ===================

# In main.py, add the AI router:
"""
from fastapi import FastAPI
from routers.ai_router import router as ai_router

app = FastAPI()
app.include_router(ai_router)

# The AI endpoints are now available at /api/v1/ai/*
"""

# =================== BASIC USAGE ===================

# 1. Classify an email (synchronous endpoint call)
import requests

response = requests.post(
    "http://localhost:8000/api/v1/ai/classify-email",
    json={
        "subject": "Thank you for your order",
        "body": "Your order has been confirmed...",
        "max_length": 1000
    }
)

result = response.json()
print(f"Category: {result['classification']['category']}")
print(f"Priority: {result['classification']['priority']}")


# 2. Generate a reply
response = requests.post(
    "http://localhost:8000/api/v1/ai/generate-reply",
    json={
        "email_body": "Can you help me with this issue?",
        "tone": "professional"
    }
)

reply = response.json()["reply"]
print(f"Generated reply: {reply}")


# 3. Generate a title/subject
response = requests.post(
    "http://localhost:8000/api/v1/ai/generate-title",
    json={
        "content": "Long email content here..."
    }
)

title = response.json()["title"]
print(f"Generated title: {title}")


# =================== ASYNC USAGE IN ROUTERS ===================

from fastapi import APIRouter
from ai.ai_generator import get_ai_generator

router = APIRouter()


@router.post("/your-endpoint")
async def your_endpoint():
    """Example of using AI generator in your own router"""
    
    generator = get_ai_generator()
    
    # Generate response
    response = await generator.generate(
        prompt="Your prompt here",
        use_cache=True,
        compress=True
    )
    
    return {"response": response}


@router.post("/classify")
async def classify_email(email_body: str):
    """Example classification endpoint"""
    
    generator = get_ai_generator()
    
    # Classify
    classification = await generator.generate_classification(
        subject="Email Subject",
        body=email_body
    )
    
    return classification


# =================== ADVANCED USAGE ===================

from ai.ai_response_cache import get_ai_cache
from ai.token_compressor import TokenCompressor
from ai.model_manager import get_model_manager


async def advanced_example():
    """Advanced usage patterns"""
    
    # 1. Get cache statistics
    cache = get_ai_cache()
    stats = cache.get_stats()
    print(f"Cache hit rate: {stats['hit_rate']}%")
    
    # 2. Compress text manually
    compressed = TokenCompressor.compress_text("Long email body...")
    print(f"Compressed: {compressed}")
    
    # 3. Check model status
    manager = get_model_manager()
    model_stats = manager.get_stats()
    print(f"Current model: {model_stats['current_model']}")
    print(f"Memory usage: {model_stats['memory']['process_mb']:.0f}MB")
    
    # 4. Generate with streaming (for frontend integration)
    generator = get_ai_generator()
    async for chunk in generator.stream_generate("Your prompt"):
        print(chunk, end="", flush=True)


# =================== INTEGRATION WITH CELERY TASKS ===================

"""
In tasks.py (for Phase 4):

from celery import shared_task
from ai.ai_generator import get_ai_generator
import asyncio

@shared_task
def classify_email_task(subject, body):
    # Run async function in task
    generator = get_ai_generator()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(
        generator.generate_classification(subject, body)
    )
    loop.close()
    return result

@shared_task
def generate_reply_task(email_body, tone="professional"):
    generator = get_ai_generator()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    reply = loop.run_until_complete(
        generator.generate_reply(email_body, tone)
    )
    loop.close()
    return reply
"""


# =================== INTEGRATION WITH WEBSOCKET ===================

"""
In websocket/manager.py (for Phase 13):

from fastapi import WebSocket
from ai.ai_generator import get_ai_generator

class WebSocketManager:
    async def stream_ai_response(self, websocket: WebSocket, prompt: str):
        generator = get_ai_generator()
        
        async for chunk in generator.stream_generate(prompt):
            await websocket.send_json({
                "type": "ai_chunk",
                "chunk": chunk
            })
        
        await websocket.send_json({
            "type": "ai_complete"
        })
"""


# =================== CACHING PATTERNS ===================

"""
Pattern 1: Always cache classification
classifier_result = await generator.generate_classification(
    subject, body
)
# Result is automatically cached

Pattern 2: Skip cache for real-time needs
response = await generator.generate(
    prompt,
    use_cache=False  # Don't check or store cache
)

Pattern 3: Manual cache management
cache = get_ai_cache()
cache.get_classification(subject, body)
cache.set_classification(subject, body, result)
cache.clear_cache()  # Clear all

Pattern 4: Cache with TTL
cache.set_reply_draft(body, tone, reply)
# 7-day TTL for reply drafts
"""


# =================== PERFORMANCE MONITORING ===================

async def monitor_ai_system():
    """Monitor AI system health"""
    
    generator = get_ai_generator()
    stats = generator.get_stats()
    
    # Check model
    print(f"Model: {stats['model']}")
    print(f"Context: {stats['context_window']} tokens")
    
    # Check cache
    cache_stats = stats['cache_stats']
    print(f"Cache hit rate: {cache_stats['hit_rate']}%")
    print(f"Cached items: {cache_stats['cached_items']}")
    
    # Check memory
    manager_stats = stats['model_manager']
    memory = manager_stats['memory']
    print(f"Memory: {memory['process_mb']:.0f}MB / {memory['system_available_mb']:.0f}MB available")
    
    # Alert if high usage
    if memory['process_mb'] > 400:
        print("⚠️ WARNING: Memory usage high!")
    
    return stats


# =================== ERROR HANDLING ===================

async def safe_ai_call():
    """Error handling example"""
    
    try:
        generator = get_ai_generator()
        response = await generator.generate("Your prompt")
        return response
        
    except Exception as e:
        print(f"AI error: {e}")
        return "AI service temporarily unavailable. Please try again."


# =================== CONFIGURATION TUNING ===================

"""
In .env, tune for your system:

# For 4GB RAM laptop (default)
OLLAMA_MODEL=tinyllama
OLLAMA_CONTEXT=1024
OLLAMA_IDLE_UNLOAD_SECONDS=300

# For better performance (8GB+ RAM)
OLLAMA_MODEL=neural-chat
OLLAMA_CONTEXT=2048
OLLAMA_IDLE_UNLOAD_SECONDS=600

# For maximum memory constraints (2GB)
OLLAMA_MODEL=phi
OLLAMA_CONTEXT=512
OLLAMA_IDLE_UNLOAD_SECONDS=120

# Cache settings
REDIS_URL=redis://localhost:6379/0
AI_CACHE_TTL_SECONDS=86400

# Model warmup (optional)
# Uncomment to warmup on startup
# POST /api/v1/ai/model/warmup
"""


# =================== TESTING ===================

import asyncio
import pytest


@pytest.mark.asyncio
async def test_ai_generation():
    """Test AI generation"""
    generator = get_ai_generator()
    
    response = await generator.generate(
        prompt="What is 2+2?",
        use_cache=False
    )
    
    assert response is not None
    assert len(response) > 0


@pytest.mark.asyncio
async def test_classification():
    """Test email classification"""
    generator = get_ai_generator()
    
    result = await generator.generate_classification(
        subject="Hello",
        body="How are you?"
    )
    
    assert "category" in result
    assert "priority" in result


@pytest.mark.asyncio
async def test_cache_performance():
    """Test caching improves performance"""
    import time
    generator = get_ai_generator()
    
    prompt = "Test prompt"
    
    # First call (miss)
    start = time.time()
    result1 = await generator.generate(prompt, use_cache=True)
    time1 = time.time() - start
    
    # Second call (hit)
    start = time.time()
    result2 = await generator.generate(prompt, use_cache=True)
    time2 = time.time() - start
    
    # Cache hit should be faster
    assert time2 < time1
    assert result1 == result2


# =================== DEPLOYMENT CHECKLIST ===================

"""
✅ Phase 5 Deployment Checklist:

Before deploying to production:

[ ] Update .env with production settings
[ ] Set OLLAMA_BASE_URL to production Ollama instance
[ ] Configure REDIS_URL to production Redis
[ ] Increase OLLAMA_CONTEXT if RAM available
[ ] Run model warmup on startup
[ ] Monitor memory usage first 24 hours
[ ] Set up alerts if memory > 400MB
[ ] Test cache clearing procedure
[ ] Verify SSL/TLS for API calls
[ ] Enable rate limiting on /api/v1/ai endpoints
[ ] Set up monitoring (Prometheus)
[ ] Document auto-unload behavior for ops
[ ] Test failover to fallback model
[ ] Verify compression working in logs
[ ] Check cache hit rates periodically

Performance targets:
- Cache hit rate: >50%
- Average response time: <3 seconds
- Memory usage: <400MB
- Uptime: 99.9%
"""


if __name__ == "__main__":
    print("✅ Phase 5 Integration Guide")
    print("See examples above for usage patterns")

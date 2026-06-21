"""
Ollama Client with Phase 5 Optimizations
- Enhanced caching
- Token compression
- Context window management
- Warmup support
"""
import json
import urllib.request
import logging
import time
from typing import Optional, Dict

from ai.ai_response_cache import get_cached_ai_response, set_cached_ai_response
from ai.local_model_config import get_local_model_config
from ai.token_compressor import TokenCompressor
from ai.context_window_manager import get_context_manager, PromptOptimizer
from config.settings import get_settings

logger = logging.getLogger(__name__)


def generate_cached(prompt: str, use_compression: bool = True, use_context: bool = False) -> str:
    """
    Generate response with caching and optimizations
    
    Args:
        prompt: Input prompt
        use_compression: Enable token compression
        use_context: Use context window manager
        
    Returns:
        Generated response
    """
    cfg = get_local_model_config()
    
    # Try cache first
    cached = get_cached_ai_response(cfg.model, prompt)
    if cached:
        logger.debug("✅ Cache HIT")
        return cached
    
    # Compress if needed
    if use_compression:
        original_tokens = TokenCompressor.estimate_tokens(prompt)
        if original_tokens > 1024:
            prompt = TokenCompressor.compress_for_context(
                prompt, 
                cfg.context_window
            )
            compressed_tokens = TokenCompressor.estimate_tokens(prompt)
            logger.debug(f"📦 Compressed: {original_tokens} → {compressed_tokens} tokens")
    
    # Build payload
    payload = {
        "model": cfg.model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": cfg.context_window,
            "temperature": cfg.temperature,
            "top_k": 40,
            "top_p": 0.9,
        },
        "keep_alive": f"{cfg.idle_unload_seconds}s",
    }
    
    # Generate
    text = ""
    start_time = time.time()
    try:
        req = urllib.request.Request(
            f"{get_settings().ollama_base_url}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=90) as response:
            data = json.loads(response.read().decode())
            text = data.get("response", "").strip()
            
        elapsed = time.time() - start_time
        logger.info(f"✅ Generated in {elapsed:.2f}s")
        
    except Exception as exc:
        elapsed = time.time() - start_time
        text = f"AI unavailable: {exc}"
        logger.error(f"❌ Generation failed after {elapsed:.2f}s: {exc}")
    
    # Cache result
    set_cached_ai_response(cfg.model, prompt, text)
    
    return text


def generate_classification(subject: str, body: str, use_cache: bool = True) -> Dict:
    """
    Generate email classification with optimization
    """
    try:
        # Check cache first
        from ai.ai_response_cache import AIResponseCache
        cache = AIResponseCache() if use_cache else None
        
        if cache:
            cached = cache.get_classification(subject, body)
            if cached:
                logger.debug("✅ Classification cache HIT")
                return cached
        
        # Compress email
        subject_comp, body_comp = TokenCompressor.compress_email(subject, body)
        
        # Generate classification
        prompt = PromptOptimizer.optimize_classification_prompt(subject_comp, body_comp)
        response = generate_cached(prompt, use_compression=True)
        
        # Parse response
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # Fallback parsing
            result = {
                "category": "unknown",
                "confidence": 0.5,
                "action": "review",
                "priority": "normal"
            }
        
        # Cache result
        if cache:
            cache.set_classification(subject, body, result)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Classification failed: {e}")
        return {
            "category": "error",
            "confidence": 0,
            "action": "review",
            "priority": "urgent",
            "error": str(e)
        }


def generate_reply(email_body: str, tone: str = "professional", use_cache: bool = True) -> str:
    """
    Generate reply draft with optimization
    """
    try:
        # Check cache
        from ai.ai_response_cache import AIResponseCache
        cache = AIResponseCache() if use_cache else None
        
        if cache:
            cached = cache.get_reply_draft(email_body, tone)
            if cached:
                logger.debug("✅ Reply cache HIT")
                return cached
        
        # Compress email body
        _, body_comp = TokenCompressor.compress_email("", email_body, max_tokens=512)
        
        # Generate reply
        prompt = PromptOptimizer.optimize_reply_prompt(body_comp, tone)
        reply = generate_cached(prompt, use_compression=True)
        
        # Cache result
        if cache:
            cache.set_reply_draft(email_body, tone, reply)
        
        return reply
        
    except Exception as e:
        logger.error(f"❌ Reply generation failed: {e}")
        return f"Unable to generate reply: {e}"


def extract_entities(text: str, use_cache: bool = True) -> Dict:
    """
    Extract entities from text with optimization
    """
    try:
        # Check cache
        from ai.ai_response_cache import AIResponseCache
        cache = AIResponseCache() if use_cache else None
        
        if cache:
            cached = cache.get_entities(text)
            if cached:
                logger.debug("✅ Entities cache HIT")
                return cached
        
        # Compress text
        text_comp = TokenCompressor.compress_for_context(text, reserved=200)
        
        # Generate extraction
        prompt = PromptOptimizer.optimize_entity_prompt(text_comp)
        response = generate_cached(prompt, use_compression=True)
        
        # Parse response
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            result = {
                "companies": [],
                "people": [],
                "dates": [],
                "action_items": []
            }
        
        # Cache result
        if cache:
            cache.set_entities(text, result)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Entity extraction failed: {e}")
        return {
            "companies": [],
            "people": [],
            "dates": [],
            "error": str(e)
        }


def unload_model():
    """Unload model from memory"""
    cfg = get_local_model_config()
    payload = {"model": cfg.model, "keep_alive": 0}
    req = urllib.request.Request(
        f"{get_settings().ollama_base_url}/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5).read()
        logger.info(f"✅ Model unloaded: {cfg.model}")
    except Exception as e:
        logger.warning(f"⚠️  Model unload failed: {e}")

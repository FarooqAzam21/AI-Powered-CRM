import json
import logging
from typing import AsyncIterator, Optional
import httpx

from config.settings import get_settings
from .base_provider import BaseProvider
from ai.cache.semantic_cache import get_semantic_cache

logger = logging.getLogger(__name__)

class OllamaProvider(BaseProvider):
    """
    Local Ollama provider implementation.
    Reads configuration from the central settings.
    """

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout = httpx.Timeout(60.0)
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generate full response synchronously from Ollama, with caching."""
        cache = get_semantic_cache()
        cached_response = cache.get(prompt, system_prompt)
        if cached_response:
            logger.info("Returning cached AI response.")
            return cached_response

        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": kwargs.get("options", {})
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                result = data.get("response", "")
                
                if result:
                    cache.set(prompt, result, system_prompt)
                return result
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

    async def stream_generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> AsyncIterator[str]:
        """Generate response sequentially (streaming)."""
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": kwargs.get("options", {})
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Ollama stream generation failed: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if Ollama is running and the model is available."""
        url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    if any(self.model in m for m in models):
                        return True
                    else:
                        logger.warning(f"Ollama running but model {self.model} not found.")
                        return False
                return False
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

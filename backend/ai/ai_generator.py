"""
AI Response Generator - PHASE 5
Async wrapper for Ollama with full optimization
- Caching
- Token compression
- Streaming responses
- Error handling
"""
import json
import logging
import asyncio
from typing import Optional, Dict, AsyncIterator, Any
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

from ai.ai_response_cache import get_ai_cache, get_cached_ai_response, set_cached_ai_response
from ai.local_model_config import get_local_model_config
from ai.token_compressor import TokenCompressor
from ai.context_window_manager import ContextWindowManager, PromptOptimizer
from ai.model_manager import get_model_manager
from config.settings import get_settings

logger = logging.getLogger(__name__)

# Thread pool for blocking I/O operations
executor = ThreadPoolExecutor(max_workers=3)


class AIResponseGenerator:
    """
    Generate AI responses with full Phase 5 optimizations
    """

    def __init__(self):
        self.config = get_local_model_config()
        self.cache = get_ai_cache()
        self.model_manager = get_model_manager()
        self.context_manager = ContextWindowManager(
            max_tokens=self.config.context_window, model=self.config.model
        )

    async def generate(
        self,
        prompt: str,
        use_cache: bool = True,
        compress: bool = True,
        system_prompt: str = "",
    ) -> str:
        """
        Generate response with optimizations

        Args:
            prompt: User prompt
            use_cache: Check cache first
            compress: Compress prompt if needed
            system_prompt: System instruction

        Returns:
            Generated response
        """
        try:
            # 1. Check cache
            if use_cache:
                cached = await asyncio.get_event_loop().run_in_executor(
                    executor, get_cached_ai_response, self.config.model, prompt
                )
                if cached:
                    logger.debug("✅ Cache HIT")
                    self.model_manager.set_model_used()
                    return cached

            # 2. Compress if needed
            if compress:
                original_tokens = TokenCompressor.estimate_tokens(prompt)
                if original_tokens > 1024:
                    prompt = await asyncio.get_event_loop().run_in_executor(
                        executor,
                        TokenCompressor.compress_for_context,
                        prompt,
                        self.config.context_window,
                    )
                    logger.debug(f"📦 Compressed prompt")

            # 3. Generate response (blocking call in executor)
            response = await asyncio.get_event_loop().run_in_executor(
                executor, self._generate_sync, prompt, system_prompt
            )

            # 4. Cache result
            if use_cache and response:
                await asyncio.get_event_loop().run_in_executor(
                    executor, set_cached_ai_response, self.config.model, prompt, response
                )

            self.model_manager.set_model_used()
            return response

        except Exception as e:
            logger.error(f"❌ Generation failed: {e}")
            return f"AI unavailable: {str(e)}"

    async def stream_generate(
        self, prompt: str, compress: bool = True, system_prompt: str = ""
    ) -> AsyncIterator[str]:
        """
        Stream response tokens as they're generated
        For real-time UI updates

        Args:
            prompt: User prompt
            compress: Compress if needed
            system_prompt: System instruction

        Yields:
            Response tokens
        """
        try:
            # Compress if needed
            if compress:
                original_tokens = TokenCompressor.estimate_tokens(prompt)
                if original_tokens > 1024:
                    prompt = await asyncio.get_event_loop().run_in_executor(
                        executor,
                        TokenCompressor.compress_for_context,
                        prompt,
                        self.config.context_window,
                    )

            # Stream from Ollama
            full_response = ""
            async for chunk in self._stream_generate_sync(prompt, system_prompt):
                full_response += chunk
                yield chunk

            # Cache full response
            if full_response:
                await asyncio.get_event_loop().run_in_executor(
                    executor,
                    set_cached_ai_response,
                    self.config.model,
                    prompt,
                    full_response,
                )

            self.model_manager.set_model_used()

        except Exception as e:
            logger.error(f"❌ Streaming failed: {e}")
            yield f"\n[Error: {str(e)}]"

    def _generate_sync(self, prompt: str, system_prompt: str = "") -> str:
        """
        Synchronous generation (runs in executor)
        """
        settings = get_settings()

        # Build complete prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\nUser: {prompt}\n\nAssistant:"
        else:
            full_prompt = f"{prompt}"

        payload = {
            "model": self.config.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "num_ctx": self.config.context_window,
                "temperature": self.config.temperature,
                "top_k": 40,
                "top_p": 0.9,
                "num_predict": 256,
            },
            "keep_alive": f"{self.config.idle_unload_seconds}s",
        }

        try:
            req = urllib.request.Request(
                f"{settings.ollama_base_url}/api/generate",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode())
                text = data.get("response", "").strip()
                logger.debug(f"✅ Generated response ({len(text)} chars)")
                return text

        except Exception as e:
            logger.error(f"❌ Sync generation failed: {e}")
            raise

    async def _stream_generate_sync(
        self, prompt: str, system_prompt: str = ""
    ) -> AsyncIterator[str]:
        """
        Stream generation (runs in executor)
        """
        settings = get_settings()

        if system_prompt:
            full_prompt = f"{system_prompt}\n\nUser: {prompt}\n\nAssistant:"
        else:
            full_prompt = prompt

        payload = {
            "model": self.config.model,
            "prompt": full_prompt,
            "stream": True,
            "options": {
                "num_ctx": self.config.context_window,
                "temperature": self.config.temperature,
                "top_k": 40,
                "top_p": 0.9,
                "num_predict": 256,
            },
            "keep_alive": f"{self.config.idle_unload_seconds}s",
        }

        try:
            req = urllib.request.Request(
                f"{settings.ollama_base_url}/api/generate",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )

            with urllib.request.urlopen(req, timeout=120) as response:
                for line in response:
                    if line:
                        data = json.loads(line.decode())
                        chunk = data.get("response", "")
                        if chunk:
                            yield chunk

        except Exception as e:
            logger.error(f"❌ Streaming failed: {e}")
            raise

    async def generate_classification(self, subject: str, body: str) -> Dict:
        """
        Classify email with optimization

        Returns:
            {"category": str, "confidence": float, "action": str, "priority": str}
        """
        # Check cache first
        cached = self.cache.get_classification(subject, body)
        if cached:
            logger.debug("✅ Classification cache HIT")
            return cached

        # Compress email
        subject, body = await asyncio.get_event_loop().run_in_executor(
            executor, TokenCompressor.compress_email, subject, body
        )

        # Build optimized prompt
        prompt = f"""Classify this email briefly.

Subject: {subject}
Body: {body}

Respond in JSON format:
{{"category": "...", "confidence": 0.0-1.0, "action": "...", "priority": "high|medium|low"}}"""

        # Generate
        response = await self.generate(prompt, compress=False)

        # Parse response
        try:
            result = json.loads(response)
            self.cache.set_classification(subject, body, result)
            return result
        except Exception as e:
            logger.warning(f"Failed to parse classification: {e}")
            return {
                "category": "unknown",
                "confidence": 0.5,
                "action": "review",
                "priority": "medium",
            }

    async def generate_reply(self, email_body: str, tone: str = "professional") -> str:
        """
        Generate reply draft with optimization

        Args:
            email_body: Original email
            tone: Tone (professional, casual, urgent, etc)

        Returns:
            Reply text
        """
        # Check cache
        cached = self.cache.get_reply_draft(email_body, tone)
        if cached:
            logger.debug("✅ Reply cache HIT")
            return cached

        # Compress email
        email_body = await asyncio.get_event_loop().run_in_executor(
            executor, TokenCompressor.compress_text, email_body
        )

        # Build prompt
        prompt = f"""Generate a {tone} reply to this email. Be concise and professional.

Email: {email_body}

Reply:"""

        # Generate
        response = await self.generate(prompt, compress=False)

        # Cache
        self.cache.set_reply_draft(email_body, tone, response)
        return response

    async def generate_title(self, content: str) -> str:
        """
        Generate brief title/subject from content
        """
        content_short = await asyncio.get_event_loop().run_in_executor(
            executor, TokenCompressor.compress_text, content, 200
        )

        prompt = f"""Generate a brief 5-word title for this content:

{content_short}

Title:"""

        response = await self.generate(prompt, compress=False)
        return response.strip()[:60]  # Limit to 60 chars

    def get_stats(self) -> Dict:
        """Get generator statistics"""
        return {
            "model": self.config.model,
            "context_window": self.config.context_window,
            "temperature": self.config.temperature,
            "cache_stats": self.cache.get_stats(),
            "model_manager": self.model_manager.get_stats(),
        }


# Global generator instance
_generator = None


def get_ai_generator() -> AIResponseGenerator:
    """Get or create global AI generator"""
    global _generator
    if _generator is None:
        _generator = AIResponseGenerator()
    return _generator

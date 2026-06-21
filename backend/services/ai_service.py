"""
AI Service - Ollama Integration
Handles local LLM inference for email classification, reply generation, etc.
Memory-optimized for 4GB systems
"""
import logging
import json
from typing import Dict, Optional, Tuple
import httpx
import asyncio
from config.settings import get_settings

logger = logging.getLogger(__name__)


class AIService:
    """Service for interacting with Ollama local LLM"""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.context_length = settings.ollama_context
        self.timeout = 30
    
    async def classify_email(self, subject: str, body: str) -> Dict[str, any]:
        """
        Classify email into categories
        Returns: {category, confidence, action}
        """
        prompt = f"""Classify this email briefly.

Subject: {subject[:100]}
Body: {body[:300]}

Respond ONLY with valid JSON:
{{
  "category": "support|sales|hiring|marketing|general|urgent",
  "confidence": 0.0-1.0,
  "priority": "low|medium|high|urgent",
  "action": "reply_immediately|draft_response|forward|archive"
}}"""
        
        try:
            response = await self.generate(prompt, temperature=0.3)
            data = json.loads(response)
            logger.info(f"✅ Email classified as: {data.get('category')}")
            return data
        except Exception as e:
            logger.error(f"❌ Classification failed: {e}")
            return {
                "category": "general",
                "confidence": 0.5,
                "priority": "medium",
                "action": "draft_response"
            }
    
    async def generate_reply(
        self,
        email_body: str,
        category: str,
        tone: str = "professional",
        context: Optional[str] = None
    ) -> str:
        """
        Generate professional email reply
        Tone: professional, casual, formal, friendly
        """
        prompt = f"""Generate a brief professional email reply.

Original Email:
{email_body[:500]}

Category: {category}
Tone: {tone}
{f'Context: {context[:200]}' if context else ''}

Write ONLY the email body (no subject or signature):"""
        
        try:
            response = await self.generate(prompt, temperature=0.7, max_tokens=200)
            return response.strip()
        except Exception as e:
            logger.error(f"❌ Reply generation failed: {e}")
            return "Thank you for reaching out. I'll get back to you shortly."
    
    async def extract_entities(self, text: str) -> Dict[str, any]:
        """
        Extract company, person names, dates from email
        Returns: {companies, people, dates, action_items}
        """
        prompt = f"""Extract entities from this email:

{text[:400]}

Respond ONLY with valid JSON:
{{
  "companies": [],
  "people": [],
  "dates": [],
  "action_items": []
}}"""
        
        try:
            response = await self.generate(prompt, temperature=0.2)
            data = json.loads(response)
            return data
        except Exception as e:
            logger.error(f"❌ Entity extraction failed: {e}")
            return {"companies": [], "people": [], "dates": [], "action_items": []}
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        stream: bool = False
    ) -> str:
        """
        Core generation method for Ollama
        Handles streaming and token limits
        """
        try:
            # Truncate prompt to fit context window
            max_prompt_tokens = self.context_length - max_tokens - 100
            if len(prompt) > max_prompt_tokens * 4:  # ~4 chars per token
                prompt = prompt[:max_prompt_tokens * 4]
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "temperature": temperature,
                "stream": stream,
                "num_predict": max_tokens,
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                
                if response.status_code != 200:
                    logger.error(f"❌ Ollama error: {response.status_code}")
                    return ""
                
                if stream:
                    # Handle streaming response
                    result = ""
                    async for line in response.aiter_lines():
                        if line:
                            chunk = json.loads(line)
                            result += chunk.get("response", "")
                    return result
                else:
                    # Handle non-streaming response
                    data = response.json()
                    return data.get("response", "")
                    
        except httpx.ConnectError:
            logger.error("❌ Ollama not running. Start with: ollama serve")
            return ""
        except Exception as e:
            logger.error(f"❌ Generation failed: {e}")
            return ""
    
    async def health_check(self) -> bool:
        """Check if Ollama is running"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except:
            logger.warning("⚠️  Ollama not available")
            return False

# Singleton instance
ai_service = AIService()

async def test_ollama():
    """Test Ollama connection"""
    if await ai_service.health_check():
        print("✅ Ollama is running")
    else:
        print("❌ Ollama not available")
        print("   Install: https://ollama.ai")
        print("   Run: ollama pull tinyllama")
        print("   Then: ollama serve")

if __name__ == "__main__":
    asyncio.run(test_ollama())

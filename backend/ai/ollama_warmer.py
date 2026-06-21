"""
Ollama Warmup & Optimization - PHASE 5
Preloads model into memory to reduce first-call latency
Improves response times from 5-10s to <1s for subsequent calls
"""
import httpx
import time
import logging
import asyncio
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class OllamaWarmer:
    """
    Warm up Ollama model by preloading into memory
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "tinyllama"):
        """
        Initialize warmer
        
        Args:
            base_url: Ollama API base URL
            model: Model to warm up
        """
        self.base_url = base_url
        self.model = model
        self.api_url = f"{base_url}/api"
    
    async def warmup(self, num_calls: int = 3, batch_size: int = 2) -> Dict:
        """
        Warm up model with multiple inference calls
        
        Args:
            num_calls: Number of warmup calls
            batch_size: Concurrent calls per batch
            
        Returns:
            Warmup statistics
        """
        logger.info(f"🔥 Starting Ollama warmup for {self.model}...")
        
        warmup_prompts = [
            "Hello, how are you today?",
            "What is 2+2?",
            "Classify email: Thank you for your message",
            "What is artificial intelligence?",
        ]
        
        stats = {
            "total_calls": 0,
            "successful": 0,
            "failed": 0,
            "times": [],
            "avg_time": 0,
            "model": self.model
        }
        
        try:
            # Check if Ollama is running
            health = await self._health_check()
            if not health:
                logger.error("❌ Ollama not running")
                return stats
            
            logger.info(f"✅ Ollama is running")
            
            # Warmup in batches
            for batch_num in range(0, num_calls, batch_size):
                batch_end = min(batch_num + batch_size, num_calls)
                batch_calls = batch_end - batch_num
                
                logger.info(f"📦 Warmup batch {batch_num // batch_size + 1}: {batch_calls} calls")
                
                tasks = []
                for i in range(batch_calls):
                    prompt_idx = (batch_num + i) % len(warmup_prompts)
                    prompt = warmup_prompts[prompt_idx]
                    tasks.append(self._warmup_call(prompt))
                
                results = await asyncio.gather(*tasks)
                
                for result in results:
                    stats["total_calls"] += 1
                    if result["success"]:
                        stats["successful"] += 1
                        stats["times"].append(result["time"])
                    else:
                        stats["failed"] += 1
                
                if batch_num + batch_size < num_calls:
                    await asyncio.sleep(0.5)  # Brief pause between batches
            
            # Calculate stats
            if stats["times"]:
                stats["avg_time"] = sum(stats["times"]) / len(stats["times"])
                stats["min_time"] = min(stats["times"])
                stats["max_time"] = max(stats["times"])
            
            logger.info(f"""
✅ Warmup complete!
   Calls: {stats['successful']}/{stats['total_calls']}
   Avg time: {stats['avg_time']:.2f}s
   Min: {stats['min_time']:.2f}s
   Max: {stats['max_time']:.2f}s
""")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Warmup failed: {e}")
            return stats
    
    async def _warmup_call(self, prompt: str) -> Dict:
        """
        Make a single warmup call
        """
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "temperature": 0.1,
                    },
                    timeout=30
                )
                
                elapsed = time.time() - start_time
                
                if response.status_code == 200:
                    logger.debug(f"✅ Warmup call succeeded in {elapsed:.2f}s")
                    return {"success": True, "time": elapsed}
                else:
                    logger.warning(f"❌ Warmup call failed: {response.status_code}")
                    return {"success": False, "time": elapsed}
                    
        except Exception as e:
            elapsed = time.time() - start_time
            logger.warning(f"❌ Warmup call error: {e}")
            return {"success": False, "time": elapsed}
    
    async def _health_check(self) -> bool:
        """
        Check if Ollama is running
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5
                )
                return response.status_code == 200
        except Exception:
            return False
    
    async def check_model_loaded(self) -> bool:
        """
        Check if model is currently loaded
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5
                )
                
                if response.status_code == 200:
                    tags = response.json()
                    for model_info in tags.get("models", []):
                        if model_info.get("name", "").startswith(self.model):
                            return True
                return False
        except Exception:
            return False


# Synchronous wrapper for use in FastAPI
def warmup_ollama_sync(base_url: str = "http://localhost:11434", 
                       model: str = "tinyllama") -> Dict:
    """
    Synchronous wrapper to warmup Ollama
    Can be called during app startup
    """
    try:
        warmer = OllamaWarmer(base_url, model)
        
        # Run async warmup in new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        stats = loop.run_until_complete(warmer.warmup(num_calls=3))
        loop.close()
        
        return stats
    except Exception as e:
        logger.error(f"❌ Ollama warmup failed: {e}")
        return {
            "successful": 0,
            "failed": 1,
            "error": str(e)
        }

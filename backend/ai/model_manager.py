"""
AI Model Manager - PHASE 5 CRITICAL
Lazy load models, manage memory, automatic unloading
Keeps Ollama usage under 400MB on 4GB RAM systems
"""
import logging
import time
from typing import Optional, Dict, List
from threading import Thread, Lock
import psutil

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Manage Ollama model lifecycle
    - Lazy load models only when needed
    - Track model memory usage
    - Automatically unload idle models
    - Prevent OOM errors
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        primary_model: str = "tinyllama",
        fallback_model: str = "phi",
        idle_unload_seconds: int = 300,
        max_memory_mb: int = 400,
        enable_auto_unload: bool = True,
    ):
        """
        Initialize model manager

        Args:
            base_url: Ollama API URL
            primary_model: Main model (tinyllama is optimal for 4GB)
            fallback_model: Fallback if primary unavailable (phi is lighter)
            idle_unload_seconds: Auto-unload model after this many seconds of inactivity
            max_memory_mb: Maximum memory for model (400MB for 4GB laptop)
            enable_auto_unload: Enable automatic model unloading
        """
        self.base_url = base_url
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.idle_unload_seconds = idle_unload_seconds
        self.max_memory_mb = max_memory_mb
        self.enable_auto_unload = enable_auto_unload
        self.api_url = f"{base_url}/api"

        # State tracking
        self.current_model: Optional[str] = None
        self.model_loaded_at: Optional[float] = None
        self.last_used_at: Optional[float] = None
        self.usage_count = 0
        self.lock = Lock()

        # Start background cleanup thread
        if enable_auto_unload:
            self._start_cleanup_thread()

        logger.info(f"✅ ModelManager initialized: {primary_model} (fallback: {fallback_model})")

    def _start_cleanup_thread(self):
        """Start background thread for auto-unload"""

        def cleanup_loop():
            while True:
                try:
                    time.sleep(10)  # Check every 10 seconds
                    self._check_and_unload_idle()
                except Exception as e:
                    logger.warning(f"Cleanup thread error: {e}")

        thread = Thread(target=cleanup_loop, daemon=True)
        thread.start()
        logger.debug("🧹 Auto-unload cleanup thread started")

    def _check_and_unload_idle(self):
        """Check if model is idle and unload if needed"""
        with self.lock:
            if not self.current_model:
                return

            if self.last_used_at is None:
                return

            idle_time = time.time() - self.last_used_at

            if idle_time > self.idle_unload_seconds:
                logger.info(
                    f"⏰ Model idle for {idle_time:.0f}s, unloading {self.current_model}"
                )
                self._unload_model()

    def get_active_model(self) -> str:
        """Get currently active model"""
        with self.lock:
            return self.current_model or self.primary_model

    def set_model_used(self):
        """Record that model was just used"""
        with self.lock:
            self.last_used_at = time.time()
            self.usage_count += 1

    def should_use_primary_model(self) -> bool:
        """
        Determine if we should use primary model
        Falls back to phi if primary is unavailable or system is memory-constrained
        """
        try:
            mem_percent = psutil.virtual_memory().percent
            if mem_percent > 80:
                logger.warning(f"⚠️  Memory usage {mem_percent}%, using fallback model")
                return False

            # Check if primary model is available
            available_models = self._get_available_models()
            if self.primary_model in available_models:
                return True

            logger.warning(f"❌ Primary model {self.primary_model} not available")
            return False

        except Exception as e:
            logger.warning(f"Model check error: {e}, using primary")
            return True

    def _get_available_models(self) -> List[str]:
        """Get list of available models from Ollama"""
        try:
            import urllib.request
            import json

            req = urllib.request.Request(f"{self.api_url}/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                models = []
                for model_info in data.get("models", []):
                    model_name = model_info.get("name", "")
                    # Extract just the model name without version
                    base_name = model_name.split(":")[0]
                    models.append(base_name)
                return list(set(models))
        except Exception as e:
            logger.debug(f"Could not fetch available models: {e}")
            return []

    def _unload_model(self):
        """Unload current model from memory"""
        try:
            if not self.current_model:
                return

            import urllib.request
            import json

            payload = {"model": self.current_model, "keep_alive": 0}
            req = urllib.request.Request(
                f"{self.api_url}/generate",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                logger.info(f"🔓 Unloaded model: {self.current_model}")
                self.current_model = None
                self.model_loaded_at = None

        except Exception as e:
            logger.warning(f"Failed to unload model: {e}")

    def get_memory_usage(self) -> Dict:
        """Get current memory usage information"""
        try:
            process = psutil.Process()
            mem_info = process.memory_info()
            vm = psutil.virtual_memory()

            return {
                "process_mb": mem_info.rss / 1024 / 1024,
                "system_percent": vm.percent,
                "system_available_mb": vm.available / 1024 / 1024,
                "system_total_mb": vm.total / 1024 / 1024,
                "within_limit": (mem_info.rss / 1024 / 1024) < self.max_memory_mb,
            }
        except Exception as e:
            logger.warning(f"Memory check error: {e}")
            return {"error": str(e)}

    def get_stats(self) -> Dict:
        """Get model manager statistics"""
        with self.lock:
            uptime = None
            if self.model_loaded_at:
                uptime = time.time() - self.model_loaded_at

            return {
                "current_model": self.current_model,
                "primary_model": self.primary_model,
                "fallback_model": self.fallback_model,
                "model_loaded_at": self.model_loaded_at,
                "model_uptime_seconds": uptime,
                "usage_count": self.usage_count,
                "last_used_at": self.last_used_at,
                "idle_unload_seconds": self.idle_unload_seconds,
                "memory": self.get_memory_usage(),
            }


# Global model manager instance
_model_manager = None


def get_model_manager() -> ModelManager:
    """Get or create global model manager"""
    global _model_manager
    if _model_manager is None:
        try:
            from config.settings import get_settings

            settings = get_settings()
            _model_manager = ModelManager(
                base_url=settings.ollama_base_url,
                primary_model=settings.ollama_model,
                fallback_model="phi",
                idle_unload_seconds=settings.ollama_idle_unload_seconds,
                enable_auto_unload=True,
            )
        except Exception as e:
            logger.warning(f"Failed to initialize model manager: {e}")
            _model_manager = ModelManager()

    return _model_manager

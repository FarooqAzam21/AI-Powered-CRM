"""
AI Module - PHASE 5 OPTIMIZATION
Production-grade AI system optimized for 4GB RAM systems

Exports:
- AIResponseGenerator: Main interface for AI generation
- AIResponseCache: Redis-based response caching
- TokenCompressor: Aggressive token compression
- ContextWindowManager: Context management
- ModelManager: Model lifecycle management
- OllamaWarmer: Model preloading
"""

from ai.ai_generator import AIResponseGenerator, get_ai_generator
from ai.ai_response_cache import AIResponseCache, get_ai_cache
from ai.token_compressor import TokenCompressor
from ai.context_window_manager import ContextWindowManager, PromptOptimizer
from ai.model_manager import ModelManager, get_model_manager
from ai.ollama_warmer import OllamaWarmer, warmup_ollama_sync
from ai.local_model_config import LocalModelConfig, get_local_model_config

__all__ = [
    "AIResponseGenerator",
    "get_ai_generator",
    "AIResponseCache",
    "get_ai_cache",
    "TokenCompressor",
    "ContextWindowManager",
    "PromptOptimizer",
    "ModelManager",
    "get_model_manager",
    "OllamaWarmer",
    "warmup_ollama_sync",
    "LocalModelConfig",
    "get_local_model_config",
]


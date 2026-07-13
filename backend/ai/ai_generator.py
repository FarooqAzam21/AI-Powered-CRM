"""
Legacy AI Generator Wrapper
Provides backwards compatibility for legacy routers after the Phase 2-12 Multi-Agent refactoring.
"""
from ai.services.ai_engine import get_ai_engine

def get_ai_generator():
    """
    Returns the central AIEngine which has legacy methods (e.g. generate_reply) 
    built-in for backwards compatibility.
    """
    return get_ai_engine()

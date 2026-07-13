"""
Legacy Ollama Client Wrapper
Provides backwards compatibility for Phase 6/7 services after the Phase 2-12 Multi-Agent refactoring.
"""
from ai.services.ai_engine import get_ai_engine
from ai.parser.json_parser import ResponseParser

async def generate_cached(prompt: str, **kwargs) -> str:
    """
    Legacy method for cached AI generation.
    Routes through the new AIEngine provider which handles caching natively.
    """
    engine = get_ai_engine()
    # Extract kwargs that might have been passed in legacy code
    system_prompt = kwargs.get('system_prompt', None)
    return await engine.provider.generate(prompt, system_prompt=system_prompt)

async def generate_classification(prompt: str, **kwargs) -> dict:
    """
    Legacy method for JSON classification generation.
    Routes through the new AIEngine provider.
    """
    engine = get_ai_engine()
    return await ResponseParser.parse_with_retry(
        llm_callable=engine.provider.generate,
        initial_prompt=prompt,
        fallback_response={"category": "unknown", "priority": "medium"}
    )

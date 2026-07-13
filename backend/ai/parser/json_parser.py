import json
import logging
from typing import Callable, Awaitable, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ResponseParser:
    """
    Enforces strict JSON parsing on LLM outputs.
    Automatically retries with error feedback if the LLM returns invalid JSON.
    """

    @staticmethod
    async def parse_with_retry(
        llm_callable: Callable[[str], Awaitable[str]],
        initial_prompt: str,
        max_retries: int = 3,
        fallback_response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes `llm_callable` with `initial_prompt`. If it returns invalid JSON,
        it appends the error to the prompt and retries up to `max_retries` times.
        """
        current_prompt = initial_prompt

        for attempt in range(max_retries):
            try:
                response_text = await llm_callable(current_prompt)
                return ResponseParser._extract_json(response_text)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse JSON on attempt {attempt + 1}: {e}")
                
                # Append error feedback to the prompt for the next attempt
                error_feedback = (
                    f"\n\n--- SYSTEM ERROR ON PREVIOUS ATTEMPT ---\n"
                    f"Your previous response failed to parse as valid JSON. Error: {str(e)}\n"
                    f"Ensure you return ONLY a raw JSON object, without any markdown formatting, preambles, or explanations."
                )
                current_prompt = initial_prompt + error_feedback

        logger.error(f"Exhausted {max_retries} retries. Returning fallback response.")
        return fallback_response or {}

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        """
        Attempts to find and parse a JSON object from the raw text.
        """
        text = text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
            
        if text.endswith("```"):
            text = text[:-3]
            
        text = text.strip()
        
        # Try to parse
        return json.loads(text)

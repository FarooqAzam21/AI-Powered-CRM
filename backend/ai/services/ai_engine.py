import logging
from typing import Dict, Any, Optional, AsyncIterator

from config.settings import get_settings
from ai.providers.base_provider import BaseProvider
from ai.providers.ollama_provider import OllamaProvider
from ai.context.context_builder import get_context_builder
from ai.prompts.prompt_manager import get_prompt_manager
from ai.parser.json_parser import ResponseParser
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class AIEngine:
    """
    Core AI Engine.
    All CRM modules MUST communicate ONLY with this class.
    It routes requests to the configured provider (e.g., Ollama) and manages the AI lifecycle.
    """

    def __init__(self):
        settings = get_settings()
        self.provider_name = settings.ai_provider.lower()
        self.provider: BaseProvider = self._initialize_provider()
        self._register_agents()

    def _register_agents(self):
        from ai.agents.agent_registry import get_agent_registry
        from ai.agents.specialized import (
            EmailAgent, SalesAgent, HiringAgent, SupportAgent,
            MarketingAgent, AnalyticsAgent, KnowledgeAgent
        )
        registry = get_agent_registry()
        registry.register(EmailAgent)
        registry.register(SalesAgent)
        registry.register(HiringAgent)
        registry.register(SupportAgent)
        registry.register(MarketingAgent)
        registry.register(AnalyticsAgent)
        registry.register(KnowledgeAgent)
        logger.info("All specialized AI agents registered.")

    def _initialize_provider(self) -> BaseProvider:
        if self.provider_name == "ollama":
            return OllamaProvider()
        # Future providers (e.g. fine_tuned_model) can be added here
        logger.warning(f"Unknown provider '{self.provider_name}', falling back to Ollama.")
        return OllamaProvider()

    async def health_check(self) -> bool:
        return await self.provider.health_check()

    # =========================================================================
    # Phase 2+ Agent Routing: The new multi-agent architecture uses this method.
    # It delegates entirely to the AgentRouter.
    # =========================================================================

    async def execute_agent(self, task_type: str, payload: Dict[str, Any], db: Session, contact_id: int = None, user_id: int = None):
        """
        Delegates the task to the correct specialized agent via AgentRouter.
        """
        from ai.agents.agent_router import get_agent_router
        from ai.agents.agent_context import AgentContext
        
        ctx = AgentContext(
            task_type=task_type,
            payload=payload,
            contact_id=contact_id,
            user_id=user_id
        )
        router = get_agent_router()
        return await router.route_task(ctx, db)

    # =========================================================================
    # Legacy Direct Methods
    # These remain for backwards compatibility so CRM features do not break.
    # =========================================================================

    async def generate_reply(self, db: Session, contact_id: int | None, email_body: str, tone: str = "professional") -> str:
        context_builder = get_context_builder()
        context = context_builder.build_context(db, contact_id, query=email_body)
        pm = get_prompt_manager()
        prompt = pm.render("reply_generation", tone=tone, email_body=email_body, crm_context=context)
        return await self.provider.generate(prompt)

    async def stream_reply(self, db: Session, contact_id: int, email_body: str, tone: str = "professional") -> AsyncIterator[str]:
        """Streams the generated reply token by token."""
        context_builder = get_context_builder()
        context = context_builder.build_context(db, contact_id, query=email_body)
        pm = get_prompt_manager()
        prompt = pm.render("reply_generation", tone=tone, email_body=email_body, crm_context=context)
        
        async for token in self.provider.stream_generate(prompt):
            yield token

    async def classify_email(self, subject: str, body: str) -> Dict[str, Any]:
        pm = get_prompt_manager()
        prompt = pm.render("email_classification", subject=subject, body=body)
        return await ResponseParser.parse_with_retry(
            llm_callable=self.provider.generate,
            initial_prompt=prompt,
            fallback_response={"category": "generic"}
        )

    async def score_lead(self, contact_info: Dict[str, Any]) -> Dict[str, Any]:
        pm = get_prompt_manager()
        prompt = pm.render("lead_scoring", contact_info=contact_info)
        return await ResponseParser.parse_with_retry(
            llm_callable=self.provider.generate,
            initial_prompt=prompt,
            fallback_response={"score": 0, "label": "cold"}
        )

    async def summarize_email(self, body: str) -> str:
        prompt = f"Summarize this email concisely: {body}"
        return await self.provider.generate(prompt)

    async def summarize_thread(self, thread_messages: list) -> str:
        prompt = f"Summarize this email thread: {thread_messages}"
        return await self.provider.generate(prompt)

    async def extract_candidate(self, resume_text: str) -> str:
        prompt = f"Extract candidate skills and experience from this resume: {resume_text}"
        return await self.provider.generate(prompt)

    async def analyze_sentiment(self, text: str) -> str:
        prompt = f"Analyze the sentiment of this text (Positive/Neutral/Negative): {text}"
        return await self.provider.generate(prompt)

    async def generate_followup(self, db: Session, contact_id: int, previous_interaction: str) -> str:
        context_builder = get_context_builder()
        context = context_builder.build_context(db, contact_id, query=previous_interaction)
        pm = get_prompt_manager()
        prompt = pm.render("followup_generation", previous_interaction=previous_interaction, crm_context=context)
        return await self.provider.generate(prompt)

    async def generate_customer_profile(self, activities: list) -> str:
        prompt = f"Create a brief customer profile based on these activities: {activities}"
        return await self.provider.generate(prompt)

    async def predict_next_action(self, history: list) -> str:
        prompt = f"Predict the next best action for the sales team based on this history: {history}"
        return await self.provider.generate(prompt)

    async def generate_campaign(self, goal: str, target_audience: str) -> str:
        prompt = f"Generate an email campaign. Goal: {goal}. Audience: {target_audience}."
        return await self.provider.generate(prompt)

    async def generate_meeting_notes(self, transcript: str) -> str:
        prompt = f"Generate meeting notes and action items from this transcript: {transcript}"
        return await self.provider.generate(prompt)


# Singleton pattern for the engine
_engine = None

def get_ai_engine() -> AIEngine:
    global _engine
    if _engine is None:
        _engine = AIEngine()
    return _engine

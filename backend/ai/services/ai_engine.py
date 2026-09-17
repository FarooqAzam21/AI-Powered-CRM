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
        try:
            context_builder = get_context_builder()
            context = context_builder.build_context(db, contact_id, query=email_body)
            pm = get_prompt_manager()
            prompt = pm.render("reply_generation", tone=tone, email_body=email_body, crm_context=context)
            return await self.provider.generate(prompt)
        except Exception as e:
            logger.warning("AI provider generation failed (%s). Using fallback reply generator.", e)
            return self._build_fallback_reply(db, contact_id, email_body, tone)

    async def stream_reply(self, db: Session, contact_id: int, email_body: str, tone: str = "professional") -> AsyncIterator[str]:
        """Streams the generated reply token by token."""
        try:
            context_builder = get_context_builder()
            context = context_builder.build_context(db, contact_id, query=email_body)
            pm = get_prompt_manager()
            prompt = pm.render("reply_generation", tone=tone, email_body=email_body, crm_context=context)
            
            async for token in self.provider.stream_generate(prompt):
                yield token
        except Exception as e:
            logger.warning("AI stream generation failed (%s). Using fallback reply stream.", e)
            fallback = self._build_fallback_reply(db, contact_id, email_body, tone)
            for word in fallback.split(" "):
                yield word + " "

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
        try:
            context_builder = get_context_builder()
            context = context_builder.build_context(db, contact_id, query=previous_interaction)
            pm = get_prompt_manager()
            prompt = pm.render("followup_generation", previous_interaction=previous_interaction, crm_context=context)
            return await self.provider.generate(prompt)
        except Exception as e:
            logger.warning("AI followup generation failed (%s). Using fallback followup.", e)
            return self._build_fallback_reply(db, contact_id, previous_interaction, "professional")

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

    def _build_fallback_reply(self, db: Session, contact_id: int | None, email_body: str, tone: str = "professional") -> str:
        contact_name = "there"
        if contact_id and db:
            try:
                from models.crm_unified import Contact
                contact = db.query(Contact).filter(Contact.id == contact_id).first()
                if contact:
                    if getattr(contact, "first_name", None):
                        contact_name = contact.first_name
                    elif getattr(contact, "name", None):
                        contact_name = contact.name.split()[0]
            except Exception:
                pass

        tone_lower = (tone or "professional").lower()
        body_lower = (email_body or "").lower()

        is_pricing = any(k in body_lower for k in ["price", "pricing", "cost", "quote", "rate", "budget"])
        is_demo = any(k in body_lower for k in ["demo", "walkthrough", "presentation", "meeting", "call", "schedule"])
        is_support = any(k in body_lower for k in ["issue", "problem", "bug", "error", "help", "support", "broken"])

        if is_pricing:
            if tone_lower == "friendly":
                return (
                    f"Hi {contact_name}!\n\n"
                    f"Thanks for asking about our pricing options! We offer tailored packages designed to fit your team's specific goals and scale.\n\n"
                    f"I would love to walk you through our tiers and find the best fit for your needs. Would you have a few minutes for a quick chat this week?\n\n"
                    f"Looking forward to connecting!\n\nBest,\nSales Team"
                )
            elif tone_lower == "urgent":
                return (
                    f"Hello {contact_name},\n\n"
                    f"Thank you for contacting us regarding pricing. We understand this is time-sensitive and are expediting our quotation for you.\n\n"
                    f"I will follow up shortly with our detailed pricing breakdown. In the meantime, please let us know if there are specific volume requirements we should account for.\n\n"
                    f"Regards,\nSales Management"
                )
            else:
                return (
                    f"Dear {contact_name},\n\n"
                    f"Thank you for your interest in our solutions and for requesting pricing information.\n\n"
                    f"Our pricing is structured to deliver maximum ROI based on your team's size and feature requirements. I am preparing an overview tailored to your needs and will share it with you shortly.\n\n"
                    f"Please let me know if you would like to schedule a brief consultation to review the options together.\n\n"
                    f"Best regards,\nAccount Executive"
                )
        elif is_demo:
            if tone_lower == "friendly":
                return (
                    f"Hi {contact_name}!\n\n"
                    f"We'd love to show you a demo of our platform in action! There are so many exciting features that can help streamline your workflows.\n\n"
                    f"Feel free to reply with a day and time that works best for you, or let me know and I'll send over a calendar invite.\n\n"
                    f"Cheers,\nCustomer Success Team"
                )
            elif tone_lower == "urgent":
                return (
                    f"Hello {contact_name},\n\n"
                    f"Thank you for reaching out to schedule a demonstration. We have prioritized your request and are ready to accommodate your schedule promptly.\n\n"
                    f"Please let us know your availability today or tomorrow so we can lock in a session right away.\n\n"
                    f"Sincerely,\nProduct Solutions Team"
                )
            else:
                return (
                    f"Dear {contact_name},\n\n"
                    f"Thank you for requesting a demonstration of our platform.\n\n"
                    f"We would be delighted to guide you through key capabilities and demonstrate how our AI-powered features can optimize your operations. Please let me know your preferred availability over the coming days so we can coordinate a suitable time.\n\n"
                    f"Best regards,\nSolutions Consultant"
                )
        elif is_support:
            if tone_lower == "friendly":
                return (
                    f"Hi {contact_name}!\n\n"
                    f"Thanks for letting us know about this! We're here to help get everything sorted for you as quickly as possible.\n\n"
                    f"Our technical team is already looking into the details you provided. I'll stay on top of this and update you as soon as we make progress.\n\n"
                    f"Best,\nCustomer Support"
                )
            else:
                return (
                    f"Dear {contact_name},\n\n"
                    f"Thank you for contacting support regarding your issue.\n\n"
                    f"We have registered your ticket and our engineering team is actively investigating. We will provide an update as soon as we have identified the resolution.\n\n"
                    f"If you have any supplementary details or screenshots, please feel free to send them over.\n\n"
                    f"Sincerely,\nTechnical Support Team"
                )
        else:
            if tone_lower == "friendly":
                return (
                    f"Hi {contact_name}!\n\n"
                    f"Thanks so much for reaching out! I've reviewed your message and wanted to get back to you right away.\n\n"
                    f"Everything looks good on our end, and I am gathering the necessary details to answer your questions thoroughly. I'll be in touch with an update very soon!\n\n"
                    f"Best regards,\nCustomer Success Team"
                )
            elif tone_lower == "urgent":
                return (
                    f"Hello {contact_name},\n\n"
                    f"Thank you for your message. We have flagged your request as a top priority and are reviewing the details immediately.\n\n"
                    f"You can expect a direct follow-up shortly with the next steps.\n\n"
                    f"Best regards,\nOperations Team"
                )
            else:
                return (
                    f"Dear {contact_name},\n\n"
                    f"Thank you for getting in touch with us.\n\n"
                    f"I have received your email and am reviewing the details. I will follow up shortly with the requested information to ensure we address all your points thoroughly.\n\n"
                    f"Please do not hesitate to reach out if you have any immediate questions in the meantime.\n\n"
                    f"Best regards,\nAccount Management Team"
                )


# Singleton pattern for the engine
_engine = None

def get_ai_engine() -> AIEngine:
    global _engine
    if _engine is None:
        _engine = AIEngine()
    return _engine

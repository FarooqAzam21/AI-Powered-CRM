"""
EmailAgent — Handles all email-related AI tasks.
"""
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from ai.agents.base_agent import BaseAgent
from ai.agents.agent_context import AgentContext

logger = logging.getLogger(__name__)


class EmailAgent(BaseAgent):
    agent_name = "email_agent"
    supported_tasks = [
        "classify_email",
        "generate_reply",
        "summarize_thread",
        "detect_urgency"
    ]

    async def prepare_context(self, ctx: AgentContext, db: Session) -> str:
        """
        Build CRM context only if we need it (e.g. for generating replies).
        """
        if ctx.task_type == "generate_reply" and ctx.contact_id:
            return self.context_builder.build_context(db, ctx.contact_id, query=ctx.payload.get("email_body"))
        
        # Other tasks like classification might just need basic contact info or none
        if ctx.contact_id:
            return self.context_builder.build_context(db, ctx.contact_id)
        return ""

    async def build_prompt(self, ctx: AgentContext, crm_context: str) -> str:
        """
        Render the appropriate template for the task.
        """
        if ctx.task_type == "classify_email":
            return self.prompt_manager.render(
                "agents/email_classify", 
                subject=ctx.payload.get("subject"), 
                body=ctx.payload.get("body")
            )
        
        elif ctx.task_type == "generate_reply":
            return self.prompt_manager.render(
                "agents/email_reply", 
                email_body=ctx.payload.get("email_body"), 
                tone=ctx.payload.get("tone", "professional"),
                crm_context=crm_context
            )
            
        elif ctx.task_type == "summarize_thread":
            return self.prompt_manager.render(
                "agents/email_summarize", 
                thread_messages=ctx.payload.get("thread_messages")
            )
            
        elif ctx.task_type == "detect_urgency":
            return self.prompt_manager.render(
                "agents/email_urgency", 
                subject=ctx.payload.get("subject"), 
                body=ctx.payload.get("body")
            )

        raise ValueError(f"Unknown task type for EmailAgent: {ctx.task_type}")

    async def validate(self, raw_output: str, ctx: AgentContext) -> Dict[str, Any]:
        """
        Parse and validate LLM output.
        Classification and Urgency require JSON parsing. If it fails, let it raise 
        so BaseAgent catches it and retries.
        Reply and Summarize return raw strings wrapped in a dict.
        """
        if ctx.task_type in ["classify_email", "detect_urgency"]:
            # This will raise JSONDecodeError or ValueError if invalid, triggering a retry
            return self.parser._extract_json(raw_output)
                
        # For non-JSON tasks, wrap in a data dict
        return {"result": raw_output}

    async def update_memory(self, result_data: Dict[str, Any], ctx: AgentContext, db: Session):
        """
        Update memory after task.
        E.g. if we generate a reply, we can append a summary of it to memory.
        """
        if ctx.task_type == "generate_reply" and ctx.contact_id:
            memory = self._get_agent_memory(db, ctx.contact_id)
            if memory:
                summary = f"Sent email reply regarding: {ctx.payload.get('email_body')[:50]}..."
                memory.append_summary(self.agent_name, summary)

"""
SupportAgent — Handles customer support related AI tasks.
"""
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from ai.agents.base_agent import BaseAgent
from ai.agents.agent_context import AgentContext

logger = logging.getLogger(__name__)


class SupportAgent(BaseAgent):
    agent_name = "support_agent"
    supported_tasks = [
        "classify_issue",
        "detect_escalation",
        "suggest_solution"
    ]

    async def prepare_context(self, ctx: AgentContext, db: Session) -> str:
        if ctx.contact_id:
            return self.context_builder.build_context(db, ctx.contact_id)
        return ""

    async def build_prompt(self, ctx: AgentContext, crm_context: str) -> str:
        if ctx.task_type == "classify_issue":
            return self.prompt_manager.render(
                "agents/support_classify", 
                issue_text=ctx.payload.get("issue_text"),
                crm_context=crm_context
            )
            
        elif ctx.task_type == "detect_escalation":
            return self.prompt_manager.render(
                "agents/support_escalation", 
                issue_text=ctx.payload.get("issue_text"),
                crm_context=crm_context
            )
            
        elif ctx.task_type == "suggest_solution":
            return self.prompt_manager.render(
                "agents/support_solution", 
                issue_text=ctx.payload.get("issue_text"),
                crm_context=crm_context
            )

        raise ValueError(f"Unknown task type for SupportAgent: {ctx.task_type}")

    async def validate(self, raw_output: str, ctx: AgentContext) -> Dict[str, Any]:
        """
        Support tasks return JSON (classifications, escalation flags, solutions).
        """
        return self.parser._extract_json(raw_output)

    async def update_memory(self, result_data: Dict[str, Any], ctx: AgentContext, db: Session):
        """
        Update memory with support history.
        """
        if ctx.task_type == "classify_issue" and ctx.contact_id:
            memory = self._get_agent_memory(db, ctx.contact_id)
            if memory and "category" in result_data:
                memory.update({"support_history": [f"Reported issue: {result_data['category']}"]})

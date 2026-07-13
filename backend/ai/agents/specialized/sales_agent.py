"""
SalesAgent — Handles sales and pipeline related AI tasks.
"""
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from ai.agents.base_agent import BaseAgent
from ai.agents.agent_context import AgentContext

logger = logging.getLogger(__name__)


class SalesAgent(BaseAgent):
    agent_name = "sales_agent"
    supported_tasks = [
        "score_lead",
        "detect_intent",
        "predict_next_action",
        "revenue_insights"
    ]

    async def prepare_context(self, ctx: AgentContext, db: Session) -> str:
        """
        Sales tasks heavily rely on CRM context.
        """
        if ctx.contact_id:
            return self.context_builder.build_context(db, ctx.contact_id)
        return ""

    async def build_prompt(self, ctx: AgentContext, crm_context: str) -> str:
        if ctx.task_type == "score_lead":
            return self.prompt_manager.render(
                "agents/sales_score", 
                contact_info=ctx.payload,
                crm_context=crm_context
            )
            
        elif ctx.task_type == "detect_intent":
            return self.prompt_manager.render(
                "agents/sales_intent", 
                recent_activity=ctx.payload.get("recent_activity"),
                crm_context=crm_context
            )
            
        elif ctx.task_type == "predict_next_action":
            return self.prompt_manager.render(
                "agents/sales_next_action", 
                history=ctx.payload.get("history"),
                crm_context=crm_context
            )

        elif ctx.task_type == "revenue_insights":
            return self.prompt_manager.render(
                "agents/sales_revenue", 
                pipeline_data=ctx.payload.get("pipeline_data")
            )

        raise ValueError(f"Unknown task type for SalesAgent: {ctx.task_type}")

    async def validate(self, raw_output: str, ctx: AgentContext) -> Dict[str, Any]:
        """
        All sales tasks return structured JSON (scores, recommended actions).
        Will raise an exception if invalid JSON, triggering BaseAgent to retry.
        """
        return self.parser._extract_json(raw_output)

    async def update_memory(self, result_data: Dict[str, Any], ctx: AgentContext, db: Session):
        """
        Update memory with buying signals if intent is detected.
        """
        if ctx.task_type == "detect_intent" and ctx.contact_id:
            memory = self._get_agent_memory(db, ctx.contact_id)
            if memory and "buying_signals" in result_data:
                memory.update({"buying_signals": result_data["buying_signals"]})

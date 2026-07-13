"""
MarketingAgent — Handles marketing and campaign related AI tasks.
"""
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from ai.agents.base_agent import BaseAgent
from ai.agents.agent_context import AgentContext

logger = logging.getLogger(__name__)


class MarketingAgent(BaseAgent):
    agent_name = "marketing_agent"
    supported_tasks = [
        "generate_campaign",
        "optimize_cta",
        "segment_audience"
    ]

    async def prepare_context(self, ctx: AgentContext, db: Session) -> str:
        if ctx.contact_id:
            return self.context_builder.build_context(db, ctx.contact_id)
        return ""

    async def build_prompt(self, ctx: AgentContext, crm_context: str) -> str:
        if ctx.task_type == "generate_campaign":
            return self.prompt_manager.render(
                "agents/marketing_campaign", 
                goal=ctx.payload.get("goal"),
                target_audience=ctx.payload.get("target_audience")
            )
            
        elif ctx.task_type == "optimize_cta":
            return self.prompt_manager.render(
                "agents/marketing_cta", 
                copy=ctx.payload.get("copy")
            )
            
        elif ctx.task_type == "segment_audience":
            return self.prompt_manager.render(
                "agents/marketing_segment", 
                audience_data=ctx.payload.get("audience_data"),
                criteria=ctx.payload.get("criteria")
            )

        raise ValueError(f"Unknown task type for MarketingAgent: {ctx.task_type}")

    async def validate(self, raw_output: str, ctx: AgentContext) -> Dict[str, Any]:
        """
        Marketing tasks return JSON (campaign copy, CTAs, segments).
        """
        return self.parser._extract_json(raw_output)

    async def update_memory(self, result_data: Dict[str, Any], ctx: AgentContext, db: Session):
        """
        Update memory with campaign history.
        """
        if ctx.task_type == "generate_campaign" and ctx.contact_id:
            memory = self._get_agent_memory(db, ctx.contact_id)
            if memory and "subject" in result_data:
                memory.update({"campaign_history": [f"Sent campaign: {result_data['subject']}"]})

"""
AnalyticsAgent — Handles data analysis, KPI summary, and trends detection.
"""
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from ai.agents.base_agent import BaseAgent
from ai.agents.agent_context import AgentContext

logger = logging.getLogger(__name__)


class AnalyticsAgent(BaseAgent):
    agent_name = "analytics_agent"
    supported_tasks = [
        "summarize_kpis",
        "identify_trends",
        "explain_dashboard"
    ]

    async def prepare_context(self, ctx: AgentContext, db: Session) -> str:
        # Analytics doesn't usually use individual CRM contact context.
        return ""

    async def build_prompt(self, ctx: AgentContext, crm_context: str) -> str:
        if ctx.task_type == "summarize_kpis":
            return self.prompt_manager.render(
                "agents/analytics_kpi", 
                metrics=ctx.payload.get("metrics")
            )
            
        elif ctx.task_type == "identify_trends":
            return self.prompt_manager.render(
                "agents/analytics_trends", 
                data_series=ctx.payload.get("data_series")
            )
            
        elif ctx.task_type == "explain_dashboard":
            return self.prompt_manager.render(
                "agents/analytics_dashboard", 
                dashboard_data=ctx.payload.get("dashboard_data")
            )

        raise ValueError(f"Unknown task type for AnalyticsAgent: {ctx.task_type}")

    async def validate(self, raw_output: str, ctx: AgentContext) -> Dict[str, Any]:
        """
        Analytics returns structured JSON insights.
        """
        return self.parser._extract_json(raw_output)

    async def update_memory(self, result_data: Dict[str, Any], ctx: AgentContext, db: Session):
        pass # Analytics typically doesn't update individual customer memory

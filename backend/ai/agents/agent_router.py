"""
AgentRouter — Intelligent routing layer for the AI Engine.
Delegates tasks to the correct specialized agent.
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from ai.agents.agent_context import AgentContext
from ai.agents.agent_result import AgentResult, AgentStatus
from ai.agents.agent_registry import get_agent_registry

logger = logging.getLogger(__name__)

class AgentRouter:
    def __init__(self):
        self.registry = get_agent_registry()

    async def route_task(self, ctx: AgentContext, db: Session) -> AgentResult:
        """
        Routes a task to the appropriate agent based on task_type.
        """
        logger.info(f"AgentRouter routing task: {ctx.task_type}")
        agent = self.registry.get_agent_for_task(ctx.task_type)
        
        if not agent:
            error_msg = f"No agent registered for task type: {ctx.task_type}"
            logger.error(error_msg)
            return AgentResult(
                agent_name="AgentRouter",
                task_type=ctx.task_type,
                status=AgentStatus.FAILED,
                data={},
                error=error_msg,
                contact_id=ctx.contact_id
            )
            
        return await agent.run(ctx, db)

# Singleton instance
_router = AgentRouter()

def get_agent_router() -> AgentRouter:
    return _router

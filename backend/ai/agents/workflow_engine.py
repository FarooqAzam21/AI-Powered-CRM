"""
WorkflowEngine — Multi-agent chain orchestrator.
Allows multiple agents to collaborate sequentially, passing context to each other.
"""
import uuid
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from ai.agents.agent_context import AgentContext
from ai.agents.agent_result import AgentResult, AgentStatus, WorkflowState
from ai.agents.agent_router import get_agent_router

logger = logging.getLogger(__name__)

class WorkflowEngine:
    def __init__(self):
        self.router = get_agent_router()

    async def execute_workflow(
        self, 
        trigger: str,
        tasks: List[Dict[str, Any]], 
        db: Session,
        contact_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> WorkflowState:
        """
        Executes a sequence of agent tasks.
        Each task payload can optionally use results from previous tasks.
        
        Args:
            trigger: Identifier for what started this workflow (e.g. 'new_email')
            tasks: List of dicts, each specifying:
                   - 'task_type': str
                   - 'payload': Dict (initial payload for this step)
        """
        workflow_id = str(uuid.uuid4())
        state = WorkflowState(
            workflow_id=workflow_id,
            trigger=trigger,
            contact_id=contact_id,
            steps=[t['task_type'] for t in tasks]
        )
        
        logger.info(f"Starting workflow {workflow_id} ({trigger}) with {len(tasks)} steps.")
        
        upstream_results = []
        
        for step_idx, task_def in enumerate(tasks):
            task_type = task_def['task_type']
            payload = task_def.get('payload', {})
            
            ctx = AgentContext(
                task_type=task_type,
                payload=payload,
                contact_id=contact_id,
                user_id=user_id,
                workflow_id=workflow_id,
                upstream_results=upstream_results
            )
            
            logger.info(f"Workflow {workflow_id} executing step {step_idx + 1}/{len(tasks)}: {task_type}")
            
            result: AgentResult = await self.router.route_task(ctx, db)
            state.add_result(result)
            
            if result.status == AgentStatus.FAILED:
                logger.error(f"Workflow {workflow_id} aborted at step {step_idx + 1} due to agent failure.")
                state.status = "failed"
                break
                
            # Add successful result to upstream for the next agent
            upstream_results.append(result.to_dict())
            
        logger.info(f"Workflow {workflow_id} finished with status: {state.status}")
        return state

# Singleton instance
_engine = WorkflowEngine()

def get_workflow_engine() -> WorkflowEngine:
    return _engine

import logging
import asyncio
from typing import Dict, Any, List

from tasks.celery_app import celery_app
from database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(name="agents.execute_task", queue="ai")
def execute_agent_task_bg(task_type: str, payload: Dict[str, Any], contact_id: int = None, user_id: int = None):
    """
    Executes a single agent task in the background via Celery.
    """
    from ai.services.ai_engine import get_ai_engine
    
    db = SessionLocal()
    try:
        engine = get_ai_engine()
        result = asyncio.run(engine.execute_agent(task_type, payload, db, contact_id=contact_id, user_id=user_id))
        
        if not result.is_success():
            logger.error(f"Agent task {task_type} failed in background: {result.error}")
            return {"status": "failed", "error": result.error}
            
        logger.info(f"Agent task {task_type} succeeded in background.")
        return result.to_dict()
    finally:
        db.close()


@celery_app.task(name="agents.execute_workflow", queue="ai")
def execute_agent_workflow_bg(trigger: str, tasks: List[Dict[str, Any]], contact_id: int = None, user_id: int = None):
    """
    Executes a multi-agent workflow sequentially in the background via Celery.
    """
    from ai.agents.workflow_engine import get_workflow_engine
    
    db = SessionLocal()
    try:
        engine = get_workflow_engine()
        state = asyncio.run(engine.execute_workflow(trigger, tasks, db, contact_id=contact_id, user_id=user_id))
        
        logger.info(f"Workflow {state.workflow_id} ({trigger}) finished with status: {state.status}")
        return state.to_dict()
    finally:
        db.close()

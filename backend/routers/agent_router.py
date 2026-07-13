from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from database import get_db
from ai.services.ai_engine import get_ai_engine
from ai.agents.workflow_engine import get_workflow_engine

router = APIRouter(prefix="/api/v1/agents", tags=["AI Agents"])

@router.post("/execute")
async def execute_agent_task(
    task_type: str,
    payload: Dict[str, Any],
    contact_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Executes a single agent task synchronously.
    """
    engine = get_ai_engine()
    result = await engine.execute_agent(task_type, payload, db, contact_id=contact_id)
    if not result.is_success():
        raise HTTPException(status_code=500, detail=result.error)
    return result.to_dict()


@router.post("/workflow/sync")
async def execute_workflow_sync(
    trigger: str,
    tasks: List[Dict[str, Any]],
    contact_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Executes a multi-agent workflow sequentially and waits for the result.
    """
    engine = get_workflow_engine()
    state = await engine.execute_workflow(trigger, tasks, db, contact_id=contact_id)
    return state.to_dict()


@router.post("/workflow/async")
async def execute_workflow_async(
    trigger: str,
    tasks: List[Dict[str, Any]],
    background_tasks: BackgroundTasks,
    contact_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Kicks off a multi-agent workflow in the background using FastAPI BackgroundTasks.
    For more robust execution, Celery tasks are recommended.
    """
    engine = get_workflow_engine()
    
    async def run_bg():
        # Open a new session for the background task
        from database import SessionLocal
        bg_db = SessionLocal()
        try:
            await engine.execute_workflow(trigger, tasks, bg_db, contact_id=contact_id)
        finally:
            bg_db.close()
            
    background_tasks.add_task(run_bg)
    return {"status": "started", "trigger": trigger, "steps": len(tasks)}

from fastapi import APIRouter, HTTPException

from tasks.task_status import get_task

router = APIRouter(prefix="/tasks", tags=["AI Tasks"])


@router.get("/{task_id}")
def task_status(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task

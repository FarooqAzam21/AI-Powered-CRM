import json
import uuid
from datetime import datetime

from cache.redis_client import cache_json, get_cached_json

TASK_TTL = 86400


def new_task(queue: str, task_type: str, payload=None, user_id=None) -> dict:
    task = {
        "id": uuid.uuid4().hex,
        "queue": queue,
        "task_type": task_type,
        "status": "queued",
        "progress": 0,
        "payload": payload or {},
        "result": None,
        "error": None,
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    cache_json(f"task:{task['id']}", task, TASK_TTL)
    return task


def update_task(task_id: str, **updates) -> dict:
    task = get_task(task_id) or {"id": task_id}
    task.update(updates)
    task["updated_at"] = datetime.utcnow().isoformat()
    cache_json(f"task:{task_id}", task, TASK_TTL)
    return task


def get_task(task_id: str):
    return get_cached_json(f"task:{task_id}")

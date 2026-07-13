import logging

from kombu.exceptions import OperationalError

from tasks.celery_app import CELERY_REDIS_AVAILABLE, celery_app
from tasks.task_status import get_task, new_task, update_task

logger = logging.getLogger(__name__)


def _run_local(task_name: str, task_id: str, payload: dict):
    local_tasks = {
        "workers.email_tasks.sync_gmail_metadata": ("workers.email_tasks", "_sync_gmail_metadata"),
        "workers.email_tasks.generate_reply": ("workers.email_tasks", "_generate_reply"),
        "workers.campaign_tasks.send_campaign": ("workers.campaign_tasks", "_send_campaign"),
    }
    target = local_tasks.get(task_name)
    if not target:
        update_task(
            task_id,
            status="deferred",
            progress=0,
            result={"message": "Task recorded locally; start Redis and Celery to process this queue."},
        )
        return

    module_name, function_name = target
    try:
        module = __import__(module_name, fromlist=[function_name])
        function = getattr(module, function_name)
        function(task_id, payload)
    except Exception as exc:
        update_task(task_id, status="failed", error=str(exc))
        raise


def enqueue_task(task_name: str, queue: str, payload=None, user_id=None) -> dict:
    task = new_task(queue=queue, task_type=task_name, payload=payload, user_id=user_id)
    if celery_app and CELERY_REDIS_AVAILABLE:
        try:
            celery_app.send_task(task_name, args=[task["id"], payload or {}], queue=queue)
            return task
        except OperationalError as exc:
            logger.warning("Celery broker unavailable; running %s locally: %s", task_name, exc)

    if queue in {"email", "ai", "campaigns"}:
        _run_local(task_name, task["id"], payload or {})
        return get_task(task["id"]) or task
    else:
        update_task(
            task["id"],
            status="deferred",
            progress=0,
            result={"message": "Redis/Celery is unavailable; task recorded for worker pickup."},
        )
    return get_task(task["id"]) or task

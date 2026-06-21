from tasks.celery_app import celery_app
from tasks.task_status import new_task, update_task


def enqueue_task(task_name: str, queue: str, payload=None, user_id=None) -> dict:
    task = new_task(queue=queue, task_type=task_name, payload=payload, user_id=user_id)
    if celery_app:
        celery_app.send_task(task_name, args=[task["id"], payload or {}], queue=queue)
    else:
        update_task(
            task["id"],
            status="deferred",
            progress=0,
            result={"message": "Celery is not installed/running; task recorded for worker pickup."},
        )
    return task

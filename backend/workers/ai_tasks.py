from tasks.celery_app import celery_app
from tasks.task_status import update_task


def _score_lead(task_id, payload):
    from services.crm_service import score_lead

    update_task(task_id, status="running", progress=30)
    result = score_lead(payload.get("text", ""), payload.get("interaction_count", 1))
    update_task(task_id, status="completed", progress=100, result=result)
    return result


if celery_app:
    score_lead = celery_app.task(name="workers.ai_tasks.score_lead")(_score_lead)
else:
    score_lead = _score_lead

from ai.ollama_client import generate_cached
from ai.prompt_optimizer import build_email_prompt
from config.settings import get_settings
from database import SessionLocal
from crm_email.incremental_sync import sync_metadata_page
from auth.models import User
from tasks.celery_app import celery_app
from tasks.task_status import update_task


def _sync_gmail_metadata(task_id, payload):
    db = SessionLocal()
    try:
        update_task(task_id, status="running", progress=10)
        user = db.query(User).filter(User.id == payload["user_id"]).first()
        result = sync_metadata_page(db, user, page_size=get_settings().gmail_page_size)
        update_task(task_id, status="completed", progress=100, result=result)
        return result
    except Exception as exc:
        update_task(task_id, status="failed", error=str(exc))
        raise
    finally:
        db.close()


def _generate_reply(task_id, payload):
    update_task(task_id, status="running", progress=20)
    prompt = build_email_prompt("Generate CRM email reply", payload.get("body", ""), payload.get("context", ""), payload.get("tone", "professional"))
    text = generate_cached(prompt)
    update_task(task_id, status="completed", progress=100, result={"draft": text})
    return {"draft": text}


if celery_app:
    sync_gmail_metadata = celery_app.task(name="workers.email_tasks.sync_gmail_metadata")(_sync_gmail_metadata)
    generate_reply = celery_app.task(name="workers.email_tasks.generate_reply")(_generate_reply)
else:
    sync_gmail_metadata = _sync_gmail_metadata
    generate_reply = _generate_reply

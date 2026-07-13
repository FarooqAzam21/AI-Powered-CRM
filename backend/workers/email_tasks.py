from config.settings import get_settings
from database import SessionLocal
from crm_email.incremental_sync import sync_metadata_page
from auth.models import User
from tasks.celery_app import celery_app
from tasks.task_status import update_task
import asyncio
from ai.services.ai_engine import get_ai_engine


def _sync_gmail_metadata(task_id, payload):
    db = SessionLocal()
    try:
        update_task(task_id, status="running", progress=10)
        user = db.query(User).filter(User.id == payload["user_id"]).first()
        result = sync_metadata_page(
            db,
            user,
            page_size=max(get_settings().gmail_page_size, 100) if payload.get("recent_first", True) else get_settings().gmail_page_size,
            recent_first=bool(payload.get("recent_first", True)),
        )
        update_task(task_id, status="completed", progress=100, result=result)
        return result
    except Exception as exc:
        update_task(task_id, status="failed", error=str(exc))
        raise
    finally:
        db.close()


def _generate_reply(task_id, payload):
    db = SessionLocal()
    try:
        update_task(task_id, status="running", progress=20)
        
        contact_id = payload.get("contact_id")
        email_body = payload.get("email_body")
        tone = payload.get("tone", "professional")
        
        engine = get_ai_engine()
        # Celery tasks are synchronous, so we run the async engine in an event loop
        reply = asyncio.run(engine.generate_reply(db, contact_id, email_body, tone))
        
        update_task(task_id, status="completed", progress=100, result={"draft": reply})
        return {"draft": reply}
    except Exception as exc:
        update_task(task_id, status="failed", error=str(exc))
        raise
    finally:
        db.close()


if celery_app:
    sync_gmail_metadata = celery_app.task(name="workers.email_tasks.sync_gmail_metadata")(_sync_gmail_metadata)
    generate_reply = celery_app.task(name="workers.email_tasks.generate_reply")(_generate_reply)
else:
    sync_gmail_metadata = _sync_gmail_metadata
    generate_reply = _generate_reply


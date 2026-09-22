"""
P5 — Workflow Celery Tasks
Async execution of workflow nodes with:
- Execution locking (Redis SETNX / in-memory fallback)
- Exponential backoff retries (max 5)
- Workspace isolation re-validation inside worker
- Idempotency via WorkflowExecution.idempotency_key
"""
import logging
from datetime import datetime
from typing import Optional

from celery import Task
from tasks.celery_app import celery_app
from database import SessionLocal

logger = logging.getLogger(__name__)

# ── Execution lock helpers (Redis preferred, dict fallback) ───────────────────

_memory_locks: dict = {}


def _acquire_lock(key: str, ttl_seconds: int = 600) -> bool:
    """Try to acquire an execution lock. Returns True if acquired."""
    try:
        from cache.redis_client import get_cache
        cache = get_cache()
        from cache.redis_client import MemoryCache
        if not isinstance(cache, MemoryCache):
            # Use Redis SETNX (set if not exists)
            import redis
            client = redis.Redis.from_url(
                __import__("os").getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
                socket_timeout=1,
            )
            return bool(client.set(f"wf_lock:{key}", "1", ex=ttl_seconds, nx=True))
    except Exception:
        pass
    # In-memory fallback
    if key in _memory_locks:
        return False
    _memory_locks[key] = True
    return True


def _release_lock(key: str):
    try:
        from cache.redis_client import get_cache
        cache = get_cache()
        from cache.redis_client import MemoryCache
        if not isinstance(cache, MemoryCache):
            import redis
            client = redis.Redis.from_url(
                __import__("os").getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
                socket_timeout=1,
            )
            client.delete(f"wf_lock:{key}")
            return
    except Exception:
        pass
    _memory_locks.pop(key, None)


# ── Main workflow execution task ──────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="tasks.workflow_tasks.execute_workflow_async",
    queue="workflow",
    max_retries=5,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
)
def execute_workflow_async(
    self: Task,
    *,
    workflow_id: int,
    execution_id: int,
    workspace_id: int,
    org_id: int,
) -> dict:
    """
    Execute a single workflow asynchronously.
    Workspace isolation is RE-VALIDATED from the database — never trusted from args.
    """
    lock_key = f"{execution_id}"

    if not _acquire_lock(lock_key):
        logger.info("Execution %d already locked — skipping duplicate", execution_id)
        return {"skipped": True, "reason": "lock_exists"}

    db = SessionLocal()
    try:
        # ── Import models here (Celery workers may not have app context) ───────
        from models.workflow import WorkflowExecution, Workflow
        from workflow.engine import WorkflowEngine

        # Re-validate workspace from DB — NEVER trust serialized task args
        execution = db.query(WorkflowExecution).filter(
            WorkflowExecution.id == execution_id
        ).first()

        if not execution:
            logger.error("Execution %d not found", execution_id)
            return {"error": "execution_not_found"}

        if execution.workspace_id != workspace_id or execution.organization_id != org_id:
            logger.critical(
                "SECURITY: workspace mismatch execution=%d claimed=%d actual=%d",
                execution_id, workspace_id, execution.workspace_id,
            )
            execution.status = "failed"
            execution.error = "Workspace isolation violation detected"
            db.commit()
            return {"error": "workspace_isolation_violation"}

        if execution.status in ("completed", "failed", "canceled"):
            logger.info("Execution %d already %s — skipping", execution_id, execution.status)
            return {"skipped": True, "reason": execution.status}

        # Load a system-level user for worker actions
        from auth.models import User
        system_user = db.query(User).filter(
            User.workspace_id == execution.workspace_id,
        ).first()

        if not system_user:
            # Create minimal user-like object for context
            system_user = _make_system_actor(workspace_id, org_id)

        engine = WorkflowEngine(
            workspace_id=execution.workspace_id,
            org_id=execution.organization_id,
            user=system_user,
            db=db,
        )

        result = engine.execute(
            workflow_id=execution.workflow_id,
            trigger_data=execution.trigger_data or {},
            execution_id=execution_id,
        )

        return {
            "execution_id": execution_id,
            "status": result.status,
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
        }

    except Exception as exc:
        logger.exception("Workflow execution %d failed (attempt %d): %s", execution_id, self.request.retries + 1, exc)

        # Update execution status
        try:
            from models.workflow import WorkflowExecution
            execution = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
            if execution and execution.status not in ("awaiting_approval", "completed", "canceled"):
                execution.status = "failed"
                execution.error = str(exc)[:500]
                db.commit()
        except Exception:
            pass

        # Exponential backoff retry: 60, 120, 240, 480, 960 seconds
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown, max_retries=5)

    finally:
        db.close()
        _release_lock(lock_key)


# ── Resume after approval ─────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="tasks.workflow_tasks.resume_workflow_after_approval",
    queue="workflow",
    max_retries=3,
    default_retry_delay=30,
)
def resume_workflow_after_approval(self: Task, *, execution_id: int, approval_id: int) -> dict:
    """
    Re-queue workflow execution after a human approval.
    Continues from the approved step onward.
    """
    db = SessionLocal()
    try:
        from models.workflow import WorkflowExecution, WorkflowApproval

        execution = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
        approval = db.query(WorkflowApproval).filter(WorkflowApproval.id == approval_id).first()

        if not execution or not approval:
            return {"error": "not_found"}

        if approval.status != "approved":
            return {"skipped": True, "reason": f"approval status is {approval.status}"}

        # Re-fire the workflow from the beginning with idempotency cleared
        # (approved step will be skipped as it's already marked completed)
        execute_workflow_async.apply_async(
            kwargs={
                "workflow_id": execution.workflow_id,
                "execution_id": execution_id,
                "workspace_id": execution.workspace_id,
                "org_id": execution.organization_id,
            },
            queue="workflow",
        )
        return {"resumed": True, "execution_id": execution_id}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()


# ── Scheduled workflow check task ─────────────────────────────────────────────

@celery_app.task(
    name="tasks.workflow_tasks.check_scheduled_workflows",
    queue="workflow",
)
def check_scheduled_workflows() -> dict:
    """Periodic task: dispatch all scheduled workflows whose time has come."""
    try:
        from workflow.scheduler import check_and_dispatch_scheduled_workflows
        count = check_and_dispatch_scheduled_workflows()
        return {"dispatched": count}
    except Exception as exc:
        logger.exception("Scheduled workflow check error: %s", exc)
        return {"error": str(exc)}


# ── Helper ────────────────────────────────────────────────────────────────────

class _SystemActor:
    """Minimal user-like object for Celery worker actions."""
    def __init__(self, workspace_id: int, org_id: int):
        self.id = 0
        self.workspace_id = workspace_id
        self.organization_id = org_id
        self.role = "Workspace Admin"
        self.email = "system@workflow"


def _make_system_actor(workspace_id: int, org_id: int) -> _SystemActor:
    return _SystemActor(workspace_id, org_id)

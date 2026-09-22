"""
P5 — Trigger Dispatcher
Finds all active workflows in a workspace that match a given trigger type
and dispatches them asynchronously via Celery.
"""
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from models.workflow import Workflow, WorkflowExecution

logger = logging.getLogger(__name__)


# ── Valid trigger types ────────────────────────────────────────────────────────
VALID_TRIGGER_TYPES = {
    "contact_created",
    "contact_updated",
    "deal_created",
    "deal_stage_changed",
    "email_received",
    "email_classified",
    "task_completed",
    "scheduled",
    "webhook_received",
}


def _sanitize_trigger_data(trigger_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return a sanitized copy of the trigger event — no raw email bodies,
    no raw PII beyond IDs and status fields.
    """
    safe = {
        "trigger_type": trigger_type,
        "timestamp": datetime.utcnow().isoformat(),
    }
    # Allow non-sensitive scalar fields only
    allowed_keys = {
        "contact_id", "deal_id", "email_id", "task_id",
        "stage", "classification", "subject_snippet",
        "lead_score", "deal_amount", "event_type",
        "contact_name", "contact_email",  # non-body PII acceptable
    }
    for key, val in event_data.items():
        if key in allowed_keys and isinstance(val, (str, int, float, bool, type(None))):
            safe[key] = val
    return safe


def _make_idempotency_key(workflow_id: int, event_data: Dict[str, Any]) -> str:
    """
    SHA-256 of (workflow_id + sorted event_data JSON).
    Period-windowed: includes current hour to prevent cross-hour dedup.
    """
    period = datetime.utcnow().strftime("%Y-%m-%dT%H")  # 1-hour window
    payload = f"{workflow_id}:{period}:{json.dumps(event_data, sort_keys=True, default=str)}"
    return hashlib.sha256(payload.encode()).hexdigest()


class TriggerDispatcher:

    @staticmethod
    def dispatch(
        *,
        trigger_type: str,
        event_data: Dict[str, Any],
        workspace_id: int,
        org_id: int,
        db: Session,
        triggered_by_user_id: Optional[int] = None,
    ) -> int:
        """
        Find all active workflows for this workspace+trigger_type and
        dispatch an async Celery task for each.
        Returns the number of workflows dispatched.
        """
        if trigger_type not in VALID_TRIGGER_TYPES:
            logger.warning("Unknown trigger type '%s' — skipping dispatch", trigger_type)
            return 0

        workflows = (
            db.query(Workflow)
            .filter(
                Workflow.workspace_id == workspace_id,
                Workflow.organization_id == org_id,
                Workflow.trigger_type == trigger_type,
                Workflow.status == "active",
                Workflow.is_deleted.is_(False),
            )
            .all()
        )

        if not workflows:
            return 0

        safe_data = _sanitize_trigger_data(trigger_type, event_data)
        dispatched = 0

        for wf in workflows:
            idempotency_key = _make_idempotency_key(wf.id, safe_data)

            # Check for duplicate execution within the current hour window
            existing = (
                db.query(WorkflowExecution)
                .filter(WorkflowExecution.idempotency_key == idempotency_key)
                .first()
            )
            if existing:
                logger.info(
                    "Skipping duplicate execution workflow=%d ikey=%s (already=%s)",
                    wf.id, idempotency_key[:8], existing.status,
                )
                continue

            # Create execution record first (so idempotency key is committed)
            execution = WorkflowExecution(
                workflow_id=wf.id,
                organization_id=org_id,
                workspace_id=workspace_id,
                triggered_by_user_id=triggered_by_user_id,
                trigger_data=safe_data,
                status="pending",
                idempotency_key=idempotency_key,
            )
            db.add(execution)
            db.commit()
            db.refresh(execution)

            # Dispatch to Celery
            try:
                from tasks.workflow_tasks import execute_workflow_async
                task = execute_workflow_async.apply_async(
                    kwargs={
                        "workflow_id": wf.id,
                        "execution_id": execution.id,
                        "workspace_id": workspace_id,
                        "org_id": org_id,
                    },
                    queue="workflow",
                    countdown=1,  # Small delay to allow DB commit to propagate
                )
                execution.celery_task_id = task.id
                db.commit()
                dispatched += 1
                logger.info("Dispatched workflow=%d execution=%d task=%s", wf.id, execution.id, task.id)
            except Exception as exc:
                logger.warning("Failed to dispatch workflow=%d: %s", wf.id, exc)
                execution.status = "failed"
                execution.error = str(exc)
                db.commit()

        return dispatched

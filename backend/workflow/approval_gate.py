"""
P5 — Approval Gate
Creates, fetches, and processes human approval requests for workflow actions.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models.workflow import WorkflowApproval, WorkflowExecution, WorkflowExecutionStep, WorkflowAuditLog
from auth.models import User

logger = logging.getLogger(__name__)

DEFAULT_APPROVAL_TTL_HOURS = 48


class ApprovalGate:

    @staticmethod
    def request_approval(
        *,
        execution_id: int,
        step_id: int,
        action_type: str,
        action_payload: dict,
        requested_by_user_id: Optional[int],
        assigned_to_user_id: Optional[int],
        db: Session,
        ttl_hours: int = DEFAULT_APPROVAL_TTL_HOURS,
    ) -> WorkflowApproval:
        """Create a pending approval record and mark the execution as awaiting_approval."""
        approval = WorkflowApproval(
            execution_id=execution_id,
            step_id=step_id,
            requested_by_user_id=requested_by_user_id,
            assigned_to_user_id=assigned_to_user_id,
            action_type=action_type,
            action_payload=action_payload,
            status="pending",
            expires_at=datetime.utcnow() + timedelta(hours=ttl_hours),
        )
        db.add(approval)

        # Update execution status
        execution = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
        if execution:
            execution.status = "awaiting_approval"

        db.commit()
        db.refresh(approval)

        # Audit
        if execution:
            _write_audit(
                db=db,
                workflow_id=execution.workflow_id,
                execution_id=execution_id,
                org_id=execution.organization_id,
                workspace_id=execution.workspace_id,
                user_id=requested_by_user_id,
                event_type="approval_requested",
                details={"action_type": action_type, "approval_id": approval.id},
            )

        logger.info("Approval requested execution=%d step=%d action=%s", execution_id, step_id, action_type)
        return approval

    @staticmethod
    def process_approval(
        *,
        approval_id: int,
        decision: str,  # "approved" | "rejected"
        actor: User,
        workspace_id: int,
        notes: Optional[str],
        db: Session,
    ) -> WorkflowApproval:
        """Accept or reject a pending approval. Validates workspace ownership."""
        if decision not in ("approved", "rejected"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Decision must be 'approved' or 'rejected'")

        approval = db.query(WorkflowApproval).filter(WorkflowApproval.id == approval_id).first()
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")

        # Workspace isolation: approval must belong to the actor's workspace
        execution = db.query(WorkflowExecution).filter(WorkflowExecution.id == approval.execution_id).first()
        if not execution or execution.workspace_id != workspace_id:
            raise HTTPException(status_code=403, detail="Approval does not belong to this workspace")

        if approval.status != "pending":
            raise HTTPException(status_code=400, detail=f"Approval is already {approval.status}")

        if approval.expires_at and datetime.utcnow() > approval.expires_at:
            approval.status = "expired"
            db.commit()
            raise HTTPException(status_code=400, detail="Approval has expired")

        approval.status = decision
        approval.decision_by = actor.id
        approval.decision_at = datetime.utcnow()
        approval.notes = notes

        # Update execution and step statuses
        step = db.query(WorkflowExecutionStep).filter(WorkflowExecutionStep.id == approval.step_id).first()
        if step:
            step.status = "approved" if decision == "approved" else "rejected"

        if execution:
            if decision == "rejected":
                execution.status = "canceled"
                execution.completed_at = datetime.utcnow()
                execution.error = f"Rejected by user {actor.id}: {notes or ''}"
            else:
                # Approved — re-queue the Celery task to resume
                execution.status = "running"

        db.commit()
        db.refresh(approval)

        # Audit
        if execution:
            event = "approval_approved" if decision == "approved" else "approval_rejected"
            _write_audit(
                db=db,
                workflow_id=execution.workflow_id,
                execution_id=execution.id,
                org_id=execution.organization_id,
                workspace_id=execution.workspace_id,
                user_id=actor.id,
                event_type=event,
                details={"approval_id": approval_id, "notes": notes},
            )

        # If approved, re-queue Celery task
        if decision == "approved" and execution:
            try:
                from tasks.workflow_tasks import resume_workflow_after_approval
                resume_workflow_after_approval.delay(
                    execution_id=execution.id,
                    approval_id=approval_id,
                )
            except Exception as exc:
                logger.warning("Could not re-queue workflow after approval: %s", exc)

        logger.info("Approval %s execution=%d by user=%d", decision, approval.execution_id, actor.id)
        return approval

    @staticmethod
    def list_pending(workspace_id: int, db: Session):
        """Return all non-expired pending approvals for a workspace."""
        return (
            db.query(WorkflowApproval)
            .join(WorkflowExecution, WorkflowApproval.execution_id == WorkflowExecution.id)
            .filter(
                WorkflowExecution.workspace_id == workspace_id,
                WorkflowApproval.status == "pending",
            )
            .order_by(WorkflowApproval.created_at.desc())
            .all()
        )


# ── Internal helper ───────────────────────────────────────────────────────────

def _write_audit(*, db, workflow_id, execution_id, org_id, workspace_id, user_id, event_type, details):
    try:
        log = WorkflowAuditLog(
            workflow_id=workflow_id,
            execution_id=execution_id,
            organization_id=org_id,
            workspace_id=workspace_id,
            user_id=user_id,
            event_type=event_type,
            details=details or {},
        )
        db.add(log)
        db.commit()
    except Exception as exc:
        logger.warning("Audit log write failed: %s", exc)

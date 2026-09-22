"""
P5 — Workflow REST API Router
All endpoints are workspace-scoped via AuthContext.
Prefix: /api/v1/workflows
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from auth.rbac import get_auth_context, AuthContext, Role
from auth.dependencies import require_workspace_member
from models.workflow import (
    Workflow, WorkflowExecution, WorkflowExecutionStep, WorkflowApproval, WorkflowAuditLog,
)
from workflow.engine import WorkflowEngine
from workflow.approval_gate import ApprovalGate
from workflow.trigger_dispatcher import TriggerDispatcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workflows", tags=["Workflows"])


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    trigger_type: str
    trigger_config: Dict[str, Any] = {}
    nodes: List[Dict[str, Any]] = []


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[Dict[str, Any]] = None
    nodes: Optional[List[Dict[str, Any]]] = None


class ApprovalDecision(BaseModel):
    decision: str  # "approved" | "rejected"
    notes: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_org_id(auth: AuthContext, db: Session) -> int:
    """Resolve org_id from auth context; 404 if missing."""
    org_id = auth.organization_id
    if not org_id and auth.workspace_id:
        from auth.models import Workspace
        ws = db.query(Workspace).filter(Workspace.id == auth.workspace_id).first()
        if ws:
            org_id = ws.organization_id
    if not org_id:
        raise HTTPException(status_code=404, detail="Organization not resolved")
    return org_id


def _require_admin(auth: AuthContext):
    if auth.role not in (Role.SUPER_ADMIN, Role.WORKSPACE_ADMIN):
        raise HTTPException(status_code=403, detail="Workspace Admin role required")


def _wf_to_dict(wf: Workflow) -> dict:
    return {
        "id": wf.id,
        "name": wf.name,
        "description": wf.description,
        "status": wf.status,
        "trigger_type": wf.trigger_type,
        "trigger_config": wf.trigger_config,
        "nodes": wf.nodes,
        "workspace_id": wf.workspace_id,
        "organization_id": wf.organization_id,
        "created_by": wf.created_by,
        "created_at": wf.created_at.isoformat() if wf.created_at else None,
        "updated_at": wf.updated_at.isoformat() if wf.updated_at else None,
    }


def _exec_to_dict(ex: WorkflowExecution, include_steps: bool = False) -> dict:
    d = {
        "id": ex.id,
        "workflow_id": ex.workflow_id,
        "status": ex.status,
        "trigger_data": ex.trigger_data,
        "idempotency_key": ex.idempotency_key,
        "celery_task_id": ex.celery_task_id,
        "error": ex.error,
        "started_at": ex.started_at.isoformat() if ex.started_at else None,
        "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
        "created_at": ex.created_at.isoformat() if ex.created_at else None,
    }
    if include_steps:
        d["steps"] = [_step_to_dict(s) for s in (ex.steps or [])]
    return d


def _step_to_dict(s: WorkflowExecutionStep) -> dict:
    return {
        "id": s.id,
        "node_id": s.node_id,
        "node_type": s.node_type,
        "status": s.status,
        "output_summary": s.output_summary,
        "retry_count": s.retry_count,
        "error": s.error,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
    }


def _approval_to_dict(a: WorkflowApproval) -> dict:
    return {
        "id": a.id,
        "execution_id": a.execution_id,
        "step_id": a.step_id,
        "action_type": a.action_type,
        "action_payload": a.action_payload,
        "status": a.status,
        "requested_by_user_id": a.requested_by_user_id,
        "assigned_to_user_id": a.assigned_to_user_id,
        "decision_by": a.decision_by,
        "decision_at": a.decision_at.isoformat() if a.decision_at else None,
        "expires_at": a.expires_at.isoformat() if a.expires_at else None,
        "notes": a.notes,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


# ── Workflow CRUD ──────────────────────────────────────────────────────────────

@router.get("/", summary="List workflows in workspace")
def list_workflows(
    status_filter: Optional[str] = Query(None, alias="status"),
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    q = db.query(Workflow).filter(
        Workflow.workspace_id == auth.workspace_id,
        Workflow.is_deleted.is_(False),
    )
    if status_filter:
        q = q.filter(Workflow.status == status_filter)
    workflows = q.order_by(Workflow.created_at.desc()).all()
    return {"workflows": [_wf_to_dict(wf) for wf in workflows]}


@router.post("/", status_code=status.HTTP_201_CREATED, summary="Create workflow")
def create_workflow(
    payload: WorkflowCreate,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    _require_admin(auth)
    org_id = _get_org_id(auth, db)

    # Check billing feature flag
    try:
        from billing.service import BillingService
        BillingService.enforce_subscription(org_id, db)
        quota = BillingService.check_quota(org_id, "workflows", db)
        if not quota.allowed:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={"error": "quota_exceeded", "resource": "workflows", "limit": quota.limit},
            )
    except HTTPException:
        raise
    except Exception:
        pass  # Billing not critical path for creation

    engine = WorkflowEngine(
        workspace_id=auth.workspace_id,
        org_id=org_id,
        user=auth.user,
        db=db,
    )
    is_valid, errors = engine.validate_definition(payload.dict())
    if not is_valid:
        raise HTTPException(status_code=422, detail={"errors": errors})

    wf = Workflow(
        organization_id=org_id,
        workspace_id=auth.workspace_id,
        created_by=auth.user.id,
        name=payload.name,
        description=payload.description,
        trigger_type=payload.trigger_type,
        trigger_config=payload.trigger_config,
        nodes=payload.nodes,
        status="draft",
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)

    # Audit
    _log_audit(db, wf.id, None, org_id, auth.workspace_id, auth.user.id, "workflow_created",
               {"name": wf.name, "trigger_type": wf.trigger_type})

    return _wf_to_dict(wf)


@router.get("/{workflow_id}", summary="Get workflow")
def get_workflow(
    workflow_id: int,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    wf = _load_wf(workflow_id, auth.workspace_id, db)
    return _wf_to_dict(wf)


@router.put("/{workflow_id}", summary="Update workflow")
def update_workflow(
    workflow_id: int,
    payload: WorkflowUpdate,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    _require_admin(auth)
    wf = _load_wf(workflow_id, auth.workspace_id, db)

    if payload.name is not None:
        wf.name = payload.name
    if payload.description is not None:
        wf.description = payload.description
    if payload.trigger_type is not None:
        wf.trigger_type = payload.trigger_type
    if payload.trigger_config is not None:
        wf.trigger_config = payload.trigger_config
    if payload.nodes is not None:
        org_id = _get_org_id(auth, db)
        engine = WorkflowEngine(workspace_id=auth.workspace_id, org_id=org_id, user=auth.user, db=db)
        is_valid, errors = engine.validate_definition({
            "trigger_type": wf.trigger_type,
            "nodes": payload.nodes,
        })
        if not is_valid:
            raise HTTPException(status_code=422, detail={"errors": errors})
        wf.nodes = payload.nodes

    db.commit()
    db.refresh(wf)

    org_id = _get_org_id(auth, db)
    _log_audit(db, wf.id, None, org_id, auth.workspace_id, auth.user.id, "workflow_updated", {})
    return _wf_to_dict(wf)


@router.delete("/{workflow_id}", status_code=204, summary="Archive workflow")
def delete_workflow(
    workflow_id: int,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    _require_admin(auth)
    wf = _load_wf(workflow_id, auth.workspace_id, db)
    wf.is_deleted = True
    wf.status = "archived"
    db.commit()

    org_id = _get_org_id(auth, db)
    _log_audit(db, wf.id, None, org_id, auth.workspace_id, auth.user.id, "workflow_deleted", {})


@router.post("/{workflow_id}/enable", summary="Enable workflow")
def enable_workflow(
    workflow_id: int,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    _require_admin(auth)
    wf = _load_wf(workflow_id, auth.workspace_id, db)
    wf.status = "active"
    db.commit()

    org_id = _get_org_id(auth, db)
    _log_audit(db, wf.id, None, org_id, auth.workspace_id, auth.user.id, "workflow_enabled", {})
    return {"status": "active", "workflow_id": workflow_id}


@router.post("/{workflow_id}/disable", summary="Disable workflow")
def disable_workflow(
    workflow_id: int,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    _require_admin(auth)
    wf = _load_wf(workflow_id, auth.workspace_id, db)
    wf.status = "paused"
    db.commit()

    org_id = _get_org_id(auth, db)
    _log_audit(db, wf.id, None, org_id, auth.workspace_id, auth.user.id, "workflow_disabled", {})
    return {"status": "paused", "workflow_id": workflow_id}


@router.post("/{workflow_id}/validate", summary="Validate workflow definition")
def validate_workflow(
    workflow_id: int,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    wf = _load_wf(workflow_id, auth.workspace_id, db)
    org_id = _get_org_id(auth, db)
    engine = WorkflowEngine(workspace_id=auth.workspace_id, org_id=org_id, user=auth.user, db=db)
    is_valid, errors = engine.validate_definition({
        "trigger_type": wf.trigger_type,
        "nodes": wf.nodes or [],
    })
    return {"valid": is_valid, "errors": errors}


@router.post("/{workflow_id}/test", summary="Test-fire a workflow")
def test_workflow(
    workflow_id: int,
    test_data: Dict[str, Any] = {},
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    _require_admin(auth)
    wf = _load_wf(workflow_id, auth.workspace_id, db)
    org_id = _get_org_id(auth, db)

    # For interactive/test testing, run directly through the engine synchronously
    # so immediate validation, execution steps, and approvals can be inspected
    execution = WorkflowExecution(
        workflow_id=wf.id,
        organization_id=org_id,
        workspace_id=auth.workspace_id,
        triggered_by_user_id=auth.user.id,
        trigger_data={"test": True, **test_data},
        status="pending",
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    engine = WorkflowEngine(workspace_id=auth.workspace_id, org_id=org_id, user=auth.user, db=db)
    try:
        execution = engine.execute_sync(
            workflow_id=wf.id,
            trigger_data={"test": True, **test_data},
            execution_id=execution.id,
        )
    except Exception as exc:
        logger.warning("Test workflow execution %d finished with: %s", execution.id, exc)

    return {
        "id": execution.id,
        "workflow_id": workflow_id,
        "status": execution.status,
        "dispatched": 1,
    }


# ── Execution history ──────────────────────────────────────────────────────────

@router.get("/{workflow_id}/executions", summary="List execution history")
def list_executions(
    workflow_id: int,
    limit: int = Query(20, le=100),
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    _load_wf(workflow_id, auth.workspace_id, db)
    executions = (
        db.query(WorkflowExecution)
        .filter(
            WorkflowExecution.workflow_id == workflow_id,
            WorkflowExecution.workspace_id == auth.workspace_id,
        )
        .order_by(WorkflowExecution.created_at.desc())
        .limit(limit)
        .all()
    )
    return {"executions": [_exec_to_dict(e) for e in executions]}


@router.get("/executions/{exec_id}", summary="Get execution details with steps")
def get_execution(
    exec_id: int,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    ex = db.query(WorkflowExecution).filter(
        WorkflowExecution.id == exec_id,
        WorkflowExecution.workspace_id == auth.workspace_id,
    ).first()
    if not ex:
        raise HTTPException(status_code=404, detail="Execution not found in this workspace")
    return _exec_to_dict(ex, include_steps=True)


@router.post("/executions/{exec_id}/cancel", summary="Cancel a running execution")
def cancel_execution(
    exec_id: int,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    _require_admin(auth)
    ex = db.query(WorkflowExecution).filter(
        WorkflowExecution.id == exec_id,
        WorkflowExecution.workspace_id == auth.workspace_id,
    ).first()
    if not ex:
        raise HTTPException(status_code=404, detail="Execution not found")
    if ex.status in ("completed", "failed", "canceled"):
        raise HTTPException(status_code=400, detail=f"Execution already {ex.status}")

    ex.status = "canceled"
    from datetime import datetime
    ex.completed_at = datetime.utcnow()
    ex.error = f"Manually canceled by user {auth.user.id}"
    db.commit()

    org_id = _get_org_id(auth, db)
    _log_audit(db, ex.workflow_id, ex.id, org_id, auth.workspace_id, auth.user.id, "execution_canceled", {})

    # Revoke Celery task if possible
    if ex.celery_task_id:
        try:
            from tasks.celery_app import celery_app
            celery_app.control.revoke(ex.celery_task_id, terminate=True)
        except Exception:
            pass

    return {"canceled": True, "execution_id": exec_id}


# ── Approvals ──────────────────────────────────────────────────────────────────

@router.get("/approvals/pending", summary="List pending approvals")
def list_pending_approvals(
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    approvals = ApprovalGate.list_pending(auth.workspace_id, db)
    return {"approvals": [_approval_to_dict(a) for a in approvals]}


@router.post("/approvals/{approval_id}/approve", summary="Approve a workflow action")
def approve_action(
    approval_id: int,
    payload: ApprovalDecision,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    approval = ApprovalGate.process_approval(
        approval_id=approval_id,
        decision="approved",
        actor=auth.user,
        workspace_id=auth.workspace_id,
        notes=payload.notes,
        db=db,
    )
    return _approval_to_dict(approval)


@router.post("/approvals/{approval_id}/reject", summary="Reject a workflow action")
def reject_action(
    approval_id: int,
    payload: ApprovalDecision,
    auth: AuthContext = Depends(require_workspace_member),
    db: Session = Depends(get_db),
):
    approval = ApprovalGate.process_approval(
        approval_id=approval_id,
        decision="rejected",
        actor=auth.user,
        workspace_id=auth.workspace_id,
        notes=payload.notes,
        db=db,
    )
    return _approval_to_dict(approval)


# ── Internal helpers ───────────────────────────────────────────────────────────

def _load_wf(workflow_id: int, workspace_id: int, db: Session) -> Workflow:
    wf = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.workspace_id == workspace_id,
        Workflow.is_deleted.is_(False),
    ).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found in this workspace")
    return wf


def _log_audit(db, workflow_id, execution_id, org_id, workspace_id, user_id, event_type, details):
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
        logger.warning("Workflow audit log failed: %s", exc)

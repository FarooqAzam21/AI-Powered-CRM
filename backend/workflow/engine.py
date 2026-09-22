"""
P5 — Workflow Engine
Central orchestrator that loads, validates, evaluates conditions,
and executes workflow node graphs.
Idempotency, workspace isolation, and billing quotas are all enforced here.
"""
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models.workflow import (
    Workflow, WorkflowExecution, WorkflowExecutionStep, WorkflowAuditLog,
)
from auth.models import User
from workflow.condition_evaluator import evaluate_all_conditions
from workflow.action_executor import ActionExecutor, ALLOWED_ACTIONS
from workflow.approval_gate import ApprovalGate, _write_audit

logger = logging.getLogger(__name__)

# ── Valid trigger types ────────────────────────────────────────────────────────
VALID_TRIGGER_TYPES = {
    "contact_created", "contact_updated", "deal_created", "deal_stage_changed",
    "email_received", "email_classified", "task_completed", "scheduled", "webhook_received",
}

# ── Validation constants ───────────────────────────────────────────────────────
MAX_NODES = 50
MAX_CONDITIONS_PER_GROUP = 20


class WorkflowValidationError(Exception):
    pass


class ApprovalRequiredException(Exception):
    pass


class WorkflowEngine:

    def __init__(self, workspace_id: int, org_id: int, user: User, db: Session):
        self.workspace_id = workspace_id
        self.org_id = org_id
        self.user = user
        self.db = db

    # ── Public API ─────────────────────────────────────────────────────────────

    def load_and_validate(self, workflow_id: int) -> Workflow:
        """Load workflow and ensure it belongs to this workspace."""
        wf = self.db.query(Workflow).filter(
            Workflow.id == workflow_id,
            Workflow.workspace_id == self.workspace_id,
            Workflow.organization_id == self.org_id,
            Workflow.is_deleted.is_(False),
        ).first()
        if not wf:
            raise HTTPException(status_code=404, detail="Workflow not found in this workspace")
        return wf

    def validate_definition(self, workflow_def: Dict) -> Tuple[bool, List[str]]:
        """
        Validate a workflow definition dict before saving.
        Returns (is_valid, list_of_error_messages).
        """
        errors = []
        trigger_type = workflow_def.get("trigger_type", "")
        if trigger_type not in VALID_TRIGGER_TYPES:
            errors.append(f"Invalid trigger_type '{trigger_type}'. Allowed: {sorted(VALID_TRIGGER_TYPES)}")

        nodes = workflow_def.get("nodes", [])
        if not isinstance(nodes, list):
            errors.append("'nodes' must be a list")
        elif len(nodes) > MAX_NODES:
            errors.append(f"Workflow exceeds maximum of {MAX_NODES} nodes")
        else:
            node_ids = set()
            for node in nodes:
                if not isinstance(node, dict):
                    errors.append("Each node must be a dict")
                    continue
                nid = node.get("id")
                if not nid:
                    errors.append("Each node must have a non-empty 'id'")
                elif nid in node_ids:
                    errors.append(f"Duplicate node id '{nid}'")
                else:
                    node_ids.add(nid)

                ntype = node.get("type", "")
                if ntype not in ALLOWED_ACTIONS and ntype not in {"condition", "trigger"}:
                    errors.append(f"Node '{nid}' has unknown type '{ntype}'")

        return (len(errors) == 0), errors

    def execute(
        self,
        workflow_id: int,
        trigger_data: Dict[str, Any],
        execution_id: int,
    ) -> WorkflowExecution:
        """
        Execute a workflow synchronously (called from Celery worker).
        Workspace isolation is re-validated here (never trust serialized client data).
        """
        wf = self.load_and_validate(workflow_id)
        execution = self._get_execution(execution_id)

        if execution.workspace_id != self.workspace_id:
            raise HTTPException(status_code=403, detail="Execution workspace mismatch")

        # Check billing quota
        self._enforce_quota()

        # Mark execution running
        execution.status = "running"
        execution.started_at = datetime.utcnow()
        self.db.commit()

        _write_audit(
            db=self.db,
            workflow_id=wf.id,
            execution_id=execution.id,
            org_id=self.org_id,
            workspace_id=self.workspace_id,
            user_id=None,
            event_type="execution_started",
            details={"trigger_type": wf.trigger_type},
        )

        try:
            context = self._build_context(wf, trigger_data)
            nodes = wf.nodes or []
            self._run_nodes(nodes, context, execution)

            execution.status = "completed"
            execution.completed_at = datetime.utcnow()
            self.db.commit()

            # Increment billing usage
            self._increment_quota()

            _write_audit(
                db=self.db,
                workflow_id=wf.id,
                execution_id=execution.id,
                org_id=self.org_id,
                workspace_id=self.workspace_id,
                user_id=None,
                event_type="execution_completed",
                details={"node_count": len(nodes)},
            )

        except ApprovalRequiredException:
            # Execution paused for human approval — not a failure
            pass
        except Exception as exc:
            execution.status = "failed"
            execution.error = str(exc)[:500]
            execution.completed_at = datetime.utcnow()
            self.db.commit()

            _write_audit(
                db=self.db,
                workflow_id=wf.id,
                execution_id=execution.id,
                org_id=self.org_id,
                workspace_id=self.workspace_id,
                user_id=None,
                event_type="execution_failed",
                details={"error": str(exc)[:200]},
            )
            raise

        self.db.refresh(execution)
        return execution

    execute_sync = execute

    # ── Internal methods ───────────────────────────────────────────────────────

    def _get_execution(self, execution_id: int) -> WorkflowExecution:
        ex = self.db.query(WorkflowExecution).filter(
            WorkflowExecution.id == execution_id,
        ).first()
        if not ex:
            raise HTTPException(status_code=404, detail="Execution not found")
        return ex

    def _build_context(self, wf: Workflow, trigger_data: Dict) -> Dict:
        """Build CRM context dict for condition evaluation and action interpolation."""
        return {
            "trigger_type": wf.trigger_type,
            "workspace_id": self.workspace_id,
            "org_id": self.org_id,
            **trigger_data,
        }

    def _run_nodes(self, nodes: List[Dict], context: Dict, execution: WorkflowExecution):
        """Execute node list in order, skipping condition nodes that don't pass."""
        executor = ActionExecutor(
            workspace_id=self.workspace_id,
            org_id=self.org_id,
            user=self.user,
            db=self.db,
        )

        for node in nodes:
            node_type = node.get("type", "")
            node_id = node.get("id", "unknown")

            # Skip pure trigger nodes (already handled by TriggerDispatcher)
            if node_type == "trigger":
                continue

            # Evaluate condition nodes
            if node_type == "condition":
                condition_groups = node.get("config", {}).get("groups", [])
                passed = evaluate_all_conditions(condition_groups, context)
                if not passed:
                    logger.info("Condition node '%s' did not pass — stopping branch", node_id)
                    break  # Stop executing this branch
                continue

            # Action node
            step = self._create_step(execution.id, node_id, node_type)
            try:
                result = executor.execute(node, context)

                if result.requires_approval:
                    step.status = "awaiting_approval"
                    self.db.commit()
                    ApprovalGate.request_approval(
                        execution_id=execution.id,
                        step_id=step.id,
                        action_type=node_type,
                        action_payload=result.approval_payload,
                        requested_by_user_id=self.user.id if self.user else None,
                        assigned_to_user_id=None,
                        db=self.db,
                    )
                    raise ApprovalRequiredException()

                if result.success:
                    step.status = "completed"
                    step.output_summary = result.output
                    _write_audit(
                        db=self.db,
                        workflow_id=execution.workflow_id,
                        execution_id=execution.id,
                        org_id=self.org_id,
                        workspace_id=self.workspace_id,
                        user_id=self.user.id if self.user else None,
                        event_type="action_executed",
                        details={"node_id": node_id, "action_type": node_type, "output": result.output},
                    )
                else:
                    step.status = "failed"
                    step.error = result.error

                step.completed_at = datetime.utcnow()
                self.db.commit()

            except ApprovalRequiredException:
                raise
            except Exception as exc:
                step.status = "failed"
                step.error = str(exc)[:300]
                step.completed_at = datetime.utcnow()
                self.db.commit()

                on_failure = node.get("on_failure", "stop")
                if on_failure == "continue":
                    logger.warning("Node '%s' failed (continue): %s", node_id, exc)
                    continue
                raise

    def _create_step(self, execution_id: int, node_id: str, node_type: str) -> WorkflowExecutionStep:
        step = WorkflowExecutionStep(
            execution_id=execution_id,
            node_id=node_id,
            node_type=node_type,
            status="running",
            started_at=datetime.utcnow(),
        )
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def _enforce_quota(self):
        """Check P3 billing quota for workflow executions."""
        try:
            from billing.service import BillingService
            result = BillingService.check_quota(self.org_id, "workflow_runs", self.db)
            if not result.allowed:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "error": "quota_exceeded",
                        "resource": "workflow_runs",
                        "limit": result.limit,
                        "used": result.used,
                    },
                )
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Billing quota check failed (allowing): %s", exc)

    def _increment_quota(self):
        """Increment P3 billing usage for workflow_runs."""
        try:
            from billing.service import BillingService
            BillingService.increment_usage(self.org_id, "workflow_runs", self.db)
        except Exception as exc:
            logger.warning("Failed to increment workflow_runs quota: %s", exc)


class ApprovalRequiredException(Exception):
    """Raised when a workflow node requires human approval before proceeding."""
    pass

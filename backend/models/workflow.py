"""
P5 — Workflow Automation Models
Tenant-isolated workflow definitions, executions, approvals, and audit logs.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, DateTime,
    ForeignKey, JSON, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from database import Base


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(Text, default="")

    # draft | active | paused | archived
    status = Column(String(32), default="draft", nullable=False, index=True)

    # contact_created | contact_updated | deal_created | deal_stage_changed |
    # email_received | email_classified | task_completed | scheduled | webhook_received
    trigger_type = Column(String(64), nullable=False, index=True)
    trigger_config = Column(JSON, default=dict)   # schedule expression, webhook secret, etc.

    # Full node graph: [{id, type, config, position, next_nodes, on_failure}]
    nodes = Column(JSON, default=list)

    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")
    audit_logs = relationship("WorkflowAuditLog", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    triggered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Sanitized trigger event — no raw PII
    trigger_data = Column(JSON, default=dict)

    # pending | running | completed | failed | canceled | awaiting_approval
    status = Column(String(32), default="pending", nullable=False, index=True)

    # SHA-256 of (workflow_id + trigger_hash + period) for dedup
    idempotency_key = Column(String(64), nullable=True, index=True)
    celery_task_id = Column(String(255), nullable=True)

    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    workflow = relationship("Workflow", back_populates="executions")
    steps = relationship("WorkflowExecutionStep", back_populates="execution", cascade="all, delete-orphan")
    approvals = relationship("WorkflowApproval", back_populates="execution", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_workflow_execution_idempotency"),
        Index("ix_wf_exec_workspace_status", "workspace_id", "status"),
    )


class WorkflowExecutionStep(Base):
    __tablename__ = "workflow_execution_steps"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("workflow_executions.id"), nullable=False, index=True)
    node_id = Column(String(64), nullable=False)  # matches Workflow.nodes[].id
    node_type = Column(String(64), nullable=False)

    # pending | running | completed | failed | skipped | awaiting_approval
    status = Column(String(32), default="pending", nullable=False)

    # Sanitized summaries — no raw PII / email bodies stored here
    input_summary = Column(JSON, default=dict)
    output_summary = Column(JSON, default=dict)

    retry_count = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    execution = relationship("WorkflowExecution", back_populates="steps")
    approval = relationship("WorkflowApproval", back_populates="step", uselist=False)


class WorkflowApproval(Base):
    __tablename__ = "workflow_approvals"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("workflow_executions.id"), nullable=False, index=True)
    step_id = Column(Integer, ForeignKey("workflow_execution_steps.id"), nullable=False, index=True)

    requested_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # If null, any workspace admin may approve
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    action_type = Column(String(64), nullable=False)
    # Sanitized action payload (no raw email body)
    action_payload = Column(JSON, default=dict)

    # pending | approved | rejected | expired
    status = Column(String(32), default="pending", nullable=False, index=True)

    decision_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    decision_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    execution = relationship("WorkflowExecution", back_populates="approvals")
    step = relationship("WorkflowExecutionStep", back_populates="approval")


class WorkflowAuditLog(Base):
    __tablename__ = "workflow_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=True, index=True)
    execution_id = Column(Integer, ForeignKey("workflow_executions.id"), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # workflow_created | workflow_updated | workflow_deleted | workflow_enabled | workflow_disabled
    # execution_started | execution_completed | execution_failed | execution_canceled
    # action_executed | ai_decision | approval_requested | approval_approved | approval_rejected
    event_type = Column(String(64), nullable=False, index=True)

    # Sanitized metadata only — never full email bodies or raw contact PII
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    workflow = relationship("Workflow", back_populates="audit_logs")

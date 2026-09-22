"""
P6 — Public API v1 Router
Prefix: /api/public/v1
Versioned, tenant-isolated, scope-enforced, and rate-limited public endpoints.
Reuses existing CRM services and models without duplicating business logic.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import get_db
from auth.api_key_auth import get_api_key_context, require_scope, APIKeyContext
from models.crm import Contact, Deal, TaskRecord, Activity, EmailMetadata
from models.workflow import Workflow, WorkflowExecution
from billing.service import BillingService
from services.contact_service import ContactService
from services.webhook_dispatcher import WebhookDispatcher
from workflow.engine import WorkflowEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public/v1", tags=["Public API v1"])


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class PublicContactCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None


class PublicContactUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None


class PublicDealCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    value: float = Field(default=0.0, ge=0)
    stage: str = "Lead"
    contact_id: Optional[int] = None
    notes: Optional[str] = None


class PublicDealUpdate(BaseModel):
    title: Optional[str] = None
    value: Optional[float] = None
    stage: Optional[str] = None
    notes: Optional[str] = None


class PublicTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = ""
    priority: str = "medium"
    due_date: Optional[datetime] = None
    assigned_to: Optional[int] = None


class PublicTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None


class PublicActivityCreate(BaseModel):
    type: str  # "call", "email", "meeting", "note"
    title: str
    description: Optional[str] = ""
    contact_id: Optional[int] = None
    deal_id: Optional[int] = None


class PublicAICompleteRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    max_tokens: int = Field(default=256, ge=1, le=1024)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)


# ── Contacts Endpoints ─────────────────────────────────────────────────────────

@router.get("/contacts", summary="List contacts (paginated)")
def list_contacts(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    ctx: APIKeyContext = Depends(require_scope("contacts:read")),
    db: Session = Depends(get_db),
):
    query = db.query(Contact).filter(Contact.workspace_id == ctx.workspace_id)
    if search:
        query = query.filter(
            or_(
                Contact.name.ilike(f"%{search}%"),
                Contact.email.ilike(f"%{search}%"),
                Contact.company.ilike(f"%{search}%"),
            )
        )
    total = query.count()
    contacts = query.order_by(Contact.id.desc()).offset(offset).limit(limit).all()

    items = [
        {
            "id": c.id,
            "email": c.email,
            "name": c.name,
            "company": c.company,
            "title": c.title,
            "phone": getattr(c, "phone", None),
            "score": c.lead.score if hasattr(c, "lead") and c.lead else getattr(c, "relationship_score", 0.0),
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in contacts
    ]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": items,
        "items": items,
    }


@router.post("/contacts", status_code=status.HTTP_201_CREATED, summary="Create contact")
def create_contact(
    payload: PublicContactCreate,
    ctx: APIKeyContext = Depends(require_scope("contacts:write")),
    db: Session = Depends(get_db),
):
    # Check contacts quota
    quota = BillingService.check_quota(ctx.organization_id, "contacts", db=db)
    if not quota.allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"error": "quota_exceeded", "resource": "contacts", "message": "Contacts quota exceeded for your plan."},
        )

    # Check for existing contact in workspace
    existing = db.query(Contact).filter(
        Contact.workspace_id == ctx.workspace_id,
        Contact.email == payload.email,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Contact with this email already exists in workspace")

    user_id = getattr(ctx, "user_id", None)
    if not user_id:
        from auth.models import WorkspaceMember
        member = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == ctx.workspace_id).first()
        user_id = member.user_id if member else 1

    contact = Contact(
        workspace_id=ctx.workspace_id,
        user_id=user_id,
        email=payload.email,
        name=payload.name,
        company=payload.company,
        title=payload.title,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)

    BillingService.increment_usage(ctx.organization_id, "contacts", 1, db=db)

    # Trigger outbound webhook
    WebhookDispatcher.dispatch_event(
        event_type="contact.created",
        workspace_id=ctx.workspace_id,
        organization_id=ctx.organization_id,
        data={"id": contact.id, "email": contact.email, "name": contact.name, "company": contact.company},
        db=db,
    )

    return {
        "id": contact.id,
        "email": contact.email,
        "name": contact.name,
        "company": contact.company,
        "title": contact.title,
        "phone": getattr(contact, "phone", None),
        "created_at": contact.created_at.isoformat(),
    }


@router.patch("/contacts/{contact_id}", summary="Update contact")
def update_contact(
    contact_id: int,
    payload: PublicContactUpdate,
    ctx: APIKeyContext = Depends(require_scope("contacts:write")),
    db: Session = Depends(get_db),
):
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.workspace_id == ctx.workspace_id,
    ).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found in this workspace")

    if payload.name is not None:
        contact.name = payload.name
    if payload.company is not None:
        contact.company = payload.company
    if payload.title is not None:
        contact.title = payload.title
    if payload.phone is not None and hasattr(contact, "phone"):
        setattr(contact, "phone", payload.phone)
    contact.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(contact)

    WebhookDispatcher.dispatch_event(
        event_type="contact.updated",
        workspace_id=ctx.workspace_id,
        organization_id=ctx.organization_id,
        data={"id": contact.id, "email": contact.email, "name": contact.name, "company": contact.company},
        db=db,
    )

    return {"id": contact.id, "email": contact.email, "name": contact.name, "company": contact.company, "title": contact.title, "phone": getattr(contact, "phone", None)}


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete contact")
def delete_contact(
    contact_id: int,
    ctx: APIKeyContext = Depends(require_scope("contacts:write")),
    db: Session = Depends(get_db),
):
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.workspace_id == ctx.workspace_id,
    ).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    email = contact.email
    db.delete(contact)
    db.commit()

    WebhookDispatcher.dispatch_event(
        event_type="contact.deleted",
        workspace_id=ctx.workspace_id,
        organization_id=ctx.organization_id,
        data={"id": contact_id, "email": email},
        db=db,
    )


# ── Deals Endpoints ───────────────────────────────────────────────────────────

@router.get("/deals", summary="List deals (paginated)")
def list_deals(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    stage: Optional[str] = None,
    ctx: APIKeyContext = Depends(require_scope("deals:read")),
    db: Session = Depends(get_db),
):
    query = db.query(Deal).filter(Deal.workspace_id == ctx.workspace_id)
    if stage:
        query = query.filter(Deal.stage == stage)
    total = query.count()
    deals = query.order_by(Deal.id.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": d.id,
                "title": d.title,
                "value": d.value,
                "stage": d.stage,
                "contact_id": d.contact_id,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in deals
        ],
    }


@router.post("/deals", status_code=status.HTTP_201_CREATED, summary="Create deal")
def create_deal(
    payload: PublicDealCreate,
    ctx: APIKeyContext = Depends(require_scope("deals:write")),
    db: Session = Depends(get_db),
):
    quota = BillingService.check_quota(ctx.organization_id, "deals", db=db)
    if not quota.allowed:
        raise HTTPException(status_code=402, detail="Deals quota exceeded for your plan")

    deal = Deal(
        workspace_id=ctx.workspace_id,
        title=payload.title,
        value=payload.value,
        stage=payload.stage,
        contact_id=payload.contact_id,
        notes=payload.notes,
        created_at=datetime.utcnow(),
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)

    BillingService.increment_usage(ctx.organization_id, "deals", 1, db=db)

    WebhookDispatcher.dispatch_event(
        event_type="deal.created",
        workspace_id=ctx.workspace_id,
        organization_id=ctx.organization_id,
        data={"id": deal.id, "title": deal.title, "value": deal.value, "stage": deal.stage},
        db=db,
    )

    return {"id": deal.id, "title": deal.title, "value": deal.value, "stage": deal.stage, "contact_id": deal.contact_id}


@router.patch("/deals/{deal_id}", summary="Update deal")
def update_deal(
    deal_id: int,
    payload: PublicDealUpdate,
    ctx: APIKeyContext = Depends(require_scope("deals:write")),
    db: Session = Depends(get_db),
):
    deal = db.query(Deal).filter(Deal.id == deal_id, Deal.workspace_id == ctx.workspace_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found in this workspace")

    stage_changed = False
    if payload.stage is not None and payload.stage != deal.stage:
        stage_changed = True
        deal.stage = payload.stage

    if payload.title is not None:
        deal.title = payload.title
    if payload.value is not None:
        deal.value = payload.value
    if payload.notes is not None:
        deal.notes = payload.notes
    db.commit()
    db.refresh(deal)

    if stage_changed:
        WebhookDispatcher.dispatch_event(
            event_type="deal.stage_changed",
            workspace_id=ctx.workspace_id,
            organization_id=ctx.organization_id,
            data={"id": deal.id, "title": deal.title, "stage": deal.stage},
            db=db,
        )
    else:
        WebhookDispatcher.dispatch_event(
            event_type="deal.updated",
            workspace_id=ctx.workspace_id,
            organization_id=ctx.organization_id,
            data={"id": deal.id, "title": deal.title, "value": deal.value, "stage": deal.stage},
            db=db,
        )

    return {"id": deal.id, "title": deal.title, "value": deal.value, "stage": deal.stage}


# ── Tasks Endpoints ───────────────────────────────────────────────────────────

@router.get("/tasks", summary="List tasks (paginated)")
def list_tasks(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, alias="status"),
    ctx: APIKeyContext = Depends(require_scope("tasks:read")),
    db: Session = Depends(get_db),
):
    from auth.models import WorkspaceMember
    members = db.query(WorkspaceMember.user_id).filter(WorkspaceMember.workspace_id == ctx.workspace_id).all()
    user_ids = [m[0] for m in members] if members else []
    
    query = db.query(TaskRecord).filter(TaskRecord.user_id.in_(user_ids)) if user_ids else db.query(TaskRecord).filter(False)
    if status_filter:
        query = query.filter(TaskRecord.status == status_filter)
    total = query.count()
    tasks = query.order_by(TaskRecord.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": t.id,
                "task_type": t.task_type or "task",
                "queue": t.queue or "default",
                "status": t.status,
                "progress": t.progress,
                "result": t.result,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks
        ],
    }


@router.post("/tasks", status_code=status.HTTP_201_CREATED, summary="Create task")
def create_task(
    payload: PublicTaskCreate,
    ctx: APIKeyContext = Depends(require_scope("tasks:write")),
    db: Session = Depends(get_db),
):
    task = TaskRecord(
        workspace_id=ctx.workspace_id,
        user_id=None,
        assigned_to=payload.assigned_to,
        title=payload.title,
        description=payload.description or "",
        priority=payload.priority,
        status="open",
        due_date=payload.due_date,
        source="public_api",
        created_at=datetime.utcnow(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    WebhookDispatcher.dispatch_event(
        event_type="task.created",
        workspace_id=ctx.workspace_id,
        organization_id=ctx.organization_id,
        data={"id": task.id, "title": task.title, "priority": task.priority},
        db=db,
    )

    return {"id": task.id, "title": task.title, "status": task.status, "priority": task.priority}


@router.patch("/tasks/{task_id}", summary="Update task")
def update_task(
    task_id: int,
    payload: PublicTaskUpdate,
    ctx: APIKeyContext = Depends(require_scope("tasks:write")),
    db: Session = Depends(get_db),
):
    task = db.query(TaskRecord).filter(TaskRecord.id == task_id, TaskRecord.workspace_id == ctx.workspace_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found in this workspace")

    was_completed = task.status == "completed"
    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.status is not None:
        task.status = payload.status
    if payload.priority is not None:
        task.priority = payload.priority
    db.commit()
    db.refresh(task)

    if task.status == "completed" and not was_completed:
        WebhookDispatcher.dispatch_event(
            event_type="task.completed",
            workspace_id=ctx.workspace_id,
            organization_id=ctx.organization_id,
            data={"id": task.id, "title": task.title},
            db=db,
        )

    return {"id": task.id, "title": task.title, "status": task.status, "priority": task.priority}


# ── Activities Endpoints ──────────────────────────────────────────────────────

@router.get("/activities", summary="List activities (paginated)")
def list_activities(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    contact_id: Optional[int] = None,
    ctx: APIKeyContext = Depends(require_scope("activities:read")),
    db: Session = Depends(get_db),
):
    query = db.query(Activity).filter(Activity.workspace_id == ctx.workspace_id)
    if contact_id:
        query = query.filter(Activity.contact_id == contact_id)
    total = query.count()
    activities = query.order_by(Activity.id.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": a.id,
                "type": a.type,
                "title": a.title,
                "description": a.description,
                "contact_id": a.contact_id,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in activities
        ],
    }


@router.post("/activities", status_code=status.HTTP_201_CREATED, summary="Create activity")
def create_activity(
    payload: PublicActivityCreate,
    ctx: APIKeyContext = Depends(require_scope("activities:write")),
    db: Session = Depends(get_db),
):
    activity = Activity(
        workspace_id=ctx.workspace_id,
        user_id=None,
        contact_id=payload.contact_id,
        type=payload.type,
        title=payload.title,
        description=payload.description or "",
        created_at=datetime.utcnow(),
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)

    return {"id": activity.id, "type": activity.type, "title": activity.title, "contact_id": activity.contact_id}


# ── Emails Endpoints ──────────────────────────────────────────────────────────

@router.get("/emails", summary="Search & read workspace email metadata")
def list_emails(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    q: Optional[str] = None,
    ctx: APIKeyContext = Depends(require_scope("emails:read")),
    db: Session = Depends(get_db),
):
    query = db.query(EmailMetadata).filter(EmailMetadata.workspace_id == ctx.workspace_id)
    if q:
        query = query.filter(
            or_(
                EmailMetadata.subject.ilike(f"%{q}%"),
                EmailMetadata.sender.ilike(f"%{q}%"),
            )
        )
    total = query.count()
    emails = query.order_by(EmailMetadata.received_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": e.id,
                "sender": e.sender,
                "recipient": e.recipient,
                "subject": e.subject,
                "classification": e.classification,
                "priority": e.priority,
                "received_at": e.received_at.isoformat() if e.received_at else None,
            }
            for e in emails
        ],
    }


# ── Workflows Endpoints ───────────────────────────────────────────────────────

@router.get("/workflows", summary="List active workflows in workspace")
def list_workflows(
    ctx: APIKeyContext = Depends(require_scope("workflows:read")),
    db: Session = Depends(get_db),
):
    workflows = (
        db.query(Workflow)
        .filter(
            Workflow.workspace_id == ctx.workspace_id,
            Workflow.organization_id == ctx.organization_id,
            Workflow.is_deleted.is_(False),
        )
        .all()
    )
    return {
        "workflows": [
            {
                "id": wf.id,
                "name": wf.name,
                "status": wf.status,
                "trigger_type": wf.trigger_type,
                "description": wf.description,
            }
            for wf in workflows
        ]
    }


@router.get("/workflows/{workflow_id}", summary="Get workflow details")
def get_workflow(
    workflow_id: int,
    ctx: APIKeyContext = Depends(require_scope("workflows:read")),
    db: Session = Depends(get_db),
):
    wf = (
        db.query(Workflow)
        .filter(
            Workflow.id == workflow_id,
            Workflow.workspace_id == ctx.workspace_id,
            Workflow.organization_id == ctx.organization_id,
            Workflow.is_deleted.is_(False),
        )
        .first()
    )
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found in this workspace")
    return {
        "id": wf.id,
        "name": wf.name,
        "status": wf.status,
        "trigger_type": wf.trigger_type,
        "description": wf.description,
        "nodes": wf.nodes,
    }


@router.post("/workflows/{workflow_id}/execute", summary="Execute an active workflow")
def execute_workflow(
    workflow_id: int,
    payload: Dict[str, Any] = {},
    ctx: APIKeyContext = Depends(require_scope("workflows:execute")),
    db: Session = Depends(get_db),
):
    wf = (
        db.query(Workflow)
        .filter(
            Workflow.id == workflow_id,
            Workflow.workspace_id == ctx.workspace_id,
            Workflow.organization_id == ctx.organization_id,
            Workflow.status == "active",
            Workflow.is_deleted.is_(False),
        )
        .first()
    )
    if not wf:
        raise HTTPException(status_code=404, detail="Active workflow not found in this workspace")

    # Create execution record
    execution = WorkflowExecution(
        workflow_id=wf.id,
        organization_id=ctx.organization_id,
        workspace_id=ctx.workspace_id,
        trigger_data=payload,
        status="pending",
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    engine = WorkflowEngine(workspace_id=ctx.workspace_id, org_id=ctx.organization_id, user=None, db=db)
    try:
        execution = engine.execute(
            workflow_id=wf.id,
            trigger_data=payload,
            execution_id=execution.id,
        )
    except Exception as exc:
        logger.warning("Workflow execution %d finished with exception: %s", execution.id, exc)

    return {
        "execution_id": execution.id,
        "workflow_id": wf.id,
        "status": execution.status,
    }


# ── Analytics Endpoints ───────────────────────────────────────────────────────

@router.get("/analytics/overview", summary="Read-only workspace analytics metrics")
def get_analytics_overview(
    ctx: APIKeyContext = Depends(require_scope("analytics:read")),
    db: Session = Depends(get_db),
):
    from auth.models import WorkspaceMember
    members = db.query(WorkspaceMember.user_id).filter(WorkspaceMember.workspace_id == ctx.workspace_id).all()
    user_ids = [m[0] for m in members] if members else []

    contacts_count = db.query(Contact).filter(Contact.workspace_id == ctx.workspace_id).count()
    deals_count = db.query(Deal).filter(Deal.workspace_id == ctx.workspace_id).count()
    open_tasks_count = db.query(TaskRecord).filter(TaskRecord.user_id.in_(user_ids), TaskRecord.status == "queued").count() if user_ids else 0
    active_workflows_count = db.query(Workflow).filter(
        Workflow.workspace_id == ctx.workspace_id,
        Workflow.status == "active",
        Workflow.is_deleted.is_(False),
    ).count()

    return {
        "workspace_id": ctx.workspace_id,
        "metrics": {
            "total_contacts": contacts_count,
            "total_deals": deals_count,
            "open_tasks": open_tasks_count,
            "active_workflows": active_workflows_count,
        },
        "generated_at": datetime.utcnow().isoformat(),
    }


# ── AI Endpoints ─────────────────────────────────────────────────────────────

@router.post("/ai/complete", summary="Controlled public AI prompt completion")
def ai_complete(
    payload: PublicAICompleteRequest,
    ctx: APIKeyContext = Depends(require_scope("ai:use")),
    db: Session = Depends(get_db),
):
    # Enforce P3 AI Quota
    quota = BillingService.check_quota(ctx.organization_id, "ai_requests", db=db)
    if not quota.allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"error": "quota_exceeded", "resource": "ai_requests", "message": "AI request quota exceeded for your plan."},
        )

    # Use Ollama provider exclusively
    from ai.providers.ollama_provider import OllamaProvider
    provider = OllamaProvider()
    response_text = provider.generate_response(
        prompt=payload.prompt,
        max_tokens=payload.max_tokens,
        temperature=payload.temperature,
    )

    # Increment P3 AI usage counter
    BillingService.increment_usage(ctx.organization_id, "ai_requests", 1, db=db)

    return {
        "completion": response_text,
        "model": provider.model_name,
        "tokens_used": len(response_text.split()),
    }

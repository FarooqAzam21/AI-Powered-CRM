from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from auth.models import User
from cache.redis_client import cache_json, get_cached_json
from database import get_db
from models.crm import Campaign, CampaignRecipient, Contact, Deal, EmailMetadata, Lead, TaskRecord

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary")
def summary(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == current_user["sub"]).first()
    workspace_id = current_user.get("workspace_id")
    key = f"analytics:summary:{user.id}:{workspace_id}"
    cached = get_cached_json(key)
    if cached:
        return cached
    workspace_id = current_user.get("workspace_id")
    hot = db.query(Lead).filter(Lead.user_id == user.id, Lead.workspace_id == workspace_id, Lead.label == "hot").count()
    data = {
        "emails": db.query(EmailMetadata).filter(EmailMetadata.user_id == user.id, EmailMetadata.workspace_id == workspace_id).count(),
        "contacts": db.query(Contact).filter(Contact.user_id == user.id, Contact.workspace_id == workspace_id).count(),
        "hot_leads": hot,
        "campaigns": db.query(Campaign).filter(Campaign.user_id == user.id, Campaign.workspace_id == workspace_id).count(),
    }
    cache_json(key, data, ttl=30)
    return data


@router.get("/engine")
def analytics_engine(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == current_user["sub"]).first()
    workspace_id = current_user.get("workspace_id")
    key = f"analytics:engine:{user.id}:{workspace_id}"
    cached = get_cached_json(key)
    if cached:
        return cached

    workspace_id = current_user.get("workspace_id")
    email_categories = [
        {"name": row[0] or "uncategorized", "value": row[1]}
        for row in db.query(EmailMetadata.ai_status, func.count(EmailMetadata.id))
        .filter(EmailMetadata.user_id == user.id, EmailMetadata.workspace_id == workspace_id)
        .group_by(EmailMetadata.ai_status)
        .all()
    ]
    lead_labels = [
        {"name": row[0] or "cold", "value": row[1]}
        for row in db.query(Lead.label, func.count(Lead.id))
        .filter(Lead.user_id == user.id, Lead.workspace_id == workspace_id)
        .group_by(Lead.label)
        .all()
    ]
    campaign_statuses = [
        {"name": row[0] or "queued", "value": row[1]}
        for row in db.query(CampaignRecipient.status, func.count(CampaignRecipient.id))
        .join(Campaign, CampaignRecipient.campaign_id == Campaign.id)
        .filter(Campaign.user_id == user.id, Campaign.workspace_id == workspace_id)
        .group_by(CampaignRecipient.status)
        .all()
    ]
    ai_activity = [
        {"name": row[0].rsplit(".", 1)[-1] if row[0] else "task", "value": row[1]}
        for row in db.query(TaskRecord.task_type, func.count(TaskRecord.id))
        .filter(TaskRecord.user_id == user.id, TaskRecord.queue == "ai")
        .group_by(TaskRecord.task_type)
        .all()
    ]
    pipeline = [
        {"name": row[0] or "lead", "count": row[1], "value": float(row[2] or 0)}
        for row in db.query(Deal.stage, func.count(Deal.id), func.sum(Deal.value))
        .filter(Deal.user_id == user.id, Deal.workspace_id == workspace_id)
        .group_by(Deal.stage)
        .all()
    ]

    data = {
        "email_categories": email_categories,
        "lead_labels": lead_labels,
        "campaign_statuses": campaign_statuses,
        "ai_activity": ai_activity,
        "pipeline": pipeline,
    }
    cache_json(key, data, ttl=60)
    return data

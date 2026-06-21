from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from auth.models import User
from config.settings import get_settings
from database import get_db
from models.crm import Campaign, CampaignRecipient
from tasks.task_router import enqueue_task

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


class CampaignCreate(BaseModel):
    name: str
    subject: str
    template: str
    recipients: list[str] = []


def _user(db, token):
    return db.query(User).filter(User.email == token["sub"]).first()


@router.get("")
def list_campaigns(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _user(db, current_user)
    return db.query(Campaign).filter(Campaign.user_id == user.id).order_by(Campaign.created_at.desc()).all()


@router.post("")
def create_campaign(data: CampaignCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _user(db, current_user)
    campaign = Campaign(
        user_id=user.id,
        name=data.name,
        subject=data.subject,
        template=data.template,
        throttle_per_minute=get_settings().campaign_send_rate_per_minute,
    )
    db.add(campaign)
    db.flush()
    for email in data.recipients:
        db.add(CampaignRecipient(campaign_id=campaign.id, email=email))
    db.commit()
    db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/start")
def start_campaign(campaign_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _user(db, current_user)
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.user_id == user.id).first()
    campaign.status = "queued"
    db.commit()
    task = enqueue_task("workers.campaign_tasks.send_campaign", "campaigns", {"campaign_id": campaign_id}, user_id=user.id)
    return {"task_id": task["id"], "status": task["status"]}

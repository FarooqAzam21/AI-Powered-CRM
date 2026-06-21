from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from auth.models import User
from cache.redis_client import cache_json, get_cached_json
from database import get_db
from models.crm import Campaign, Contact, EmailMetadata, Lead

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary")
def summary(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == current_user["sub"]).first()
    key = f"analytics:summary:{user.id}"
    cached = get_cached_json(key)
    if cached:
        return cached
    hot = db.query(Lead).filter(Lead.user_id == user.id, Lead.label == "hot").count()
    data = {
        "emails": db.query(EmailMetadata).filter(EmailMetadata.user_id == user.id).count(),
        "contacts": db.query(Contact).filter(Contact.user_id == user.id).count(),
        "hot_leads": hot,
        "campaigns": db.query(Campaign).filter(Campaign.user_id == user.id).count(),
    }
    cache_json(key, data, ttl=30)
    return data

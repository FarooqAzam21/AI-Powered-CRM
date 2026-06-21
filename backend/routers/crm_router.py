from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from auth.models import User
from database import get_db
from models.crm import Activity, AIInsight, Contact, CustomerProfile, Deal, Interaction, Lead
from services.profile_service import CustomerProfileService

router = APIRouter(prefix="/crm", tags=["CRM"])


def _user(db, token):
    return db.query(User).filter(User.email == token["sub"]).first()


@router.get("/contacts")
def contacts(limit: int = 50, offset: int = 0, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _user(db, current_user)
    return db.query(Contact).filter(Contact.user_id == user.id).order_by(Contact.last_interaction_at.desc().nullslast()).offset(offset).limit(min(limit, 100)).all()


@router.get("/leads")
def leads(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _user(db, current_user)
    return db.query(Lead).filter(Lead.user_id == user.id).order_by(Lead.score.desc()).limit(50).all()


@router.get("/pipeline")
def pipeline(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _user(db, current_user)
    deals = db.query(Deal).filter(Deal.user_id == user.id).all()
    stages = {}
    for deal in deals:
        stages.setdefault(deal.stage, {"count": 0, "value": 0})
        stages[deal.stage]["count"] += 1
        stages[deal.stage]["value"] += deal.value or 0
    return [{"stage": key, **value} for key, value in stages.items()]


@router.get("/activities")
def activities(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _user(db, current_user)
    return db.query(Activity).filter(Activity.user_id == user.id).order_by(Activity.created_at.desc()).limit(50).all()


@router.get("/contacts/{contact_id}/interactions")
def contact_interactions(contact_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _user(db, current_user)
    contact = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == user.id).first()
    if not contact:
        raise HTTPException(404, "Contact not found")
    return (
        db.query(Interaction)
        .filter(Interaction.user_id == user.id, Interaction.contact_id == contact_id)
        .order_by(Interaction.occurred_at.desc())
        .limit(100)
        .all()
    )


@router.get("/contacts/{contact_id}/profile")
def contact_profile(contact_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _user(db, current_user)
    contact = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == user.id).first()
    if not contact:
        raise HTTPException(404, "Contact not found")
    profile = db.query(CustomerProfile).filter(CustomerProfile.contact_id == contact_id).first()
    if not profile:
        profile = CustomerProfileService.generate_profile(db, contact_id)
    return profile


@router.post("/contacts/{contact_id}/profile/refresh")
def refresh_contact_profile(contact_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _user(db, current_user)
    contact = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == user.id).first()
    if not contact:
        raise HTTPException(404, "Contact not found")
    profile = CustomerProfileService.generate_profile(db, contact_id, use_cache=False)
    if not profile:
        raise HTTPException(500, "Profile generation failed")
    return profile


@router.get("/insights")
def insights(limit: int = 50, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _user(db, current_user)
    limit = min(max(limit, 1), 100)
    return db.query(AIInsight).filter(AIInsight.user_id == user.id).order_by(AIInsight.created_at.desc()).limit(limit).all()

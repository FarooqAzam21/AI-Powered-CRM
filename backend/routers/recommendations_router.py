"""AI recommendation endpoints — Phase 6."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user_model
from auth.models import User
from database import get_db
from services.recommendation_service import RecommendationEngine

router = APIRouter(prefix="/api/v1/recommendations", tags=["Recommendations"])


@router.get("")
def list_recommendations(
    limit: int = 10,
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db),
):
    return RecommendationEngine.get_active_recommendations(db, current_user.id, limit=limit)


@router.post("/contacts/{contact_id}/generate")
def generate_for_contact(
    contact_id: int,
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db),
):
    recs = RecommendationEngine.generate_contact_recommendations(db, current_user.id, contact_id)
    if not recs:
        raise HTTPException(404, "Contact not found or no recommendations generated")
    return {"count": len(recs), "recommendations": [{"id": r.id, "title": r.title, "description": r.description, "type": r.recommendation_type} for r in recs]}


@router.post("/{recommendation_id}/action")
def mark_actioned(
    recommendation_id: int,
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db),
):
    ok = RecommendationEngine.mark_recommendation_actioned(db, recommendation_id)
    if not ok:
        raise HTTPException(404, "Recommendation not found")
    return {"status": "actioned"}

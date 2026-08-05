"""
Deal Pipeline Router - Phase 6
REST API endpoints for deal management
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from auth.dependencies import get_current_user_model
from auth.models import User
from models.crm import Deal
from database import SessionLocal
from services.deal_service import DealService
from services.activity_service import ActivityTimelineService
from services.profile_service import CustomerProfileService
from services.recommendation_service import RecommendationEngine
from services.webhook_service import trigger_webhook_event
from typing import List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Pydantic models
class DealCreate(BaseModel):
    name: str
    contact_id: Optional[int] = None
    value: float
    stage: str = "prospecting"
    expected_close_date: Optional[datetime] = None

class DealUpdate(BaseModel):
    name: Optional[str] = None
    value: Optional[float] = None
    stage: Optional[str] = None
    probability: Optional[float] = None
    expected_close_date: Optional[datetime] = None

class DealResponse(BaseModel):
    id: int
    name: str
    value: float
    stage: str
    status: str
    probability: float
    expected_close_date: Optional[datetime]
    actual_close_date: Optional[datetime]
    ai_recommendation: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class DealDetailResponse(DealResponse):
    contact_id: Optional[int]
    ai_score: float
    activities: list

class PipelineSummaryResponse(BaseModel):
    total_deals: int
    total_pipeline_value: float
    avg_deal_value: float
    weighted_forecast: float
    by_stage: dict
    by_status: dict

# Router
router = APIRouter(prefix="/api/v1/deals", tags=["Deals"])

@router.post("/", response_model=DealResponse)
async def create_deal(
    deal: DealCreate,
    current_user: User = Depends(get_current_user_model)
):
    """Create a new deal"""
    try:
        db = SessionLocal()
        new_deal = DealService.create_deal(
            db=db,
            user_id=current_user.id,
            contact_id=deal.contact_id,
            name=deal.name,
            value=deal.value,
            stage=deal.stage,
            expected_close=deal.expected_close_date,
            workspace_id=current_user.workspace_id
        )
        
        # Record activity
        ActivityTimelineService.record_activity(
            db=db,
            user_id=current_user.id,
            contact_id=deal.contact_id,
            activity_type="deal_created",
            subject=f"Deal Created: {deal.name}",
            description=f"New deal: ${deal.value}"
        )
        
        # Fire webhook event
        if hasattr(current_user, 'workspace_id') and current_user.workspace_id:
            trigger_webhook_event(db, current_user.workspace_id, "deal.created", {
                "id": new_deal.id, "name": new_deal.name,
                "value": new_deal.value, "stage": new_deal.stage
            })
        
        db.close()
        return new_deal
        
    except Exception as e:
        logger.error(f"❌ Deal creation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[DealResponse])
async def list_deals(
    status: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user_model)
):
    """List deals for current user"""
    try:
        db = SessionLocal()
        deals = DealService.get_user_deals(
            db=db,
            user_id=current_user.id,
            workspace_id=current_user.workspace_id,
            status=status,
            stage=stage,
            limit=limit
        )
        db.close()
        return deals
        
    except Exception as e:
        logger.error(f"❌ Deals retrieval failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/pipeline/summary", response_model=PipelineSummaryResponse)
async def get_pipeline_summary(
    current_user: User = Depends(get_current_user_model)
):
    """Get pipeline summary with stats"""
    try:
        db = SessionLocal()
        summary = DealService.get_pipeline_summary(db=db, user_id=current_user.id, workspace_id=current_user.workspace_id)
        db.close()
        return summary
        
    except Exception as e:
        logger.error(f"❌ Pipeline summary failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{deal_id}", response_model=DealDetailResponse)
async def get_deal(
    deal_id: int,
    current_user: User = Depends(get_current_user_model)
):
    """Get single deal details"""
    try:
        db = SessionLocal()
        deal = db.query(Deal).filter(Deal.id == deal_id, Deal.workspace_id == current_user.workspace_id).first()
        
        if not deal or deal.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        # Get activities
        activities = ActivityTimelineService.get_deal_activity_timeline(db=db, deal_id=deal_id)
        
        db.close()
        return {**deal.__dict__, "activities": activities}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Deal retrieval failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{deal_id}", response_model=DealResponse)
async def update_deal(
    deal_id: int,
    deal_update: DealUpdate,
    current_user: User = Depends(get_current_user_model)
):
    """Update deal details"""
    try:
        db = SessionLocal()
        deal = db.query(Deal).filter(Deal.id == deal_id, Deal.workspace_id == current_user.workspace_id).first()
        
        if not deal or deal.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        # Update fields
        if deal_update.name:
            deal.name = deal_update.name
        if deal_update.value:
            old_value = deal.value
            deal.value = deal_update.value
            ActivityTimelineService.record_activity(
                db=db,
                user_id=current_user.id,
                contact_id=deal.contact_id,
                activity_type="deal_updated",
                description=f"Value changed: ${old_value} → ${deal_update.value}"
            )
        if deal_update.stage:
            deal = DealService.move_deal_stage(db=db, deal_id=deal_id, new_stage=deal_update.stage)
        if deal_update.probability:
            deal.probability = deal_update.probability
        if deal_update.expected_close_date:
            deal.expected_close_date = deal_update.expected_close_date
        
        deal.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(deal)
        
        # Fire webhook event
        if hasattr(current_user, 'workspace_id') and current_user.workspace_id:
            trigger_webhook_event(db, current_user.workspace_id, "deal.updated", {
                "id": deal.id, "name": deal.name,
                "value": deal.value, "stage": deal.stage
            })
        
        db.close()
        return deal
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Deal update failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{deal_id}/close")
async def close_deal(
    deal_id: int,
    won: bool = Query(True),
    reason: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user_model)
):
    """Close deal as won or lost"""
    try:
        db = SessionLocal()
        deal = db.query(Deal).filter(Deal.id == deal_id, Deal.workspace_id == current_user.workspace_id).first()
        
        if not deal or deal.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        stage = "won" if won else "lost"
        deal = DealService.move_deal_stage(db=db, deal_id=deal_id, new_stage=stage)
        
        if reason:
            deal.close_reason = reason
        
        # Fire webhook event
        event_name = "deal.won" if won else "deal.lost"
        if hasattr(current_user, 'workspace_id') and current_user.workspace_id:
            trigger_webhook_event(db, current_user.workspace_id, event_name, {
                "id": deal_id, "stage": stage, "reason": reason or ""
            })
        
        db.commit()
        db.close()
        
        return {"message": f"Deal marked as {stage}", "deal_id": deal_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Deal close failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/overdue/list")
async def get_overdue_deals(
    current_user: User = Depends(get_current_user_model)
):
    """Get overdue deals"""
    try:
        db = SessionLocal()
        deals = DealService.get_overdue_deals(db=db, user_id=current_user.id, workspace_id=current_user.workspace_id)
        
        result = []
        for deal in deals:
            days_overdue = (datetime.utcnow() - deal.expected_close_date).days
            result.append({
                "id": deal.id,
                "name": deal.name,
                "value": deal.value,
                "stage": deal.stage,
                "expected_close": deal.expected_close_date,
                "days_overdue": days_overdue
            })
        
        db.close()
        return result
        
    except Exception as e:
        logger.error(f"❌ Overdue deals retrieval failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{deal_id}/activity")
async def add_deal_activity(
    deal_id: int,
    activity_type: str,
    description: str,
    value_impact: float = 0,
    probability_impact: float = 0,
    current_user: User = Depends(get_current_user_model)
):
    """Add activity to deal"""
    try:
        db = SessionLocal()
        deal = db.query(Deal).filter(Deal.id == deal_id, Deal.workspace_id == current_user.workspace_id).first()
        
        if not deal or deal.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        activity = DealService.add_activity(
            db=db,
            deal_id=deal_id,
            activity_type=activity_type,
            description=description,
            value_impact=value_impact,
            probability_impact=probability_impact
        )
        
        db.close()
        return {
            "id": activity.id,
            "activity_type": activity.activity_type,
            "description": activity.description,
            "created_at": activity.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Activity creation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/forecast/revenue")
async def get_revenue_forecast(
    current_user: User = Depends(get_current_user_model)
):
    """Get revenue forecast based on deal pipeline"""
    try:
        db = SessionLocal()
        summary = DealService.get_pipeline_summary(db=db, user_id=current_user.id, workspace_id=current_user.workspace_id)
        
        forecast = {
            "total_pipeline": summary.get("total_pipeline_value", 0),
            "weighted_forecast": summary.get("weighted_forecast", 0),
            "by_stage": {
                stage: details.get("value", 0) * details.get("avg_probability", 0) / 100
                for stage, details in summary.get("by_stage", {}).items()
            }
        }
        
        db.close()
        return forecast
        
    except Exception as e:
        logger.error(f"❌ Forecast generation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

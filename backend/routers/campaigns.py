"""
Campaign Router - Phase 9
REST API endpoints for bulk email campaigns
"""
import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from auth.dependencies import get_current_user_model
from auth.models import User
from database import SessionLocal
from models.campaigns import Campaign, CampaignSend, CampaignStatus, EmailStatus
from schemas.campaigns import (
    CampaignCreate, CampaignUpdate, CampaignResponse, CampaignListResponse,
    CampaignStart, BulkSendRequest, BulkRetryRequest, CampaignSendResponse
)
from services.campaign_service import CampaignService
from services.webhook_service import trigger_webhook_event
from scheduler.campaign_scheduler import scheduler
from tasks.campaign_tasks import bulk_send_campaign, retry_failed_sends, update_campaign_analytics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/campaigns", tags=["Campaigns"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =================== CRUD ENDPOINTS ===================

@router.post("", response_model=CampaignResponse)
async def create_campaign(
    data: CampaignCreate,
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Create new campaign"""
    try:
        campaign = CampaignService.create_campaign(
            db,
            current_user.id,
            data.model_dump(),
            workspace_id=current_user.workspace_id,
        )
        return campaign
    except Exception as e:
        logger.error(f"❌ Campaign creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=List[CampaignListResponse])
async def list_campaigns(
    status: Optional[CampaignStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """List campaigns"""
    try:
        query = db.query(Campaign).filter(
            Campaign.user_id == current_user.id,
            Campaign.workspace_id == current_user.workspace_id,
        )
        
        if status:
            query = query.filter(Campaign.status == status)
        
        campaigns = query.order_by(
            Campaign.created_at.desc()
        ).offset(skip).limit(limit).all()
        
        return campaigns
    except Exception as e:
        logger.error(f"❌ Campaign list failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get campaign details"""
    try:
        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == current_user.id,
            Campaign.workspace_id == current_user.workspace_id,
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        return campaign
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get campaign failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    data: CampaignUpdate,
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Update campaign (only draft campaigns)"""
    try:
        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == current_user.id,
            Campaign.workspace_id == current_user.workspace_id,
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign.status != CampaignStatus.DRAFT:
            raise HTTPException(status_code=400, detail="Can only edit draft campaigns")
        
        # Update fields
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(campaign, field, value)
        
        db.commit()
        db.refresh(campaign)
        
        logger.info(f"✅ Campaign {campaign_id} updated")
        return campaign
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Campaign update failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Delete campaign (only draft campaigns)"""
    try:
        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == current_user.id,
            Campaign.workspace_id == current_user.workspace_id,
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign.status != CampaignStatus.DRAFT:
            raise HTTPException(status_code=400, detail="Can only delete draft campaigns")
        
        db.delete(campaign)
        db.commit()
        
        logger.info(f"✅ Campaign {campaign_id} deleted")
        return {"status": "success", "message": "Campaign deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Campaign deletion failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# =================== CAMPAIGN ACTIONS ===================

@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: int,
    data: CampaignStart,
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Start campaign sending"""
    try:
        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == current_user.id,
            Campaign.workspace_id == current_user.workspace_id,
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign.status != CampaignStatus.DRAFT:
            raise HTTPException(status_code=400, detail="Can only start draft campaigns")
        
        # Schedule or start immediately
        if data.scheduled_at:
            campaign.scheduled_at = data.scheduled_at
            campaign.status = CampaignStatus.SCHEDULED
        else:
            campaign.status = CampaignStatus.RUNNING
            campaign.started_at = datetime.utcnow()
        
        db.commit()
        
        # Queue bulk send task
        bulk_send_campaign.delay(campaign_id)
        
        # Fire webhook event for external integrations
        if hasattr(current_user, 'workspace_id') and current_user.workspace_id:
            trigger_webhook_event(db, current_user.workspace_id, "campaign.started", {
                "id": campaign_id, "name": campaign.name,
                "status": campaign.status.value if hasattr(campaign.status, 'value') else str(campaign.status)
            })
        
        logger.info(f"🚀 Campaign {campaign_id} started")
        return {
            "status": "started",
            "campaign_id": campaign_id,
            "campaign_name": campaign.name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Campaign start failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Pause campaign sending"""
    try:
        if scheduler.pause_campaign(campaign_id):
            return {"status": "paused", "campaign_id": campaign_id}
        else:
            raise HTTPException(status_code=404, detail="Campaign not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Campaign pause failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Resume campaign sending"""
    try:
        if scheduler.resume_campaign(campaign_id):
            return {"status": "resumed", "campaign_id": campaign_id}
        else:
            raise HTTPException(status_code=404, detail="Campaign not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Campaign resume failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== ANALYTICS & MONITORING ===================

@router.get("/{campaign_id}/analytics")
async def get_campaign_analytics(
    campaign_id: int,
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get campaign analytics"""
    try:
        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        analytics = CampaignService.get_campaign_analytics(db, campaign_id)
        return analytics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Analytics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{campaign_id}/progress")
async def get_campaign_progress(
    campaign_id: int,
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get campaign sending progress"""
    try:
        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        progress = scheduler.get_campaign_progress(campaign_id)
        return progress
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Progress retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{campaign_id}/sends")
async def list_campaign_sends(
    campaign_id: int,
    status: Optional[EmailStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """List individual sends for campaign"""
    try:
        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        query = db.query(CampaignSend).filter(CampaignSend.campaign_id == campaign_id)
        
        if status:
            query = query.filter(CampaignSend.status == status)
        
        sends = query.order_by(CampaignSend.created_at.desc()).offset(skip).limit(limit).all()
        
        return sends
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Sends list failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== RETRY & MAINTENANCE ===================

@router.post("/{campaign_id}/retry-failed")
async def retry_failed(
    campaign_id: int,
    data: BulkRetryRequest,
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Retry failed sends for campaign"""
    try:
        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == current_user.id
        ).first()
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Queue retry task
        retry_failed_sends.delay(campaign_id)
        
        return {
            "status": "retrying",
            "campaign_id": campaign_id,
            "message": "Retry process started"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Retry failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== TRACKING ENDPOINTS (NO AUTH) ===================

@router.get("/track/{tracking_id}/open")
async def track_open(
    tracking_id: str,
    db: Session = Depends(get_db)
):
    """Track email open (called via pixel)"""
    try:
        from tasks.campaign_tasks import process_open_tracking
        
        # Queue tracking task (async)
        process_open_tracking.delay(tracking_id)
        
        # Return 1x1 pixel
        return {"status": "tracked"}
    except Exception as e:
        logger.warning(f"⚠️ Open tracking error: {e}")
        return {"status": "error"}

@router.get("/track/{tracking_id}/click")
async def track_click(
    tracking_id: str,
    url: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Track email click (called via link)"""
    try:
        from tasks.campaign_tasks import process_click_tracking
        
        # Queue tracking task (async)
        process_click_tracking.delay(tracking_id, url)
        
        # Redirect to original URL or default
        if url:
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=url)
        
        return {"status": "tracked"}
    except Exception as e:
        logger.warning(f"⚠️ Click tracking error: {e}")
        return {"status": "error"}

logger.info("✅ Campaign router loaded successfully")

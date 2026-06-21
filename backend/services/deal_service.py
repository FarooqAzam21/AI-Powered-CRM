"""
Deal Pipeline Service - Phase 6
Manages sales deals, pipeline stages, and deal tracking
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from auth.models import User
from models.crm import Contact, Deal, DealActivity
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

class DealService:
    """Service for deal management and pipeline tracking"""
    
    # Pipeline stages
    STAGES = [
        "prospecting",
        "qualification",
        "proposal",
        "negotiation",
        "won",
        "lost"
    ]
    
    @staticmethod
    def create_deal(db: Session, user_id: int, contact_id: Optional[int], 
                   name: str, value: float, stage: str = "prospecting", 
                   expected_close: Optional[datetime] = None) -> Deal:
        """Create new deal"""
        try:
            deal = Deal(
                user_id=user_id,
                contact_id=contact_id,
                title=name,
                value=value,
                stage=stage,
                expected_close_at=expected_close or datetime.utcnow() + timedelta(days=30),
                probability=DealService._calculate_stage_probability(stage),
            )
            db.add(deal)
            db.commit()
            db.refresh(deal)
            logger.info(f"✅ Deal created: {deal.title} (${deal.value})")
            return deal
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Deal creation failed: {e}")
            raise
    
    @staticmethod
    def move_deal_stage(db: Session, deal_id: int, new_stage: str, 
                       probability_change: float = 0) -> Deal:
        """Move deal to new pipeline stage"""
        try:
            deal = db.query(Deal).filter(Deal.id == deal_id).first()
            if not deal:
                raise ValueError("Deal not found")
            
            old_stage = deal.stage
            deal.stage = new_stage
            deal.stage_moved_at = datetime.utcnow()
            
            # Auto-update probability based on stage
            if new_stage == "won":
                deal.status = "won"
                deal.probability = 100
                deal.actual_close_at = datetime.utcnow()
            elif new_stage == "lost":
                deal.status = "lost"
                deal.probability = 0
                deal.actual_close_at = datetime.utcnow()
            else:
                deal.probability = DealService._calculate_stage_probability(new_stage)
            
            db.commit()
            logger.info(f"📊 Deal moved: {old_stage} → {new_stage}")
            
            # Record activity
            DealService.add_activity(db, deal_id, "stage_change", 
                                    f"Moved from {old_stage} to {new_stage}")
            
            return deal
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Stage move failed: {e}")
            raise
    
    @staticmethod
    def update_deal_value(db: Session, deal_id: int, new_value: float) -> Deal:
        """Update deal value"""
        try:
            deal = db.query(Deal).filter(Deal.id == deal_id).first()
            if not deal:
                raise ValueError("Deal not found")
            
            old_value = deal.value
            deal.value = new_value
            deal.updated_at = datetime.utcnow()
            
            db.commit()
            logger.info(f"💰 Deal value updated: ${old_value} → ${new_value}")
            
            return deal
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Value update failed: {e}")
            raise
    
    @staticmethod
    def add_activity(db: Session, deal_id: int, activity_type: str, 
                    description: str, value_impact: float = 0,
                    probability_impact: float = 0) -> DealActivity:
        """Add activity to deal"""
        try:
            activity = DealActivity(
                deal_id=deal_id,
                activity_type=activity_type,
                description=description,
                value_impact=value_impact,
                probability_impact=probability_impact
            )
            db.add(activity)
            
            # Update deal if there's an impact
            deal = db.query(Deal).filter(Deal.id == deal_id).first()
            if deal:
                if value_impact != 0:
                    deal.value += value_impact
                if probability_impact != 0:
                    deal.probability = min(100, max(0, deal.probability + probability_impact))
            
            db.commit()
            logger.debug(f"📝 Activity added: {activity_type}")
            return activity
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Activity add failed: {e}")
            raise
    
    @staticmethod
    def get_user_deals(db: Session, user_id: int, status: Optional[str] = None,
                      stage: Optional[str] = None, limit: int = 50) -> List[Deal]:
        """Get all deals for user with optional filtering"""
        try:
            query = db.query(Deal).filter(Deal.user_id == user_id)
            
            if status:
                query = query.filter(Deal.status == status)
            if stage:
                query = query.filter(Deal.stage == stage)
            
            deals = query.order_by(Deal.updated_at.desc()).limit(limit).all()
            logger.debug(f"📋 Retrieved {len(deals)} deals")
            return deals
        except Exception as e:
            logger.error(f"❌ Deals retrieval failed: {e}")
            return []
    
    @staticmethod
    def get_pipeline_summary(db: Session, user_id: int) -> Dict:
        """Get pipeline summary stats"""
        try:
            deals = db.query(Deal).filter(Deal.user_id == user_id).all()
            
            summary = {
                "total_deals": len(deals),
                "total_pipeline_value": sum(d.value for d in deals if d.status == "open"),
                "by_stage": {},
                "by_status": {},
                "avg_deal_value": 0,
                "weighted_forecast": 0  # Value × Probability
            }
            
            # Group by stage
            for stage in DealService.STAGES:
                stage_deals = [d for d in deals if d.stage == stage]
                summary["by_stage"][stage] = {
                    "count": len(stage_deals),
                    "value": sum(d.value for d in stage_deals),
                    "avg_probability": sum(d.probability for d in stage_deals) / len(stage_deals) if stage_deals else 0
                }
            
            # Group by status
            for status in ["open", "won", "lost"]:
                status_deals = [d for d in deals if d.status == status]
                summary["by_status"][status] = {
                    "count": len(status_deals),
                    "value": sum(d.value for d in status_deals)
                }
            
            # Calculate metrics
            if deals:
                open_deals = [d for d in deals if d.status == "open"]
                summary["avg_deal_value"] = summary["total_pipeline_value"] / len(open_deals) if open_deals else 0
                summary["weighted_forecast"] = sum(d.value * d.probability / 100 for d in open_deals)
            
            logger.info(f"📊 Pipeline: ${summary['total_pipeline_value']} ({len(deals)} deals)")
            return summary
        except Exception as e:
            logger.error(f"❌ Pipeline summary failed: {e}")
            return {}
    
    @staticmethod
    def get_overdue_deals(db: Session, user_id: int) -> List[Deal]:
        """Get deals with overdue expected close dates"""
        try:
            deals = db.query(Deal).filter(
                and_(
                    Deal.user_id == user_id,
                    Deal.status == "open",
                    Deal.expected_close_at < datetime.utcnow()
                )
            ).all()
            
            logger.debug(f"⚠️  Found {len(deals)} overdue deals")
            return deals
        except Exception as e:
            logger.error(f"❌ Overdue deals check failed: {e}")
            return []
    
    @staticmethod
    def _calculate_stage_probability(stage: str) -> float:
        """Calculate default probability for stage"""
        stage_probabilities = {
            "prospecting": 10,
            "qualification": 25,
            "proposal": 50,
            "negotiation": 75,
            "won": 100,
            "lost": 0
        }
        return stage_probabilities.get(stage, 0)
    
    @staticmethod
    def bulk_import_deals(db: Session, user_id: int, deals_data: List[Dict]) -> int:
        """Bulk import deals from data"""
        try:
            count = 0
            for deal_data in deals_data:
                deal = Deal(
                    user_id=user_id,
                    contact_id=deal_data.get("contact_id"),
                    title=deal_data.get("name"),
                    value=deal_data.get("value", 0),
                    stage=deal_data.get("stage", "prospecting"),
                    expected_close_at=deal_data.get("expected_close_date")
                    or datetime.utcnow() + timedelta(days=30),
                )
                db.add(deal)
                count += 1
            
            db.commit()
            logger.info(f"✅ Imported {count} deals")
            return count
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Bulk import failed: {e}")
            return 0

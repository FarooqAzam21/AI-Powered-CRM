"""
Territory Optimization Service - Phase 7
Tracks territory-level KPIs and identifies optimization opportunities
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from auth.models import TerritoryMetrics
from models.crm import Deal, Contact, Activity
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

class TerritoryService:
    """Service for territory management and optimization"""
    
    @staticmethod
    def create_territory_metrics(db: Session, user_id: int, territory_name: str,
                                territory_type: str = "geographic") -> Optional[TerritoryMetrics]:
        """
        Create or update territory metrics
        """
        try:
            logger.info(f"📊 Calculating metrics for territory: {territory_name}")
            
            # Get deals for territory
            deals = db.query(Deal).filter(
                and_(
                    Deal.user_id == user_id,
                    Deal.territory == territory_name if hasattr(Deal, 'territory') else True
                )
            ).all()
            
            # Calculate metrics
            open_deals = [d for d in deals if d.status == "open"]
            won_deals = [d for d in deals if d.status == "won"]
            lost_deals = [d for d in deals if d.status == "lost"]
            
            # Revenue metrics
            pipeline_value = sum(d.value for d in open_deals)
            won_revenue = sum(d.value for d in won_deals)
            
            # Contact metrics
            contacts = db.query(Contact).filter(Contact.user_id == user_id).all()
            active_contacts = len([c for c in contacts if 
                db.query(Activity).filter(
                    and_(
                        Activity.contact_id == c.id,
                        Activity.created_at >= datetime.utcnow() - timedelta(days=30)
                    )
                ).first()])
            
            # Calculate KPIs
            win_rate = (len(won_deals) / len(deals) * 100) if deals else 0
            avg_cycle = sum((d.actual_close_date - d.created_at).days 
                          for d in won_deals if d.actual_close_date and d.created_at) / len(won_deals) if won_deals else 0
            
            quota_attainment = (won_revenue / 100000) * 100 if won_revenue > 0 else 0  # Assuming $100k quota
            avg_deal_size = sum(d.value for d in deals) / len(deals) if deals else 0
            
            # Opportunity and risk scores
            opportunity_score = TerritoryService._calculate_opportunity_score(deals)
            risk_score = TerritoryService._calculate_risk_score(deals, active_contacts)
            
            # Trend analysis
            period_start = datetime.utcnow() - timedelta(days=30)
            prev_deals = [d for d in deals if d.created_at and d.created_at >= period_start]
            growth_rate = (len(prev_deals) / max(len(deals) - len(prev_deals), 1) * 100) if len(deals) > len(prev_deals) else 0
            
            metrics = TerritoryMetrics(
                user_id=user_id,
                territory_name=territory_name,
                territory_type=territory_type,
                revenue_target=100000,  # Default target
                revenue_actual=won_revenue,
                revenue_variance_pct=(won_revenue - 100000) / 100000 * 100,
                total_contacts=len(contacts),
                active_contacts=active_contacts,
                engaged_pct=(active_contacts / len(contacts) * 100) if contacts else 0,
                pipeline_value=pipeline_value,
                avg_deal_size=avg_deal_size,
                deal_count=len(deals),
                win_rate_pct=win_rate,
                avg_sales_cycle_days=avg_cycle,
                quota_attainment_pct=quota_attainment,
                growth_rate_pct=growth_rate,
                opportunity_score=opportunity_score,
                risk_score=risk_score,
                period_start=datetime.utcnow().replace(day=1),
                period_end=datetime.utcnow()
            )
            
            db.add(metrics)
            db.commit()
            db.refresh(metrics)
            
            logger.info(f"✅ Territory metrics saved: {win_rate:.1f}% win rate, ${pipeline_value:.2f} pipeline")
            return metrics
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Territory metrics creation failed: {e}")
            return None
    
    @staticmethod
    def _calculate_opportunity_score(deals: List[Deal]) -> float:
        """
        Calculate territory opportunity score (0-100)
        Based on pipeline value, deal size, and conversion trends
        """
        if not deals:
            return 0
        
        score = 0
        
        # Pipeline size (0-30 points)
        pipeline_value = sum(d.value for d in [d for d in deals if d.status == "open"])
        if pipeline_value > 500000:
            score += 30
        elif pipeline_value > 250000:
            score += 20
        elif pipeline_value > 100000:
            score += 10
        
        # Deal size (0-20 points)
        avg_deal = sum(d.value for d in deals) / len(deals)
        if avg_deal > 50000:
            score += 20
        elif avg_deal > 25000:
            score += 10
        
        # Growth momentum (0-20 points)
        recent = [d for d in deals if d.created_at and d.created_at >= datetime.utcnow() - timedelta(days=30)]
        if len(recent) > len(deals) * 0.2:  # 20% of deals recent
            score += 20
        elif len(recent) > len(deals) * 0.1:
            score += 10
        
        # Win rate (0-30 points)
        won = len([d for d in deals if d.status == "won"])
        win_rate = won / len(deals) if deals else 0
        if win_rate > 0.5:
            score += 30
        elif win_rate > 0.3:
            score += 20
        elif win_rate > 0.1:
            score += 10
        
        return min(score, 100)
    
    @staticmethod
    def _calculate_risk_score(deals: List[Deal], active_contacts: int) -> float:
        """
        Calculate territory risk score (0-100)
        Higher = more risk
        """
        score = 0
        
        # Stalled deals (0-40 points)
        stalled = [d for d in deals if d.status == "open" and 
                  (datetime.utcnow() - d.stage_moved_at).days > 30 if d.stage_moved_at]
        if len(stalled) > len(deals) * 0.3:
            score += 40
        elif len(stalled) > len(deals) * 0.1:
            score += 20
        
        # Low engagement (0-30 points)
        if active_contacts < 5:
            score += 30
        elif active_contacts < 10:
            score += 15
        
        # Losing trend (0-30 points)
        recent_lost = [d for d in deals if d.status == "lost" and 
                      d.actual_close_date and d.actual_close_date >= datetime.utcnow() - timedelta(days=30)]
        if len(recent_lost) > 3:
            score += 30
        elif len(recent_lost) > 1:
            score += 15
        
        return min(score, 100)
    
    @staticmethod
    def get_territory_comparison(db: Session, user_id: int) -> Dict:
        """Compare all territories for a user"""
        try:
            metrics = db.query(TerritoryMetrics).filter(
                TerritoryMetrics.user_id == user_id
            ).all()
            
            comparison = {
                "territories": len(metrics),
                "total_pipeline": sum(m.pipeline_value for m in metrics),
                "total_revenue": sum(m.revenue_actual for m in metrics),
                "avg_win_rate": sum(m.win_rate_pct for m in metrics) / len(metrics) if metrics else 0,
                "top_performers": [],
                "at_risk": [],
                "opportunities": []
            }
            
            # Sort by win rate
            sorted_metrics = sorted(metrics, key=lambda m: m.win_rate_pct, reverse=True)
            comparison["top_performers"] = [m.territory_name for m in sorted_metrics[:3]]
            
            # Find at-risk territories
            at_risk_territories = [m for m in metrics if m.risk_score > 60]
            comparison["at_risk"] = [(m.territory_name, m.risk_score) for m in at_risk_territories]
            
            # Find opportunities
            opportunity_territories = [m for m in metrics if m.opportunity_score > 70]
            comparison["opportunities"] = [(m.territory_name, m.opportunity_score) for m in opportunity_territories]
            
            logger.debug(f"📊 Territory comparison: {len(metrics)} territories")
            return comparison
            
        except Exception as e:
            logger.error(f"❌ Territory comparison failed: {e}")
            return {}
    
    @staticmethod
    def get_optimization_recommendations(db: Session, user_id: int) -> Dict:
        """Generate optimization recommendations for territories"""
        try:
            metrics = db.query(TerritoryMetrics).filter(
                TerritoryMetrics.user_id == user_id
            ).all()
            
            recommendations = {
                "reallocate_resources": [],
                "increase_focus": [],
                "reduce_effort": [],
                "merge_territories": []
            }
            
            # Identify low performers
            low_performers = [m for m in metrics if m.win_rate_pct < 20]
            if low_performers:
                recommendations["reduce_effort"] = [m.territory_name for m in low_performers]
            
            # Identify high performers
            high_performers = [m for m in metrics if m.win_rate_pct > 50]
            if high_performers:
                recommendations["increase_focus"] = [m.territory_name for m in high_performers]
            
            # Identify small territories that could merge
            small_territories = [m for m in metrics if m.pipeline_value < 50000]
            if len(small_territories) > 1:
                recommendations["merge_territories"] = [m.territory_name for m in small_territories]
            
            logger.debug(f"📊 Optimization recommendations: {len(recommendations)} categories")
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Optimization analysis failed: {e}")
            return {}
